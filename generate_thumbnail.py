"""
Thumbnail Generator for Velocity Hebrew
- Uses 158 curated, watermark-free scenic background images of Israel.
- Supports syncing new images from Google Drive via GDRIVE_FOLDER_ID.
- Implements an LRU / Round-Robin recycling engine with persistent state
  in output/history/thumbnail_history.json so every background is used once
  before repeating, running continuously forever.
- Renders English category text in large brush script with a subtle center smile curve,
  a solid pure white tapered brush swoosh, and RTL-shaped Hebrew translation in YouTube Gold.
"""

import os
import sys
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import bidi.algorithm
from dotenv import load_dotenv

load_dotenv()

# Directories
BASE_DIR = Path(__file__).resolve().parent
FONTS_DIR = BASE_DIR / "fonts"
BACKGROUNDS_DIR = BASE_DIR / "backgrounds"
HISTORY_DIR = BASE_DIR / "output" / "history"
STATE_FILE = HISTORY_DIR / "thumbnail_history.json"

# Google Drive Folder ID secret / environment variable
# Default Hebrew Drive Folder: https://drive.google.com/drive/folders/1nIA9jI0w2imEuTEbjtME0kGfGSmmgSHJ
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "1nIA9jI0w2imEuTEbjtME0kGfGSmmgSHJ")

# Fonts
KALAM_FONT = FONTS_DIR / "Kalam-Bold.ttf"
RUBIK_HEBREW_FONT = FONTS_DIR / "Rubik-BoldItalic.ttf"
if not RUBIK_HEBREW_FONT.exists():
    RUBIK_HEBREW_FONT = FONTS_DIR / "Rubik-Bold.ttf"

# Fallback system fonts if bundled fonts not found
if not KALAM_FONT.exists():
    KALAM_FONT = Path("C:/Windows/Fonts/segoeuib.ttf")
if not RUBIK_HEBREW_FONT.exists():
    for f in ["C:/Windows/Fonts/Rubik-BoldItalic.ttf", "C:/Windows/Fonts/Rubik-Bold.ttf", "C:/Windows/Fonts/segoeuib.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(f).exists():
            RUBIK_HEBREW_FONT = Path(f)
            break


def sync_from_google_drive(folder_id: str = None) -> int:
    """
    Syncs/downloads images from Google Drive if backgrounds folder is empty
    or if explicitly requested.
    """
    fid = folder_id or GDRIVE_FOLDER_ID
    if not fid:
        return 0
    
    BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(BACKGROUNDS_DIR.glob("*.jpg")) + list(BACKGROUNDS_DIR.glob("*.png"))
    if len(existing) >= 10:
        # Already populated
        return len(existing)
        
    print(f"[thumbnail] Downloading backgrounds from Google Drive folder: {fid}...")
    try:
        import gdown
        url = f"https://drive.google.com/drive/folders/{fid}"
        gdown.download_folder(url, output=str(BACKGROUNDS_DIR), quiet=False, use_cookies=False)
        # Convert any PNGs to JPGs
        for png in list(BACKGROUNDS_DIR.glob("*.png")):
            jpg_path = png.with_suffix(".jpg")
            if not jpg_path.exists():
                img = Image.open(png).convert("RGB")
                img.save(jpg_path, "JPEG", quality=88, optimize=True)
                png.unlink(missing_ok=True)
        files = list(BACKGROUNDS_DIR.glob("*.jpg"))
        print(f"[thumbnail] Successfully synced {len(files)} backgrounds from Google Drive.")
        return len(files)
    except Exception as e:
        print(f"[thumbnail] Google Drive sync warning: {e}. Using local backgrounds.")
        return len(list(BACKGROUNDS_DIR.glob("*.jpg")))


def load_lru_state() -> dict:
    """Loads persistent LRU history from output/history/thumbnail_history.json."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[thumbnail] Error reading state file ({e}), resetting state.")
    return {"used_counts": {}, "last_used": {}, "history": [], "cycle": 1}


def save_lru_state(state: dict):
    """Saves persistent LRU history atomically."""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = STATE_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    temp_file.replace(STATE_FILE)


def pick_next_background(category: str = "") -> Path:
    """
    Selects the next background image using LRU / round-robin recycling logic.
    Ensures every background is used once per cycle before any repeating.
    """
    BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
    bg_files = sorted(list(BACKGROUNDS_DIR.glob("*.jpg")) + list(BACKGROUNDS_DIR.glob("*.png")))
    
    if not bg_files:
        sync_from_google_drive()
        bg_files = sorted(list(BACKGROUNDS_DIR.glob("*.jpg")) + list(BACKGROUNDS_DIR.glob("*.png")))
        
    if not bg_files:
        raise FileNotFoundError(f"No background images found in {BACKGROUNDS_DIR}")

    state = load_lru_state()
    used_counts = state.get("used_counts", {})
    last_used = state.get("last_used", {})
    current_cycle = state.get("cycle", 1)

    # Find files used fewer times than current_cycle
    unvisited = [f for f in bg_files if used_counts.get(f.name, 0) < current_cycle]

    if not unvisited:
        # All files used in this cycle, advance to next cycle
        current_cycle += 1
        state["cycle"] = current_cycle
        unvisited = bg_files
        print(f"[thumbnail] Completed cycle {current_cycle - 1}! Starting cycle {current_cycle}.")

    # Pick the least recently used among the unvisited pool
    def get_sort_key(f: Path):
        # Sort by: (usage count, last used timestamp string)
        return (used_counts.get(f.name, 0), last_used.get(f.name, ""))

    chosen = min(unvisited, key=get_sort_key)

    # Update state
    now_str = datetime.now(timezone.utc).isoformat()
    used_counts[chosen.name] = used_counts.get(chosen.name, 0) + 1
    last_used[chosen.name] = now_str
    
    history_entry = {
        "filename": chosen.name,
        "category": category,
        "timestamp": now_str,
        "cycle": current_cycle
    }
    history = state.get("history", [])
    history.append(history_entry)
    # Keep last 500 history records to avoid file bloat
    if len(history) > 500:
        history = history[-500:]

    state["used_counts"] = used_counts
    state["last_used"] = last_used
    state["history"] = history
    state["cycle"] = current_cycle

    save_lru_state(state)
    print(f"[thumbnail] Selected background: {chosen.name} (Cycle {current_cycle}, used {used_counts[chosen.name]}x)")
    return chosen


def create_pure_white_swoosh(width: int, height: int = 40, start_thickness: float = 18.0, end_thickness: float = 3.0, curve_depth: float = 13.0) -> Image.Image:
    """
    Creates a solid pure white brush swoosh that curves in a gentle smile arc
    and tapers smoothly to the right tip.
    """
    scale = 3
    sw = width * scale
    sh = height * scale
    img = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    p0 = (10.0 * scale, sh * 0.35)
    p1 = (sw * 0.45, sh * 0.35 + curve_depth * scale)
    p2 = (sw - 5.0 * scale, sh * 0.22)
    
    steps = 200
    top_points = []
    bot_points = []
    
    for i in range(steps + 1):
        t = i / steps
        bx = (1 - t)**2 * p0[0] + 2 * (1 - t) * t * p1[0] + t**2 * p2[0]
        by = (1 - t)**2 * p0[1] + 2 * (1 - t) * t * p1[1] + t**2 * p2[1]
        
        dx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
        dy = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
        length = math.hypot(dx, dy)
        nx, ny = (-dy / length, dx / length) if length > 0 else (0, 1)
        
        thick = ((1 - t) * start_thickness + t * end_thickness) * scale
        
        top_points.append((bx + nx * (thick / 2), by + ny * (thick / 2)))
        bot_points.append((bx - nx * (thick / 2), by - ny * (thick / 2)))
        
    poly = top_points + bot_points[::-1]
    draw.polygon(poly, fill=(255, 255, 255, 255))
    start_r = (start_thickness * scale) / 2
    draw.ellipse([p0[0] - start_r, p0[1] - start_r, p0[0] + start_r, p0[1] + start_r], fill=(255, 255, 255, 255))
    
    return img.resize((width, height), Image.Resampling.LANCZOS)


def render_thumbnail_image(
    bg_path: Path,
    category_en: str,
    category_he: str,
    output_path: Path,
    hebrew_color=(255, 215, 0),
    curve_depth: int = 16
) -> Path:
    """
    Renders the complete thumbnail:
    - Base scenic background image
    - English category with subtle center smile curve
    - Solid white curved brush swoosh
    - RTL Hebrew translation centered beneath
    - High-quality 3D drop shadow
    - Centered right in the open middle space
    """
    bg = Image.open(bg_path).convert("RGBA")
    bw, bh = bg.size
    
    # Coordinates calibrated for 1376x768 (standard AI resolution)
    # Scales proportionally if background is 1920x1080
    scale_factor = bh / 768.0
    
    max_w = int(980 * scale_factor)
    center_x = int(760 * scale_factor)
    center_y = int(505 * scale_factor)
    
    # 1. Size English Font dynamically
    en_size = int(185 * scale_factor)
    f_en = ImageFont.truetype(str(KALAM_FONT), en_size)
    dummy = Image.new("RGBA", (1, 1))
    dd = ImageDraw.Draw(dummy)
    bb = dd.textbbox((0, 0), category_en, font=f_en)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    
    min_en_size = int(75 * scale_factor)
    while tw > max_w and en_size > min_en_size:
        en_size -= int(4 * scale_factor)
        f_en = ImageFont.truetype(str(KALAM_FONT), en_size)
        bb = dd.textbbox((0, 0), category_en, font=f_en)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        
    pad = int(50 * scale_factor)
    en_img_w = tw + pad * 2
    en_img_h = th + pad * 2
    en_img = Image.new("RGBA", (en_img_w, en_img_h), (0, 0, 0, 0))
    d_en = ImageDraw.Draw(en_img)
    
    tx = pad - bb[0]
    ty = pad - bb[1]
    stroke_w = max(4, int(7 * scale_factor))
    d_en.text((tx, ty), category_en, font=f_en, fill=(255, 255, 255, 255),
              stroke_width=stroke_w, stroke_fill=(15, 15, 20, 255))
              
    scaled_curve = int(curve_depth * scale_factor)
    warped_h = en_img_h + scaled_curve * 2 + int(20 * scale_factor)
    warped_en = Image.new("RGBA", (en_img_w, warped_h), (0, 0, 0, 0))
    
    for x in range(en_img_w):
        nx = (x - en_img_w / 2) / (en_img_w / 2)
        y_shift = int(scaled_curve * (1.0 - nx**2))
        col = en_img.crop((x, 0, x + 1, en_img_h))
        warped_en.paste(col, (x, y_shift + int(10 * scale_factor)), col)
        
    bbox_w = warped_en.getbbox()
    if bbox_w:
        warped_en = warped_en.crop(bbox_w)
    en_final_w, en_final_h = warped_en.size
    
    # 2. Swoosh
    swoosh_w = max(int(360 * scale_factor), int(en_final_w * 0.78))
    swoosh_h = max(25, int(40 * scale_factor))
    swoosh_img = create_pure_white_swoosh(
        swoosh_w,
        swoosh_h,
        start_thickness=18.0 * scale_factor,
        end_thickness=3.0 * scale_factor,
        curve_depth=13.0 * scale_factor
    )
    
    # 3. Hebrew Font & BiDi Shaping
    he_size = max(int(55 * scale_factor), int(en_size * 0.52))
    f_he = ImageFont.truetype(str(RUBIK_HEBREW_FONT), he_size)
    he_display = bidi.algorithm.get_display(category_he)
    bb_he = dd.textbbox((0, 0), he_display, font=f_he)
    he_w = bb_he[2] - bb_he[0]
    he_h = bb_he[3] - bb_he[1]
    
    he_pad = int(30 * scale_factor)
    he_img = Image.new("RGBA", (he_w + he_pad * 2, he_h + he_pad * 2), (0, 0, 0, 0))
    d_he = ImageDraw.Draw(he_img)
    he_stroke_w = max(3, int(6 * scale_factor))
    d_he.text((he_pad - bb_he[0], he_pad - bb_he[1]), he_display, font=f_he,
              fill=hebrew_color, stroke_width=he_stroke_w, stroke_fill=(15, 15, 20, 255))
    bbox_he = he_img.getbbox()
    if bbox_he:
        he_img = he_img.crop(bbox_he)
    he_final_w, he_final_h = he_img.size
    
    # 4. Assemble Card
    gap1 = max(6, int(8 * scale_factor))
    gap2 = max(8, int(12 * scale_factor))
    total_card_h = en_final_h + gap1 + swoosh_h + gap2 + he_final_h
    total_card_w = max(en_final_w, swoosh_w, he_final_w) + int(30 * scale_factor)
    card = Image.new("RGBA", (total_card_w, total_card_h), (0, 0, 0, 0))
    
    card.paste(warped_en, ((total_card_w - en_final_w) // 2, 0), warped_en)
    swoosh_y = en_final_h + gap1
    card.paste(swoosh_img, ((total_card_w - swoosh_w) // 2, swoosh_y), swoosh_img)
    he_y = swoosh_y + swoosh_h + gap2
    card.paste(he_img, ((total_card_w - he_final_w) // 2, he_y), he_img)
    
    # 5. Composite right into center of open middle space
    cw, ch = card.size
    px = int(center_x - cw / 2)
    py = int(center_y - ch / 2)
    
    shadow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    alpha = card.split()[3]
    black_card = Image.new("RGBA", (cw, ch), (0, 0, 0, 230))
    black_card.putalpha(alpha)
    shadow.paste(black_card, (px + int(4 * scale_factor), py + int(8 * scale_factor)), black_card)
    shadow = shadow.filter(ImageFilter.GaussianBlur(int(14 * scale_factor)))
    
    bg.alpha_composite(shadow)
    bg.paste(card, (px, py), card)
    
    # Save as high-quality JPEG under 2MB (YouTube limit)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    rgb = bg.convert("RGB")
    quality = 92
    thumb_bytes = io.BytesIO()
    rgb.save(thumb_bytes, format="JPEG", quality=quality, optimize=True)
    while thumb_bytes.tell() > 2097152 and quality > 30:
        quality -= 5
        thumb_bytes = io.BytesIO()
        rgb.save(thumb_bytes, format="JPEG", quality=quality, optimize=True)
        
    with open(output_path, "wb") as f:
        f.write(thumb_bytes.getvalue())
        
    print(f"[thumbnail] Saved thumbnail: {output_path} ({output_path.stat().st_size // 1024} KB)")
    return output_path


def generate_thumbnail(category_english: str, category_hebrew: str = None, output_path: str = None) -> str:
    """
    Main entry point for generating a thumbnail:
    - Selects background via LRU / round-robin from backgrounds/
    - Renders bilingual curved category text with swoosh
    - Saves to output_path and returns the path
    """
    if not category_hebrew:
        # Fallback dictionary for common categories
        category_hebrew = category_english
        
    if not output_path:
        output_path = str(BASE_DIR / "output" / "thumbnail.jpg")
        
    bg_file = pick_next_background(category_english)
    result = render_thumbnail_image(
        bg_path=bg_file,
        category_en=category_english,
        category_he=category_hebrew,
        output_path=Path(output_path),
        hebrew_color=(255, 215, 0),
        curve_depth=16
    )
    return str(result)


def generate_scenic_image(category_english: str, category_hebrew: str, output_path: str) -> str:
    """Alias for backwards compatibility."""
    return generate_thumbnail(category_english, category_hebrew, output_path)


if __name__ == "__main__":
    cat_en = sys.argv[1] if len(sys.argv) > 1 else "Positive Life"
    cat_he = sys.argv[2] if len(sys.argv) > 2 else "חיים חיוביים"
    out_p = sys.argv[3] if len(sys.argv) > 3 else str(BASE_DIR / "output" / "test_thumb.jpg")
    
    out = generate_thumbnail(cat_en, cat_he, out_p)
    print(f"Generated test thumbnail at: {out}")
