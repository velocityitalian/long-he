"""Build one Velocity long-form chapter lesson end to end."""

from __future__ import annotations

import argparse
import json
import sys
import time
import webbrowser
from datetime import datetime

import config
from config import CATEGORY_NAMES
from engine import audio, content, renderer, seo, thumbnails, timeline, tts

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

TARGET_SECONDS = 660
MIN_PHRASES_PER_CHAPTER = 5


def _speech_len(clip, words_key, duration_key, pad):
    words = clip.get(words_key) or []
    total = clip.get(duration_key) or 0.0
    if words:
        return min(total, max(w["end"] for w in words) + pad)
    return total


def _phrase_seconds(clip):
    en_len = _speech_len(clip, "en_words", "en_duration", 0.35)
    vi_len = _speech_len(clip, "vi_words", "vi_duration", 0.45)
    return (
        config.EN_CARD_IN + en_len + config.GAP_EN_NATIVE + config.NATIVE_CARD_LEAD
        + vi_len + config.GAP_BEFORE_REPEAT + vi_len + config.TAIL_HOLD
    )


def _lesson_seconds(chapters):
    total = config.INTRO_DURATION + len(chapters) * config.CHAPTER_INTRO_DURATION + config.OUTRO_DURATION
    return total + sum(_phrase_seconds(p["clip"]) for ch in chapters for p in ch["phrases"])


def _trim_to_target(chapters):
    """Drop the tail phrase of the fullest chapter until the lesson lands near 11 minutes."""
    while _lesson_seconds(chapters) > TARGET_SECONDS:
        candidates = [ch for ch in chapters if len(ch["phrases"]) > MIN_PHRASES_PER_CHAPTER]
        if not candidates:
            break
        chapter = max(candidates, key=lambda ch: (len(ch["phrases"]), _phrase_seconds(ch["phrases"][-1]["clip"])))
        chapter["phrases"].pop()
    return [p for ch in chapters for p in ch["phrases"]]


def parse_args():
    parser = argparse.ArgumentParser(description=f"{config.BRAND} longform builder")
    parser.add_argument("--fps", type=int, default=config.FPS, help=f"render fps (default {config.FPS})")
    parser.add_argument("--skip-video", action="store_true", help="build content, audio and timeline only")
    parser.add_argument("--open", action="store_true", help="open the interactive preview when finished")
    parser.add_argument("--list-categories", action="store_true", help="print the topic pool and exit")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.list_categories:
        for i, name in enumerate(CATEGORY_NAMES, 1):
            print(f"{i:2d}. {name} · {config.CATEGORIES[name]}")
        return 0

    print("=" * 78)
    print(f"  {config.BRAND} · LONGFORM CHAPTER LESSON")
    print("=" * 78)

    chapter_names = content.pick_categories(config.TARGET_CHAPTERS)
    per_chapter = config.PHRASES_PER_CHAPTER

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_lang = config.LANGUAGE["name"].replace(" ", "")
    lesson_dir = config.LESSONS_DIR / f"{safe_lang}_Longform_{stamp}"
    audio_dir = lesson_dir / "audio"
    work_dir = lesson_dir / "work"
    lesson_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[1/7] Chapters: {', '.join(chapter_names)}  ({per_chapter} phrases each)")
    print(f"      Output: {lesson_dir}")

    chapters = content.build_lesson(chapter_names, per_chapter)
    flat = [p for ch in chapters for p in ch["phrases"]]
    for ch in chapters:
        print(f"      · {ch['english']} — {len(ch['phrases'])} phrases")
        for p in ch["phrases"]:
            print(f"          {p['english']}")
            print(f"          {p['native']}  [{p['transliteration']}]")

    print(f"\n[2/7] Voice + word clocks ({len(flat)} phrases)")
    clips = tts.synthesize_all(flat, audio_dir)
    i = 0
    for ch in chapters:
        for p in ch["phrases"]:
            p["clip"] = clips[i]
            i += 1

    kept = _trim_to_target(chapters)
    if len(kept) != len(flat):
        print(f"      trimmed to {len(kept)} phrases for a ~{TARGET_SECONDS / 60:.1f} min lesson")
    flat = kept
    clips = [p["clip"] for p in flat]

    print("\n[3/7] Timeline")
    tl = timeline.build_timeline(chapters)
    timeline_path = lesson_dir / "timeline.json"
    timeline_path.write_text(json.dumps(tl, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"      {tl['duration']:.1f}s · {len(tl['phrases'])} phrases · {len(tl['chapters'])} chapters · {len(tl['sfx'])} sfx")

    print("\n[4/7] Music + sound design")
    mix_path = lesson_dir / "mix.wav"
    audio.build_mix(clips, tl, mix_path)

    video_info = {}
    started = time.time()
    if args.skip_video:
        print("\n[5/7] Video skipped (--skip-video)")
    else:
        print("\n[5/7] Animated 1080p video")
        out_mp4 = lesson_dir / "final_longform.mp4"
        video_info = renderer.render_video(tl, mix_path, out_mp4, work_dir, fps=args.fps)
        print(f"      render time: {(time.time() - started) / 60:.1f} min")

    print("\n[6/7] YouTube thumbnails")
    thumb_info = thumbnails.render_thumbnails(chapters, tl, lesson_dir)
    print(f"      picked: {thumb_info['layout']} (thumb_{thumb_info['selected']:02d}.jpg)")

    print("\n[7/7] Preview + metadata")
    preview = renderer.write_preview(tl, mix_path)
    details = seo.build_metadata(chapters, tl)

    metadata = {
        "brand": config.BRAND,
        "handle": config.HANDLE,
        "language": config.LANGUAGE["name"],
        **details,
        "timestamp": stamp,
        "duration": tl["duration"],
        "minutes": tl["minutes"],
        "chapters": [
            {
                "english": ch["english"],
                "native": ch["native"],
                "phrases": [
                    {
                        "english": p["english"],
                        "native": p["native"],
                        "transliteration": p["transliteration"],
                    }
                    for p in ch["phrases"]
                ],
            }
            for ch in chapters
        ],
        "video": video_info.get("video"),
        "cover": video_info.get("cover"),
        "thumbnail": thumb_info["picked"],
        "thumbnail_selected": thumb_info["selected"],
        "thumbnail_layout": thumb_info["layout"],
        "thumbnails": thumb_info["variants"],
        "thumbnails_contact": thumb_info["contact"],
        "audio": str(mix_path),
        "timeline": str(timeline_path),
        "preview": str(preview),
    }
    metadata_path = lesson_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    latest = {
        "video_path": metadata.get("video"),
        "thumbnail_path": thumb_info["picked"],
        "cover_path": metadata.get("cover"),
        "title": details["title"],
        "description": details["description"],
        "tags": details["tags"],
        "category_id": details["category_id"],
        "privacy": details["privacy"],
        "duration_seconds": tl["duration"],
        "minutes": tl["minutes"],
        "lesson_dir": str(lesson_dir),
        "timestamp": stamp,
        "language": config.LANGUAGE["name"],
        "language_code": config.LANGUAGE["code"],
        "handle": config.HANDLE,
    }
    (config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    (config.OUTPUT_DIR / "latest_video.json").write_text(
        json.dumps(latest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (config.OUTPUT_DIR / "latest.txt").write_text(str(lesson_dir), encoding="utf-8")

    print("\n" + "=" * 78)
    print("  LONGFORM LESSON COMPLETE")
    print("=" * 78)
    print(f"  Folder     : {lesson_dir}")
    print(f"  Title      : {details['title']}")
    print(f"  Timeline   : {timeline_path.name}")
    print(f"  Audio mix  : {mix_path.name}")
    if video_info:
        print(f"  Video      : {video_info['video']}")
        print(f"  Cover      : {video_info['cover']}")
    print(f"  Thumbnail  : {thumb_info['picked']}  [{thumb_info['layout']}]")
    print(f"  Variants   : {thumb_info['contact']}")
    print(f"  Preview    : {preview}")

    if args.open:
        webbrowser.open(preview.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
