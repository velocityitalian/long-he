import os, sys, re, time
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

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


def reformat_description(desc):
    """Re-insert line breaks into a flattened description based on its structure.
    Language-agnostic: works for any Velocity <Language> channel."""
    if not desc:
        return desc

    # The description was flattened: collapse any existing newlines to single spaces
    text = re.sub(r"\s*\n\s*", " ", desc)
    text = re.sub(r"\s+", " ", text).strip()

    # 1) Blank lines before section markers (language-agnostic emoji headers)
    for marker in ["📚 WHAT YOU'LL LEARN", "⏱️ VIDEO TIMESTAMPS", "📝 ALL",
                   "🎯 PERFECT FOR", "💡 TIPS FOR LEARNING",
                   "🔔 SUBSCRIBE", "👍 LIKE", "💬 COMMENT"]:
        text = re.sub(r"\s+(?=" + re.escape(marker) + ")", "\n\n", text)

    # 2) Newline after the flag header: "<flag> Learn <Lang> with Velocity <Lang>! <flag>"
    text = re.sub(r"(! [🇦-🇿]{2}) ", lambda m: m.group(1) + "\n", text)
    # Generic: newline right before "In this video, you'll learn"
    text = re.sub(r" (In this video, you'll learn)", "\n\n\\1", text)

    # 3) Newline before each timestamp "MM:SS  Phrases X-Y"
    text = re.sub(r"(?=\d{2}:\d{2}\s{2}Phrases \d+-\d+)", "\n", text)

    # 4) Newline before each numbered phrase "N. English" (after a space)
    text = re.sub(r" (?=\d{1,3}\. [A-Z])", "\n", text)

    # 5) Newline before flag emoji lines and phonetic (🔤) lines inside phrases
    #    Only when the flag follows an English phrase (ends in a letter/period),
    #    NOT the header flag at the start. Any regional-indicator flag pair works.
    text = re.sub(r"(?<=[a-zA-Z.,])\s+(?=[🇦-🇿]{2})", "\n    ", text)
    text = re.sub(r" (?=🔤 )", "\n    ", text)

    # 6) Blank line before the hashtag line
    text = re.sub(r" (#\w[\w#]* #)", "\n\n\\1", text, count=1)

    # 7) Blank line before the copyright footer
    text = re.sub(r" (© Velocity)", "\n\n\\1", text)

    # Clean up triple+ newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Sanitize: remove lone surrogates / control chars that YouTube rejects,
    # but KEEP \n and \r (needed for spacing) and real emoji.
    text = "".join(c for c in text
                   if not (0xD800 <= ord(c) <= 0xDFFF)
                   and not (0x00 <= ord(c) <= 0x09)
                   and not (0x0B <= ord(c) <= 0x0C)
                   and not (0x0E <= ord(c) <= 0x1F)
                   and ord(c) not in (0x7F, 0xFEFF))

    # YouTube description limit is 5000 chars - truncate cleanly if needed
    if len(text) > 4900:
        text = text[:4900]
        cut = text.rfind("\n\n")
        if cut > 3000:
            text = text[:cut]
        text += "\n\n... and more!\n\n#LanguageLearning #LearnLanguages"
    return text.strip()


def list_uploads(youtube):
    channel = _execute_with_retry(youtube.channels().list(part="contentDetails", mine=True))
    uploads_id = channel["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    videos = []
    page_token = None
    while True:
        pl = _execute_with_retry(youtube.playlistItems().list(
            part="contentDetails", playlistId=uploads_id, maxResults=50,
            pageToken=page_token))
        for item in pl.get("items", []):
            videos.append(item["contentDetails"]["videoId"])
        page_token = pl.get("nextPageToken")
        if not page_token:
            break
    return videos


def _quota_wait(e, attempts):
    """If quota exceeded (403), wait and return True; else False."""
    msg = str(e)
    if "quotaExceeded" in msg or "403" in msg or "Quota" in msg:
        wait = min(60, 5 * (2 ** attempts))
        print(f"  [quota] quota exceeded, waiting {wait}s...")
        time.sleep(wait)
        return True
    return False


def _execute_with_retry(req, attempts=8):
    """Execute a YouTube API request with quota backoff retry."""
    for i in range(attempts):
        try:
            return req.execute()
        except Exception as e:
            if not _quota_wait(e, i):
                raise
    raise RuntimeError("retries exhausted")


def fix_video(youtube, video_id, dry_run=False):
    v = None
    for attempt in range(6):
        try:
            v = youtube.videos().list(part="snippet", id=video_id).execute()
            break
        except Exception as e:
            if not _quota_wait(e, attempt):
                print(f"  [ERROR] {video_id} list: {e}")
                return False
    if not v or not v.get("items"):
        print(f"  [skip] {video_id} not found")
        return False
    snippet = v["items"][0]["snippet"]
    title = snippet.get("title", "")
    desc = snippet.get("description", "")
    new_desc = reformat_description(desc)
    if new_desc == desc:
        print(f"  [same] {video_id} - no change needed ({title[:40]})")
        return False
    if dry_run:
        print(f"  [DRY] {video_id} - would update ({title[:40]})")
        return True
    for attempt in range(6):
        try:
            youtube.videos().update(
                part="snippet,status",
                body={
                    "id": video_id,
                    "snippet": {
                        "title": title,
                        "description": new_desc,
                        "tags": snippet.get("tags", []),
                        "categoryId": snippet.get("categoryId", "27"),
                    },
                    "status": v["items"][0].get("status", {"privacyStatus": "public"}),
                }
            ).execute()
            print(f"  [UPDATED] {video_id} - {title[:40]} (desc {len(desc)}->{len(new_desc)})")
            return True
        except Exception as e:
            if not _quota_wait(e, attempt):
                print(f"  [ERROR] {video_id}: {e}")
                return False
    print(f"  [ERROR] {video_id}: still failing after retries")
    return False


def main():
    dry = os.getenv("DRY_RUN", "1") == "1"
    youtube = get_authenticated_service()
    videos = list_uploads(youtube)
    print(f"Found {len(videos)} uploaded videos")
    updated = 0
    for vid in videos:
        if fix_video(youtube, vid, dry_run=dry):
            updated += 1
        time.sleep(0.5)
    print(f"Done. {updated} {'would-be updated' if dry else 'updated'} videos.")


if __name__ == "__main__":
    main()
