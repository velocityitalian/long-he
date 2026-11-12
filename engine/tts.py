"""Edge TTS synthesis with word-boundary timings for karaoke highlighting."""

from __future__ import annotations

import asyncio
import re
import subprocess
import unicodedata
from pathlib import Path

import edge_tts
import numpy as np

import config

SR = 48000
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_SPACE = re.compile(r"\s+")
_BRACKETED = re.compile(r"[\[\(\{<][^\]\}\)>]*[\]\}\)>]")
_ZWJ = {"\u200c", "\u200d"}


def _for_speech(text: str) -> str:
    """Drop bracketed placeholders so narration never says 'bracket name bracket'."""
    cleaned = _BRACKETED.sub(" ", str(text))
    cleaned = re.sub(r"[\[\]\(\)\{\}<>]", " ", cleaned)
    cleaned = _SPACE.sub(" ", cleaned)
    return re.sub(r"\s+([,.;:!?])", r"\1", cleaned).strip()


def _norm(text: str) -> str:
    return _PUNCT.sub("", text).strip().lower()


def _audio_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def _audio_peak(path: Path) -> float:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True,
    )
    if result.returncode != 0 or not result.stdout:
        return 0.0
    data = np.frombuffer(result.stdout, dtype="<f4")
    return float(np.max(np.abs(data))) if data.size else 0.0


async def _stream(text: str, voice: str, rate: str, pitch: str, boundary: str):
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary=boundary)
    boundaries = []
    audio = bytearray()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            boundaries.append({
                "text": chunk["text"],
                "start": chunk["offset"] / 1e7,
                "duration": chunk["duration"] / 1e7,
            })
    return boundaries, bytes(audio)


async def _synth_once(text: str, voice: str, out_path: Path, rate: str, pitch: str):
    try:
        boundaries, audio = await _stream(text, voice, rate, pitch, "WordBoundary")
        if len(audio) < 500:
            raise RuntimeError("TTS returned empty audio")
    except Exception:  # noqa: BLE001 - some locales reject WordBoundary
        boundaries, audio = await _stream(text, voice, rate, pitch, "SentenceBoundary")
        if len(audio) < 500:
            raise RuntimeError("TTS returned empty audio")
    out_path.write_bytes(audio)
    return boundaries


async def _try_voice(text: str, voice: str, out_path: Path, rate: str, pitch: str, semaphore, attempts: int):
    last_error = None
    for attempt in range(attempts):
        try:
            if semaphore:
                async with semaphore:
                    boundaries = await _synth_once(text, voice, out_path, rate, pitch)
            else:
                boundaries = await _synth_once(text, voice, out_path, rate, pitch)
            duration = _audio_duration(out_path)
            peak = _audio_peak(out_path)
            if duration > 0.2 and peak > 0.01:
                return boundaries, duration
            raise RuntimeError(f"invalid audio (duration {duration:.2f}s, peak {peak:.3f})")
        except Exception as exc:  # noqa: BLE001 - network boundary
            last_error = exc
            if "No audio was received" in str(exc):
                break
            print(f"  [tts] retry {attempt + 1}/{attempts} for {voice}: {exc}")
            await asyncio.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"voice {voice} failed after {attempts} attempts: {last_error}")


async def _synth_with_retry(text: str, voices: list, out_path: Path, rate: str, pitch: str, semaphore=None):
    combos = [(voice, rate, pitch) for voice in dict.fromkeys(voices) if voice]
    primary = next((v for v in voices if v), "")
    if primary and (rate not in ("+0%", "0%") or pitch not in ("+0Hz", "0Hz")):
        combos.append((primary, "+0%", "+0Hz"))
    last_error = None
    for voice, voice_rate, voice_pitch in combos:
        try:
            return await _try_voice(text, voice, out_path, voice_rate, voice_pitch, semaphore, attempts=3)
        except Exception as exc:  # noqa: BLE001 - try the next voice/setting
            last_error = exc
            print(f"  [tts] {voice} ({voice_rate}, {voice_pitch}) unavailable: {exc}")
    raise RuntimeError(f"All voices failed for text: {text[:60]!r} ({last_error})")


def _clusters(text: str) -> list:
    """Grapheme-ish units: base char + combining marks, joined punctuation."""
    out: list[str] = []
    join_next = False
    for ch in text:
        if ch.isspace():
            join_next = False
            continue
        category = unicodedata.category(ch)
        if out and (unicodedata.combining(ch) or category.startswith("M") or ch in _ZWJ or join_next):
            out[-1] += ch
        elif out and category.startswith(("P", "S")):
            out[-1] += ch
        else:
            out.append(ch)
        join_next = ch in _ZWJ
    return out


def _units(text: str, split_chars: bool) -> list:
    return _clusters(text) if split_chars else text.split()


def map_word_timings(text: str, boundaries: list, duration: float, split_chars: bool = False) -> list:
    words = _units(text, split_chars)
    if not words:
        return []

    clean = [b for b in boundaries if _norm(b["text"])]
    if len(clean) == len(words) and all(_norm(b["text"]) == _norm(w) for b, w in zip(clean, words)):
        return [
            {
                "start": round(max(0.0, b["start"]), 3),
                "end": round(min(duration, b["start"] + b["duration"]), 3),
            }
            for b in clean
        ]

    speech_start = clean[0]["start"] if clean else 0.06
    speech_end = max((b["start"] + b["duration"]) for b in clean) if clean else duration * 0.92
    speech_end = min(max(speech_start + 0.2, speech_end), duration)
    span = speech_end - speech_start
    weights = [max(1, len(w)) for w in words]
    total = sum(weights)
    out = []
    cursor = speech_start
    for weight in weights:
        share = (weight / total) * span
        out.append({"start": round(cursor, 3), "end": round(min(speech_end, cursor + share), 3)})
        cursor += share
    return out


async def _synth_native(text: str, out_path: Path, semaphore):
    lang = config.LANGUAGE
    return await _synth_with_retry(
        text,
        [lang.get("native_voice", ""), lang.get("native_fallback_voice", "")],
        out_path, lang.get("native_rate", "-6%"), lang.get("native_pitch", "+0Hz"), semaphore,
    )


async def _synth_phrase(index: int, phrase: dict, audio_dir: Path, semaphore):
    lang = config.LANGUAGE
    en_path = audio_dir / f"en_{index}.mp3"
    vi_path = audio_dir / f"vi_{index}.mp3"
    english = _for_speech(phrase["english"])
    native = _for_speech(phrase["native"])

    en_bounds, en_dur = await _synth_with_retry(
        english,
        [lang["english_voice"], lang.get("english_fallback_voice", "en-US-GuyNeural")],
        en_path, lang["english_rate"], lang["english_pitch"], semaphore,
    )

    vi_bounds, vi_dur = await _synth_native(native, vi_path, semaphore)

    return {
        "index": index,
        "english": english,
        "native": native,
        "transliteration": phrase.get("transliteration", ""),
        "en_path": en_path,
        "vi_path": vi_path,
        "en_duration": en_dur,
        "vi_duration": vi_dur,
        "en_words": map_word_timings(english, en_bounds, en_dur),
        "vi_words": map_word_timings(native, vi_bounds, vi_dur,
                                     split_chars=bool(lang.get("char_tiles"))),
    }


def synthesize_all(phrases: list, audio_dir: Path) -> list:
    audio_dir.mkdir(parents=True, exist_ok=True)
    lang = config.LANGUAGE
    print(f"[tts] Synthesizing {len(phrases)} phrases with {lang['english_voice']} + {lang.get('native_voice', '?')}")

    async def run():
        semaphore = asyncio.Semaphore(2)
        return await asyncio.gather(*[_synth_phrase(i, p, audio_dir, semaphore) for i, p in enumerate(phrases)])

    results = asyncio.run(run())
    for r in results:
        print(f"  {r['index'] + 1}. EN {r['en_duration']:.2f}s | VI {r['vi_duration']:.2f}s | {r['english']}")
    return results
