"""
Update thumbnails for previous Velocity Hebrew videos on YouTube.
- Fetches the last N videos from the channel's uploads playlist.
- Identifies the category for each video from its title/description.
- Generates a custom thumbnail using generate_thumbnail() (with LRU background cycling,
  center smile curve, brush swoosh, and Hebrew gold translation).
- Uploads the new thumbnail directly to YouTube via Data API v3.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseUpload

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from upload_to_youtube import get_authenticated_service, compress_thumbnail
from generate_thumbnail import generate_thumbnail
from youtube_longform_automation import CATEGORIES_HEBREW


def detect_category(title: str, description: str):
    """
    Detects the English category and Hebrew translation from video title or description.
    """
    # 1. Check exact category match in title
    for cat_en, cat_he in CATEGORIES_HEBREW.items():
        if cat_en.lower() in title.lower():
            return cat_en, cat_he
            
    # 2. Check exact category match in description
    for cat_en, cat_he in CATEGORIES_HEBREW.items():
        if cat_en.lower() in description.lower():
            return cat_en, cat_he
            
    # 3. Check partial keywords
    title_clean = title.replace("|", " ").replace("-", " ")
    for cat_en, cat_he in CATEGORIES_HEBREW.items():
        words = [w.lower() for w in cat_en.split() if len(w) > 3]
        if any(w in title_clean.lower() for w in words):
            return cat_en, cat_he
            
    # 4. Fallback default
    return "Daily Life", CATEGORIES_HEBREW.get("Daily Life", "חיי היומיום")


def update_previous_thumbnails(count: int = 10):
    print(f"\n=======================================================")
    print(f"  Updating thumbnails for the last {count} Velocity Hebrew videos")
    print(f"=======================================================\n")

    youtube = get_authenticated_service()

    # 1. Get channel's uploads playlist ID
    channels_res = youtube.channels().list(mine=True, part="contentDetails").execute()
    if not channels_res.get("items"):
        print("[ERROR] No channel found for authenticated user.")
        return False
        
    uploads_id = channels_res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"[youtube] Uploads playlist ID: {uploads_id}")

    # 2. Fetch last `count` videos
    playlist_items = []
    next_token = None
    while len(playlist_items) < count:
        fetch_limit = min(50, count - len(playlist_items))
        res = youtube.playlistItems().list(
            playlistId=uploads_id,
            part="snippet,contentDetails",
            maxResults=fetch_limit,
            pageToken=next_token
        ).execute()
        items = res.get("items", [])
        if not items:
            break
        playlist_items.extend(items)
        next_token = res.get("nextPageToken")
        if not next_token:
            break

    print(f"[youtube] Found {len(playlist_items)} videos to process.\n")

    temp_dir = BASE_DIR / "output" / "updated_thumbnails"
    temp_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0

    for idx, item in enumerate(playlist_items[:count], 1):
        vid_id = item["contentDetails"]["videoId"]
        title = item["snippet"]["title"]
        desc = item["snippet"].get("description", "")
        
        cat_en, cat_he = detect_category(title, desc)
        print(f"[{idx}/{len(playlist_items)}] Video ID: {vid_id}")
        print(f"    Title: {title[:75]}...")
        print(f"    Detected Category: {cat_en} ({cat_he})")
        
        # Generate new thumbnail
        thumb_out = temp_dir / f"thumb_{vid_id}.jpg"
        try:
            generate_thumbnail(cat_en, cat_he, str(thumb_out))
            print(f"    Generated thumbnail: {thumb_out.name} ({thumb_out.stat().st_size // 1024} KB)")
            
            # Upload to YouTube
            thumb_stream = compress_thumbnail(str(thumb_out))
            youtube.thumbnails().set(
                videoId=vid_id,
                media_body=MediaIoBaseUpload(thumb_stream, mimetype="image/jpeg", resumable=False)
            ).execute()
            print(f"    SUCCESS: Thumbnail updated on YouTube!\n")
            success_count += 1
        except Exception as e:
            print(f"    FAILED to update thumbnail: {e}\n")
            fail_count += 1

    print("=======================================================")
    print(f"  SUMMARY: {success_count} succeeded, {fail_count} failed")
    print("=======================================================\n")
    return success_count > 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update previous video thumbnails on YouTube")
    parser.add_argument("--count", type=int, default=10, help="Number of recent videos to update (default: 10)")
    args = parser.parse_args()

    ok = update_previous_thumbnails(args.count)
    sys.exit(0 if ok else 1)
