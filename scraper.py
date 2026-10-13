#!/usr/bin/env python3
"""
scraper.py: polling adapter for the Hamilton County 9-1-1 Active Incidents list.

Every POLL interval it:
  1. loads the public Active Incidents page (Playwright, because the rows load via JavaScript)
  2. parses the incident table
  3. turns sensitive calls into CODE RED alerts (location and time only, see content rules)
  4. trims locations to the street block ("1234 BOYNTON DR" -> "1200 block of Boynton Dr")
  5. geocodes the block (US Census geocoder, then OpenStreetMap Nominatim) with a local cache
  6. writes a fact-only voiceover script for each call
  7. merges everything into incidents.json, which index.html reads

Usage:
  python scraper.py                  # poll forever (every 240 s)
  python scraper.py --once           # one poll, then exit
  python scraper.py --fixture page.html --once   # parse a saved copy of the page
  python scraper.py --simulate 12    # write 12 simulated incidents (no network needed)

Be polite: the page limits sessions and is marked "All Rights Reserved".
Keep the interval at 3 minutes or more and see docs/legal/911_outreach.md.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.hamiltontn911.gov/active-incidents.php"
HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "incidents.json"
GEOCACHE = HERE / "geocache.json"
USER_AGENT = os.environ.get(
    "SCRAPER_USER_AGENT", "ChattanoogaSafetyFeed/0.1 (contact: set SCRAPER_USER_AGENT)"
)
KEEP_HOURS = 12          # drop cleared calls after this long
MAX_ITEMS = 60           # cap the feed size

STATUS_LABELS = {
    "Q": "Queued", "R": "Reported", "D": "Dispatched", "E": "Enroute", "OS": "On Scene",
    "T": "Transporting", "H": "At Hospital",
}

# Crashes and road hazards are shown under Roads (type "Traffic"), whichever agency handles them.
TRAFFIC_EVENT = re.compile(
    r"\bmvc\b|\bmva\b|crash|wreck|accident|collision|hit\s+and\s+run|disabled\s+vehicle|"
    r"stalled|debris|traffic\s+hazard|lane\s+block|road\s+block|vehicle\s+in\s+roadway",
    re.I,
)
EVENT_SPOKEN = [  # county shorthand -> words for the voiceover (screen keeps the county wording)
    (r"\bmvc\b", "motor vehicle crash"), (r"\bmva\b", "motor vehicle accident"),
    (r"\bw/\s*", "with "), (r"\s*\bno injur(y|ies)\b", " with no injuries"), (r"\s+-\s+", ", "),
]

# ---------------------------------------------------------------- content rules
# See docs/CONTENT_POLICY.md. Calls are posted with full details unless the topic would cause
# trouble on TikTok or YouTube, or would expose a private person's health or abuse situation.
# Those become CODE RED: map pin, street block, area and time, plus a neutral label.
# Everything else about the call (event, agency, status, incident number) is removed before saving.
#
#   "Medical Response"  medical, overdose, suicide/self-harm and mental-health calls
#                        (YouTube: drugs, suicide and self-harm are sensitive topics; TikTok: behavioral health
#                        content can lose For You reach; and these are private health matters)
#   "Police Response"   domestic, sexual, child-related and death calls
#                        (YouTube limits ads on child abuse; both platforms treat sexual and domestic abuse
#                        as sensitive; these calls can identify victims)
#
# Shootings, assaults, robberies, burglaries, thefts, fires and wrecks keep full details: both platforms
# allow non-graphic news reporting of crime.
CODE_RED = "Code Red"
MEDICAL = "Medical Response"
POLICE = "Police Response"

MEDICAL_EVENT = re.compile(
    r"medical|overdose|\bod\b|cardiac|heart|breath|unconscious|unresponsive|seizure|stroke|diabet|"
    r"sick|fall\b|lift\s+assist|\bems\b|ambulance|bleed|"
    r"suicid|self.?harm|mental|crisis|10-96|psych|behavior",
    re.I,
)
POLICE_SENSITIVE_EVENT = re.compile(
    r"domestic|\bdv\b|family\s+(dispute|disturbance|violence)|protective\s+order|"
    r"sex|rape|molest|indecent|\bindec|stalk|"
    r"juvenile|\bjuv\b|child|minor|\bcps\b|runaway|missing|amber|abuse|neglect|"
    r"death|\bdoa\b|deceased|\bbody\b|welfare",
    re.I,
)


def classify(inc: dict) -> str | None:
    """Return the Code Red label for a call, or None if it is posted with full details."""
    if inc["type"] == "EMS" or MEDICAL_EVENT.search(inc["event"]):
        return MEDICAL
    if POLICE_SENSITIVE_EVENT.search(inc["event"]):
        return POLICE
    return None


def categorize(inc: dict) -> dict:
    """Apply Code Red redaction, otherwise move crashes and road hazards under Roads."""
    traffic = inc.pop("_traffic", False)
    label = classify(inc)
    if label:
        return redact(inc, label)
    if traffic and inc["type"] != "Road Closure":
        inc["type"] = "Traffic"
    return inc


def redact(inc: dict, label: str) -> dict:
    """Strip every detail about the call. Only the id, location, area, time and label survive."""
    inc.update(type=CODE_RED, event=label, agency="", status="CR", status_label="")
    return inc


# ---------------------------------------------------------------- fetching
def fetch_html(url: str = SOURCE_URL) -> str:
    """Render the page in headless Chromium so the JavaScript-loaded rows exist."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed; falling back to plain HTTP (table may be empty)", file=sys.stderr)
        return requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30).text

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        try:
            page.wait_for_selector("table tbody tr td", timeout=20_000)
        except Exception:
            pass  # quiet night or layout change: parse whatever is there
        html = page.content()
        browser.close()
        return html


# ---------------------------------------------------------------- parsing
def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


# Hamilton County sits around 35.0 N, -85.2 W
COORDS = re.compile(r"\b(3[45]\.\d{3,})[^\d]{1,40}?(-8[45]\.\d{3,})")
COORDS_REV = re.compile(r"(-8[45]\.\d{3,})[^\d]{1,40}?\b(3[45]\.\d{3,})")


def parse_rows(html: str) -> list[dict]:
    """Return one dict per table row, keyed by the header text."""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        headers = [_clean(th.get_text()) for th in table.find_all("th")]
        if not any(h.lower().startswith("master incident") for h in headers):
            continue
        for junk in table.find_all(["script", "style"]):
            junk.decompose()
        rows = []
        for tr in table.find_all("tr"):
            # The location is the text of the "locate on map" button, so button text is kept.
            cells = [_clean(td.get_text(" ")) for td in tr.find_all("td")]
            if len(cells) >= len(headers) - 1 and any(cells):
                row = dict(zip(headers, cells))
                # The map buttons may carry coordinates in their attributes; use them if present.
                m = COORDS.search(str(tr))
                if m:
                    row["_lat"], row["_lng"] = float(m.group(1)), float(m.group(2))
                else:
                    m = COORDS_REV.search(str(tr))
                    if m:
                        row["_lat"], row["_lng"] = float(m.group(2)), float(m.group(1))
                rows.append(row)
        return rows
    return []


def _col(row: dict, name: str) -> str:
    for k, v in row.items():
        if k.lower().startswith(name.lower()):
            return v
    return ""


def parse_time(raw: str) -> str | None:
    raw = _clean(raw)
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M %p", "%H:%M:%S"):
        try:
            dt = datetime.strptime(raw, fmt)
            if fmt == "%H:%M:%S":  # time only: assume today
                now = datetime.now()
                dt = dt.replace(year=now.year, month=now.month, day=now.day)
            return dt.isoformat(timespec="seconds")
        except ValueError:
            continue
    return None


def normalize(row: dict) -> dict | None:
    iid = re.sub(r"^\s*(master\s+)?incident\s*#?\s*", "", _col(row, "Master Incident"), flags=re.I)
    if not iid:
        return None
    status_raw = _col(row, "Status").upper()
    status = status_raw if status_raw in STATUS_LABELS else next(
        (k for k, v in STATUS_LABELS.items() if v.upper() == status_raw), status_raw
    )
    return {
        "id": iid,
        "type": _col(row, "Type"),
        "status": status,
        "status_label": STATUS_LABELS.get(status, status_raw.title()),
        "agency": _col(row, "Agency"),
        "event": _col(row, "Event"),
        "location_raw": _col(row, "Location"),
        "area": _col(row, "Area").title(),
        "_traffic": bool(TRAFFIC_EVENT.search(_col(row, "Event"))),
        "created_at": parse_time(_col(row, "Time Created")),
        "_point": (row["_lat"], row["_lng"]) if "_lat" in row else None,
    }


# ---------------------------------------------------------------- locations
ABBREV = {
    "DR": "Drive", "ST": "Street", "AVE": "Avenue", "AV": "Avenue", "BLVD": "Boulevard", "RD": "Road",
    "HWY": "Highway", "PKWY": "Parkway", "PIKE": "Pike", "LN": "Lane", "CT": "Court", "CIR": "Circle",
    "PL": "Place", "TER": "Terrace", "TRL": "Trail", "WAY": "Way", "N": "North", "S": "South",
    "E": "East", "W": "West", "MLK": "M L K", "I": "Interstate",
}


def _title(s: str) -> str:
    """Title-case a street name but keep ordinals lowercase: 23rd, not 23Rd."""
    s = re.sub(r"(\d)(St|Nd|Rd|Th)\b", lambda m: m.group(1) + m.group(2).lower(), s.title())
    return re.sub(r"\bMc([a-z])", lambda m: "Mc" + m.group(1).upper(), s)


def block_of(location: str) -> tuple[str, str]:
    """Return (display, geocode_query). Exact house numbers are rounded down to the block."""
    loc = _clean(location).upper()
    loc = re.sub(r"\s*\(.*?\)\s*", " ", loc).strip()  # drop "(BUTTON)" text etc.
    loc = re.sub(r"\b(LOCATE( ON MAP)?|VIEW MAP|MAP)\b", " ", loc)
    loc = re.sub(r"\s+", " ", loc).strip()
    m = re.match(r"^(\d+)\s+(?:BLOCK\s+(?:OF\s+)?)?(.+)$", loc)
    if m:
        n = int(m.group(1))
        block = (n // 100) * 100
        street = _title(m.group(2))
        return f"{block} block of {street}", f"{max(block, 1) + 50} {m.group(2)}"
    # Intersections ("MARKET ST / MAIN ST") and named places stay as-is.
    return _title(loc).replace(" / ", " & "), loc.replace(" / ", " & ")


def speakable(text: str) -> str:
    words = text.split()
    return " ".join(ABBREV.get(w.upper().strip(".,"), w) for w in words)


def _load_cache() -> dict:
    try:
        return json.loads(GEOCACHE.read_text())
    except Exception:
        return {}


def geocode(query: str, area: str, cache: dict) -> tuple[float, float] | None:
    key = f"{query}|{area}".upper()
    if key in cache:
        return tuple(cache[key]) if cache[key] else None
    city = area if area and area != "Hamilton County" else "Chattanooga"
    full = f"{query}, {city}, TN"
    point = None
    errored = False
    try:
        r = requests.get(
            "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
            params={"address": full, "benchmark": "Public_AR_Current", "format": "json"},
            timeout=20,
        )
        matches = r.json()["result"]["addressMatches"]
        if matches:
            c = matches[0]["coordinates"]
            point = (c["y"], c["x"])
    except Exception as e:
        errored = True
        print(f"census geocode failed for {full}: {e}", file=sys.stderr)
    if point is None:
        try:
            time.sleep(1)  # Nominatim policy: max 1 request/second
            r = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": f"{full}, Hamilton County", "format": "json", "limit": 1},
                headers={"User-Agent": USER_AGENT},
                timeout=20,
            )
            hits = r.json()
            if hits:
                point = (float(hits[0]["lat"]), float(hits[0]["lon"]))
        except Exception as e:
            errored = True
            print(f"nominatim geocode failed for {full}: {e}", file=sys.stderr)
    # ~100 m precision: enough for a map pin, not enough to point at a house
    point = (round(point[0], 3), round(point[1], 3)) if point else None
    if point or not errored:  # never cache a network failure as "no match"
        cache[key] = list(point) if point else None
    return point


# ---------------------------------------------------------------- voiceover
def _agency_spoken(agency: str) -> str:
    a = re.sub(r"\bPD\b", "Police", agency, flags=re.I)
    a = re.sub(r"\bFD\b", "Fire", a, flags=re.I)
    a = re.sub(r"\bSO\b", "Sheriff's Office", a, flags=re.I)
    return a


def _clock(iso: str | None) -> str:
    if not iso:
        return ""
    dt = datetime.fromisoformat(iso)
    return dt.strftime("%I:%M %p").lstrip("0")


def voiceover(inc: dict) -> str:
    """Fact-only script: every phrase comes from a field on the 911 list."""
    agency = _agency_spoken(inc["agency"]) or "Emergency crews"
    event = inc["event"].lower()
    for pat, words in EVENT_SPOKEN:
        event = re.sub(pat, words, event, flags=re.I)
    loc = speakable(inc["location"]).replace(" & ", " and ")
    where = f"the {loc}" if " block of " in loc else loc
    at = f" at {where}" if loc else ""
    area = f" in {inc['area']}" if inc["area"] and inc["area"] != "Hamilton County" else " in Hamilton County"
    t = _clock(inc["created_at"])
    when = f" The call came in around {t}." if t else ""
    if inc["type"] == CODE_RED:
        return f"Code red. {inc['event']}{at}{area}.{when}"
    if inc["type"] == "Road Closure":
        return f"Heads up. A road closure was reported{at}{area}.{when} Expect delays and use another route."
    if inc["type"] == "Traffic":
        if inc["status"] in ("E", "OS"):
            verb = "are on scene of" if inc["status"] == "OS" else "are on the way to"
            return f"Heads up. {agency} units {verb} a reported {event}{at}{area}.{when} Expect delays in the area."
        return f"Heads up. A {event} was reported{at}{area}.{when} Expect delays in the area."
    if inc["status"] == "OS":
        return f"{agency} units are on scene of a reported {event}{at}{area}.{when}"
    if inc["status"] == "E":
        return f"{agency} units are on the way to a reported {event}{at}{area}.{when}"
    return f"A {event} was reported{at}{area}.{when} Units are being assigned."


# ---------------------------------------------------------------- merge + write
def enrich(inc: dict, cache: dict) -> dict:
    display, query = block_of(inc.pop("location_raw"))
    inc["location"] = display
    page_point = inc.pop("_point", None)
    if page_point:  # coordinates from the 911 page itself, rounded to about 100 m
        point = (round(page_point[0], 3), round(page_point[1], 3))
    else:
        point = geocode(query, inc["area"], cache) if query else None
    inc["lat"], inc["lng"] = point if point else (None, None)
    inc["script"] = voiceover(inc)
    return inc


def merge(existing: list[dict], fresh: list[dict], now: datetime) -> list[dict]:
    by_id = {i["id"]: i for i in existing}
    live_ids = set()
    for inc in fresh:
        live_ids.add(inc["id"])
        old = by_id.get(inc["id"])
        if old:
            if old["status"] != inc["status"]:
                inc["history"] = old.get("history", []) + [{"status": inc["status"], "at": now.isoformat(timespec="seconds")}]
            else:
                inc["history"] = old.get("history", [])
            inc["first_seen"] = old.get("first_seen")
        else:
            inc["first_seen"] = now.isoformat(timespec="seconds")
            inc["history"] = [{"status": inc["status"], "at": inc["first_seen"]}]
        inc["cleared_at"] = None
        by_id[inc["id"]] = inc
    cutoff = now - timedelta(hours=KEEP_HOURS)
    out = []
    for inc in by_id.values():
        if inc["id"] not in live_ids and not inc.get("cleared_at"):
            inc["cleared_at"] = now.isoformat(timespec="seconds")
        if inc.get("cleared_at") and datetime.fromisoformat(inc["cleared_at"]) < cutoff:
            continue
        out.append(inc)
    out.sort(key=lambda i: i.get("created_at") or i.get("first_seen") or "", reverse=True)
    return out[:MAX_ITEMS]


def write_feed(path: Path, incidents: list[dict], simulated: bool) -> None:
    doc = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": SOURCE_URL,
        "simulated": simulated,
        "disclaimer": "Based on public 9-1-1 dispatch data. Not an official statement. Details may change.",
        "incidents": incidents,
    }
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(doc, f, indent=2)
    os.replace(tmp, path)  # atomic: the feed never reads a half-written file


def read_feed(path: Path) -> list[dict]:
    try:
        return json.loads(path.read_text()).get("incidents", [])
    except Exception:
        return []


def poll_once(out: Path, fixture: Path | None = None) -> int:
    html = fixture.read_text(encoding="utf-8") if fixture else fetch_html()
    if not fixture:  # keep the last page for debugging (python scraper.py --fixture last_page.html)
        (HERE / "last_page.html").write_text(html, encoding="utf-8")
    rows = parse_rows(html)
    if not rows:
        print("WARNING: no rows parsed (quiet period, blocked, or the page layout changed)", file=sys.stderr)
    cache = _load_cache()
    fresh = []
    for row in rows:
        inc = normalize(row)
        if not inc:
            continue
        fresh.append(enrich(categorize(inc), cache))
    GEOCACHE.write_text(json.dumps(cache, indent=1))
    existing = [i for i in read_feed(out) if not str(i.get("id", "")).startswith("SIM-")]  # drop demo data
    merged = merge(existing, fresh, datetime.now())
    write_feed(out, merged, simulated=False)
    print(f"{datetime.now():%H:%M:%S} parsed={len(rows)} published={len(fresh)} feed={len(merged)}")
    return len(fresh)


# ---------------------------------------------------------------- simulation
SIM_PLACES = [  # (raw location, area, lat, lng): approximate, for demo only
    ("1234 BOYNTON DR", "Chattanooga", 35.072, -85.301),
    ("412 MARKET ST", "Chattanooga", 35.051, -85.310),
    ("2150 E MAIN ST", "Chattanooga", 35.031, -85.283),
    ("5420 BRAINERD RD", "Chattanooga", 35.012, -85.205),
    ("7010 LEE HWY", "Chattanooga", 35.048, -85.158),
    ("1820 DAYTON BLVD", "Red Bank", 35.087, -85.296),
    ("3715 RINGGOLD RD", "East Ridge", 35.001, -85.239),
    ("4530 HIXSON PIKE", "Hamilton County", 35.115, -85.256),
    ("9410 APISON PIKE", "Collegedale", 35.045, -85.055),
    ("640 SIGNAL MOUNTAIN RD", "Chattanooga", 35.090, -85.333),
    ("2010 GUNBARREL RD", "Chattanooga", 35.042, -85.156),
    ("11050 DAYTON PIKE", "Soddy-Daisy", 35.235, -85.190),
    ("1410 MCCALLIE AVE", "Chattanooga", 35.043, -85.279),
    ("3020 BROAD ST", "Chattanooga", 35.028, -85.317),
    ("1200 TAFT HWY", "Signal Mountain", 35.122, -85.343),
]
SIM_EVENTS = [
    ("Law", "Burglary"), ("Law", "Theft From Vehicle"), ("Law", "Suspicious Person"),
    ("Law", "Shots Fired Call"), ("Law", "Shoplifting"), ("Law", "Disorder"), ("Law", "Stolen Vehicle"),
    ("Fire", "Structure Fire"), ("Fire", "Vehicle Fire"), ("Fire", "Fire Alarm"), ("Fire", "Brush Fire"),
    ("Road Closure", "Road Closure - Crash"), ("Law", "MVC No Injuries"), ("Law", "MVC With Injuries"),
    ("EMS", "Medical Call"), ("Law", "Domestic Disturbance"),  # become Code Red
    ("Law", "Robbery"), ("Law", "Assault"), ("Law", "Traffic Accident w/ Injuries"),
]
SIM_AGENCY = {
    "Chattanooga": ("Chattanooga PD", "Chattanooga FD"), "Red Bank": ("Red Bank PD", "Red Bank FD"),
    "East Ridge": ("East Ridge PD", "East Ridge FD"), "Collegedale": ("Collegedale PD", "Tri-Community FD"),
    "Soddy-Daisy": ("Soddy-Daisy PD", "Soddy-Daisy FD"), "Signal Mountain": ("Signal Mountain PD", "Signal Mountain FD"),
    "Hamilton County": ("Hamilton County SO", "Hamilton County FD"),
}


def simulate(out: Path, n: int) -> None:
    now = datetime.now()
    fresh = []
    for k in range(n):
        raw, area, lat, lng = random.choice(SIM_PLACES)
        typ, event = random.choice(SIM_EVENTS)
        police, fire = SIM_AGENCY[area]
        created = now - timedelta(minutes=random.randint(2, 240))
        inc = normalize({
            "Type": typ, "Status": random.choice(["R", "E", "E", "OS", "OS"]),
            "Master Incident": f"SIM-{created:%y%m%d}-{random.randint(1000, 9999)}",
            "Time Created": created.strftime("%m/%d/%Y %H:%M:%S"),
            "Agency": fire if typ == "Fire" else police, "Event": event, "Location": raw, "Area": area,
        })
        categorize(inc)
        inc.pop("_point", None)
        display, _ = block_of(inc.pop("location_raw"))
        inc.update(location=display, lat=lat, lng=lng)
        inc["script"] = voiceover(inc)
        fresh.append(inc)
    write_feed(out, merge([], fresh, now), simulated=True)
    print(f"wrote {len(fresh)} simulated incidents to {out}")


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--interval", type=int, default=240, help="seconds between polls (min 180)")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--fixture", type=Path, help="parse a saved HTML file instead of the live page")
    ap.add_argument("--simulate", type=int, metavar="N", help="write N simulated incidents and exit")
    args = ap.parse_args()

    if args.simulate:
        simulate(args.out, args.simulate)
        return
    interval = max(args.interval, 180)
    while True:
        try:
            poll_once(args.out, args.fixture)
        except Exception as e:  # keep the poller alive through network blips
            print(f"poll failed: {e}", file=sys.stderr)
        if args.once or args.fixture:
            break
        time.sleep(interval)


if __name__ == "__main__":
    main()
