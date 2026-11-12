"""Publish the day's lesson to the Facebook Page in one multipart API call."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

META_PATH = Path("output") / "latest_video.json"


def upload():
    token = os.getenv("FACEBOOK_ACCESS_TOKEN") or os.getenv("FB_ACCESS_TOKEN", "")
    page_id = os.getenv("FACEBOOK_PAGE_ID") or os.getenv("FB_PAGE_ID", "")
    if not token or not page_id:
        print("[facebook] credentials not set - skipping")
        return True

    if not META_PATH.exists():
        print("[facebook] latest_video.json missing - skipping")
        return True

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    video = Path(meta["video_path"])
    if not video.exists():
        print(f"[facebook] video not found: {video}")
        return False

    title = str(meta.get("title", ""))[:200]
    description = str(meta.get("description", ""))[:4950]
    thumb = Path(meta.get("thumbnail_path", ""))

    print(f"[facebook] {video.name} ({video.stat().st_size // (1024 * 1024)} MB)")
    with open(video, "rb") as video_file:
        files = {"source": (video.name, video_file, "video/mp4")}
        thumb_file = None
        if thumb.exists():
            thumb_file = open(thumb, "rb")
            files["thumb"] = (thumb.name, thumb_file, "image/jpeg")
        try:
            response = requests.post(
                f"https://graph-video.facebook.com/v21.0/{page_id}/videos",
                data={
                    "title": title,
                    "description": description,
                    "published": "true",
                    "access_token": token,
                },
                files=files,
                timeout=900,
            )
        finally:
            if thumb_file:
                thumb_file.close()

    if response.status_code not in (200, 201):
        print(f"[facebook] failed ({response.status_code}): {response.text[:300]}")
        return False

    video_id = response.json().get("id")
    print(f"[facebook] published https://www.facebook.com/{video_id}")
    return True


if __name__ == "__main__":
    sys.exit(0 if upload() else 1)
