"""
Facebook Page Video Upload Script
Robust uploader for educational videos and reels to Facebook Pages using Meta Graph API.
Includes automatic metadata detection, thumbnail attachment, resumable fallback, and retry logic.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()

def safe_print(msg: str):
    """Print message safely across all platforms and Windows code pages."""
    try:
        print(msg)
    except UnicodeEncodeError:
        safe_msg = msg.encode("ascii", "replace").decode("ascii")
        print(safe_msg)


def mask_secret(s: str) -> str:
    """Safely mask tokens for logs without leaking."""
    if not s:
        return "NOT SET"
    if len(s) > 8:
        return f"{s[:4]}...{s[-4:]}"
    return "***"


def get_latest_video():
    """Find the most recently generated long-form video directory and files."""
    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir / "output" / "longform_videos",
        base_dir.parent / "output" / "longform_videos",
        Path.cwd() / "output" / "longform_videos",
    ]
    
    longform_dir = None
    for cand in candidates:
        if cand.exists():
            longform_dir = cand
            break
            
    if not longform_dir:
        safe_print("[Facebook] Note: No 'output/longform_videos' directory found")
        return None

    dirs = sorted(
        [d for d in longform_dir.iterdir() if d.is_dir()],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    if not dirs:
        safe_print("[Facebook] Note: No video folders found in output/longform_videos")
        return None

    latest_dir = dirs[0]
    video_file = latest_dir / "final_video.mp4"
    metadata_file = latest_dir / "video_metadata.json"
    info_file = latest_dir / "youtube_upload_info.txt"
    thumbnail_file = latest_dir / "thumbnail.jpg"

    if not video_file.exists():
        safe_print(f"[Facebook] Note: Video file not found: {video_file}")
        return None

    if not thumbnail_file.exists():
        phrase_images = sorted(latest_dir.glob("phrase_*.jpg"))
        if phrase_images:
            thumbnail_file = phrase_images[0]
        else:
            thumbnail_file = None

    return {
        "dir": latest_dir,
        "video": video_file,
        "thumbnail": thumbnail_file if thumbnail_file and thumbnail_file.exists() else None,
        "metadata": metadata_file if metadata_file.exists() else None,
        "info": info_file if info_file.exists() else None
    }


def parse_video_metadata(video_info: dict):
    """Extract clean title and description from metadata or info file."""
    title = "Language Learning Video"
    description = ""

    if video_info.get("metadata") and video_info["metadata"].exists():
        try:
            with open(video_info["metadata"], "r", encoding="utf-8") as f:
                meta = json.load(f)
                title = meta.get("selected_title", title)
                description = meta.get("description", "")
        except Exception as e:
            safe_print(f"[Facebook] Notice: Could not read video_metadata.json: {e}")

    if not description and video_info.get("info") and video_info["info"].exists():
        try:
            with open(video_info["info"], "r", encoding="utf-8") as f:
                content = f.read()
                if "SELECTED TITLE" in content:
                    title_part = content.split("SELECTED TITLE")[1].split("---")[1].strip()
                    title = title_part.splitlines()[0].strip()
                if "VIDEO DESCRIPTION:" in content:
                    description = content.split("VIDEO DESCRIPTION:")[1].split("---")[1].strip()
        except Exception as e:
            safe_print(f"[Facebook] Notice: Could not read youtube_upload_info.txt: {e}")

    # Trim description if exceeds limit
    if len(description) > 5000:
        description = description[:4950] + "\n\n..."

    return title, description


def upload_to_facebook_page(video_path, title, description, thumbnail_path=None, page_id=None, access_token=None):
    """
    Uploads a video to a Facebook Page via Graph Video API.
    Supports direct multipart upload and chunked resumable upload fallback.
    """
    access_token = access_token or os.getenv("FACEBOOK_ACCESS_TOKEN") or os.getenv("FB_ACCESS_TOKEN")
    page_id = page_id or os.getenv("FACEBOOK_PAGE_ID") or os.getenv("FB_PAGE_ID")

    if not access_token or not page_id:
        safe_print("[Facebook] Notice: FACEBOOK_ACCESS_TOKEN or FACEBOOK_PAGE_ID not provided. Skipping upload.")
        return None

    video_path = Path(video_path)
    if not video_path.exists():
        safe_print(f"[Facebook] Error: Video file not found: {video_path}")
        return None

    file_size = video_path.stat().st_size
    file_size_mb = file_size / (1024 * 1024)

    safe_print("\n" + "=" * 60)
    safe_print("FACEBOOK PAGE VIDEO UPLOAD")
    safe_print("=" * 60)
    safe_print(f"[Facebook] Page ID: {page_id}")
    safe_print(f"[Facebook] Token: {mask_secret(access_token)}")
    safe_print(f"[Facebook] Video: {video_path.name} ({file_size_mb:.2f} MB)")
    safe_print(f"[Facebook] Title: {title[:70]}...")
    if thumbnail_path and Path(thumbnail_path).exists():
        safe_print(f"[Facebook] Thumbnail: {Path(thumbnail_path).name}")

    # Attempt 1: Direct upload via graph-video (fastest and most reliable for files < 100MB)
    direct_url = f"https://graph-video.facebook.com/v21.0/{page_id}/videos"
    max_retries = 3

    for attempt in range(1, max_retries + 1):
        safe_print(f"[Facebook] Upload attempt {attempt}/{max_retries}...")
        try:
            data = {
                "title": title,
                "description": description,
                "access_token": access_token
            }
            files = {
                "source": (video_path.name, open(video_path, "rb"), "video/mp4")
            }
            if thumbnail_path and Path(thumbnail_path).exists():
                files["thumb"] = (Path(thumbnail_path).name, open(thumbnail_path, "rb"), "image/jpeg")

            res = requests.post(direct_url, data=data, files=files, timeout=600)
            
            # Close files
            for f_tuple in files.values():
                try:
                    f_tuple[1].close()
                except:
                    pass

            if res.status_code in [200, 201]:
                res_data = res.json()
                video_id = res_data.get("id")
                if video_id:
                    safe_print("\n" + "=" * 60)
                    safe_print("SUCCESS: FACEBOOK VIDEO UPLOAD COMPLETE!")
                    safe_print(f"[Facebook] Video ID: {video_id}")
                    safe_print(f"[Facebook] Video URL: https://www.facebook.com/{video_id}")
                    safe_print("=" * 60)
                    return {
                        "video_id": video_id,
                        "url": f"https://www.facebook.com/{video_id}",
                        "page_id": page_id,
                        "status": "success",
                        "title": title,
                        "uploaded_at": datetime.now().isoformat()
                    }
            
            err_msg = res.text
            safe_print(f"[Facebook] Attempt {attempt} response {res.status_code}: {err_msg[:300]}")
            if attempt < max_retries:
                wait_time = attempt * 5
                safe_print(f"[Facebook] Retrying in {wait_time}s...")
                time.sleep(wait_time)

        except requests.exceptions.Timeout:
            safe_print(f"[Facebook] Attempt {attempt} timed out.")
            if attempt < max_retries:
                time.sleep(5)
        except Exception as e:
            safe_print(f"[Facebook] Attempt {attempt} error: {e}")
            if attempt < max_retries:
                time.sleep(5)

    # Attempt 2: Resumable Chunked Upload fallback
    safe_print("[Facebook] Direct upload did not succeed, trying Resumable Session Upload...")
    try:
        # Phase 1: Start
        start_url = f"https://graph.facebook.com/v21.0/{page_id}/videos"
        start_payload = {
            "upload_phase": "start",
            "file_size": file_size,
            "access_token": access_token
        }
        res_start = requests.post(start_url, data=start_payload, timeout=30)
        if res_start.status_code == 200:
            start_data = res_start.json()
            upload_session_id = start_data.get("upload_session_id")
            video_id = start_data.get("video_id")
            start_offset = int(start_data.get("start_offset", 0))
            end_offset = int(start_data.get("end_offset", file_size))

            # Phase 2: Transfer chunk
            transfer_url = f"https://graph-video.facebook.com/v21.0/{page_id}/videos"
            with open(video_path, "rb") as f:
                f.seek(start_offset)
                chunk = f.read(end_offset - start_offset)
                transfer_data = {
                    "upload_phase": "transfer",
                    "upload_session_id": upload_session_id,
                    "start_offset": start_offset,
                    "access_token": access_token
                }
                transfer_files = {
                    "video_file_chunk": ("chunk.mp4", chunk, "application/octet-stream")
                }
                res_transfer = requests.post(transfer_url, data=transfer_data, files=transfer_files, timeout=600)
                if res_transfer.status_code == 200:
                    # Phase 3: Finish
                    finish_url = f"https://graph.facebook.com/v21.0/{page_id}/videos"
                    finish_payload = {
                        "upload_phase": "finish",
                        "upload_session_id": upload_session_id,
                        "title": title,
                        "description": description,
                        "access_token": access_token
                    }
                    res_finish = requests.post(finish_url, data=finish_payload, timeout=60)
                    if res_finish.status_code in [200, 201] and res_finish.json().get("success"):
                        final_id = video_id or res_finish.json().get("id")
                        safe_print("\n" + "=" * 60)
                        safe_print("SUCCESS: FACEBOOK RESUMABLE UPLOAD COMPLETE!")
                        safe_print(f"[Facebook] Video ID: {final_id}")
                        safe_print(f"[Facebook] Video URL: https://www.facebook.com/{final_id}")
                        safe_print("=" * 60)
                        return {
                            "video_id": final_id,
                            "url": f"https://www.facebook.com/{final_id}",
                            "page_id": page_id,
                            "status": "success",
                            "title": title,
                            "uploaded_at": datetime.now().isoformat()
                        }
                    else:
                        safe_print(f"[Facebook] Finish phase error: {res_finish.text}")
                else:
                    safe_print(f"[Facebook] Transfer phase error: {res_transfer.text}")
        else:
            safe_print(f"[Facebook] Start phase error: {res_start.text}")
    except Exception as e:
        safe_print(f"[Facebook] Resumable upload error: {e}")

    safe_print("[Facebook] Upload failed after all attempts.")
    return None


def upload_to_facebook(video_path, description, title="Language Learning Video", thumbnail_path=None):
    """Convenience function for compatibility with existing scripts."""
    return upload_to_facebook_page(
        video_path=video_path,
        title=title,
        description=description,
        thumbnail_path=thumbnail_path
    )


def main():
    """Main CLI entry point for workflow and local execution."""
    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN") or os.getenv("FB_ACCESS_TOKEN")
    page_id = os.getenv("FACEBOOK_PAGE_ID") or os.getenv("FB_PAGE_ID")

    if not access_token or not page_id:
        safe_print("[Facebook] Notice: FACEBOOK_ACCESS_TOKEN or FACEBOOK_PAGE_ID is not set. Skipping Facebook upload.")
        # Return 0 so workflows without Facebook pages proceed normally
        return 0

    video_info = get_latest_video()
    if not video_info:
        safe_print("[Facebook] Notice: No video found to upload. Skipping.")
        return 0

    title, description = parse_video_metadata(video_info)
    result = upload_to_facebook_page(
        video_path=video_info["video"],
        title=title,
        description=description,
        thumbnail_path=video_info.get("thumbnail"),
        page_id=page_id,
        access_token=access_token
    )

    if result:
        result_path = video_info["dir"] / "facebook_upload_result.json"
        try:
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            safe_print(f"[Facebook] Saved result to: {result_path}")
        except Exception as e:
            safe_print(f"[Facebook] Warning: Could not save result file: {e}")
        return 0
    else:
        safe_print("[Facebook] Warning: Video upload to Facebook did not complete successfully.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
