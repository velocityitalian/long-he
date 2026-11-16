"""Publish the day's lesson to the Facebook Page via resumable chunked upload."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

META_PATH = Path("output") / "latest_video.json"
BASE_URL = "https://graph-video.facebook.com/v21.0"


def _post(url, *, data, files=None, timeout=300, attempts=3):
    last = None
    for attempt in range(attempts):
        try:
            response = requests.post(url, data=data, files=files, timeout=timeout)
        except requests.RequestException as exc:
            last = exc
            print(f"[facebook] request error (attempt {attempt + 1}/{attempts}): {exc}")
        else:
            if response.status_code in (200, 201) or response.status_code < 500 and response.status_code != 429:
                return response
            last = response
            print(f"[facebook] transient failure {response.status_code} (attempt {attempt + 1}/{attempts})")
        if attempt < attempts - 1:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"upload request failed: {last}")


def _set_thumbnail(video_id, token, thumb):
    try:
        with open(thumb, "rb") as fh:
            response = requests.post(
                f"https://graph.facebook.com/v21.0/{video_id}/thumbnails",
                data={"is_preferred": "true", "access_token": token},
                files={"source": (thumb.name, fh, "image/jpeg")},
                timeout=120,
            )
        if response.status_code in (200, 201):
            print("[facebook] thumbnail set")
        else:
            print(f"[facebook] thumbnail skipped ({response.status_code})")
    except requests.RequestException as exc:
        print(f"[facebook] thumbnail skipped ({exc})")


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
    size = video.stat().st_size

    print(f"[facebook] {video.name} ({size // (1024 * 1024)} MB)")
    start = _post(
        f"{BASE_URL}/{page_id}/videos",
        data={
            "upload_phase": "start",
            "file_size": str(size),
            "title": title,
            "description": description,
            "published": "true",
            "access_token": token,
        },
        timeout=120,
    )
    if start.status_code not in (200, 201):
        print(f"[facebook] failed to start ({start.status_code}): {start.text[:300]}")
        return False

    session = start.json()
    session_id = session["upload_session_id"]
    video_id = session["video_id"]
    start_offset = int(session["start_offset"])
    end_offset = int(session["end_offset"])

    with open(video, "rb") as fh:
        while start_offset < size:
            fh.seek(start_offset)
            chunk = fh.read(end_offset - start_offset)
            part = _post(
                f"{BASE_URL}/{page_id}/videos",
                data={
                    "upload_phase": "transfer",
                    "upload_session_id": session_id,
                    "start_offset": str(start_offset),
                    "end_offset": str(end_offset),
                    "access_token": token,
                },
                files={"video_file_chunk": ("chunk", chunk, "application/octet-stream")},
            )
            if part.status_code not in (200, 201):
                print(f"[facebook] chunk failed ({part.status_code}): {part.text[:300]}")
                return False
            offsets = part.json()
            start_offset = int(offsets["start_offset"])
            end_offset = int(offsets["end_offset"]) or size
            print(f"[facebook] uploaded {min(start_offset, size) * 100 // size}%")

    finish = _post(
        f"{BASE_URL}/{page_id}/videos",
        data={
            "upload_phase": "finish",
            "upload_session_id": session_id,
            "access_token": token,
        },
        timeout=600,
    )
    if finish.status_code not in (200, 201) or not finish.json().get("success"):
        print(f"[facebook] failed to finish ({finish.status_code}): {finish.text[:300]}")
        return False

    if thumb.exists():
        _set_thumbnail(video_id, token, thumb)

    print(f"[facebook] published https://www.facebook.com/{video_id}")
    return True


if __name__ == "__main__":
    sys.exit(0 if upload() else 1)
