#!/usr/bin/env python3
"""
tiktok_upload.py: send a vertical MP4 to your TikTok inbox as a draft (Content Posting API, Upload).

You get a TikTok notification, open it, add sounds or edits if you like, and tap Post. Fully
automatic public posting (Direct Post) needs TikTok to audit your app first; see the setup guide.

One-time setup (see docs/AUTOPOST_SETUP.md):
  1. developers.tiktok.com -> create an app -> add Login Kit and Content Posting API
     -> scopes user.info.basic and video.upload
     -> redirect URI (Login Kit, Desktop):  http://127.0.0.1:8723/callback/
  2. Save tiktok_app.json in this folder:
       {"client_key": "...", "client_secret": "...", "redirect_uri": "http://127.0.0.1:8723/callback/"}
  3. python tiktok_upload.py --auth      (a browser opens; approve; token saved to tiktok_token.json)

Limits: at most 5 pending drafts in any 24 hours, and 6 upload requests per minute.

Usage:
  python tiktok_upload.py --file output/X.mp4
"""
from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import secrets
import sys
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
APP = HERE / "tiktok_app.json"
TOKEN = HERE / "tiktok_token.json"
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
SCOPES = "user.info.basic,video.upload"
MIN_CHUNK, MAX_CHUNK = 5 * 1024 * 1024, 64 * 1024 * 1024


def _app() -> dict:
    if not APP.exists():
        raise RuntimeError(f"Missing {APP.name}. See docs/AUTOPOST_SETUP.md, TikTok step 2.")
    return json.loads(APP.read_text())


def _save_token(tok: dict) -> dict:
    tok["expires_at"] = time.time() + int(tok.get("expires_in", 0)) - 60
    tok["refresh_expires_at"] = time.time() + int(tok.get("refresh_expires_in", 0)) - 60
    TOKEN.write_text(json.dumps(tok, indent=1))
    return tok


def authorize() -> None:
    """Desktop OAuth with PKCE (TikTok wants the challenge as hex SHA-256)."""
    app = _app()
    redirect = app.get("redirect_uri", "http://127.0.0.1:8723/callback/")
    parsed = urllib.parse.urlparse(redirect)
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = hashlib.sha256(verifier.encode()).hexdigest()
    state = secrets.token_urlsafe(16)
    result: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            msg = "TikTok connected. You can close this tab." if "code" in result else f"TikTok error: {result}"
            self.wfile.write(f"<h2>{msg}</h2>".encode())

        def log_message(self, *a):
            pass

    server = http.server.HTTPServer((parsed.hostname, parsed.port), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_key": app["client_key"], "scope": SCOPES, "response_type": "code",
        "redirect_uri": redirect, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })
    print("Opening TikTok sign-in in your browser...")
    webbrowser.open(url)
    for _ in range(300):
        if result:
            break
        time.sleep(1)
    server.server_close()
    if result.get("state") != state or "code" not in result:
        raise RuntimeError(f"TikTok sign-in failed: {result or 'timed out'}")
    r = requests.post(TOKEN_URL, data={
        "client_key": app["client_key"], "client_secret": app["client_secret"],
        "code": result["code"], "grant_type": "authorization_code",
        "redirect_uri": redirect, "code_verifier": verifier,
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    tok = r.json()
    if "access_token" not in tok:
        raise RuntimeError(f"TikTok token exchange failed: {tok}")
    _save_token(tok)
    print(f"TikTok authorized. Token saved to {TOKEN.name}.")


def access_token() -> str:
    if not TOKEN.exists():
        raise RuntimeError("TikTok is not authorized yet. Run: python tiktok_upload.py --auth")
    tok = json.loads(TOKEN.read_text())
    if time.time() < tok.get("expires_at", 0):
        return tok["access_token"]
    if time.time() > tok.get("refresh_expires_at", 0):
        raise RuntimeError("TikTok sign-in expired. Run: python tiktok_upload.py --auth")
    app = _app()
    r = requests.post(TOKEN_URL, data={
        "client_key": app["client_key"], "client_secret": app["client_secret"],
        "grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
    }, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    new = r.json()
    if "access_token" not in new:
        raise RuntimeError(f"TikTok token refresh failed: {new}")
    return _save_token(new)["access_token"]


def upload(path: Path) -> dict:
    """Send the video to the TikTok inbox. Returns {"publish_id", "status"}."""
    size = path.stat().st_size
    if size <= MAX_CHUNK:
        chunk, count = size, 1
    else:
        chunk = 10 * 1024 * 1024
        count = size // chunk  # TikTok folds the remainder into the last chunk
    headers = {"Authorization": f"Bearer {access_token()}", "Content-Type": "application/json; charset=UTF-8"}
    r = requests.post(INIT_URL, headers=headers, json={"source_info": {
        "source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": count,
    }}, timeout=30)
    body = r.json()
    if body.get("error", {}).get("code") != "ok":
        raise RuntimeError(f"TikTok init failed: {body.get('error')}")
    publish_id, upload_url = body["data"]["publish_id"], body["data"]["upload_url"]

    with path.open("rb") as f:
        for i in range(count):
            start = i * chunk
            end = size - 1 if i == count - 1 else start + chunk - 1
            f.seek(start)
            data = f.read(end - start + 1)
            put = requests.put(upload_url, data=data, timeout=300, headers={
                "Content-Type": "video/mp4", "Content-Length": str(len(data)),
                "Content-Range": f"bytes {start}-{end}/{size}",
            })
            if put.status_code not in (200, 201, 206):
                raise RuntimeError(f"TikTok upload failed on chunk {i + 1}/{count}: HTTP {put.status_code} {put.text[:200]}")

    status = "UPLOADED"
    for _ in range(10):  # wait briefly for TikTok to finish processing
        time.sleep(3)
        s = requests.post(STATUS_URL, headers=headers, json={"publish_id": publish_id}, timeout=30).json()
        status = s.get("data", {}).get("status", status)
        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE", "FAILED"):
            break
    if status == "FAILED":
        raise RuntimeError(f"TikTok processing failed for {publish_id}")
    return {"publish_id": publish_id, "status": status}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auth", action="store_true", help="sign in to TikTok (first time, or when it expires)")
    ap.add_argument("--file", type=Path)
    args = ap.parse_args()
    if args.auth:
        authorize()
        return
    if not args.file:
        sys.exit("Give --file, or --auth to sign in.")
    print(upload(args.file))


if __name__ == "__main__":
    main()
