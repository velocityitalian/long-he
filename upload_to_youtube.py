import os, sys, json, time, re, io
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

load_dotenv()

YT_CLIENT_ID = os.getenv("YT_CLIENT_ID") or os.getenv("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET") or os.getenv("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN") or os.getenv("YOUTUBE_REFRESH_TOKEN", "")


def get_authenticated_service():
    if not all([YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN]):
        raise ValueError("Missing YouTube credentials")
    creds = Credentials(
        None, refresh_token=YT_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YT_CLIENT_ID, client_secret=YT_CLIENT_SECRET
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def compress_thumbnail(img_path, max_size=2097152):
    img = Image.open(img_path)
    thumb_bytes = io.BytesIO()
    quality = 85
    img.save(thumb_bytes, format="JPEG", quality=quality)
    while thumb_bytes.tell() > max_size and quality > 10:
        quality -= 10
        thumb_bytes = io.BytesIO()
        img.save(thumb_bytes, format="JPEG", quality=quality)
    thumb_bytes.seek(0)
    return thumb_bytes



def ensure_playlist(youtube, title="Velocity Hebrew - Hebrew Phrases", description="All Hebrew phrases videos in one playlist. Learn Hebrew with Velocity Hebrew!"):
    """Find an existing playlist by title or create a new one. Returns playlist_id."""
    try:
        req = youtube.playlists().list(part="snippet", mine=True, maxResults=50)
        playlists = req.execute().get("items", [])
        for p in playlists:
            if p["snippet"]["title"] == title:
                print(f"[youtube] Found existing playlist: {title} (id={p['id']})")
                return p["id"]
    except Exception as e:
        print(f"[youtube] Playlist lookup failed: {e}")
    try:
        body = {
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": "public"}
        }
        resp = youtube.playlists().insert(part="snippet,status", body=body).execute()
        pid = resp["id"]
        print(f"[youtube] Created playlist: {title} (id={pid})")
        # YouTube API propagation lag - wait until the playlist is visible
        for _ in range(5):
            try:
                youtube.playlists().list(part="id", mine=True, maxResults=50).execute()
                youtube.playlistItems().list(part="id", playlistId=pid, maxResults=1).execute()
                break
            except Exception:
                time.sleep(2)
        return pid
    except Exception as e:
        print(f"[youtube] Playlist creation failed: {e}")
        return None


def add_video_to_playlist(youtube, playlist_id, video_id):
    """Add a video to a playlist. Skips if already present."""
    if not playlist_id or not video_id:
        return False
    try:
        items = youtube.playlistItems().list(part="contentDetails", playlistId=playlist_id, maxResults=50).execute().get("items", [])
        existing = {i["contentDetails"]["videoId"] for i in items}
        if video_id in existing:
            print(f"[youtube] Video already in playlist: {video_id}")
            return True
    except Exception as e:
        print(f"[youtube] Playlist items check failed: {e}")
    try:
        youtube.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
        print(f"[youtube] Added video {video_id} to playlist {playlist_id}")
        return True
    except Exception as e:
        print(f"[youtube] Playlist insert failed: {e}")
        return False


def backfill_playlist(youtube, playlist_id, max_videos=100):
    """Add all existing channel phrase videos to the playlist (idempotent)."""
    if not playlist_id:
        return
    try:
        channel_req = youtube.channels().list(part="contentDetails", mine=True).execute()
        uploads_id = channel_req["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    except Exception as e:
        print(f"[youtube] Could not get uploads playlist: {e}")
        return
    existing = set()
    try:
        items = youtube.playlistItems().list(part="contentDetails", playlistId=playlist_id, maxResults=50).execute().get("items", [])
        existing = {i["contentDetails"]["videoId"] for i in items}
    except Exception as e:
        print(f"[youtube] Playlist items check failed: {e}")
    try:
        uploaded = youtube.playlistItems().list(part="contentDetails,snippet", playlistId=uploads_id, maxResults=max_videos).execute().get("items", [])
        added = 0
        for item in uploaded:
            vid = item["contentDetails"]["videoId"]
            if vid in existing:
                continue
            try:
                youtube.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
                existing.add(vid)
                added += 1
            except Exception as e:
                print(f"[youtube] Backfill failed for {vid}: {e}")
        print(f"[youtube] Playlist backfill done: added {added} videos")
    except Exception as e:
        print(f"[youtube] Backfill error: {e}")


def sanitize_for_youtube(text):
    """Strip zero-width/control chars and lone surrogates; keep emoji+accents."""
    if not text:
        return ""
    text = "".join(c for c in text if not (0x200B <= ord(c) <= 0x200F) and not (0x202A <= ord(c) <= 0x202E))
    text = re.sub(r"[\x00-\x1f\x7f\ufeff]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def upload_to_youtube():
    try:
        meta_path = Path("output") / "latest_video.json"
        if not meta_path.exists():
            print("[youtube] No latest_video.json found")
            return False

        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        video_path = Path(meta["video_path"])
        if not video_path.exists():
            print(f"[youtube] Video not found: {video_path}")
            return False

        title = sanitize_for_youtube(meta["title"])
        if len(title) > 100:
            title = title[:97] + "..."
        description = sanitize_for_youtube(meta["description"])
        if len(description) > 4900:
            description = description[:4900]
            cut = description.rfind("\n\n")
            if cut > 3000:
                description = description[:cut]
            description += "\n\n#LearnHebrew #Hebrew #LanguageLearning"
            print(f"[youtube] Description truncated to {len(description)} chars")
        tags = [sanitize_for_youtube(t) for t in meta.get("tags", []) if t]

        print(f"[youtube] Title: {title[:80]}...")
        print(f"[youtube] Video: {video_path}")

        youtube = get_authenticated_service()

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "27"
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            }
        }

        media = MediaFileUpload(str(video_path), chunksize=1024*1024*10, resumable=True)
        request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"[youtube] Upload: {int(status.progress() * 100)}%")

        video_id = response["id"]
        print(f"[youtube] Uploaded! ID: {video_id}")
        print(f"[youtube] URL: https://youtube.com/watch?v={video_id}")

        thumbnail_path = Path(meta.get("thumbnail_path", ""))
        print(f"[youtube] Checking thumbnail: {thumbnail_path}")
        if thumbnail_path.exists():
            print(f"[youtube] Thumbnail file found ({thumbnail_path.stat().st_size // 1024}KB)")
            try:
                thumb_bytes = compress_thumbnail(str(thumbnail_path))
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaIoBaseUpload(thumb_bytes, mimetype="image/jpeg", resumable=False)
                ).execute()
                print(f"[youtube] Thumbnail uploaded!")
            except Exception as e:
                print(f"[youtube] Thumbnail upload failed: {e}")
        else:
            print(f"[youtube] Thumbnail NOT FOUND at: {thumbnail_path}")

        playlist_id = ensure_playlist(youtube)
        if playlist_id:
            add_video_to_playlist(youtube, playlist_id, video_id)
            backfill_playlist(youtube, playlist_id)

        result = {
            "video_id": video_id,
            "url": f"https://youtube.com/watch?v={video_id}",
            "title": title,
            "uploaded_at": str(Path(meta_path).stat().st_mtime)
        }
        with open("output/upload_result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"[youtube] Success!")
        return True

    except Exception as e:
        print(f"[youtube] Failed: {e}")
        return False


if __name__ == "__main__":
    success = upload_to_youtube()
    sys.exit(0 if success else 1)
