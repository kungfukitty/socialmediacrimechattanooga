# socialmediacrimechattanooga

A TikTok and YouTube Shorts page covering daily public-safety activity in Chattanooga and Hamilton County. `scraper.py` polls the public Hamilton County 9-1-1 Active Incidents list and writes `incidents.json`. `index.html` turns that file into a vertical, swipeable feed with a map, an automatic voiceover and word-by-word captions, ready to screen-record as a Short.

## Run it

```
pip install -r requirements.txt
python -m playwright install chromium

python scraper.py --simulate 15     # demo data, no network needed
python scraper.py                   # live: polls the 911 list every 4 minutes
python -m http.server 8000          # then open http://localhost:8000
```

In the feed: tap **Tap for voiceover**, swipe or use the arrow keys, **Caption** copies a ready-to-post caption, **Record** hides the controls for screen recording.

## Files

- `index.html`: TikTok-style vertical feed (map, voiceover, captions, auto-advance, record mode)
- `incidents.json`: the feed's data (currently simulated)
- `scraper.py`: polling adapter for the 911 list (filters, block-level locations, geocoding, voiceover scripts)
- `requirements.txt`

## Docs

- **90-day plan, deliverables and crosswalk:** [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
- **Crosswalk (spreadsheet):** [docs/crosswalk.csv](docs/crosswalk.csv)
- **Content rules:** [docs/CONTENT_POLICY.md](docs/CONTENT_POLICY.md)
- **911 district email:** [docs/legal/911_outreach.md](docs/legal/911_outreach.md)

Videos describe reported and dispatched incidents only. They are not official statements from any agency.
