"""Chapter content: category rotation, history-aware de-duplication, AI generation."""

from __future__ import annotations

import json
import random
import re
import time
from difflib import SequenceMatcher
from datetime import datetime

import requests

import config
from config import CATEGORIES, HISTORY_DIR

PHRASE_HISTORY_FILE = HISTORY_DIR / "all_generated_phrases.json"
CATEGORY_HISTORY_FILE = HISTORY_DIR / "used_categories.json"

LANGUAGE_NAME = config.LANGUAGE["name"]
NATIVE_NAME = config.LANGUAGE["native_name"]
PHRASE_KEY = config.LANGUAGE["history_key"]

_META_KEYS = {"english", "native", "translation", "transliteration", "romanization", "category", "generated_at"}
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_SPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_CHAR_SCRIPT = re.compile(r"[\u0590-\u05FF\u0600-\u06FF\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0B80-\u0BFF\u0C00-\u0C7F\u0D00-\u0D7F\u0E00-\u0E7F\u1000-\u109F\u10A0-\u10FF\u3040-\u30FF\u3400-\u9FFF\uAC00-\uD7AF]")


def _load_json(path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return default


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _norm(text: str) -> str:
    return _SPACE.sub(" ", _PUNCT.sub(" ", str(text).lower())).strip()


def _tokens(text: str) -> set:
    return set(_WORD.findall(_norm(text)))


def _bigrams(text: str) -> set:
    clean = _SPACE.sub("", _norm(text))
    return {clean[i:i + 2] for i in range(len(clean) - 1)} or {clean}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _shape(text: str):
    return _bigrams(text) if _CHAR_SCRIPT.search(text) else _tokens(text)


def _native_of(entry: dict) -> str:
    value = entry.get(PHRASE_KEY)
    if isinstance(value, str) and value.strip():
        return value.strip()
    value = entry.get("native")
    if isinstance(value, str) and value.strip():
        return value.strip()
    for key, val in entry.items():
        if key not in _META_KEYS and isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def _load_history():
    history = _load_json(PHRASE_HISTORY_FILE, {"phrases": []})
    used_en, used_nat = set(), set()
    recent_en, recent_nat = [], []
    by_category: dict[str, list[str]] = {}

    for entry in history.get("phrases", []):
        english = str(entry.get("english", "")).strip()
        native = _native_of(entry)
        if english:
            norm_en = _norm(english)
            used_en.add(norm_en)
            recent_en.append(norm_en)
            cat = str(entry.get("category", "")).strip()
            if cat:
                by_category.setdefault(cat, []).append(norm_en)
        if native:
            used_nat.add(_norm(native))
            recent_nat.append(_shape(native))

    return (
        history,
        used_en,
        used_nat,
        recent_en[-500:],
        recent_nat[-400:],
        {k: v[-200:] for k, v in by_category.items()},
    )


def _is_duplicate(english, native, used_en, used_nat, recent_en, recent_nat, category_recent):
    key_en, key_nat = _norm(english), _norm(native)
    if key_en in used_en or key_nat in used_nat:
        return True

    en_tokens = _tokens(english)
    pool = list(category_recent) + list(recent_en)
    token_limit = 0.60 if len(en_tokens) <= 6 else 0.80
    for old in pool:
        if _jaccard(en_tokens, _tokens(old)) >= token_limit:
            return True
        if abs(len(old) - len(key_en)) <= 18 and SequenceMatcher(None, key_en, old).ratio() >= 0.86:
            return True

    if _CHAR_SCRIPT.search(native):
        nat_shape = _shape(native)
        if any(_jaccard(nat_shape, old) >= 0.84 for old in recent_nat):
            return True
    return False


def _normalize(item):
    if not isinstance(item, dict):
        return None
    english = str(item.get("english", "")).strip()
    native = _native_of(item)
    translit = str(item.get("transliteration") or item.get("romanization") or "").strip()
    if not english or not native:
        return None

    english = _SPACE.sub(" ", english).strip()
    words = english.split()
    if not 2 <= len(words) <= 16:
        return None
    if "/" in native or "|" in native:
        native = re.split(r"[/|]", native)[0].strip()
    native = native.strip(" \t\"'“”‘’")
    if not native:
        return None
    translit = translit.strip().strip("[]()").strip()

    return {"english": " ".join(words), "native": native, "transliteration": translit}


def _extract_array(content: str):
    content = content.strip()
    if "```" in content:
        content = re.sub(r"```[a-zA-Z]*", "", content).replace("```", "").strip()
    start, end = content.find("["), content.rfind("]")
    if start >= 0 and end > start:
        content = content[start:end + 1]

    for attempt in range(2):
        try:
            data = json.loads(content)
            break
        except json.JSONDecodeError:
            if attempt == 0:
                content = re.sub(r",\s*([\]}])", r"\1", content)
            else:
                raise
    if isinstance(data, dict):
        for key in ("phrases", "items", "data", "results"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise ValueError("AI did not return a JSON array")
    return data


def _chat(model: str, prompt: str, seed: int) -> str:
    response = requests.post(
        "https://gen.pollinations.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {config.POLLINATIONS_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "seed": seed,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"You are a gifted {LANGUAGE_NAME} teacher and copywriter. "
                        "You write short, vivid, genuinely useful bilingual phrases for adult learners. "
                        "Reply with a JSON array only - no commentary."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 1.0,
        },
        timeout=150,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _request_chapter(category, native_category, avoid, need, seed):
    avoid_block = ""
    if avoid:
        avoid_block = "\nAlready used - every new phrase must be clearly different from these:\n" + "\n".join(
            f"- {p}" for p in avoid[:90]
        )

    prompt = f"""Create {max(14, need * 3)} fresh "{category}" phrases for English speakers learning {LANGUAGE_NAME}.

The topic in {LANGUAGE_NAME} is "{native_category}".{avoid_block}

Rules:
1. English side: 3-10 words, conversational and memorable. At most two lines may reach 12 words.
2. Each phrase must be usable in real life today - not textbook filler.
3. Every phrase needs a distinct idea. Never paraphrase another line on the list.
4. Native side: natural {LANGUAGE_NAME} written in {NATIVE_NAME}, correct script and accents, one translation only.
5. Transliteration: friendly Roman letters for English speakers (not IPA), stressed syllables in CAPITALS.
6. No slashes, no brackets, no quotes, no emoji, no numbering inside the phrases.
7. Add a natural comma for breathing pauses where it helps the voice.
8. Vary the length: punchy one-liners plus a few warmer, longer sentences.

Return ONLY a JSON array:
[{{"english": "...", "native": "...", "transliteration": "..."}}]"""

    models = [config.AI_MODEL]
    if config.AI_FALLBACK_MODEL and config.AI_FALLBACK_MODEL != config.AI_MODEL:
        models.append(config.AI_FALLBACK_MODEL)

    last_error = None
    for model in models:
        for attempt in range(3):
            try:
                return _extract_array(_chat(model, prompt, seed + attempt * 137))
            except Exception as exc:  # noqa: BLE001 - network + model boundary
                last_error = exc
                print(f"  [ai] {category}: {model} attempt {attempt + 1} failed: {exc}")
                time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"AI failed for {category!r}: {last_error}")


def _avoid_list(category_recent, recent_en, picked):
    avoid = [p["english"] for p in picked]
    avoid.extend(list(category_recent)[-35:])
    return avoid


def _used_categories():
    data = _load_json(CATEGORY_HISTORY_FILE, {"categories": []})
    entries = data.get("categories", []) if isinstance(data, dict) else data
    last_seen, counts = {}, {}
    for entry in entries:
        if isinstance(entry, str):
            name, date = entry, ""
        elif isinstance(entry, dict):
            name = str(entry.get("category", ""))
            date = str(entry.get("date", ""))
        else:
            continue
        if not name:
            continue
        counts[name] = counts.get(name, 0) + 1
        if date > last_seen.get(name, ""):
            last_seen[name] = date
    return last_seen, counts


def pick_categories(count: int, seed: str | None = None) -> list:
    """Least-recently-used rotation across the whole topic pool."""
    seed = seed or datetime.now().strftime("%Y%m%d")
    last_seen, counts = _used_categories()
    rng = random.Random(f"{seed}:{LANGUAGE_NAME}")

    order = list(CATEGORIES.keys())
    rng.shuffle(order)
    order.sort(key=lambda c: (last_seen.get(c, ""), counts.get(c, 0)))
    return order[:count]


def _record_categories(chapter_names):
    data = _load_json(CATEGORY_HISTORY_FILE, {"categories": []})
    if isinstance(data, list):
        data = {"categories": data}
    today = datetime.now().strftime("%Y-%m-%d")
    for name in chapter_names:
        data.setdefault("categories", []).append({"category": name, "date": today})
    data["last_updated"] = datetime.now().isoformat()
    _save_json(CATEGORY_HISTORY_FILE, data)


def _save_history(chapters):
    history = _load_json(PHRASE_HISTORY_FILE, {"phrases": []})
    stamp = datetime.now().isoformat()
    for chapter in chapters:
        for phrase in chapter["phrases"]:
            history.setdefault("phrases", []).append({
                "english": phrase["english"],
                PHRASE_KEY: phrase["native"],
                "transliteration": phrase.get("transliteration", ""),
                "category": chapter["english"],
                "generated_at": stamp,
            })
    history["last_updated"] = stamp
    _save_json(PHRASE_HISTORY_FILE, history)


def build_lesson(chapter_names, per_chapter, record=True):
    """Return [{english, native, icon, accent, ambient, phrases:[...]}, ...]."""
    if not config.POLLINATIONS_API_KEY:
        raise RuntimeError("POLLINATIONS_API_KEY is required")

    chapters: list = []

    history, used_en, used_nat, recent_en, recent_nat, by_category = _load_history()
    print(f"[content] history: {len(history.get('phrases', []))} phrases · {len(used_en)} unique English")

    for name in chapter_names:
        meta = config_style(name)
        native_category = CATEGORIES[name]
        category_recent = by_category.get(name, [])
        picked = []
        seed = random.randint(1, 2_000_000_000)

        for round_no in range(4):
            avoid = _avoid_list(category_recent, recent_en, picked)
            raw = _request_chapter(name, native_category, avoid, per_chapter, seed + round_no * 7919)
            for item in raw:
                phrase = _normalize(item)
                if not phrase:
                    continue
                if _is_duplicate(
                    phrase["english"], phrase["native"],
                    used_en, used_nat, recent_en, recent_nat, category_recent,
                ):
                    continue
                used_en.add(_norm(phrase["english"]))
                used_nat.add(_norm(phrase["native"]))
                recent_en.append(_norm(phrase["english"]))
                recent_nat.append(_shape(phrase["native"]))
                category_recent.append(_norm(phrase["english"]))
                picked.append(phrase)
                if len(picked) >= per_chapter:
                    break
            print(f"      · {name}: {len(picked)}/{per_chapter} fresh")
            if len(picked) >= per_chapter:
                break
            time.sleep(2.0 + 2.0 * round_no)

        if len(picked) < per_chapter:
            raise RuntimeError(f"Only {len(picked)}/{per_chapter} fresh phrases for {name}")

        chapters.append({
            "english": name,
            "native": native_category,
            **meta,
            "phrases": [dict(p, index=i) for i, p in enumerate(picked[:per_chapter])],
        })

    if record:
        _save_history(chapters)
        _record_categories(chapter_names)
    return chapters


def config_style(name):
    from engine import catalog
    return catalog.style(name)
