"""Upload the freshly built lesson to YouTube with SEO metadata and thumbnail."""

from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from PIL import Image

load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

YT_CLIENT_ID = os.getenv("YT_CLIENT_ID") or os.getenv("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET") or os.getenv("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN") or os.getenv("YOUTUBE_REFRESH_TOKEN", "")

META_PATH = Path("output") / "latest_video.json"
RESULT_PATH = Path("output") / "upload_result.json"


def get_authenticated_service():
    if not all([YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN]):
        raise ValueError("Missing YouTube credentials")
    creds = Credentials(
        None,
        refresh_token=YT_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID,
        client_secret=YT_CLIENT_SECRET,
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def compress_thumbnail(path: str, max_size: int = 2 * 1024 * 1024):
    img = Image.open(path).convert("RGB")
    buffer = io.BytesIO()
    quality = 92
    img.save(buffer, format="JPEG", quality=quality)
    while buffer.tell() > max_size and quality > 20:
        quality -= 6
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)
    return buffer


def upload():
    if not META_PATH.exists():
        print("[youtube] latest_video.json missing - skipping")
        return False

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    video_path = Path(meta["video_path"])
    if not video_path.exists():
        print(f"[youtube] video not found: {video_path}")
        return False

    title = str(meta.get("title", ""))[:100]
    description = str(meta.get("description", ""))[:4900]
    tags = meta.get("tags", [])
    language_code = meta.get("language_code", "")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": str(meta.get("category_id", "27")),
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }
    if language_code:
        body["snippet"]["defaultLanguage"] = language_code
        body["snippet"]["defaultAudioLanguage"] = language_code

    print(f"[youtube] {title}")
    print(f"[youtube] {video_path.name} ({video_path.stat().st_size // (1024 * 1024)} MB)")

    youtube = get_authenticated_service()
    media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    error = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"[youtube] upload {int(status.progress() * 100)}%")
        except Exception as exc:  # noqa: BLE001 - resumable retry boundary
            error = exc
            print(f"[youtube] chunk failed, retrying: {exc}")
            time.sleep(5)

    video_id = response["id"]
    url = f"https://youtube.com/watch?v={video_id}"
    print(f"[youtube] published {url}")

    thumb = Path(meta.get("thumbnail_path", ""))
    if thumb.exists():
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaIoBaseUpload(compress_thumbnail(str(thumb)), mimetype="image/jpeg", resumable=False),
            ).execute()
            print("[youtube] thumbnail set")
        except Exception as exc:  # noqa: BLE001 - thumbnail is best effort
            print(f"[youtube] thumbnail failed: {exc}")

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps({"video_id": video_id, "url": url, "title": title, "uploaded_at": time.time()}, indent=2),
        encoding="utf-8",
    )
    return True


if __name__ == "__main__":
    try:
        sys.exit(0 if upload() else 1)
    except Exception as exc:  # noqa: BLE001 - workflow boundary
        print(f"[youtube] failed: {exc}")
        sys.exit(1)
