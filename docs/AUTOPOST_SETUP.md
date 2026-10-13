# Auto-posting setup

The flow:

```
scraper.py → incidents.json → autopost.py picks newsworthy calls → make_short.py → output/<id>.mp4
                                                                  ├→ YouTube (youtube_upload.py)
                                                                  └→ TikTok drafts (tiktok_upload.py)
published.json remembers every posted call, so nothing goes up twice.
```

Do the steps in order. Each one works on its own before you add the next.

---

## Step 0: Install the new packages (5 min)

In PowerShell, in your project folder:

```
python -m pip install -r requirements.txt
```

## Step 1: Make test videos, no uploads (5 min)

Double-click **`run_test.bat`**, or run `python autopost.py --once --dry-run`.

It pulls the 911 list, makes a video for each newsworthy new call, and opens the `output` folder. Watch one and check the map, the text and the voice.

- To see why calls did or didn't get a video: `python autopost.py --scores`. Calls marked `VIDEO` scored at least `min_score`.
- To make a video for one specific call: `python make_short.py --id 2026-10-19569`.
- To use **your own voice** instead of the computer voice, record a .wav and run `python make_short.py --id <id> --voice my_take.wav`.

Settings are in **`autopost_config.json`**, which is created on the first run:

| Setting | Default | What it does |
|---|---|---|
| `min_score` | 4 | Higher means fewer, bigger stories. Shootings 6–7, structure fires 5–6, robberies 5, road closures 4, injury crashes 3–5, burglaries 3, thefts 1, alarms never |
| `max_posts_per_day` | 5 | Hard daily cap. TikTok allows 5 pending drafts per 24 hours; YouTube's free quota allows about 6 uploads a day |
| `max_posts_per_cycle` | 2 | Videos per run |
| `max_age_minutes` | 90 | Skip calls older than this |
| `post_code_red` | false | Code Red calls stay on the feed only |
| `youtube.enabled` / `tiktok.enabled` | false | Turn uploads on (steps 2 and 3) |
| `youtube.privacy` | private | Change to `public` only after the Google audit |

## Step 2: YouTube (30 min)

1. Go to **console.cloud.google.com** and sign in with the Google account that owns your YouTube channel. Create a **new project** (any name).
2. Open **APIs & Services → Library**, search for **YouTube Data API v3** and click **Enable**.
3. Open **Google Auth Platform** (it may also be labeled "OAuth consent screen") and fill in:
   - **Branding:** app name, your email.
   - **Audience:** External. Under **Test users**, add your own Gmail.
4. Go to **Clients → Create client → Desktop app**. Download the JSON file, rename it to **`client_secret.json`**, and put it in your project folder.
5. In PowerShell, run `python youtube_upload.py --auth`. A browser opens: pick your channel and allow access. If Google shows an "unverified app" warning, click **Advanced → Continue**, because it's your own app.
6. In `autopost_config.json`, set `"youtube": {"enabled": true, "privacy": "private"}`.

**Good to know:**
- **Everything uploads as private at first.** Google keeps uploads from new API projects private until the project passes its audit. To go public, submit the **YouTube API Services audit form** (search "YouTube API Services Audit and Quota Extension Form"). Then set `privacy` to `public`.
- **The sign-in expires every 7 days** while the app is in "Testing". You can re-run `--auth`, or click **Publish app** on the Audience page so the token doesn't expire.

## Step 3: TikTok drafts (45 min, plus TikTok's review)

1. Go to **developers.tiktok.com**, sign in, open **Manage apps** and click **Connect an app**.
2. Fill in the app details. TikTok asks for a **Terms of Service URL** and a **Privacy Policy URL**, so add two simple pages to your link-in-bio site first.
3. Add these products:
   - **Login Kit**, with platform **Desktop** and redirect URI **`http://127.0.0.1:8723/callback/`**
   - **Content Posting API**. Leave **Direct Post** off for now.
4. Add these scopes: **`user.info.basic`** and **`video.upload`**.
5. Create a file named **`tiktok_app.json`** in your project folder:
   ```json
   {"client_key": "YOUR_CLIENT_KEY", "client_secret": "YOUR_CLIENT_SECRET", "redirect_uri": "http://127.0.0.1:8723/callback/"}
   ```
6. **Before TikTok approves the app**, use its **Sandbox**: create a sandbox, add your own TikTok account as a **target user**, and use the sandbox client key and secret in `tiktok_app.json`.
7. Run `python tiktok_upload.py --auth`. A browser opens: approve access.
8. In `autopost_config.json`, set `"tiktok": {"enabled": true}`.
9. Submit the app for review in the developer portal. Once approved, switch `tiktok_app.json` to the production key and secret, and run `--auth` again.

**How posting works:** each video lands in your TikTok **inbox as a draft**. You get a notification; open it, adjust anything you like, and tap **Post**. Fully automatic public posting (**Direct Post**) needs a separate TikTok audit. Until then, direct posts can only be private.

## Step 4: Run it

- **`run_once.bat`** does one cycle.
- **`run_continuous.bat`** keeps running, one cycle every 5 minutes. Leave the window open.

Every run prints what it did. `published.json` lists every post with its YouTube link or TikTok publish ID, or the error if an upload failed.

---

## Rules that protect the channel

- **Never put these files on GitHub:** `client_secret.json`, `youtube_token.json`, `tiktok_app.json`, `tiktok_token.json`. They're already in `.gitignore`.
- **Keep the daily cap low.** Dozens of near-identical alerts a day looks like spam to both platforms.
- **Monetization:** YouTube's "inauthentic content" policy targets mass-produced, templated videos with AI narration. Automated alerts are fine as a news service, but **the money videos should carry your own voice**. Keep doing the daily recap with your voice (`--voice`), and treat the auto alerts as the thing that brings people to the page.
- **Don't add big promotional watermarks** to videos sent through TikTok's API. TikTok's sharing guidelines restrict that. The small "CHA 911" title is fine.
- **The content policy still applies:** Code Red calls aren't posted by default, and every video carries the dispatch-data disclaimer.
