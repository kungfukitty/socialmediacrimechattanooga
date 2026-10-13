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

## Auto-post to TikTok and YouTube

`autopost.py` picks newsworthy new calls, renders a vertical MP4 for each (`make_short.py`), uploads it to YouTube (`youtube_upload.py`) and sends it to your TikTok drafts (`tiktok_upload.py`). `published.json` prevents duplicates. Start with **`run_test.bat`** (makes videos, uploads nothing), then follow **[docs/AUTOPOST_SETUP.md](docs/AUTOPOST_SETUP.md)** to connect the accounts.

## Files

- `index.html`: TikTok-style vertical feed (map, voiceover, captions, auto-advance, record mode)
- `incidents.json`: the feed's data (currently simulated)
- `scraper.py`: polling adapter for the 911 list (filters, block-level locations, geocoding, voiceover scripts)
- `make_short.py`: renders one call as a 1080×1920 MP4 (map, card, captions, voiceover)
- `autopost.py`: scoring, duplicate protection, daily cap, uploads
- `youtube_upload.py`, `tiktok_upload.py`: platform uploaders
- `run_test.bat`, `run_once.bat`, `run_continuous.bat`: double-click runners for Windows
- `requirements.txt`

## Docs

- **90-day plan, deliverables and crosswalk:** [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
- **Crosswalk (spreadsheet):** [docs/crosswalk.csv](docs/crosswalk.csv)
- **Content rules:** [docs/CONTENT_POLICY.md](docs/CONTENT_POLICY.md)
- **911 district email:** [docs/legal/911_outreach.md](docs/legal/911_outreach.md)

Videos describe reported and dispatched incidents only. They are not official statements from any agency.
