"""
YouTube Long-Form Video Automation - Bilingual English/Hebrew Content Generator
GENERATES 10-MINUTE VIDEOS with improved backgrounds for YouTube
"""

import os
import sys
import json
import random
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")

# Directories
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
IMAGES_DIR = OUTPUT_DIR / "images"
AUDIO_DIR = OUTPUT_DIR / "audio"
VIDEO_DIR = OUTPUT_DIR / "video"
HISTORY_DIR = OUTPUT_DIR / "history"
LONGFORM_DIR = OUTPUT_DIR / "longform_videos"

for d in [OUTPUT_DIR, IMAGES_DIR, AUDIO_DIR, VIDEO_DIR, HISTORY_DIR, LONGFORM_DIR]:
    d.mkdir(exist_ok=True)

# Video settings (16:9 horizontal for YouTube long-form)
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30
TARGET_DURATION_MINUTES = 20  # Target ~20-minute videos (120 unique phrases with natural pedagogical pauses)
TARGET_PHRASES = 120  # Number of unique phrases to generate

# English category names (for American/European learners)

# Hebrew translations for display
CATEGORIES_HEBREW = {
    "Motivation": "מוטיבציה",
    "Love": "אהבה",
    "Success": "הצלחה",
    "Wisdom": "חוכמה",
    "Happiness": "אושר",
    "Self Improvement": "שיפור עצמי",
    "Gratitude": "הכרת תודה",
    "Friendship": "חברות",
    "Hope": "תקווה",
    "Creativity": "יצירתיות",
    "Inner Peace": "שלווה פנימית",
    "Confidence": "ביטחון",
    "Perseverance": "התמדה",
    "Inspiration": "השראה",
    "Positive Life": "חיים חיוביים",
    "Courage": "אומץ",
    "Kindness": "טוב לב",
    "Patience": "סבלנות",
    "Forgiveness": "סליחה",
    "Strength": "כוח",
    "Joy": "שמחה",
    "Balance": "איזון",
    "Growth": "צמיחה",
    "Purpose": "מטרה",
    "Mindfulness": "מיינדפולנס",

    # 26-50: Practical Conversational & Real-World Life Scenarios
    "Travel & Airport": "טיולים ושדות תעופה",
    "Ordering Food & Dining": "הזמנת אוכל ואכילה במסעדות",
    "Shopping & Prices": "קניות ומחירים",
    "Asking for Directions": "בקשת הוראות הגעה",
    "Hotel & Accommodation": "מלונות ואירוח",
    "Daily Routine": "שגרת יום",
    "Meeting People & Greetings": "פגישה עם אנשים וברכות",
    "Emergency & Health": "חירום ובריאות",
    "Public Transportation": "תחבורה ציבורית",
    "Work & Office": "עבודה ומשרד",
    "Weather & Small Talk": "מזג אוויר ושיחת חולין",
    "Coffee Shop & Bakery": "בית קפה ומאפייה",
    "Family & Home": "משפחה ובית",
    "Hobbies & Free Time": "תחביבים ופנאי",
    "Dating & Romance": "דייטינג ורומנטיקה",
    "Phone Calls & Messages": "שיחות טלפון והודעות",
    "Banking & Money": "בנקאות וכסף",
    "Doctor & Pharmacy": "רופא ובית מרקחת",
    "Sports & Fitness": "ספורט וכושר",
    "Celebrations & Parties": "חגיגות ומסיבות",
    "Feelings & Emotions": "רגשות ותחושות",
    "Agreeing & Disagreeing": "הסכמה ואי-הסכמה",
    "Making Plans": "תכנון פגישות",
    "Common Native Slang": "סלנג מקומי נפוץ",
    "Cultural Traditions": "מסורות תרבותיות",
}


# English category names (dynamic)
CATEGORIES_ENGLISH = list(CATEGORIES_HEBREW.keys())
# Edge TTS voices
ENGLISH_VOICE = "en-US-GuyNeural"
HEBREW_VOICE = "he-IL-HilaNeural"

# Phrase history file (NEVER delete this!)
PHRASE_HISTORY_FILE = HISTORY_DIR / "all_generated_phrases.json"

# Viral hook styles for engagement
VIRAL_STYLES = [
    "surprising fact",
    "common mistake correction",
    "quick tip",
    "must-know phrase",
    "local secret",
    "travel hack",
    "flirty phrase",
    "funny expression",
    "cultural insight",
    "word origin story"
]

# AI Model
AI_MODEL = os.getenv("AI_MODEL") or "gemini-fast"


# ============== PHRASE HISTORY MANAGEMENT & DEDUPLICATION ==============

def normalize_phrase_text(text: str) -> str:
    """Normalize phrase text for strict duplicate detection (lowercase, alphanumeric only)."""
    import re
    return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()


def get_phrase_words(text: str) -> set:
    """Extract set of words for similarity check, ignoring trivial single-letter words."""
    import re
    words = set(re.findall(r'\b[a-z0-9]+\b', text.lower()))
    return {w for w in words if len(w) > 1}


def is_phrase_similar_fast(cand_words: set, reference_words_list: list, threshold: float = 0.65) -> bool:
    """Fast similarity check using Jaccard word overlap to prevent rephrased duplicates."""
    if not cand_words:
        return False
    cand_len = len(cand_words)
    for ref_words in reference_words_list:
        if not ref_words:
            continue
        intersection_len = len(cand_words.intersection(ref_words))
        if intersection_len == 0:
            continue
        union_len = cand_len + len(ref_words) - intersection_len
        if union_len > 0 and (intersection_len / union_len) >= threshold:
            return True
    return False


def load_phrase_history():
    """Load all previously generated phrases"""
    if PHRASE_HISTORY_FILE.exists():
        try:
            with open(PHRASE_HISTORY_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            print(f"[history] Warning: Could not read history file ({e}), initializing fresh.")
    return {"phrases": [], "last_updated": None}


def save_phrase_history(data):
    """Save phrase history"""
    data["last_updated"] = datetime.now().isoformat()
    with open(PHRASE_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_phrases_to_history(phrases, category):
    """Add new unique phrases to permanent history"""
    history = load_phrase_history()
    existing_normalized = {
        normalize_phrase_text(p.get("english", ""))
        for p in history.get("phrases", [])
        if p.get("english")
    }
    
    added_count = 0
    for phrase in phrases:
        norm = normalize_phrase_text(phrase.get("english", ""))
        if norm and norm not in existing_normalized:
            existing_normalized.add(norm)
            foreign_val = phrase.get("hebrew") or phrase.get("target") or phrase.get("foreign") or ""
            history["phrases"].append({
                "english": phrase["english"],
                "hebrew": foreign_val,
                "category": category,
                "generated_at": datetime.now().isoformat()
            })
            added_count += 1
            
    save_phrase_history(history)
    print(f"[history] Added {added_count} unique phrases to permanent history (total: {len(history['phrases'])})")


# ============== CONTENT GENERATION ==============

def calculate_phrases_needed(target_minutes: int) -> int:
    """
    Calculate how many phrases needed for target video duration.
    With pedagogical pauses (English ~2.5s + 1.2s pause + Foreign ~3.0s + 2.0s pause = ~8.7-10.0s per phrase):
    For 20 minutes (1200 seconds): 1200 / 10 = ~120 phrases.
    """
    avg_phrase_duration = 10.0  # seconds
    total_seconds = target_minutes * 60
    return int(total_seconds / avg_phrase_duration)


def repair_and_parse_json(content: str):
    """Robustly parse JSON from LLM output with truncation repair and regex recovery."""
    import re
    cleaned = content.strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end+1])
        except Exception:
            pass

    if start != -1:
        sub = cleaned[start:]
        last_brace = sub.rfind("}")
        if last_brace != -1:
            try:
                return json.loads(sub[:last_brace+1] + "]")
            except Exception:
                pass

    matches = re.findall(r'\{[^{}]*"english"[^{}]*\}', cleaned)
    results = []
    for m in matches:
        try:
            obj = json.loads(m)
            if isinstance(obj, dict) and "english" in obj:
                results.append(obj)
        except Exception:
            continue
    if results:
        return results

    raise ValueError("Could not parse or repair JSON from content")


# Sub-themes to guarantee rich vocabulary variety and completely prevent repetitive phrasing
SUBTHEMES = [
    ("Everyday Essentials & Reactions", "Focus on high-frequency everyday expressions, quick reactions, and essential conversational starters"),
    ("Questions & Interactive Dialogue", "Focus on asking questions, polite inquiries, seeking advice, and two-way conversations"),
    ("Mindset & Encouragement", "Focus on motivating thoughts, affirmations, giving praise, and positive mindset"),
    ("Native Idioms & Cultural Sayings", "Focus on natural idioms, colloquial expressions, common sayings, and local phrasing"),
    ("Reflections & Emotional Honesty", "Focus on expressing personal feelings, sincere reflections, patience, and deeper thoughts"),
    ("Practical Life Situations & Tips", "Focus on daily habits, real-world social scenarios, practical problem-solving, and actionable advice")
]


def get_next_category(categories_dict: dict) -> str:
    """Select the least recently used category to guarantee a smooth, non-repeating cycle"""
    recent_file = HISTORY_DIR / "recent_categories.json"
    recent = []
    if recent_file.exists():
        try:
            with open(recent_file, "r", encoding="utf-8") as f:
                recent = json.load(f)
        except Exception:
            recent = []

    all_cats = list(categories_dict.keys())
    cooldown = max(1, len(all_cats) - 10)
    available = [c for c in all_cats if c not in recent[-cooldown:]]
    if not available:
        available = all_cats

    chosen = random.choice(available)
    recent.append(chosen)
    if len(recent) > 100:
        recent = recent[-100:]

    try:
        with open(recent_file, "w", encoding="utf-8") as f:
            json.dump(recent, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    return chosen


def generate_phrases_for_longform(category_english: str, num_phrases: int = TARGET_PHRASES) -> list:
    """
    Generate 100% unique bilingual phrases for a ~20-minute long-form video.
    Guarantees NO repetition within the video and NO repetition across past videos.
    """
    import requests
    import time

    category_foreign = CATEGORIES_HEBREW[category_english]
    history = load_phrase_history()
    
    # Pre-index all past phrases in history
    history_phrases = history.get("phrases", [])
    history_norm_set = {
        normalize_phrase_text(p.get("english", ""))
        for p in history_phrases
        if p.get("english")
    }
    history_words_list = [
        get_phrase_words(p.get("english", ""))
        for p in history_phrases
        if p.get("english")
    ]
    
    # Category-specific past phrases (to feed directly into LLM exclusion prompts)
    category_past_english = [
        p.get("english", "")
        for p in history_phrases
        if p.get("category") == category_english and p.get("english")
    ]

    all_phrases = []
    current_video_norm_set = set()
    current_video_words_list = []

    num_batches = len(SUBTHEMES)
    target_per_batch = (num_phrases + num_batches - 1) // num_batches
    max_batch_attempts = 4

    print(f"[content] Starting generation of {num_phrases} UNIQUE phrases for '{category_english}' ({category_foreign})...")

    for batch_idx, (theme_name, theme_guidance) in enumerate(SUBTHEMES):
        remaining_needed = num_phrases - len(all_phrases)
        if remaining_needed <= 0:
            break

        batch_target = min(target_per_batch, remaining_needed)
        request_count = min(30, batch_target + 10)
        temp = round(0.85 + (batch_idx * 0.05), 2)
        viral_style = random.choice(VIRAL_STYLES)

        for attempt in range(max_batch_attempts):
            remaining_for_batch = batch_target - (len(all_phrases) - (batch_idx * target_per_batch))
            if remaining_for_batch <= 0 and len(all_phrases) >= (batch_idx + 1) * target_per_batch:
                break

            try:
                # Dynamic exclusion list:
                # 1. Phrases generated in THIS video run (prevents repeating across batches!)
                # 2. Recent phrases from past history for this category
                current_generated_en = [p["english"] for p in all_phrases[-40:]]
                recent_cat_past = category_past_english[-25:] if category_past_english else []
                combined_exclusions = list(dict.fromkeys(current_generated_en + recent_cat_past))
                
                exclusion_note = ""
                if combined_exclusions:
                    exclusion_note = (
                        f"\n\nCRITICAL: DO NOT use, repeat, or slightly rephrase any of these phrases:\n"
                        + "\n".join(f"- {p}" for p in combined_exclusions[:40])
                    )

                prompt = f"""Create {request_count} UNIQUE {category_english} phrases for English speakers learning Hebrew.

Thematic Section {batch_idx + 1}/{num_batches}: {theme_name}
Focus: {theme_guidance} related to {category_english}.
Style: Natural, authentic {viral_style} format - phrasing real native speakers use.

RULES FOR CLEAR, NATURAL SPEECH:
1. Length: Short and clear (4 to 12 words per phrase).
2. Natural pauses: Use commas (,) to indicate natural pauses for speaking practice (e.g. "Dream big, start small").
3. Everyday vocabulary: Practical, high-frequency, modern conversational vocabulary.
4. Variety: Varied grammatical forms (imperatives, questions, observations, short idioms).
5. NO REPETITION: Every phrase must express a distinct idea.{exclusion_note}

For each phrase provide:
1. "english": English phrase with commas for natural pauses
2. "hebrew": Natural Hebrew translation
3. "pronunciation": Pronunciation guide (phonetic spelling for English speakers, e.g. "Hej, hur mår du?")

Return STRICTLY a JSON array:
[{"english": "...", "hebrew": "...", "pronunciation": "..."}]"""

                url = "https://gen.pollinations.ai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": AI_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are an expert native Hebrew language instructor creating viral, high-retention educational lessons for YouTube. Always return clean, valid JSON with fresh, non-repeating phrases."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temp
                }

                response = requests.post(url, headers=headers, json=payload, timeout=90)
                response.raise_for_status()

                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                candidates = repair_and_parse_json(content)

                accepted_in_batch = 0
                for cand in candidates:
                    if len(all_phrases) >= num_phrases:
                        break

                    en_text = cand.get("english", "").strip()
                    foreign_text = (cand.get("hebrew") or cand.get("target") or cand.get("foreign") or "").strip()
                    pron_text = (cand.get("pronunciation") or cand.get("pronunciation") or cand.get("pinyin") or cand.get("romaji") or cand.get("phonetic") or "").strip()

                    if not en_text or not foreign_text:
                        continue

                    # Word count constraints (avoid single words or long run-ons)
                    words_count = len(en_text.split())
                    if words_count < 2 or words_count > 15:
                        continue

                    norm_en = normalize_phrase_text(en_text)
                    if not norm_en:
                        continue

                    # 1. Check exact match in current video (STRICT ZERO DUPLICATES in same video!)
                    if norm_en in current_video_norm_set:
                        continue

                    # 2. Check exact match in past history
                    if norm_en in history_norm_set:
                        continue

                    # 3. Check similarity against phrases already accepted in THIS video (prevents rephrasing)
                    cand_words = get_phrase_words(en_text)
                    if is_phrase_similar_fast(cand_words, current_video_words_list, threshold=0.65):
                        continue

                    # 4. Check similarity against past history
                    if is_phrase_similar_fast(cand_words, history_words_list, threshold=0.70):
                        continue

                    # Candidate is verified 100% unique!
                    valid_phrase = {
                        "english": en_text,
                        "hebrew": foreign_text,
                        "pronunciation": pron_text
                    }
                    current_video_norm_set.add(norm_en)
                    current_video_words_list.append(cand_words)
                    history_norm_set.add(norm_en)
                    history_words_list.append(cand_words)
                    all_phrases.append(valid_phrase)
                    accepted_in_batch += 1

                print(f"  [batch {batch_idx + 1}/{num_batches} '{theme_name}'] Added {accepted_in_batch} unique phrases (progress: {len(all_phrases)}/{num_phrases})")

                if len(all_phrases) >= (batch_idx + 1) * target_per_batch or len(all_phrases) >= num_phrases:
                    break

            except Exception as e:
                print(f"  [batch {batch_idx + 1}, attempt {attempt + 1}] Notice: {e}")
                time.sleep(2)

        time.sleep(0.5)

    # Secondary booster pass: if any slots remain to reach num_phrases, generate fresh conversational phrases
    attempts_booster = 0
    while len(all_phrases) < num_phrases and attempts_booster < 4:
        attempts_booster += 1
        needed = num_phrases - len(all_phrases)
        print(f"[content] Booster pass {attempts_booster}: Generating {needed} additional unique phrases...")
        try:
            current_generated_en = [p["english"] for p in all_phrases[-40:]]
            prompt = f"""Generate {needed + 8} FRESH, UNIQUE conversational phrases for English speakers learning Hebrew.
Theme: Practical life, emotional intelligence, and interpersonal communication related to {category_english}.

RULES:
1. 3 to 12 words per phrase. Natural commas for pauses.
2. DO NOT REPEAT ANY OF THESE:\n""" + "\n".join(f"- {p}" for p in current_generated_en) + f"""

Return STRICTLY a JSON array:
[{"english": "...", "hebrew": "...", "pronunciation": "..."}]"""

            url = "https://gen.pollinations.ai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": f"You are a native Hebrew tutor. Return only valid JSON array of unique phrases."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 1.05
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=90)
            resp.raise_for_status()
            candidates = repair_and_parse_json(resp.json()["choices"][0]["message"]["content"])
            
            for cand in candidates:
                if len(all_phrases) >= num_phrases:
                    break
                en_text = cand.get("english", "").strip()
                foreign_text = (cand.get("hebrew") or cand.get("target") or cand.get("foreign") or "").strip()
                pron_text = (cand.get("pronunciation") or cand.get("pronunciation") or cand.get("pinyin") or cand.get("romaji") or cand.get("phonetic") or "").strip()
                if not en_text or not foreign_text:
                    continue
                norm_en = normalize_phrase_text(en_text)
                if not norm_en or norm_en in current_video_norm_set or norm_en in history_norm_set:
                    continue
                cand_words = get_phrase_words(en_text)
                if is_phrase_similar_fast(cand_words, current_video_words_list, threshold=0.65):
                    continue
                
                valid_phrase = {"english": en_text, "hebrew": foreign_text, "pronunciation": pron_text}
                current_video_norm_set.add(norm_en)
                current_video_words_list.append(cand_words)
                history_norm_set.add(norm_en)
                history_words_list.append(cand_words)
                all_phrases.append(valid_phrase)
        except Exception as e:
            print(f"  [booster attempt {attempts_booster}] Error: {e}")
            time.sleep(2)

    final_phrases = all_phrases[:num_phrases]
    if final_phrases:
        add_phrases_to_history(final_phrases, category_english)

    print(f"\n[content] Successfully generated {len(final_phrases)} 100% UNIQUE phrases for '{category_english}'")
    return final_phrases

# ============== AUDIO GENERATION ==============

def configure_edge_tts():
    """Ensure edge_tts connects to Microsoft's active endpoint to avoid 403 on cloud runners."""
    try:
        import edge_tts.constants
        import edge_tts.communicate
        token = getattr(edge_tts.constants, "TRUSTED_CLIENT_TOKEN", "6A5AA1D4EAFF4E9FB37E23D68491D6F4")
        new_url = (
            "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
            f"?Ocp-Apim-Subscription-Key={token}"
        )
        edge_tts.constants.WSS_URL = new_url
        edge_tts.communicate.WSS_URL = new_url
    except Exception as e:
        pass


def generate_google_tts(text: str, voice_or_lang: str, output_path: str) -> bool:
    """Fallback TTS using Google Translate TTS if Edge TTS fails."""
    import urllib.request
    import urllib.parse

    lang_code = "en"
    voice_lower = str(voice_or_lang).lower()
    if voice_lower.startswith("en"):
        lang_code = "en"
    elif "-" in str(voice_or_lang):
        part = str(voice_or_lang).split("-")[0].lower()
        if part == "zh":
            lang_code = "zh-CN"
        elif part == "fil":
            lang_code = "tl"
        elif part == "nb":
            lang_code = "no"
        else:
            lang_code = part
    else:
        lang_code = voice_lower

    clean_text = text.replace("*", "").replace("#", "").strip()
    if not clean_text:
        return False

    try:
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={urllib.parse.quote(clean_text)}&tl={lang_code}&client=tw-ob"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        if len(data) > 200:
            with open(output_path, "wb") as f:
                f.write(data)
            return True
    except Exception as e:
        print(f"  Google TTS fallback error ({lang_code}): {e}")
    return False


async def generate_single_audio(text: str, voice: str, output_path: str, retries: int = 2):
    """Generate audio using Edge TTS Neural voice with automatic Google TTS fallback"""
    configure_edge_tts()
    import edge_tts
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            if Path(output_path).exists() and Path(output_path).stat().st_size > 300:
                return True
        except Exception as e:
            if attempt == retries - 1:
                print(f"  Edge TTS notice ({e}), switching to Google TTS fallback...")
            else:
                await asyncio.sleep(0.5)

    # Fallback to Google TTS
    if generate_google_tts(text, voice, output_path):
        return True

    return False


def generate_all_audio(phrases: list, output_dir: str):
    """Generate audio for all phrases with proper timing for a ~20-minute video"""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_files = []

    for i, phrase in enumerate(phrases):
        english_file = output_dir / f"english_{i:04d}.mp3"
        foreign_file = output_dir / f"hebrew_{i:04d}.mp3"
        combined_file = output_dir / f"combined_{i:04d}.mp3"

        if (i + 1) % 20 == 0 or (i + 1) == len(phrases):
            print(f"  Generating audio {i+1}/{len(phrases)}...")

        # Generate English audio
        en_success = asyncio.run(generate_single_audio(phrase["english"], ENGLISH_VOICE, str(english_file)))
        if not en_success:
            cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2", str(english_file)]
            subprocess.run(cmd, capture_output=True)

        # Generate Foreign audio
        foreign_text = phrase.get("hebrew") or phrase.get("target") or phrase.get("foreign") or ""
        foreign_success = asyncio.run(generate_single_audio(foreign_text, HEBREW_VOICE, str(foreign_file)))
        if not foreign_success:
            cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2", str(foreign_file)]
            subprocess.run(cmd, capture_output=True)

        # Get ACTUAL durations
        en_duration = get_audio_duration(str(english_file))
        foreign_duration = get_audio_duration(str(foreign_file))

        # Pedagogical pauses for optimal learning:
        # 1.2s pause after English: allows learner to process English meaning and anticipate translation
        # 2.0s pause after foreign phrase: allows learner to repeat aloud and study pronunciation
        pause_mid = 1.2
        pause_end = 2.0

        # Combine audio files with precise ffmpeg apad
        cmd = [
            "ffmpeg", "-y",
            "-i", str(english_file),
            "-i", str(foreign_file),
            "-filter_complex", f"[0:a]apad=pad_dur={pause_mid}[a0];[1:a]apad=pad_dur={pause_end}[a1];[a0][a1]concat=n=2:v=0:a=1[out]",
            "-map", "[out]",
            str(combined_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            concat_file = output_dir / f"concat_{i:04d}.txt"
            with open(concat_file, "w", encoding="utf-8") as f:
                f.write(f"file '{english_file.as_posix()}'\n")
                f.write(f"file '{foreign_file.as_posix()}'\n")

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c:a", "aac",
                str(combined_file)
            ]
            subprocess.run(cmd, capture_output=True)
            if concat_file.exists():
                concat_file.unlink()

        actual_duration = get_audio_duration(str(combined_file))

        audio_files.append({
            "index": i,
            "english": str(english_file),
            "hebrew": str(foreign_file),
            "combined": str(combined_file),
            "duration": actual_duration,
            "en_duration": en_duration,
            "foreign_duration": foreign_duration
        })

    print(f"\n[audio] Generated {len(audio_files)} phrase audios")
    return audio_files

def get_audio_duration(audio_file: str) -> float:
    """Get audio duration in seconds"""
    if not Path(audio_file).exists():
        return 2.0
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 2.0


def create_final_narration(audio_files: list, output_file: str):
    """Combine all audio files"""
    n = len(audio_files)
    print(f"[audio] Combining {n} audio files...")

    concat_file = Path(output_file).parent / "narration_list.txt"

    with open(concat_file, "w", encoding="utf-8") as f:
        for audio_info in audio_files:
            combined_path = Path(audio_info["combined"])
            if combined_path.exists():
                path_str = str(combined_path.resolve()).replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{path_str}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c:a", "copy", str(output_file)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if concat_file.exists():
        concat_file.unlink()

    if result.returncode == 0 and Path(output_file).exists() and Path(output_file).stat().st_size > 0:
        size = Path(output_file).stat().st_size
        print(f"\n[audio] ✓ Final narration: {Path(output_file).name} ({size/1024:.1f} KB)")
        return True

    return False


# ============== IMPROVED BACKGROUND GENERATION ==============

def create_premium_background(category_english: str):
    """Create Lingexa's exact light cream background"""
    from PIL import Image, ImageDraw

    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT))
    draw = ImageDraw.Draw(img)

    # Light cream gradient - NO circles, clean background
    for y in range(VIDEO_HEIGHT):
        ratio = y / VIDEO_HEIGHT
        if ratio < 0.5:
            r, g, b = 255, 252, 245
        else:
            r = int(255 + (245 - 255) * ((ratio - 0.5) * 2))
            g = int(252 + (240 - 252) * ((ratio - 0.5) * 2))
            b = int(245 + (230 - 245) * ((ratio - 0.5) * 2))
        draw.rectangle([(0, y), (VIDEO_WIDTH, y + 1)], fill=(r, g, b))

    return img



def generate_complete_image(phrase_data: dict, category_english: str, output_path: str):
    """Generate image with modern glassmorphic UI - Lingexa Inspired"""
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageFilter
    except ImportError:
        print("PIL not available. Install: pip install Pillow")
        return None

    img = create_premium_background(category_english)
    img = img.convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Load fonts
    english_font_paths = [
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    spanish_font_paths = [
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]

    def load_font(font_paths, size):
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue
        return ImageFont.load_default()

    # Refined font sizes
    font_category = load_font(english_font_paths, 42)
    font_english = load_font(english_font_paths, 68)
    font_spanish = load_font(spanish_font_paths, 82)
    font_pronunciation = load_font(spanish_font_paths, 48)
    font_branding = load_font(english_font_paths, 38)

    english = phrase_data.get("english", "")
    hebrew_text = phrase_data.get('hebrew') or phrase_data.get('spanish', '')
    pronunciation = phrase_data.get("pronunciation") or phrase_data.get("pronunciation") or phrase_data.get("pinyin") or phrase_data.get("romaji") or phrase_data.get("phonetic") or ""

    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line.append(word)
            else:
                if current_line: lines.append(' '.join(current_line))
                current_line = [word]
        if current_line: lines.append(' '.join(current_line))
        return lines

    # Header Bar (Top Left)
    cat_text = category_english.upper()
    cat_bbox = draw.textbbox((0, 0), cat_text, font=font_category)
    cat_w = cat_bbox[2] - cat_bbox[0]
    
    # Badge dimensions - fixed height for perfect centering
    badge_h = 75
    badge_pad_x = 40
    container_w = cat_w + (badge_pad_x * 2)
    
    container_x = 60
    container_y = 60
    
    draw.rounded_rectangle(
        [(container_x, container_y), (container_x + container_w, container_y + badge_h)],
        radius=15, fill=(45, 35, 65, 255)
    )
    # Draw text perfectly centered in the badge (with +2px vertical offset for visual balance)
    draw.text(
        (container_x + container_w // 2, container_y + badge_h // 2 + 2), 
        cat_text, 
        fill=(255, 255, 255, 255), 
        font=font_category, 
        anchor="mm"
    )

    # Top Right Lesson Progress Indicator
    prog_text = "120 ESSENTIAL PHRASES"
    prog_bbox = draw.textbbox((0, 0), prog_text, font=font_branding)
    prog_w = prog_bbox[2] - prog_bbox[0]
    prog_pad_x = 30
    prog_container_w = prog_w + (prog_pad_x * 2)
    prog_x = VIDEO_WIDTH - prog_container_w - 60
    draw.rounded_rectangle(
        [(prog_x, container_y), (prog_x + prog_container_w, container_y + badge_h)],
        radius=15, fill=(255, 210, 160, 255)
    )
    draw.text(
        (prog_x + prog_container_w // 2, container_y + badge_h // 2 + 2),
        prog_text,
        fill=(70, 45, 25, 255),
        font=font_branding,
        anchor="mm"
    )

    # Main Content Area - Center Vertical
    CONTENT_Y_CENTER = VIDEO_HEIGHT // 2
    GAP = 60

    # 1. English Box
    en_lines = wrap_text(english, font_english, VIDEO_WIDTH - 300)
    en_line_h = 80
    en_total_h = len(en_lines) * en_line_h
    
    # 2. Hebrew Box
    es_lines = wrap_text(hebrew_text, font_spanish, VIDEO_WIDTH - 300)
    es_line_h = 100
    es_total_h = len(es_lines) * es_line_h
    
    # 3. Pronunciation Box
    pron_text = f"[{pronunciation}]"
    pron_lines = wrap_text(pron_text, font_pronunciation, VIDEO_WIDTH - 400)
    pron_line_h = 60
    pron_total_h = len(pron_lines) * pron_line_h

    total_content_h = en_total_h + es_total_h + pron_total_h + (GAP * 2)
    y_start = CONTENT_Y_CENTER - (total_content_h // 2)

    # Draw English Section
    box_w = VIDEO_WIDTH - 200
    box_x = (VIDEO_WIDTH - box_w) // 2
    
    # English Box (Lingexa Dark Purple)
    en_box_h = en_total_h + 60
    draw.rounded_rectangle(
        [(box_x, y_start), (box_x + box_w, y_start + en_box_h)],
        radius=25, fill=(65, 50, 95, 255)
    )
    for i, line in enumerate(en_lines):
        draw.text((VIDEO_WIDTH // 2, y_start + 30 + (i * en_line_h) + en_line_h // 2), 
                  line, fill=(255, 255, 255), font=font_english, anchor="mm")
    
    y_cursor = y_start + en_box_h + GAP

    # Hebrew Section (Lingexa Lighter Purple)
    es_box_h = es_total_h + 60
    draw.rounded_rectangle(
        [(box_x, y_cursor), (box_x + box_w, y_cursor + es_box_h)],
        radius=25, fill=(95, 80, 125, 255)
    )
    for i, line in enumerate(es_lines):
        draw.text((VIDEO_WIDTH // 2, y_cursor + 30 + (i * es_line_h) + es_line_h // 2), 
                  line, fill=(255, 255, 255), font=font_spanish, anchor="mm")

    y_cursor += es_box_h + (GAP // 2)

    # Pronunciation Section (Lingexa Peach)
    pron_box_h = pron_total_h + 40
    pron_box_w = box_w - 200
    pron_box_x = (VIDEO_WIDTH - pron_box_w) // 2
    draw.rounded_rectangle(
        [(pron_box_x, y_cursor), (pron_box_x + pron_box_w, y_cursor + pron_box_h)],
        radius=20, fill=(255, 210, 160, 255)
    )

    for i, line in enumerate(pron_lines):
        draw.text((VIDEO_WIDTH // 2, y_cursor + 20 + (i * pron_line_h) + pron_line_h // 2), 
                  line, fill=(70, 45, 25), font=font_pronunciation, anchor="mm")

    # Branding (Bottom Right)
    brand_text = "VELOCITY HEBREW"
    brand_bbox = draw.textbbox((0, 0), brand_text, font=font_branding)
    brand_w = brand_bbox[2] - brand_bbox[0]
    draw.text((VIDEO_WIDTH - brand_w - 60, VIDEO_HEIGHT - 80), brand_text, 
              fill=(45, 35, 65, 255), font=font_branding)

    # Save
    img = img.convert('RGB')
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95, optimize=True)
    return output_path



# ============== THUMBNAIL GENERATION ==============

def generate_thumbnail(category_english: str, category_hebrew: str, output_path: str):
    """Generate a modern, high-impact thumbnail - Lingexa Inspired"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PIL not available for thumbnail. Install: pip install Pillow")
        return None

    # Use the same base background logic but with even more "pop"
    img = create_premium_background(category_english)
    img = img.convert('RGBA')
    draw = ImageDraw.Draw(img)

    # Load fonts
    english_font_paths = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
    spanish_font_paths = ["C:/Windows/Fonts/arialbd.ttf"]

    def load_font(font_paths, size):
        for font_path in font_paths:
            try: return ImageFont.truetype(font_path, size)
            except: continue
        return ImageFont.load_default()

    font_huge = load_font(english_font_paths, 130)
    font_main = load_font(spanish_font_paths, 110)
    font_sub = load_font(english_font_paths, 60)
    font_badge = load_font(english_font_paths, 45)

    # Big Impact Title (Dark Purple)
    draw.text((VIDEO_WIDTH // 2, 220), "MASTER HEBREW", fill=(45, 35, 65), font=font_huge, anchor="mm")
    
    # Category Badge (Lingexa Dark Purple)
    cat_text = category_english.upper()
    cat_bbox = draw.textbbox((0, 0), cat_text, font=font_sub)
    cat_w = cat_bbox[2] - cat_bbox[0]
    draw.rounded_rectangle(
        [(VIDEO_WIDTH // 2 - cat_w // 2 - 40, 320), (VIDEO_WIDTH // 2 + cat_w // 2 + 40, 410)],
        radius=20, fill=(65, 50, 95, 255)
    )
    draw.text((VIDEO_WIDTH // 2, 365), cat_text, fill=(255, 255, 255), font=font_sub, anchor="mm")

    # Hebrew Translation (Dark Purple)
    draw.text((VIDEO_WIDTH // 2, 530), category_hebrew, fill=(45, 35, 65), font=font_main, anchor="mm")

    # Features / Call to Action (Lingexa Peach)
    cta_text = "120 ESSENTIAL PHRASES"
    draw.rounded_rectangle(
        [(VIDEO_WIDTH // 2 - 300, 650), (VIDEO_WIDTH // 2 + 300, 730)],
        radius=15, fill=(255, 210, 160, 255)
    )
    draw.text((VIDEO_WIDTH // 2, 690), cta_text, fill=(70, 45, 25), font=font_badge, anchor="mm")

    # Bottom Branding (Dark Purple Bar)
    draw.rectangle([(0, VIDEO_HEIGHT - 100), (VIDEO_WIDTH, VIDEO_HEIGHT)], fill=(45, 35, 65, 255))
    draw.text((VIDEO_WIDTH // 2, VIDEO_HEIGHT - 50), "VELOCITY HEBREW", fill=(255, 255, 255), font=font_badge, anchor="mm")

    img = img.convert('RGB')
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95, optimize=True)
    return output_path



def extract_video_thumbnail(video_path: str, output_path: str, timestamp_seconds: int = 5):
    """Extract a frame from the video as thumbnail using FFmpeg"""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(timestamp_seconds),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(output_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and Path(output_path).exists():
            print(f"  ✓ Video thumbnail extracted: {Path(output_path).name}")
            return str(output_path)
        else:
            print(f"  ⚠️ Could not extract video thumbnail")
            return None
    except Exception as e:
        print(f"  ⚠️ Thumbnail extraction error: {e}")
        return None


# ============== TITLE & DESCRIPTION GENERATION ==============

def generate_title_description(category_english: str, category_foreign: str, phrases: list, duration_minutes: float, output_dir: str):
    """Generate viral YouTube title and description with all phrases - COMBINED in one file"""
    
    count = len(phrases)
    est_mins = int(round(duration_minutes)) if duration_minutes > 0 else 20
    
    # Generate viral title variations
    titles = [
        f"Learn Hebrew in {est_mins} Minutes | {count} {category_english} Phrases Every Beginner NEEDS to Know! ({category_foreign})",
        f"{count} Hebrew Phrases for {category_english} | Speak Hebrew Like a Native! ({category_foreign})",
        f"Master Hebrew {category_english} | {count} Essential Hebrew Phrases with Pronunciation | VELOCITY HEBREW",
        f"Hebrew Learning Made Easy | {category_english} Vocabulary | {est_mins} Minute Lesson",
        f"Speak Hebrew Fluently | {category_english} Phrases | English + Hebrew + Pronunciation",
    ]

    # Generate comprehensive description
    description = f"""🇮🇱 Learn Hebrew with VELOCITY HEBREW! 🇮🇱

In this video, you'll learn {count} essential Hebrew phrases about {category_english} ({category_foreign}).
Perfect for beginners and intermediate learners!

📚 WHAT YOU'LL LEARN:
• {count} practical {category_english} phrases in Hebrew
• Correct pronunciation with phonetics
• Natural pedagogical pauses for speaking practice
• Common expressions used by native speakers

⏱️ VIDEO TIMESTAMPS:
"""

    # Add timestamps for each phrase (every 10 phrases grouped)
    avg_phrase_duration = (duration_minutes * 60) / max(len(phrases), 1)
    for i in range(0, len(phrases), 10):
        timestamp = int(i * avg_phrase_duration / 60)
        minute = timestamp
        second = int((i * avg_phrase_duration) % 60)
        end_phrase = min(i + 10, len(phrases))
        description += f"{minute:02d}:{second:02d} Phrases {i+1}-{end_phrase}\n"

    description += f"""
📝 ALL PHRASES IN THIS VIDEO:
"""

    # Add all phrases
    for i, phrase in enumerate(phrases, 1):
        foreign_phrase_text = phrase.get("hebrew") or phrase.get("target") or phrase.get("foreign") or ""
        pron_phrase_text = phrase.get("pronunciation") or phrase.get("pronunciation") or phrase.get("pinyin") or phrase.get("romaji") or phrase.get("phonetic") or ""
        description += f"""
{i}. {phrase['english']}
   Hebrew: {foreign_phrase_text}
   Pronunciation: {pron_phrase_text}
"""

    description += f"""
🎯 PERFECT FOR:
• Hebrew beginners wanting to expand vocabulary
• Intermediate learners practicing pronunciation
• Anyone interested in Hebrew culture
• Language enthusiasts and polyglots
• Students preparing for Hebrew language exams

💡 TIPS FOR LEARNING:
1. Repeat each phrase out loud during the pause
2. Practice daily for best results
3. Use the pauses to speak along
4. Write down phrases you find difficult
5. Review this video multiple times

🔔 SUBSCRIBE for more Hebrew learning content!
👍 LIKE this video if you found it helpful!
💬 COMMENT which phrases you want to learn next!

📱 FOLLOW VELOCITY HEBREW:
[Add your social media links here]

🎵 MUSIC:
[Add music credits if applicable]

📖 RELATED VIDEOS:
• Hebrew Motivation Phrases
• Hebrew Love Expressions
• Hebrew Basics
• Basic Hebrew Greetings

#Hebrew #HebrewPhrases #HebrewLanguage #{category_english.replace(' ', '')} #VELOCITYHEBREW #HebrewForBeginners #SpeakHebrew #HebrewVocabulary #LanguageLearning #Hebrew101 #HebrewLesson

---
© VELOCITY HEBREW - Making Hebrew learning accessible to everyone!
"""

    # Write to COMBINED file (title + description in one)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "youtube_upload_info.txt", "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("YOUTUBE VIDEO UPLOAD INFORMATION\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("📌 RECOMMENDED TITLES (Choose one):\n")
        f.write("-" * 80 + "\n")
        for i, title in enumerate(titles, 1):
            f.write(f"\n{i}. {title}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("📝 SELECTED TITLE (Recommended):\n")
        f.write("-" * 80 + "\n")
        f.write(f"\n{titles[0]}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("📄 VIDEO DESCRIPTION:\n")
        f.write("-" * 80 + "\n\n")
        f.write(description)
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("🏷️ VIDEO TAGS (for YouTube):\n")
        f.write("-" * 80 + "\n")
        tags = [
            f"Learn Hebrew",
            f"Hebrew Phrases",
            f"Hebrew",
            category_english,
            brand_text,
            f"Hebrew for Beginners",
            f"Speak Hebrew",
            f"Hebrew Vocabulary",
            "Pronunciation",
            "Language Learning",
            f"Hebrew 101",
            f"Hebrew Lesson"
        ]
        f.write(", ".join(tags) + "\n")

    # Metadata JSON (for easy parsing)
    metadata = {
        "recommended_titles": titles,
        "selected_title": titles[0],
        "description": description,
        "category_english": category_english,
        "category_hebrew": category_foreign,
        "phrases_count": len(phrases),
        "duration_minutes": round(duration_minutes, 2),
        "tags": tags
    }

    with open(output_dir / "video_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n[metadata] Generated YouTube upload files")
    print(f"  youtube_upload_info.txt (title + description + tags)")
    print(f"  video_metadata.json")

    return metadata

def create_video_from_images_audio(image_files: list, audio_files: list, combined_audio: str, output_file: str):
    """Create video from images and audio with PERFECT synchronization"""

    print(f"\n[video] Creating long-form video from {len(image_files)} images...")
    print(f"[video] Embedding audio in each clip for frame-perfect sync...")

    temp_clips = []

    for i, (img_path, audio_info) in enumerate(zip(image_files, audio_files)):
        duration = audio_info['duration']
        print(f"  Image {i+1}/{len(image_files)}: {duration:.2f}s (EN: {audio_info.get('en_duration', 0):.1f}s + ES: {audio_info.get('he_duration', 0):.1f}s)")

        temp_clip = Path(output_file).parent / f"temp_clip_{i:04d}.mp4"
        temp_clips.append(temp_clip)

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-i", audio_info['combined'],
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            "-shortest",
            "-vsync", "cfr",
            str(temp_clip)
        ]

        subprocess.run(cmd, check=True, capture_output=True)

    print("[video] Concatenating clips...")
    concat_file = Path(output_file).parent / "concat_list.txt"

    with open(concat_file, "w", encoding="utf-8") as f:
        for clip in temp_clips:
            f.write(f"file '{clip.resolve().as_posix()}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(output_file)]
    subprocess.run(cmd, check=True, capture_output=True)

    if concat_file.exists():
        concat_file.unlink()

    video_duration = get_audio_duration(str(output_file))
    print(f"[video] ✓ Video created: {Path(output_file).name} ({video_duration:.2f}s)")

    for clip in temp_clips:
        if clip.exists():
            clip.unlink()


# ============== MAIN WORKFLOW ==============

def generate_longform_video(category_english: str = None, target_phrases: int = None):
    """Generate complete long-form YouTube video with thumbnail and metadata"""

    if not category_english:
        category_english = get_next_category(CATEGORIES_HEBREW)

    # Use provided phrases count or default
    phrases_count = target_phrases if target_phrases else TARGET_PHRASES

    print(f"\n{'='*80}")
    print(f"🎬 LONG-FORM VIDEO - Category: {category_english} ({CATEGORIES_HEBREW[category_english]})")
    print(f"🎯 Target Phrases: {phrases_count}")
    print(f"{'='*80}\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_dir = LONGFORM_DIR / f"{category_english}_longform_{timestamp}"
    video_dir.mkdir(exist_ok=True)

    # Step 1: Generate unique phrases
    print(f"[1/6] Generating {phrases_count} unique phrases (checking history)...")
    phrases = generate_phrases_for_longform(category_english, phrases_count)

    for i, phrase in enumerate(phrases, 1):
        print(f"  {i}. {phrase['english']} → {phrase['hebrew']}")

    print(f"\n[info] Total phrases: {len(phrases)}")

    # Step 2: Generate images
    print(f"\n[2/6] Generating {len(phrases)} images with premium backgrounds...")
    for i, phrase in enumerate(phrases):
        output_path = video_dir / f"phrase_{i:04d}.jpg"
        generate_complete_image(phrase, category_english, str(output_path))
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i+1}/{len(phrases)} images...")

    # Step 3: Generate thumbnail using gpt-image-2 via Pollinations
    print(f"\n[3/6] Using first phrase image as thumbnail...")
    thumbnail_path = video_dir / "thumbnail.jpg"
    first_phrase = sorted(video_dir.glob("phrase_*.jpg"))
    if first_phrase:
        import shutil
        shutil.copy2(str(first_phrase[0]), str(thumbnail_path))
        print(f"  Thumbnail: {first_phrase[0].name} (content-based)")
    else:
        try:
            from generate_thumbnail import generate_scenic_image
            result = generate_scenic_image(category_english, category_english, str(thumbnail_path))
            if result and Path(result).exists():
                print(f"  gpt-image-2 thumbnail saved")
            else:
                print(f"  gpt-image-2 failed, using built-in")
                generate_thumbnail(category_english, CATEGORIES_HEBREW[category_english], str(thumbnail_path))
        except Exception as e:
            print(f"  Thumbnail error: {e}, using built-in")
            generate_thumbnail(category_english, CATEGORIES_HEBREW[category_english], str(thumbnail_path))
    video_thumbnail_path = video_dir / "video_thumbnail_frame.jpg"
    print(f"\n[4/6] Generating audio for {len(phrases)} phrases...")
    audio_files = generate_all_audio(phrases, str(video_dir))

    final_audio = video_dir / "narration.mp3"
    create_final_narration(audio_files, str(final_audio))

    # Calculate actual duration
    total_duration = sum(a['duration'] for a in audio_files)
    print(f"\n[info] Total audio duration: {total_duration:.2f}s ({total_duration/60:.2f} minutes)")

    # Step 5: Create video
    print(f"\n[5/6] Creating long-form video with transitions...")
    output_video = video_dir / "final_video.mp4"

    image_files = sorted([str(p) for p in video_dir.glob("phrase_*.jpg")])

    create_video_from_images_audio(
        image_files,
        audio_files,
        str(final_audio),
        str(output_video)
    )
    
    # Extract video frame as thumbnail
    print(f"\n[5.5/6] Extracting video frame for thumbnail...")
    extract_video_thumbnail(str(output_video), str(video_thumbnail_path), timestamp_seconds=5)

    # Step 6: Generate title and description
    print(f"\n[6/6] Generating YouTube title, description, and metadata...")
    title_meta = generate_title_description(
        category_english,
        CATEGORIES_HEBREW[category_english],
        phrases,
        total_duration / 60,
        str(video_dir)
    )

    # Save latest video info for upload script (BEFORE metadata overwrite)
    import json as _json
    from pathlib import Path as _Path
    meta_out = {
        "title": title_meta.get("selected_title", f"Learn Hebrew: {category_english}"),
        "description": title_meta.get("description", ""),
        "tags": ["Learn Hebrew", "Hebrew Phrases", "Hebrew", category_english, "VELOCITY HEBREW"],
        "category_english": category_english,
        "category_hebrew": CATEGORIES_HEBREW[category_english],
        "phrases_count": len(phrases),
        "duration_seconds": total_duration,
        "duration_minutes": total_duration / 60,
        "video_path": str(output_video),
        "thumbnail_path": str(thumbnail_path),
        "phrases": phrases,
        "generated_at": datetime.now().isoformat(),
    }
    _Path("output").mkdir(exist_ok=True)
    with open(_Path("output") / "latest_video.json", "w", encoding="utf-8") as f:
        _json.dump(meta_out, f, indent=2, ensure_ascii=False)
    with open(_Path("output") / "latest_upload_info.json", "w", encoding="utf-8") as f:
        _json.dump({"title": meta_out["title"], "description": meta_out["description"],
                     "category": category_english, "phrases_count": len(phrases)}, f, indent=2)

    print(f"\n{'='*80}")
    print(f"✅ LONG-FORM VIDEO COMPLETE!")
    print(f"  📁 {video_dir}")
    print(f"  🎬 {output_video.name}")
    print(f"  🖼️  thumbnail.jpg (generated)")
    print(f"  🖼️  {video_thumbnail_path.name} (from video)")
    print(f"  📄 youtube_upload_info.txt (title + description + tags)")
    print(f"  ⏱️  Duration: {total_duration/60:.2f} minutes")
    print(f"  📊 Phrases: {len(phrases)}")
    print(f"  🏷️  Branding: Velocity Hebrew")
    print(f"  📺 Format: 16:9 (1920x1080)")
    print(f"{'='*80}\n")

    return meta_out


def generate_multiple_longform(count: int = 1, target_phrases: int = None):
    """Generate multiple long-form videos"""
    print(f"\n🎬 Generating {count} long-form video(s)...")
    print("="*80)

    for i in range(count):
        print(f"\n{'='*80}")
        print(f"🎬 VIDEO {i+1}/{count}")
        print("="*80)
        generate_longform_video(target_phrases=target_phrases)

    print("\n" + "="*80)
    print(f"✅ ALL {count} LONG-FORM VIDEOS COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Velocity Hebrew YouTube Long-form Video Generator")
    parser.add_argument("--phrases", type=int, default=TARGET_PHRASES, help="Number of phrases to generate (120 phrases = ~20 min video with pedagogical pauses)")
    parser.add_argument("--category", type=str, default=None, help="Specific category to generate (e.g. 'Motivation', 'Friendship'). Random if not provided.")
    args = parser.parse_args()

    print("\n" + "="*80)
    print("🇮🇱 VELOCITY HEBREW - YOUTUBE LONG-FORM AUTOMATION 🇮🇱")
    print("="*80)
    print("\n✨ FEATURES:")
    print("  ✓ 16:9 format (1920x1080) for YouTube long-form")
    print(f"  ✓ Target {args.phrases} phrases (~{args.phrases * 5.5 / 60:.1f} minute video)")
    print("  ✓ Lingexa Light Theme (Cream background, dark/light purple + peach containers)")
    print("  ✓ Natural pauses with commas (non-robotic TTS)")
    print("  ✓ Perfect audio-video synchronization")
    print("  ✓ Smooth crossfade transitions")
    print("  ✓ NEVER repeats phrases (permanent history tracking)")
    print(f"\n📊 AVAILABLE CATEGORIES ({len(CATEGORIES_ENGLISH)} total):")
    for i, cat in enumerate(CATEGORIES_ENGLISH, 1):
        print(f"   {i:2d}. {cat} ({CATEGORIES_HEBREW[cat]})")
    print(f"\n📈 VIDEO SPECIFICATIONS:")
    print(f"  • Resolution: {VIDEO_WIDTH}x{VIDEO_HEIGHT} (16:9)")
    print(f"  • Frame Rate: {FPS} FPS")
    print(f"  • Target Phrases: {args.phrases}")
    print(f"  • Estimated Duration: ~{args.phrases * 10.0 / 60:.1f} minutes")
    print(f"  • Phrase History: PERMANENT (never deletes)")
    print("="*80)

    # Note: History tracking is built-in. Check output/history/all_generated_phrases.json
    generate_longform_video(category_english=args.category, target_phrases=args.phrases)