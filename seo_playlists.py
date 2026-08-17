import os, sys, re, time, json
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

YT_CLIENT_ID = os.getenv("YT_CLIENT_ID") or os.getenv("YOUTUBE_CLIENT_ID", "")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET") or os.getenv("YOUTUBE_CLIENT_SECRET", "")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN") or os.getenv("YOUTUBE_REFRESH_TOKEN", "")

# Per-language SEO settings (edit these per repo)
LANG_NAME = os.getenv("LANG_NAME", "Japanese")
LANG_FOLDER = os.getenv("LANG_FOLDER", "japanese")
FLAG = os.getenv("FLAG", "🇯🇵")
SEO_PLAYLIST = os.getenv("SEO_PLAYLIST", f"Learn {LANG_NAME} Phrases for Beginners | Velocity {LANG_NAME}")
OLD_PLAYLIST = os.getenv("OLD_PLAYLIST", f"Velocity {LANG_NAME} - {LANG_NAME} Phrases")
CHANNEL_KEYWORDS = os.getenv("CHANNEL_KEYWORDS", f"learn {LANG_FOLDER}, {LANG_FOLDER} phrases, {LANG_FOLDER} for beginners, speak {LANG_FOLDER}, {LANG_FOLDER} language, {LANG_FOLDER} vocabulary, learn {LANG_FOLDER} fast")
CHANNEL_DESCRIPTION = os.getenv("CHANNEL_DESCRIPTION", "")
DEFAULT_CHANNEL_DESCRIPTION = (
    f"Learn {LANG_NAME} with Velocity {LANG_NAME}! {FLAG} "
    f"Daily {LANG_NAME} phrase videos with English translations, "
    f"{LANG_NAME} pronunciation guides, and phonetic spelling. "
    f"Perfect for beginners learning {LANG_NAME} fast. "
    f"Each video covers practical {LANG_NAME} phrases for everyday conversations, "
    f"travel, love, motivation, and more. "
    f"Subscribe to master {LANG_NAME} vocabulary step by step. "
    f"Learn {LANG_NAME} • Speak {LANG_NAME} • {LANG_NAME} Phrases for Beginners"
)


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


def _quota_wait(e, attempts):
    msg = str(e)
    if "quotaExceeded" in msg or "403" in msg or "Quota" in msg:
        wait = min(60, 5 * (2 ** attempts))
        print(f"  [quota] quota exceeded, waiting {wait}s...")
        time.sleep(wait)
        return True
    return False


def _execute_with_retry(req, attempts=6):
    for i in range(attempts):
        try:
            return req.execute()
        except Exception as e:
            msg = str(e)
            # quota (403) OR propagation lag (404) OR transient - wait and retry
            if "quotaExceeded" in msg or "403" in msg or "Quota" in msg:
                wait = min(60, 5 * (2 ** i))
                print(f"  [retry] quota exceeded, waiting {wait}s...")
                time.sleep(wait)
                continue
            if "404" in msg:
                wait = 3 + i * 2
                print(f"  [retry] not found (propagation lag?), waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("retries exhausted")


def ensure_seo_playlist(youtube):
    """Find the SEO playlist; if only the old-name playlist exists, rename it.
    If neither exists, create the SEO playlist. Returns playlist_id."""
    # list all playlists
    playlists = _execute_with_retry(youtube.playlists().list(part="snippet", mine=True, maxResults=50))
    items = playlists.get("items", [])
    seo_id = None
    old_id = None
    for p in items:
        title = p["snippet"]["title"]
        if title == SEO_PLAYLIST:
            seo_id = p["id"]
        elif title == OLD_PLAYLIST:
            old_id = p["id"]

    if seo_id:
        print(f"  [found] SEO playlist exists: {SEO_PLAYLIST} (id={seo_id})")
        return seo_id

    if old_id:
        # rename old playlist to SEO name (keeps all videos)
        _execute_with_retry(youtube.playlists().update(
            part="snippet,status",
            body={
                "id": old_id,
                "snippet": {"title": SEO_PLAYLIST,
                            "description": f"All {LANG_FOLDER} phrases videos in one playlist. {FLAG} Learn {LANG_NAME} with Velocity {LANG_NAME}!"},
                "status": {"privacyStatus": "public"}
            }
        ))
        print(f"  [renamed] old playlist '{OLD_PLAYLIST}' -> '{SEO_PLAYLIST}' (id={old_id})")
        return old_id

    # create new
    body = {
        "snippet": {"title": SEO_PLAYLIST,
                    "description": f"All {LANG_FOLDER} phrases videos in one playlist. {FLAG} Learn {LANG_NAME} with Velocity {LANG_NAME}!"},
        "status": {"privacyStatus": "public"}
    }
    resp = _execute_with_retry(youtube.playlists().insert(part="snippet,status", body=body))
    print(f"  [created] SEO playlist: {SEO_PLAYLIST} (id={resp['id']})")
    return resp["id"]


def get_uploads_playlist_id(youtube):
    ch = _execute_with_retry(youtube.channels().list(part="contentDetails", mine=True))
    return ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_all_video_ids(youtube, playlist_id):
    ids = []
    token = None
    while True:
        resp = _execute_with_retry(youtube.playlistItems().list(
            part="contentDetails", playlistId=playlist_id, maxResults=50, pageToken=token))
        for it in resp.get("items", []):
            ids.append(it["contentDetails"]["videoId"])
        token = resp.get("nextPageToken")
        if not token:
            break
    return ids


def get_playlist_video_ids(youtube, playlist_id):
    return get_all_video_ids(youtube, playlist_id)


def add_video(youtube, playlist_id, video_id):
    _execute_with_retry(youtube.playlistItems().insert(
        part="snippet",
        body={"snippet": {"playlistId": playlist_id,
                          "resourceId": {"kind": "youtube#video", "videoId": video_id}}}
    ))
    print(f"  [added] {video_id}")


def update_channel_seo(youtube):
    """Update channel keywords and description for SEO via brandingSettings."""
    try:
        ch = _execute_with_retry(youtube.channels().list(part="snippet,brandingSettings", mine=True))
        channel_id = ch["items"][0]["id"]
        snippet = ch["items"][0]["snippet"]
        branding = ch["items"][0].get("brandingSettings", {})
        channel_snip = branding.get("channel", {})
        new_desc = CHANNEL_DESCRIPTION or DEFAULT_CHANNEL_DESCRIPTION or channel_snip.get("description", "")
        title = snippet.get("title", "")

        # Keywords + description live in brandingSettings.channel - single call
        _execute_with_retry(youtube.channels().update(
            part="brandingSettings",
            body={
                "id": channel_id,
                "brandingSettings": {
                    "channel": {
                        "title": title,
                        "description": new_desc,
                        "keywords": CHANNEL_KEYWORDS,
                        "country": channel_snip.get("country", ""),
                        "defaultTab": channel_snip.get("defaultTab", "Videos"),
                        "showRelatedChannels": True,
                    }
                }
            }
        ))
        print(f"  [channel] branding updated: keywords={CHANNEL_KEYWORDS[:50]}... desc={new_desc[:40]}...")
    except Exception as e:
        print(f"  [channel] update failed: {e}")


def main():
    dry = os.getenv("DRY_RUN", "1") == "1"
    youtube = get_authenticated_service()

    print(f"=== {LANG_NAME} playlist/channel SEO ===")
    playlist_id = ensure_seo_playlist(youtube)
    uploads_id = get_uploads_playlist_id(youtube)
    all_vids = get_all_video_ids(youtube, uploads_id)
    in_playlist = set(get_playlist_video_ids(youtube, playlist_id))
    missing = [v for v in all_vids if v not in in_playlist]
    print(f"  total uploads: {len(all_vids)}, in playlist: {len(in_playlist)}, missing: {len(missing)}")
    if not dry:
        added = 0
        for v in missing:
            add_video(youtube, playlist_id, v)
            added += 1
            time.sleep(0.5)
        print(f"  added {added} videos to playlist")
    else:
        print(f"  (dry run) would add {len(missing)} videos")

    if os.getenv("UPDATE_CHANNEL", "0") == "1":
        update_channel_seo(youtube)
    print("=== done ===")


if __name__ == "__main__":
    main()
