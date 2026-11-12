"""Timeline assembly for the chaptered 16:9 long-form lesson."""

from __future__ import annotations

import config


def _speech_len(words, total, pad):
    """Edge TTS clips carry ~1s of trailing silence; time the visuals to speech."""
    if words:
        return min(total, max(w["end"] for w in words) + pad)
    return total


def _phrase_item(chapter_index, number, phrase, clip, start):
    en_len = _speech_len(clip["en_words"], clip["en_duration"], 0.35)
    vi_len = _speech_len(clip["vi_words"], clip["vi_duration"], 0.45)

    en_start = start + config.EN_CARD_IN
    en_end = en_start + en_len
    nat_reveal = en_end + config.GAP_EN_NATIVE
    vi_start = nat_reveal + config.NATIVE_CARD_LEAD
    vi_end = vi_start + vi_len
    repeat_start = vi_end + config.GAP_BEFORE_REPEAT
    repeat_end = repeat_start + vi_len
    end = repeat_end + config.TAIL_HOLD

    return {
        "chapter": chapter_index,
        "number": number,
        "english": phrase["english"],
        "native": phrase["native"],
        "transliteration": phrase.get("transliteration", ""),
        "start": round(start, 3),
        "end": round(end, 3),
        "en_start": round(en_start, 3),
        "en_end": round(en_end, 3),
        "nat_reveal": round(nat_reveal, 3),
        "vi_start": round(vi_start, 3),
        "vi_end": round(vi_end, 3),
        "vi_repeat_start": round(repeat_start, 3),
        "vi_repeat_end": round(repeat_end, 3),
        "en_words": [
            {"t0": round(en_start + w["start"], 3), "t1": round(en_start + w["end"], 3)}
            for w in clip["en_words"]
        ],
        "vi_words": [
            {"t0": round(vi_start + w["start"], 3), "t1": round(vi_start + w["end"], 3)}
            for w in clip["vi_words"]
        ],
        "vi_words_repeat": [
            {"t0": round(repeat_start + w["start"], 3), "t1": round(repeat_start + w["end"], 3)}
            for w in clip["vi_words"]
        ],
    }


def build_timeline(chapters: list) -> dict:
    sfx = [
        {"t": 0.45, "kind": "whoosh", "gain": 0.5},
        {"t": 1.05, "kind": "pop", "gain": 0.45},
        {"t": 2.10, "kind": "chime", "gain": 0.5},
        {"t": 3.40, "kind": "pop", "gain": 0.3},
        {"t": 3.55, "kind": "pop", "gain": 0.3},
        {"t": 3.70, "kind": "pop", "gain": 0.3},
    ]
    fx = [
        {"t": 6.75, "x": 960, "y": 620, "count": 46, "power": 1.0},
    ]

    items = []
    chapter_items = []
    cursor = config.INTRO_DURATION

    for ci, chapter in enumerate(chapters):
        intro_start = cursor
        intro_end = intro_start + config.CHAPTER_INTRO_DURATION
        cursor = intro_end
        phrase_start = cursor
        first_item = len(items)

        sfx.extend([
            {"t": round(intro_start + 0.10, 3), "kind": "whoosh", "gain": 0.4},
            {"t": round(intro_start + 0.95, 3), "kind": "pop", "gain": 0.45},
            {"t": round(intro_start + 1.60, 3), "kind": "chime", "gain": 0.4},
        ])
        fx.append({"t": round(intro_start + 1.55, 3), "x": 960, "y": 540, "count": 34, "power": 0.9})

        for number, phrase in enumerate(chapter["phrases"], 1):
            item = _phrase_item(ci, number, phrase, phrase["clip"], cursor)
            item["index"] = len(items)
            items.append(item)

            sfx.extend([
                {"t": round(item["start"] + 0.05, 3), "kind": "whoosh", "gain": 0.18},
                {"t": round(item["nat_reveal"], 3), "kind": "pop", "gain": 0.35},
                {"t": round(item["vi_repeat_start"], 3), "kind": "pop", "gain": 0.24},
                {"t": round(item["vi_repeat_end"] + 0.05, 3), "kind": "ding", "gain": 0.26},
            ])
            cursor = item["end"]

        phrase_end = cursor
        chapter_items.append({
            "index": ci,
            "english": chapter["english"],
            "native": chapter["native"],
            "icon": chapter["icon"],
            "accent": chapter["accent"],
            "ambient": chapter["ambient"],
            "intro_start": round(intro_start, 3),
            "intro_end": round(intro_end, 3),
            "start": round(intro_start, 3),
            "end": round(phrase_end, 3),
            "phrase_start": round(phrase_start, 3),
            "phrase_end": round(phrase_end, 3),
            "count": len(chapter["phrases"]),
            "first_phrase": first_item,
        })

    outro_start = cursor
    outro_end = outro_start + config.OUTRO_DURATION

    sfx.extend([
        {"t": round(outro_start + 0.3, 3), "kind": "success", "gain": 0.65},
        {"t": round(outro_start + 1.2, 3), "kind": "sparkle", "gain": 0.5},
    ])
    fx.extend([
        {"t": round(outro_start + 0.5, 3), "x": 960, "y": 420, "count": 60, "power": 1.1},
        {"t": round(outro_start + 1.8, 3), "x": 960, "y": 780, "count": 40, "power": 0.9},
    ])

    if items:
        goal = outro_start * 0.38
        thumb_item = min(items[1:], key=lambda p: abs(p["nat_reveal"] - goal)) if len(items) > 1 else items[0]
        thumb_t = round(thumb_item["nat_reveal"] + 0.95, 3)
    else:
        thumb_t = 0.0

    lang = config.LANGUAGE
    copy = {
        "intro_tag": f"Learn {lang['name']} <b>one chapter at a time</b>",
        "intro_cta": f"Let's begin · {lang.get('greeting', '')}".strip(),
        "outro_eyebrow": f"LESSON COMPLETE · {lang.get('encouragement', 'BRAVO!').upper()}",
        "outro_title": "You did it.",
    }

    return {
        "brand": config.BRAND,
        "brand_top": config.BRAND_LOCKUP_TOP,
        "brand_bottom": config.BRAND_LOCKUP_BOTTOM,
        "handle": config.HANDLE,
        "mascot": config.MASCOT_NAME,
        "copy": copy,
        "language": {
            "code": lang["code"],
            "name": lang["name"],
            "native": lang["native_name"],
            "native_label": lang["native_label"],
            "translit_label": lang["translit_label"],
            "rtl": lang.get("rtl", False),
            "char_tiles": lang.get("char_tiles", False),
            "glyphs": lang.get("glyphs", ""),
        },
        "intro": {"start": 0.0, "end": config.INTRO_DURATION},
        "chapters": chapter_items,
        "phrases": items,
        "outro": {"start": round(outro_start, 3), "end": round(outro_end, 3)},
        "duration": round(outro_end, 3),
        "fps": config.FPS,
        "thumb_t": thumb_t,
        "xp": len(items) * 12,
        "minutes": round(outro_end / 60.0, 1),
        "sfx": sorted(sfx, key=lambda e: e["t"]),
        "fx": sorted(fx, key=lambda e: e["t"]),
    }
