#!/usr/bin/env python3
"""
autopost.py: the one command that runs everything.

Each cycle it:
  1. pulls the 911 list (scraper.py) into incidents.json
  2. scores every active call and keeps only the newsworthy ones (see SCORE_RULES)
  3. skips anything already posted (published.json) and stops at the daily cap
  4. renders a vertical MP4 for each new call (make_short.py)
  5. uploads it to YouTube (private until your API project is audited) and to your TikTok drafts
  6. records what happened in published.json, so nothing is ever posted twice

Usage:
  python autopost.py --once --dry-run   # make videos only, no uploads (start here)
  python autopost.py --once             # one full cycle
  python autopost.py --loop             # keep running, one cycle every few minutes

Settings live in autopost_config.json (created on first run).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
FEED = HERE / "incidents.json"
PUBLISHED = HERE / "published.json"
CONFIG = HERE / "autopost_config.json"
OUT_DIR = HERE / "output"

DEFAULT_CONFIG = {
    "youtube": {"enabled": False, "privacy": "private"},
    "tiktok": {"enabled": False},
    "min_score": 4,               # only calls scoring this or higher become videos
    "max_posts_per_day": 5,       # TikTok allows 5 pending drafts per 24 h; YouTube quota allows about 6 uploads
    "max_posts_per_cycle": 2,
    "max_age_minutes": 90,        # don't post stale calls
    "post_code_red": False,       # Code Red calls stay on the feed only
    "loop_minutes": 5,
    "hashtags": ["Chattanooga", "HamiltonCounty", "ChattanoogaNews", "LocalNews"],
}

# (pattern on the event name, points). The highest match counts, then modifiers are added.
SCORE_RULES = [
    (r"shoot|shots|gunshot|homicide|murder|stab", 6),
    (r"structure fire|house fire|residential fire|apartment fire|commercial fire|building fire|working fire", 5),
    (r"robbery|carjack|kidnap|abduct|weapon|\bgun\b|armed|hostage|barricade|swat", 5),
    (r"road closure|road closed|lanes? (closed|blocked)", 4),
    (r"vehicle fire|car fire|brush fire|grass fire|\bfire\b", 3),
    (r"burglary|break.?in|assault|fight|pursuit|chase", 3),
    (r"\bmvc\b|\bmva\b|crash|wreck|accident|collision|hit and run", 2),
    (r"stolen vehicle|theft|shoplift|larceny|vandal", 1),
]
MODIFIERS = [
    (lambda i: re.search(r"injur", i["event"], re.I) and not re.search(r"no injur", i["event"], re.I), 1),
    (lambda i: re.search(r"\bI-?\s?(24|75|124)\b|interstate|hwy|highway|\b153\b|\bus ?27\b", i.get("location", ""), re.I), 2),
    (lambda i: re.search(r"alarm|false|test|drill", i["event"], re.I), -4),
    (lambda i: i.get("status") == "OS", 1),
]


def score(inc: dict, cfg: dict) -> int:
    if inc.get("type") == "Code Red":
        return 10 if cfg.get("post_code_red") else -1
    base = max([pts for pat, pts in SCORE_RULES if re.search(pat, inc.get("event", ""), re.I)] or [0])
    return base + sum(pts for test, pts in MODIFIERS if test(inc))


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    tmp.replace(path)


def load_config() -> dict:
    cfg = load_json(CONFIG, None)
    if cfg is None:
        save_json(CONFIG, DEFAULT_CONFIG)
        print(f"created {CONFIG.name} with default settings (uploads are OFF until you turn them on)")
        cfg = {}
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    for k, v in cfg.items():
        merged[k] = {**merged[k], **v} if isinstance(v, dict) and isinstance(merged.get(k), dict) else v
    return merged


# ---------------------------------------------------------------- post text
def nice(text: str) -> str:
    """'MVC W/ INJURIES' -> 'MVC W/ Injuries'; keeps short codes upper-case."""
    return " ".join(w if (len(w) <= 3 and w.isupper()) else w.capitalize() for w in text.split())


def clock(iso: str | None) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%I:%M %p").lstrip("0") if iso else ""
    except ValueError:
        return ""


def post_text(inc: dict, cfg: dict) -> tuple[str, str, list[str]]:
    area = inc.get("area") or "Hamilton County"
    event = nice(inc.get("event", ""))
    where = inc.get("location") or area
    if inc.get("type") == "Code Red":
        title = f"{event} at {where}, {area}"
    else:
        title = f"{event} reported at {where}, {area}"
    tags = list(dict.fromkeys(cfg["hashtags"] + [re.sub(r"[^A-Za-z]", "", area)]))
    description = (
        f"{inc.get('script', '')}\n\n"
        f"Dispatched around {clock(inc.get('created_at'))}. "
        f"Source: Hamilton County 9-1-1 public Active Incidents list.\n"
        f"Based on public 9-1-1 dispatch data. Not an official statement. Details may change.\n\n"
        + " ".join(f"#{t}" for t in tags) + " #Shorts"
    )
    return title[:100], description, tags


# ---------------------------------------------------------------- cycle
def candidates(cfg: dict, published: dict) -> list[tuple[int, dict]]:
    feed = load_json(FEED, {})
    if feed.get("simulated"):
        print("incidents.json holds demo data; nothing will be posted. Run without --no-scrape to pull real calls.")
        return []
    now = datetime.now()
    out = []
    for inc in feed.get("incidents", []):
        if inc.get("cleared_at") or inc["id"] in published:
            continue
        if inc.get("status") not in ("E", "OS", "CR") and inc.get("type") != "Road Closure":
            continue  # wait until units are actually assigned
        try:
            age = now - datetime.fromisoformat(inc["created_at"])
        except Exception:
            continue
        if age > timedelta(minutes=cfg["max_age_minutes"]):
            continue
        s = score(inc, cfg)
        if s >= cfg["min_score"]:
            out.append((s, inc))
    out.sort(key=lambda x: (x[0], x[1].get("created_at", "")), reverse=True)
    return out


def posted_today(published: dict) -> int:
    today = datetime.now().date().isoformat()
    return sum(1 for p in published.values() if str(p.get("at", "")).startswith(today) and not p.get("dry_run"))


def run_cycle(cfg: dict, dry_run: bool, scrape: bool) -> None:
    if scrape:
        import scraper
        try:
            scraper.poll_once(FEED)
        except Exception as e:
            print(f"scrape failed: {e}")
    published = load_json(PUBLISHED, {})
    room = cfg["max_posts_per_day"] - posted_today(published)
    picks = candidates(cfg, published)
    if not picks:
        print(f"{datetime.now():%H:%M:%S} no new calls worth a video")
        return
    if room <= 0:
        print(f"{datetime.now():%H:%M:%S} daily cap of {cfg['max_posts_per_day']} reached; {len(picks)} call(s) waiting")
        return

    import make_short
    for s, inc in picks[: min(room, cfg["max_posts_per_cycle"])]:
        title, description, tags = post_text(inc, cfg)
        safe = re.sub(r"[^A-Za-z0-9_-]", "_", inc["id"])
        video = OUT_DIR / f"{safe}.mp4"
        rec = {"at": datetime.now().isoformat(timespec="seconds"), "score": s, "title": title, "video": str(video.name)}
        print(f"→ [{s}] {title}")
        try:
            make_short.render(inc, video)
        except Exception as e:
            print(f"  video failed: {e}")
            continue  # not recorded, so it is retried next cycle
        if dry_run:
            rec["dry_run"] = True
            print(f"  made {video.name} (dry run, not uploaded)")
        else:
            if cfg["youtube"]["enabled"]:
                try:
                    import youtube_upload
                    vid = youtube_upload.upload(video, title, description, tags, cfg["youtube"]["privacy"])
                    rec["youtube"] = {"id": vid, "url": f"https://youtube.com/shorts/{vid}", "privacy": cfg["youtube"]["privacy"]}
                    print(f"  YouTube: https://youtube.com/shorts/{vid} ({cfg['youtube']['privacy']})")
                except Exception as e:
                    rec["youtube"] = {"error": str(e)}
                    print(f"  YouTube failed: {e}")
            if cfg["tiktok"]["enabled"]:
                try:
                    import tiktok_upload
                    rec["tiktok"] = tiktok_upload.upload(video)
                    print(f"  TikTok: sent to drafts ({rec['tiktok']['status']}). Open TikTok to post it.")
                except Exception as e:
                    rec["tiktok"] = {"error": str(e)}
                    print(f"  TikTok failed: {e}")
            if not cfg["youtube"]["enabled"] and not cfg["tiktok"]["enabled"]:
                print(f"  made {video.name}; uploads are off in {CONFIG.name}")
        published[inc["id"]] = rec
        save_json(PUBLISHED, published)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--once", action="store_true", help="run one cycle and exit")
    ap.add_argument("--loop", action="store_true", help="keep running")
    ap.add_argument("--dry-run", action="store_true", help="make videos but don't upload")
    ap.add_argument("--no-scrape", action="store_true", help="use the current incidents.json")
    ap.add_argument("--scores", action="store_true", help="list active calls with their scores and exit")
    args = ap.parse_args()
    cfg = load_config()

    if args.scores:
        feed = load_json(FEED, {})
        rows = sorted(((score(i, cfg), i) for i in feed.get("incidents", []) if not i.get("cleared_at")),
                      key=lambda x: x[0], reverse=True)
        for s, i in rows:
            mark = "VIDEO" if s >= cfg["min_score"] else "     "
            print(f"{mark} {s:>3}  {i.get('status', ''):>3}  {i.get('event', '')[:34]:34}  {i.get('location', '')[:40]}")
        return

    if not args.loop:
        run_cycle(cfg, args.dry_run, not args.no_scrape)
        return
    minutes = max(3, int(cfg["loop_minutes"]))
    print(f"running every {minutes} minutes. Press Ctrl + C to stop.")
    while True:
        try:
            run_cycle(load_config(), args.dry_run, not args.no_scrape)
        except KeyboardInterrupt:
            raise
        except Exception:
            traceback.print_exc()
        time.sleep(minutes * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
