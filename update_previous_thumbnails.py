"""
Update thumbnails for previous Velocity Hebrew LONG-FORM videos on YouTube.
- Fetches uploaded videos from the channel.
- Strictly filters ONLY for LONG-FORM videos (duration >= 3 minutes / 180 seconds).
  Automatically skips all YouTube Shorts (<= 60 seconds).
- Identifies the category for each long-form video from its title/description.
- Generates a custom thumbnail using generate_thumbnail() (with LRU background cycling,
  center smile curve, brush swoosh, and Hebrew gold translation).
- Uploads the new thumbnail directly to YouTube via Data API v3.
"""

import os
import sys
import json
import re
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


def parse_duration_seconds(duration_str: str) -> int:
    """Parses ISO 8601 duration string (e.g. PT11M24S, PT58S) to total seconds."""
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str or "")
    if not m:
        return 0
    h, m_, s = m.groups()
    return int(h or 0) * 3600 + int(m_ or 0) * 60 + int(s or 0)


def detect_category(title: str, description: str):
    """
    Detects the English category and Hebrew translation from video title or description.
    """
    # 1. Exact match in title
    for cat_en, cat_he in CATEGORIES_HEBREW.items():
        if cat_en.lower() in title.lower():
            return cat_en, cat_he
            
    # 2. Exact match in description
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


def update_previous_thumbnails(target_longform_count: int = 10):
    print(f"\n=======================================================")
    print(f"  Updating thumbnails for the last {target_longform_count} LONG-FORM videos")
    print(f"  (Strictly skipping Shorts <= 60 seconds)")
    print(f"=======================================================\n")

    youtube = get_authenticated_service()

    # 1. Get channel's uploads playlist ID
    channels_res = youtube.channels().list(mine=True, part="contentDetails").execute()
    if not channels_res.get("items"):
        print("[ERROR] No channel found for authenticated user.")
        return False
        
    uploads_id = channels_res["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"[youtube] Uploads playlist ID: {uploads_id}")

    # 2. Iterate through playlist and collect strictly LONG-FORM videos
    longform_videos = []
    next_token = None
    page = 0
    max_pages = 10  # Search up to 500 uploads to find enough long-form videos

    while len(longform_videos) < target_longform_count and page < max_pages:
        page += 1
        res = youtube.playlistItems().list(
            playlistId=uploads_id,
            part="snippet,contentDetails",
            maxResults=50,
            pageToken=next_token
        ).execute()
        
        items = res.get("items", [])
        if not items:
            break
            
        video_ids = [it["contentDetails"]["videoId"] for it in items]
        
        # Query contentDetails (duration) and snippet for the batch
        v_res = youtube.videos().list(
            id=",".join(video_ids),
            part="snippet,contentDetails"
        ).execute()
        
        video_details = {v["id"]: v for v in v_res.get("items", [])}
        
        for item in items:
            vid = item["contentDetails"]["videoId"]
            v_info = video_details.get(vid)
            if not v_info:
                continue
                
            duration_str = v_info["contentDetails"].get("duration", "")
            duration_sec = parse_duration_seconds(duration_str)
            title = v_info["snippet"]["title"]
            desc = v_info["snippet"].get("description", "")
            
            # Filter: MUST be long-form (at least 3 minutes / 180 seconds)
            # Shorts are always <= 60 seconds (or titled '5 Essential Phrases')
            if duration_sec < 180 or "5 Essential" in title:
                print(f"[SKIP SHORT] ({duration_sec}s): {title[:60]}")
                continue
                
            print(f"[FOUND LONG-FORM #{len(longform_videos)+1}] ({duration_sec // 60}m {duration_sec % 60}s): {title[:65]}")
            longform_videos.append({
                "videoId": vid,
                "title": title,
                "description": desc,
                "duration_sec": duration_sec
            })
            
            if len(longform_videos) >= target_longform_count:
                break
                
        next_token = res.get("nextPageToken")
        if not next_token:
            break

    print(f"\n[youtube] Identified {len(longform_videos)} long-form videos to update.\n")

    if not longform_videos:
        print("[WARNING] No long-form videos found on this channel.")
        return False

    temp_dir = BASE_DIR / "output" / "updated_thumbnails"
    temp_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0

    for idx, vid_info in enumerate(longform_videos, 1):
        vid_id = vid_info["videoId"]
        title = vid_info["title"]
        desc = vid_info["description"]
        duration_m = vid_info["duration_sec"] // 60
        
        cat_en, cat_he = detect_category(title, desc)
        print(f"[{idx}/{len(longform_videos)}] Updating Long-Form Video: {vid_id} ({duration_m} mins)")
        print(f"    Title: {title[:75]}...")
        print(f"    Category: {cat_en} -> {cat_he}")
        
        # Generate new thumbnail with LRU background cycling
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
            print(f"    SUCCESS: Long-form thumbnail updated on YouTube!\n")
            success_count += 1
        except Exception as e:
            print(f"    FAILED to update thumbnail: {e}\n")
            fail_count += 1

    print("=======================================================")
    print(f"  SUMMARY: {success_count} long-form videos updated, {fail_count} failed")
    print("=======================================================")
    return success_count > 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update previous long-form video thumbnails on YouTube")
    parser.add_argument("--count", type=int, default=10, help="Number of recent long-form videos to update (default: 10)")
    args = parser.parse_args()

    ok = update_previous_thumbnails(args.count)
    sys.exit(0 if ok else 1)
