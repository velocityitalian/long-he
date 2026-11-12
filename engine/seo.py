"""Search-first YouTube metadata for every lesson."""

from __future__ import annotations

import config

TITLE_LIMIT = 100
DESC_LIMIT = 4900


def _fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def _title(chapters, timeline):
    language = config.LANGUAGE["name"]
    total = len(timeline["phrases"])
    minutes = max(1, round(timeline["minutes"]))
    topic = chapters[0]["english"]
    title = f"{total} {language} Phrases in {minutes} Minutes | Learn {language} for Beginners ({topic})"
    if len(title) > TITLE_LIMIT:
        title = f"{total} {language} Phrases in {minutes} Minutes | Learn {language} for Beginners"
    return title[:TITLE_LIMIT]


def _tags(chapters):
    language = config.LANGUAGE["name"]
    native = config.LANGUAGE["native_name"]
    base = [
        language,
        f"learn {language}",
        f"{language} for beginners",
        f"{language} phrases",
        f"{language} pronunciation",
        f"{language} lesson",
        f"{language} vocabulary",
        f"english to {language}",
        f"{language} conversation",
        f"{language} listening practice",
        "language learning",
        "learn languages",
        f"velocity {language.lower()}",
        native,
    ]
    for chapter in chapters:
        tag = f"{language} {chapter['english'].lower()}"
        if len(tag) <= 40:
            base.append(tag)
    seen, tags = set(), []
    for tag in base:
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            tags.append(tag)
    return tags[:18]


def _description(chapters, timeline):
    language = config.LANGUAGE["name"]
    native = config.LANGUAGE["native_name"]
    total = len(timeline["phrases"])
    minutes = timeline["minutes"]
    handle = config.HANDLE

    lines = [
        f"Learn {total} essential {language} phrases in {minutes:.0f} minutes - the fun, fast way.",
        f"#{language.replace(' ', '')} #Learn{language.replace(' ', '')} #LanguageLearning",
        "",
        f"Every phrase follows the same rhythm: hear it in English, hear it in {native}, then say it out loud with the pronunciation guide. Perfect for beginners, travellers and anyone who wants to speak {language} with confidence.",
        "",
        "WHAT YOU GET",
        f"- {len(chapters)} themed chapters, {total} real-life phrases",
        f"- {native} audio from a native voice",
        "- English pronunciation guide for every line",
        "- A brand-new lesson every single day",
        "",
        "CHAPTERS",
    ]

    for i, chapter in enumerate(chapters):
        meta = timeline["chapters"][i] if i < len(timeline["chapters"]) else None
        stamp = _fmt_time(meta["start"]) if meta else "0:00"
        lines.append(f"{stamp}  {chapter['english']} · {chapter['native']}")

    lines += ["", "PHRASE LIST"]
    for chapter in chapters:
        lines.append("")
        lines.append(f"{chapter['english'].upper()} · {chapter['native']}")
        for phrase in chapter["phrases"]:
            entry = f"• {phrase['english']} - {phrase['native']}"
            if phrase.get("transliteration"):
                entry += f"  [{phrase['transliteration']}]"
            lines.append(entry)

    lines += [
        "",
        f"Follow {handle} for a fresh {language} lesson every day.",
        "",
        f"#Learn{language.replace(' ', '')} #{language.replace(' ', '')} #LanguageLearning",
        " ".join(config.HASHTAGS),
    ]

    description = "\n".join(lines)
    if len(description) > DESC_LIMIT:
        description = description[:DESC_LIMIT].rsplit("\n", 1)[0]
    return description


def build_metadata(chapters, timeline):
    return {
        "title": _title(chapters, timeline),
        "description": _description(chapters, timeline),
        "tags": _tags(chapters),
        "hashtags": config.HASHTAGS,
        "category_id": "27",
        "privacy": "public",
    }
