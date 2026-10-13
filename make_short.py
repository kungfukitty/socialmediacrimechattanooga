#!/usr/bin/env python3
"""
make_short.py: turn one incident from incidents.json into a 1080x1920 vertical MP4.

The video has a dark street map centered on the call's block with a pulsing pin, the call card
(type, status, event, block, area, time), word-by-word captions, the disclaimer, and a
text-to-speech voiceover of the incident's script.

Usage:
  python make_short.py                 # render the newest incident
  python make_short.py --id 2026-10-19569
  python make_short.py --voice my_take.wav --id ...   # use your own recorded voiceover instead of TTS

Needs: pillow, imageio-ffmpeg (ships its own ffmpeg), pyttsx3 (Windows voices). Map tiles: Esri.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import wave
from datetime import datetime
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "output"
TILE_CACHE = HERE / "cache" / "tiles"
W, H, FPS = 1080, 1920, 30
PIN_X, PIN_Y = 540, 520           # where the call's block sits on screen
ZOOM, TILE_SCALE = 15, 1.5        # map zoom level and upscale of 256px tiles
BRAND = os.environ.get("CHA_BRAND", "CHA 911")
DISCLAIMER = "Based on public 9-1-1 dispatch data. Not an official statement. Details may change."
UA = "ChattanoogaSafetyFeed/0.1 (map tiles for local news video)"

NIGHT = (10, 14, 19)
INK = (241, 243, 245)
DIM = (154, 166, 178)
COLORS = {"Law": (79, 140, 255), "Fire": (255, 107, 44), "Road": (255, 194, 26), "Red": (255, 59, 78)}


# ---------------------------------------------------------------- fonts
FONT_CANDIDATES = {
    "display": ["C:/Windows/Fonts/bahnschrift.ttf", "C:/Windows/Fonts/arialbd.ttf",
                "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"],
    "bold": ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "body": ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
             "/System/Library/Fonts/Supplemental/Arial.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
    "mono": ["C:/Windows/Fonts/consola.ttf", "/System/Library/Fonts/Menlo.ttc",
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"],
}
_font_cache: dict = {}


def font(role: str, size: int) -> ImageFont.FreeTypeFont:
    key = (role, size)
    if key in _font_cache:
        return _font_cache[key]
    f = None
    for path in FONT_CANDIDATES[role]:
        if Path(path).exists():
            f = ImageFont.truetype(path, size)
            if path.endswith("bahnschrift.ttf"):
                try:
                    f.set_variation_by_name("Bold Condensed")
                except Exception:
                    pass
            break
    f = f or ImageFont.load_default(size)
    _font_cache[key] = f
    return f


def wrap(draw: ImageDraw.ImageDraw, text: str, fnt, max_w: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


# ---------------------------------------------------------------- map
def _world_px(lat: float, lng: float, z: int) -> tuple[float, float]:
    n = 256 * 2 ** z
    x = (lng + 180) / 360 * n
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n
    return x, y


def _tile(layer: str, z: int, x: int, y: int) -> Image.Image | None:
    path = TILE_CACHE / layer / str(z) / str(x) / f"{y}.png"
    if path.exists():
        try:
            return Image.open(path).convert("RGBA")
        except Exception:
            pass
    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/{layer}/MapServer/tile/{z}/{y}/{x}"
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=10)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path)
        return img
    except Exception:
        return None


def grid_background() -> Image.Image:
    img = Image.new("RGB", (W, H), NIGHT)
    d = ImageDraw.Draw(img)
    for x in range(0, W, 72):
        d.line([(x, 0), (x, H)], fill=(30, 36, 44), width=1)
    for y in range(0, H, 72):
        d.line([(0, y), (W, y)], fill=(30, 36, 44), width=1)
    return img


def map_background(lat: float | None, lng: float | None) -> tuple[Image.Image, bool]:
    """Map image W x H with (lat, lng) at (PIN_X, PIN_Y). Falls back to a grid if tiles fail."""
    if lat is None or lng is None:
        return grid_background(), False
    k = TILE_SCALE
    cw, ch = math.ceil(W / k), math.ceil(H / k)               # canvas size in tile pixels
    wx, wy = _world_px(lat, lng, ZOOM)
    left, top = wx - PIN_X / k, wy - PIN_Y / k
    tx0, ty0 = int(left // 256), int(top // 256)
    tx1, ty1 = int((left + cw) // 256), int((top + ch) // 256)
    canvas = Image.new("RGBA", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256), NIGHT + (255,))
    got = 0
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            pos = ((tx - tx0) * 256, (ty - ty0) * 256)
            base = _tile("World_Dark_Gray_Base", ZOOM, tx, ty)
            if base is None:
                continue
            got += 1
            canvas.alpha_composite(base, pos)
            ref = _tile("World_Dark_Gray_Reference", ZOOM, tx, ty)
            if ref is not None:
                canvas.alpha_composite(ref, pos)
    if got == 0:
        return grid_background(), False
    ox, oy = left - tx0 * 256, top - ty0 * 256
    crop = canvas.crop((round(ox), round(oy), round(ox) + cw, round(oy) + ch))
    img = crop.resize((W, H), Image.LANCZOS).convert("RGB")
    # brighten slightly: the dark basemap is very dark on phone screens
    return Image.eval(img, lambda v: min(255, int(v * 1.25))), True


# ---------------------------------------------------------------- voice
def tts(text: str, wav_path: Path) -> float | None:
    """Speak text into a WAV file with the system voice. Returns seconds, or None if unavailable."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 172)
        for v in engine.getProperty("voices"):
            if re.search(r"zira|aria|jenny|david|en[-_]us", f"{v.name} {v.id}", re.I):
                engine.setProperty("voice", v.id)
                break
        engine.save_to_file(text, str(wav_path))
        engine.runAndWait()
        return wav_seconds(wav_path)
    except Exception as e:
        print(f"voiceover unavailable ({e}); rendering silent video", file=sys.stderr)
        return None


def wav_seconds(path: Path) -> float | None:
    try:
        with wave.open(str(path)) as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return None


# ---------------------------------------------------------------- layout
def kind(inc: dict) -> tuple[str, tuple]:
    t = inc.get("type", "")
    if t == "Code Red":
        return "CODE RED", COLORS["Red"]
    if t == "Fire":
        return "FIRE", COLORS["Fire"]
    if t in ("Road Closure", "Traffic"):
        return "ROAD", COLORS["Road"]
    return "POLICE", COLORS["Law"]


def clock(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return ""


def static_layer(inc: dict, mapped: bool) -> tuple[Image.Image, int]:
    """Everything that doesn't move. Returns (RGBA layer, y where captions start)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    # shading: top band for the brand, heavy bottom for text
    for y in range(H):
        if y < 300:
            a = int(200 * (1 - y / 300))
        elif y > 700:
            a = int(min(245, 245 * ((y - 700) / 380)))
        else:
            a = 0
        if a:
            d.line([(0, y), (W, y)], fill=NIGHT + (a,))
    pad = 64
    maxw = W - pad - 170  # keep clear of the TikTok / Shorts button rail on the right

    # brand
    d.text((pad, 120), BRAND, font=font("display", 58), fill=INK)
    bw = d.textlength(BRAND, font=font("display", 58))
    lx = pad + bw + 22
    d.rounded_rectangle([lx, 128, lx + 118, 174], radius=6, fill=COLORS["Red"])
    d.ellipse([lx + 16, 144, lx + 30, 158], fill=(255, 255, 255))
    d.text((lx + 40, 133), "LIVE", font=font("bold", 30), fill=(255, 255, 255))

    label, color = kind(inc)
    red = inc.get("type") == "Code Red"
    # disclaimer under the brand: always visible, never covered by platform captions
    df = font("body", 27)
    dy = 196
    for line in wrap(d, DISCLAIMER, df, W - 2 * pad):
        d.text((pad, dy), line, font=df, fill=(200, 206, 212))
        dy += 34

    y = 820
    # badge + status
    bf = font("bold", 34)
    bwid = d.textlength(label, font=bf) + 36
    d.rectangle([pad, y, pad + bwid, y + 56], fill=color)
    d.text((pad + 18, y + 8), label, font=bf, fill=(255, 255, 255) if red else NIGHT)
    if not red and inc.get("status_label"):
        st = f"{inc.get('status', '')}  {inc['status_label']}"
        sx = pad + bwid + 16
        sw = d.textlength(st, font=font("bold", 30)) + 32
        d.rectangle([sx, y, sx + sw, y + 56], outline=(80, 88, 98), width=2, fill=NIGHT + (200,))
        d.text((sx + 16, y + 10), st, font=font("bold", 30), fill=INK)
    y += 84

    # headline
    hf = font("display", 100 if len(inc.get("event", "")) < 22 else 82)
    for line in wrap(d, inc.get("event", "").upper(), hf, maxw)[:2]:
        d.text((pad, y), line, font=hf, fill=COLORS["Red"] if red else INK)
        y += int(hf.size * 0.98)
    y += 18

    # where + when
    area = inc.get("area") or "Hamilton County"
    where = f"{inc['location']}  ·  {area}" if inc.get("location") else area
    for line in wrap(d, where, font("bold", 42), maxw)[:2]:
        d.text((pad, y), line, font=font("bold", 42), fill=INK)
        y += 52
    meta = f"Dispatched {clock(inc.get('created_at'))}"
    if not red and inc.get("agency"):
        meta = f"{inc['agency']}  ·  {meta}"
    d.text((pad, y + 4), meta, font=font("mono", 30), fill=DIM)
    y += 62

    if mapped:  # map credit, small, on the map area
        d.text((pad, 740), "Map: Esri, HERE, Garmin, © OpenStreetMap contributors", font=font("body", 22), fill=(150, 160, 170))
    return layer, y


def caption_layer(words: list[str], k: int, top: int) -> Image.Image:
    """Caption box with word k highlighted (k = -1 for none, len(words) for all spoken)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pad, maxw = 64, W - 64 - 170
    cf = font("body", 38)
    lines, line = [], []
    for i, w in enumerate(words):
        trial = " ".join(words[j] for j in line + [i])
        if line and d.textlength(trial, font=cf) > maxw - 40:
            lines.append(line)
            line = [i]
        else:
            line.append(i)
    if line:
        lines.append(line)
    lines = lines[:5]
    box_h = len(lines) * 50 + 28
    d.rectangle([pad, top, W - 170, top + box_h], fill=NIGHT + (210,))
    d.rectangle([pad, top, pad + 6, top + box_h], fill=INK)
    y = top + 14
    for ln in lines:
        x = pad + 30
        for i in ln:
            w = words[i]
            tw = d.textlength(w, font=cf)
            if i == k:
                d.rectangle([x - 6, y + 2, x + tw + 6, y + 48], fill=(241, 243, 245, 60))
            d.text((x, y), w, font=cf, fill=INK if i <= k else DIM)
            x += tw + d.textlength(" ", font=cf)
        y += 50
    return layer


# ---------------------------------------------------------------- render
def word_times(words: list[str], start: float, dur: float) -> list[float]:
    """Approximate when each word starts, weighting by word length."""
    weights = [len(w) + 2 for w in words]
    total = sum(weights) or 1
    t, out = start, []
    for w in weights:
        out.append(t)
        t += dur * w / total
    return out


def render(inc: dict, out_path: Path, voice: Path | None = None) -> Path:
    import imageio_ffmpeg

    script = inc.get("script") or f"{inc.get('event', '')} reported at {inc.get('location', '')}."
    words = script.split()
    tmp = Path(tempfile.mkdtemp())
    wav = tmp / "voice.wav"
    if voice:
        wav = voice
        speech = wav_seconds(voice)
    else:
        speech = tts(script, wav)
    lead = 0.6
    speak_dur = speech or max(4.0, len(words) / 2.6)
    total = max(10.0, lead + speak_dur + 1.4)
    times = word_times(words, lead, speak_dur)

    bg, mapped = map_background(inc.get("lat"), inc.get("lng"))
    static, cap_top = static_layer(inc, mapped)
    _, color = kind(inc)
    cap_cache: dict[int, Image.Image] = {}

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if speech:
        cmd += ["-itsoffset", str(lead), "-i", str(wav)]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    cmd += ["-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-af", "apad",
            "-t", f"{total:.2f}", "-movflags", "+faststart", str(out_path)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    n = int(total * FPS)
    for f in range(n):
        t = f / FPS
        # slow push-in on the map, anchored on the pin
        s = 1.0 + 0.07 * (t / total)
        cw, ch = W / s, H / s
        left, top = PIN_X - PIN_X / s, PIN_Y - PIN_Y / s
        frame = bg.crop((round(left), round(top), round(left + cw), round(top + ch))).resize((W, H), Image.BILINEAR).convert("RGBA")
        d = ImageDraw.Draw(frame)
        # pulsing pin
        phase = (t % 1.6) / 1.6
        r = 18 + phase * 70
        a = int(200 * (1 - phase))
        ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([PIN_X - r, PIN_Y - r, PIN_X + r, PIN_Y + r], outline=color + (a,), width=6)
        frame.alpha_composite(ring)
        d.ellipse([PIN_X - 24, PIN_Y - 24, PIN_X + 24, PIN_Y + 24], fill=NIGHT)
        d.ellipse([PIN_X - 18, PIN_Y - 18, PIN_X + 18, PIN_Y + 18], fill=color)
        frame.alpha_composite(static)
        k = -1
        for i, wt in enumerate(times):
            if t >= wt:
                k = i
        if t >= lead + speak_dur:
            k = len(words)
        if k not in cap_cache:
            cap_cache[k] = caption_layer(words, k, cap_top)
        frame.alpha_composite(cap_cache[k])
        proc.stdin.write(frame.convert("RGB").tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed to encode the video")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", help="Master Incident number (default: newest incident)")
    ap.add_argument("--feed", type=Path, default=HERE / "incidents.json")
    ap.add_argument("--voice", type=Path, help="your own recorded voiceover (.wav) instead of TTS")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    incs = [i for i in json.loads(args.feed.read_text(encoding="utf-8"))["incidents"] if not i.get("cleared_at")]
    if not incs:
        sys.exit("No active incidents in the feed.")
    inc = next((i for i in incs if i["id"] == args.id), None) if args.id else incs[0]
    if not inc:
        sys.exit(f"Incident {args.id} not found.")
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", inc["id"])
    out = args.out or OUT_DIR / f"{safe}.mp4"
    render(inc, out, args.voice)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
