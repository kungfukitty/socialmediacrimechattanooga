#!/usr/bin/env python3
"""
youtube_upload.py: upload a vertical MP4 to your YouTube channel as a Short (YouTube Data API v3).

One-time setup (see docs/AUTOPOST_SETUP.md):
  1. Google Cloud project -> enable "YouTube Data API v3"
  2. OAuth client ID, type "Desktop app" -> download JSON -> save as client_secret.json in this folder
  3. python youtube_upload.py --auth      (a browser opens; pick your channel; token saved to youtube_token.json)

Notes:
  - Uploads from an unverified API project are locked to PRIVATE until the project passes Google's audit.
  - Default quota is 10,000 units/day and each upload costs about 1,600, so about 6 uploads a day.

Usage:
  python youtube_upload.py --file output/X.mp4 --title "..." --description "..." --privacy private
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLIENT_SECRET = HERE / "client_secret.json"
TOKEN = HERE / "youtube_token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
NEWS_CATEGORY = "25"  # News & Politics


def credentials(interactive: bool = False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not interactive:
            raise RuntimeError("YouTube is not authorized yet. Run: python youtube_upload.py --auth")
        if not CLIENT_SECRET.exists():
            raise RuntimeError(f"Missing {CLIENT_SECRET.name}. See docs/AUTOPOST_SETUP.md, step 1.")
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")
    TOKEN.write_text(creds.to_json())
    return creds


def upload(path: Path, title: str, description: str, tags: list[str], privacy: str = "private") -> str:
    """Upload and return the YouTube video id."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    yt = build("youtube", "v3", credentials=credentials(), cache_discovery=False)
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:30],
            "categoryId": NEWS_CATEGORY,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(str(path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auth", action="store_true", help="sign in to YouTube (first time only)")
    ap.add_argument("--file", type=Path)
    ap.add_argument("--title", default="Test upload")
    ap.add_argument("--description", default="")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    args = ap.parse_args()
    if args.auth:
        credentials(interactive=True)
        print(f"YouTube authorized. Token saved to {TOKEN.name}.")
        return
    if not args.file:
        sys.exit("Give --file, or --auth to sign in.")
    vid = upload(args.file, args.title, args.description, [], args.privacy)
    print(f"uploaded: https://youtube.com/shorts/{vid}")


if __name__ == "__main__":
    main()
