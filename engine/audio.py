"""Music bed, sound design and final mix for the long-form lesson."""

from __future__ import annotations

import math
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000
MUSIC_LOOP = 24.0


def _midi(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def _pluck(note: int, dur: float = 0.9) -> np.ndarray:
    f = _midi(note)
    n = int(SR * dur)
    t = np.arange(n) / SR
    env = np.exp(-t * 4.2) * np.clip(t / 0.005, 0, 1)
    sig = np.sin(2 * np.pi * f * t) + 0.32 * np.sin(4 * np.pi * f * t) + 0.09 * np.sin(6 * np.pi * f * t)
    return (sig * env).astype(np.float32)


def _bass(note: int, dur: float = 1.1) -> np.ndarray:
    f = _midi(note)
    n = int(SR * dur)
    t = np.arange(n) / SR
    env = np.exp(-t * 2.2) * np.clip(t / 0.015, 0, 1)
    return (np.sin(2 * np.pi * f * t) * env).astype(np.float32)


def _pad(notes, dur: float = 3.0) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    env = np.clip(t / 0.5, 0, 1) * np.exp(-np.maximum(0, t - dur + 0.6) * 2.5)
    out = np.zeros(n, dtype=np.float32)
    for note in notes:
        f = _midi(note)
        out += (np.sin(2 * np.pi * f * t) + 0.18 * np.sin(4 * np.pi * f * t)).astype(np.float32)
    return out * env / max(1, len(notes))


def _hat(rng, dur: float = 0.05) -> np.ndarray:
    n = int(SR * dur)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - np.convolve(noise, np.ones(4) / 4, mode="same")
    return (noise * np.exp(-t * 90) * 0.35).astype(np.float32)


def _add(out: np.ndarray, sig: np.ndarray, t0: float, gain: float = 1.0, pan: float = 0.0) -> None:
    if sig.size == 0:
        return
    i0 = int(round(t0 * SR))
    if i0 >= len(out):
        return
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    i1 = min(len(out), i0 + len(sig))
    if i1 <= i0:
        return
    seg = np.asarray(sig[: i1 - i0], dtype=np.float32) * gain
    left = seg * (1.0 - 0.42 * max(0.0, pan))
    right = seg * (1.0 + 0.42 * min(0.0, pan))
    out[i0:i1, 0] += left
    out[i0:i1, 1] += right


def synth_music(duration: float) -> np.ndarray:
    n = int(duration * SR)
    out = np.zeros((n, 2), dtype=np.float32)
    bpm = 80.0
    beat = 60.0 / bpm
    bar = beat * 4
    eighth = beat / 2
    progression = [
        [48, 55, 59, 64],
        [45, 52, 55, 60],
        [41, 48, 52, 57],
        [43, 50, 53, 59],
    ]
    pattern = [0, 2, 1, 3, 2, 1, 0, 2]
    rng = np.random.default_rng(17)
    bars = int(math.ceil(duration / bar))

    for b in range(bars):
        chord = progression[b % 4]
        base = b * bar
        _add(out, _pad([chord[0], chord[1], chord[2]], bar * 0.96), base, 0.055)
        for k, idx in enumerate(pattern):
            t0 = base + k * eighth
            note = chord[idx] + (12 if k in (2, 5) else 0)
            _add(out, _pluck(note, 1.0), t0, 0.075, pan=(-0.32 if k % 2 == 0 else 0.32))
        for k in (0, 2):
            _add(out, _bass(chord[0] - 12, 1.2), base + k * beat, 0.22)
        for k in (1, 3):
            _add(out, _hat(rng), base + k * beat + eighth, 0.055, pan=0.22)

    return out


def _music_loop() -> np.ndarray:
    loop_n = int(MUSIC_LOOP * SR)
    fade_n = int(0.4 * SR)
    music = synth_music(MUSIC_LOOP + 0.4)
    loop = music[:loop_n].copy()
    head = music[:fade_n]
    tail = music[loop_n:loop_n + fade_n]
    w = np.linspace(0.0, 1.0, fade_n, dtype=np.float32)[:, None]
    loop[:fade_n] = head * w + tail * (1.0 - w)
    return loop


def _sfx_pop() -> np.ndarray:
    dur = 0.18
    n = int(SR * dur)
    t = np.arange(n) / SR
    f = 980 * np.exp(-t * 16) + 280
    phase = 2 * np.pi * np.cumsum(f) / SR
    sig = np.sin(phase) * np.exp(-t * 24) + 0.35 * np.sin(2 * phase) * np.exp(-t * 40)
    return sig.astype(np.float32)


def _sfx_ding() -> np.ndarray:
    dur = 0.9
    n = int(SR * dur)
    t = np.arange(n) / SR
    sig = (
        np.sin(2 * np.pi * 880 * t) * np.exp(-t * 5.5)
        + 0.55 * np.sin(2 * np.pi * 1320 * t) * np.exp(-t * 7)
        + 0.22 * np.sin(2 * np.pi * 1760 * t) * np.exp(-t * 9)
    )
    return (sig * np.clip(t / 0.004, 0, 1)).astype(np.float32)


def _sfx_chime() -> np.ndarray:
    dur = 1.5
    n = int(SR * dur)
    out = np.zeros(n, dtype=np.float32)
    for i, note in enumerate([72, 76, 79, 84]):
        start = int(i * 0.1 * SR)
        f = _midi(note)
        ln = n - start
        t = np.arange(ln) / SR
        bell = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 3.6)
        out[start:] += (bell * 0.4).astype(np.float32)
    return out


def _sfx_success() -> np.ndarray:
    dur = 1.8
    n = int(SR * dur)
    out = np.zeros(n, dtype=np.float32)
    for i, note in enumerate([72, 76, 79, 84, 88]):
        start = int(i * 0.085 * SR)
        f = _midi(note)
        ln = n - start
        t = np.arange(ln) / SR
        env = np.exp(-t * 3.6) * np.clip(t / 0.003, 0, 1)
        out[start:] += ((np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * env * 0.3).astype(np.float32)
    return out


def _sfx_sparkle() -> np.ndarray:
    dur = 1.2
    n = int(SR * dur)
    out = np.zeros(n, dtype=np.float32)
    rng = np.random.default_rng(99)
    for _ in range(8):
        start = int(rng.uniform(0, 0.8) * SR)
        f = rng.uniform(1700, 3300)
        ln = min(n - start, int(0.25 * SR))
        t = np.arange(ln) / SR
        out[start:start + ln] += (np.sin(2 * np.pi * f * t) * np.exp(-t * 22) * 0.2).astype(np.float32)
    return out


def _sfx_whoosh() -> np.ndarray:
    dur = 0.5
    n = int(SR * dur)
    rng = np.random.default_rng(11)
    noise = rng.standard_normal(n)
    smooth = np.convolve(noise, np.ones(32) / 32, mode="same")
    band = noise - smooth
    t = np.arange(n) / SR
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    sig = (band * env * 1.2).astype(np.float32)
    pan = np.linspace(-0.7, 0.7, n)
    return np.stack([sig * (1 - 0.4 * np.maximum(pan, 0)), sig * (1 + 0.4 * np.minimum(pan, 0))], axis=1)


def make_sfx(kind: str) -> np.ndarray:
    return {
        "pop": _sfx_pop,
        "ding": _sfx_ding,
        "chime": _sfx_chime,
        "success": _sfx_success,
        "sparkle": _sfx_sparkle,
        "whoosh": _sfx_whoosh,
    }.get(kind, _sfx_pop)()


def _decode(path: Path) -> np.ndarray:
    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
        capture_output=True,
    )
    if result.returncode != 0 or not result.stdout:
        return np.zeros((int(0.1 * SR), 2), dtype=np.float32)
    data = np.frombuffer(result.stdout, dtype="<f4")
    if data.size % 2:
        data = data[:-1]
    return data.reshape(-1, 2).astype(np.float32)


def _place(out: np.ndarray, sig: np.ndarray, t0: float, gain: float = 1.0) -> None:
    if sig.ndim == 1:
        _add(out, sig, t0, gain)
        return
    i0 = int(round(t0 * SR))
    if i0 >= len(out):
        return
    i1 = min(len(out), i0 + len(sig))
    if i1 <= i0:
        return
    out[i0:i1] += sig[: i1 - i0] * gain


def _write_wav(path: Path, audio: np.ndarray) -> None:
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SR)
        handle.writeframes(pcm.tobytes())


def build_mix(clips: list, timeline: dict, out_path: Path) -> dict:
    duration = float(timeline["duration"])
    n = int((duration + 0.2) * SR)
    master = np.zeros((n, 2), dtype=np.float32)

    for clip, item in zip(clips, timeline["phrases"]):
        en = _decode(clip["en_path"])
        native = _decode(clip["vi_path"])
        _place(master, en, item["en_start"], 1.0)
        _place(master, native, item["vi_start"], 1.0)
        _place(master, native, item["vi_repeat_start"], 0.92)

    peak = float(np.max(np.abs(master))) or 1.0
    master *= 0.9 / peak

    block = 1024
    blocks = max(1, n // block + 1)
    env = np.zeros(blocks, dtype=np.float32)
    absmax = np.max(np.abs(master), axis=1)
    for i in range(blocks):
        seg = absmax[i * block:(i + 1) * block]
        env[i] = float(seg.max()) if seg.size else 0.0
    win = max(1, int(0.22 * SR / block))
    kernel = np.ones(win, dtype=np.float32) / win
    env = np.convolve(env, kernel, mode="same")
    env /= float(env.max()) + 1e-9
    duck = (1.0 - 0.72 * np.clip(env * 1.4, 0, 1)).astype(np.float32)
    duck = np.interp(
        np.arange(n, dtype=np.float32),
        (np.arange(blocks, dtype=np.float32) * block),
        duck,
    ).astype(np.float32)

    music = _music_loop()
    loop_n = len(music)
    for start in range(0, n, loop_n):
        stop = min(n, start + loop_n)
        master[start:stop] += music[: stop - start] * duck[start:stop, None] * 0.34

    for event in timeline.get("sfx", []):
        _place(master, make_sfx(event["kind"]), event["t"], event.get("gain", 0.4))

    fade_in = int(0.4 * SR)
    master[:fade_in] *= np.linspace(0, 1, fade_in, dtype=np.float32)[:, None]
    fade_out = int(1.6 * SR)
    master[-fade_out:] *= np.linspace(1, 0, fade_out, dtype=np.float32)[:, None]

    peak = float(np.max(np.abs(master)))
    if peak > 0.95:
        master *= 0.95 / peak
    master = np.tanh(master * 1.05) / np.tanh(1.05)

    _write_wav(out_path, master)
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"[audio] Mix: {out_path.name} ({duration:.1f}s, {size_mb:.1f} MB)")
    return {"duration": duration, "path": str(out_path), "peak": round(peak, 3)}
