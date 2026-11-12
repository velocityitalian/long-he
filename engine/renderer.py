"""Chromium frame capture -> 1080p H.264, stills and interactive preview."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from PIL import Image

import config


def _scene_uri() -> str:
    return (config.SCENE_DIR / "index.html").resolve().as_uri()


def _open_page(browser, timeline: dict, width: int = config.VIDEO_WIDTH, height: int = config.VIDEO_HEIGHT):
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
    script = "window.__TIMELINE__ = " + json.dumps(timeline, ensure_ascii=False) + ";"
    page.add_init_script(script)
    page.goto(_scene_uri(), wait_until="load")
    page.wait_for_function("window.sceneReady === true", timeout=90000)
    page.evaluate("() => document.fonts.ready")
    return page


def _launch(pw):
    return pw.chromium.launch(args=["--force-color-profile=srgb", "--font-render-hinting=none", "--disable-lcd-text"])


def render_video(timeline: dict, mix_path: Path, out_mp4: Path, work_dir: Path, fps: int = None) -> dict:
    fps = fps or config.FPS
    duration = float(timeline["duration"])
    total = max(1, int(round(duration * fps)))
    work_dir.mkdir(parents=True, exist_ok=True)
    silent = work_dir / "silent.mp4"
    thumb_png = work_dir / "thumb.png"
    thumb_jpg = out_mp4.parent / "cover.jpg"
    encode_log = work_dir / "ffmpeg_encode.log"

    print(f"[video] Rendering {total} frames at {fps}fps ({duration:.1f}s, 1920x1080)")

    proc = None
    log_handle = None
    try:
        with sync_playwright() as pw:
            browser = _launch(pw)
            page = _open_page(browser, timeline)

            page.evaluate("t => window.seek(t)", timeline.get("thumb_t", 0))
            page.screenshot(path=str(thumb_png), type="png")

            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "image2pipe", "-vcodec", "mjpeg", "-framerate", str(fps), "-i", "-",
                "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", str(silent),
            ]
            log_handle = open(encode_log, "wb")
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log_handle)

            t_start = time.time()
            for i in range(total):
                page.evaluate("t => window.seek(t)", i / fps)
                jpg = page.screenshot(type="jpeg", quality=90)
                proc.stdin.write(jpg)
                if i % 180 == 0 or i == total - 1:
                    elapsed = time.time() - t_start
                    rate = (i + 1) / elapsed if elapsed else 0
                    eta = (total - i - 1) / rate if rate else 0
                    print(f"  frame {i + 1}/{total}  {rate:4.1f} fps  eta {eta:4.0f}s")

            proc.stdin.close()
            code = proc.wait()
            log_handle.close()
            log_handle = None
            if code != 0:
                print(encode_log.read_text(errors="ignore")[-2000:])
                raise RuntimeError("ffmpeg frame encoding failed")

            browser.close()

        print("[video] Muxing audio...")
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(silent), "-i", str(mix_path),
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", str(out_mp4),
            ],
            check=True,
        )

        Image.open(thumb_png).convert("RGB").save(thumb_jpg, "JPEG", quality=94)
        size_mb = out_mp4.stat().st_size / (1024 * 1024)
        print(f"[video] Done: {out_mp4.name} ({size_mb:.1f} MB)")
        return {"video": str(out_mp4), "cover": str(thumb_jpg), "frames": total}
    finally:
        if proc and proc.poll() is None:
            proc.kill()
        if log_handle:
            log_handle.close()
        if silent.exists():
            silent.unlink()
        if thumb_png.exists():
            thumb_png.unlink()


def capture_stills(timeline: dict, times: list, out_dir: Path, prefix: str = "still") -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    with sync_playwright() as pw:
        browser = _launch(pw)
        page = _open_page(browser, timeline)
        for i, t in enumerate(times):
            page.evaluate("t => window.seek(t)", float(t))
            path = out_dir / f"{prefix}_{i:02d}_{float(t):06.2f}.png"
            page.screenshot(path=str(path), type="png")
            saved.append(path)
        browser.close()
    return saved


def write_preview(timeline: dict, mix_path: Path) -> Path:
    html = (config.SCENE_DIR / "index.html").read_text(encoding="utf-8")
    rel_audio = Path(os.path.relpath(mix_path.resolve(), config.SCENE_DIR.resolve())).as_posix()
    inject = (
        "<script>window.__TIMELINE__ = "
        + json.dumps(timeline, ensure_ascii=False)
        + "; window.__AUDIO_SRC__ = "
        + json.dumps(rel_audio)
        + ";</script>\n<script src=\"scene.js\"></script>"
    )
    html = html.replace('<script src="scene.js"></script>', inject)
    preview = config.SCENE_DIR / "preview.html"
    preview.write_text(html, encoding="utf-8")
    return preview
