import os, io, base64, random, requests
from pathlib import Path
from dotenv import load_dotenv
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "thumbnails"))
from thumbnail_manager import get_thumbnail

load_dotenv()

POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")

SCENIC_STYLES = [
    "stunning Israeli woman, Tel Aviv beachfront, modern skyline",
    "elegant Israeli woman, Jerusalem, Western Wall, golden stone",
    "beautiful Israeli woman, Negev desert, Makhtesh Ramon, sunset",
    "Israeli woman at the Dead Sea, dramatic landscape, warm light",
    "gorgeous Israeli woman in modern style, Haifa, Bahai Gardens",
    "beautiful Israeli woman, Jaffa port, Mediterranean, golden hour",
    "Israeli woman in Jerusalem market, vibrant atmosphere",
    "elegant Israeli woman, Galilee, lush green hills, peaceful",
]


def generate_scenic_image(category_english: str, category_hebrew: str, output_path: str):
    # Try pre-made thumbnail first
    premade = get_thumbnail("Hebrew", category_english)
    if premade:
        return premade
    
    img = Image.new('RGB', (1920, 1080), (45, 35, 65))
    draw = ImageDraw.Draw(img)

    for y in range(1080):
        ratio = y / 1080
        if ratio < 0.5:
            r, g, b = 65, 50, 95
        else:
            r = int(65 + (45 - 65) * ((ratio - 0.5) * 2))
            g = int(50 + (35 - 50) * ((ratio - 0.5) * 2))
            b = int(95 + (65 - 95) * ((ratio - 0.5) * 2))
        draw.rectangle([(0, y), (1920, y + 1)], fill=(r, g, b))

    en_fonts = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    ja_fonts = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                ]

    def load_font(paths, size):
        for p in paths:
            if Path(p).exists():
                try: return ImageFont.truetype(p, size)
                except: continue
        return ImageFont.load_default()

    f_big = load_font(en_fonts, 130)
    f_cat = load_font(ja_fonts, 90)
    f_sub = load_font(en_fonts, 55)
    f_brand = load_font(en_fonts, 45)

    draw.text((960, 180), "120 HEBREW PHRASES", fill=(255, 210, 0), font=f_big, anchor="mm")

    cat_text = category_english
    bb = draw.textbbox((0, 0), cat_text, font=f_cat)
    cw = bb[2] - bb[0]
    cx = (1920 - cw) // 2
    draw.rounded_rectangle([(cx - 30, 350), (cx + cw + 30, 500)], radius=20, fill=(120, 40, 200, 230))
    draw.text((960, 425), cat_text, fill=(255, 255, 255), font=f_cat, anchor="mm")

    draw.rounded_rectangle([(960 - 200, 580), (960 + 200, 670)], radius=15, fill=(0, 0, 0, 180))
    draw.text((960, 625), "10 MINUTE LESSON", fill=(255, 210, 0), font=f_sub, anchor="mm")

    brand_text = "VELOCITY HEBREW"
    bb = draw.textbbox((0, 0), brand_text, font=f_brand)
    draw.text(((1920 - (bb[2] - bb[0])) // 2, 950), brand_text, fill=(200, 200, 200), font=f_brand)

    thumb_bytes = io.BytesIO()
    quality = 85
    img.save(thumb_bytes, format="JPEG", quality=quality)
    while thumb_bytes.tell() > 2097152 and quality > 10:
        quality -= 10
        thumb_bytes = io.BytesIO()
        img.save(thumb_bytes, format="JPEG", quality=quality)
    thumb_bytes.seek(0)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(thumb_bytes.read())
    print(f"[thumbnail] Fallback thumbnail saved (AI unavailable)")
    return output_path

