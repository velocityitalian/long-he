"""Designed 1280x720 YouTube thumbnails with six layouts and daily rotation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

import config
from engine import renderer

THUMB_WIDTH = 1280
THUMB_HEIGHT = 720
VARIANT_COUNT = 6

LAYOUT_LABELS = [
    "Cream hero",
    "White card",
    "Accent split",
    "Full colour",
    "Speech bubble",
    "Night split",
]

HOOKS = (
    "love", "heart", "you", "life", "dream", "happy", "believe", "never",
    "always", "everything", "world", "smile", "tomorrow", "power", "chance",
    "free", "home", "friend", "beautiful", "strong",
)


def _thumb_uri() -> str:
    return (config.BASE_DIR / "thumbnail" / "index.html").resolve().as_uri()


def _score(phrase: dict) -> float:
    native = phrase["native"]
    english = phrase["english"]
    score = 0.0
    if 8 <= len(native) <= 30:
        score += 4
    elif len(native) <= 42:
        score += 2
    if 10 <= len(english) <= 36:
        score += 2.5
    elif len(english) <= 50:
        score += 1
    score -= max(0, len(native) - 44) * 0.25
    score -= max(0, len(english) - 52) * 0.25
    if len(native.split()) <= 6:
        score += 1
    low = english.lower()
    score += 1.3 * sum(1 for hook in HOOKS if hook in low)
    return score


def pick_heroes(chapters: list, count: int = VARIANT_COUNT, seed: int | None = None) -> list:
    day = int(seed if seed is not None else datetime.now().strftime("%Y%m%d"))
    order = list(range(len(chapters)))
    if order:
        shift = day % len(order)
        order = order[shift:] + order[:shift]

    ranked = {
        ci: sorted(ch["phrases"], key=_score, reverse=True)
        for ci, ch in enumerate(chapters)
    }

    heroes = []
    depth = 0
    while len(heroes) < count:
        added = False
        for ci in order:
            if depth < len(ranked[ci]):
                p = ranked[ci][depth]
                ch = chapters[ci]
                heroes.append({
                    "english": p["english"],
                    "native": p["native"],
                    "transliteration": p.get("transliteration", ""),
                    "chapter": ch["english"],
                    "chapterNative": ch["native"],
                    "num": ci + 1,
                    "icon": ch["icon"],
                    "accent": ch["accent"],
                })
                added = True
                if len(heroes) >= count:
                    break
        depth += 1
        if not added:
            break

    while len(heroes) < count and heroes:
        heroes.append(heroes[len(heroes) % len(heroes)])
    return heroes


def build_data(chapters: list, timeline: dict, seed: int | None = None) -> dict:
    minutes = float(timeline.get("minutes") or 0)
    minutes = int(round(minutes)) if abs(minutes - round(minutes)) < 0.05 else round(minutes, 1)
    return {
        "brandTop": config.BRAND_LOCKUP_TOP,
        "brandBottom": config.BRAND_LOCKUP_BOTTOM,
        "language": config.LANGUAGE["name"],
        "nativeName": config.LANGUAGE["native_name"],
        "translitLabel": config.LANGUAGE["translit_label"],
        "flag": config.LANGUAGE.get("flag", "se"),
        "rtl": bool(config.LANGUAGE.get("rtl", False)),
        "hasScript": bool(config.LANGUAGE.get("script_font")),
        "handle": config.HANDLE,
        "lesson": {
            "chapters": len(chapters),
            "phrases": sum(len(c["phrases"]) for c in chapters),
            "minutes": minutes,
        },
        "heroes": pick_heroes(chapters, VARIANT_COUNT, seed),
    }


def render_thumbnails(chapters: list, timeline: dict, lesson_dir: Path, seed: int | None = None) -> dict:
    data = build_data(chapters, timeline, seed)
    out_dir = lesson_dir / "thumbnails"
    out_dir.mkdir(parents=True, exist_ok=True)

    variants = []
    with sync_playwright() as pw:
        browser = renderer._launch(pw)
        page = browser.new_page(
            viewport={"width": THUMB_WIDTH, "height": THUMB_HEIGHT},
            device_scale_factor=2,
        )
        page.add_init_script("window.__THUMB__ = " + json.dumps(data, ensure_ascii=False) + ";")
        page.goto(_thumb_uri(), wait_until="load")

        for i in range(len(data["heroes"])):
            page.evaluate("i => window.renderThumb(i)", i)
            page.wait_for_function("window.thumbReady === true", timeout=60000)
            png = out_dir / f"thumb_{i + 1:02d}.png"
            page.screenshot(path=str(png), type="png")
            img = Image.open(png).convert("RGB").resize((THUMB_WIDTH, THUMB_HEIGHT), Image.LANCZOS)
            jpg = out_dir / f"thumb_{i + 1:02d}.jpg"
            img.save(jpg, "JPEG", quality=93)
            png.unlink()
            variants.append(str(jpg))
            print(f"      thumb {i + 1}/{len(data['heroes'])} · {LAYOUT_LABELS[i]}")
        browser.close()

    contact = out_dir / "contact.jpg"
    cols, rows = 3, 2
    cell_w, cell_h = THUMB_WIDTH // 2, THUMB_HEIGHT // 2
    sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), "#FFFFFF")
    for i, path in enumerate(variants[: cols * rows]):
        im = Image.open(path).resize((cell_w, cell_h), Image.LANCZOS)
        sheet.paste(im, ((i % cols) * cell_w, (i // cols) * cell_h))
    sheet.save(contact, "JPEG", quality=92)

    day = int(seed if seed is not None else datetime.now().strftime("%Y%m%d"))
    selected = day % max(1, len(variants))
    picked = lesson_dir / "thumbnail.jpg"
    Image.open(variants[selected]).convert("RGB").save(picked, "JPEG", quality=94)

    return {
        "picked": str(picked),
        "selected": selected + 1,
        "layout": LAYOUT_LABELS[selected],
        "variants": variants,
        "contact": str(contact),
        "heroes": data["heroes"],
    }
