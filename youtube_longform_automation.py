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
TARGET_DURATION_MINUTES = 15  # Target ~15-minute videos (~170 phrases)
TARGET_PHRASES = 170  # Number of phrases to generate

# English category names (for American/European learners)
CATEGORIES_ENGLISH = [
    "Motivation", "Love", "Success", "Wisdom", "Happiness",
    "Self Improvement", "Gratitude", "Friendship", "Hope", "Creativity",
    "Inner Peace", "Confidence", "Perseverance", "Inspiration", "Positive Life",
    "Courage", "Kindness", "Patience", "Forgiveness", "Strength",
    "Joy", "Balance", "Growth", "Purpose", "Mindfulness",
]

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
}

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
AI_MODEL = os.getenv("AI_MODEL")

if not AI_MODEL:
    raise ValueError(
        "AI_MODEL not set! Please add 'AI_MODEL=gemini-fast' to your .env file."
    )


# ============== PHRASE HISTORY MANAGEMENT ==============

def load_phrase_history():
    """Load all previously generated phrases"""
    if PHRASE_HISTORY_FILE.exists():
        with open(PHRASE_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"phrases": [], "last_updated": None}


def save_phrase_history(data):
    """Save phrase history"""
    data["last_updated"] = datetime.now().isoformat()
    with open(PHRASE_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_phrase_used(english_phrase):
    """Check if phrase was already generated (exact match)"""
    history = load_phrase_history()
    english_lower = english_phrase.lower().strip()
    for p in history.get("phrases", []):
        if p.get("english", "").lower().strip() == english_lower:
            return True
    return False


def is_phrase_similar(new_phrase, used_phrases, similarity_threshold=0.6):
    """Check if a phrase is too similar to previously used phrases"""
    new_words = set(new_phrase.lower().split())

    if len(new_words) < 3:
        for used in used_phrases:
            if new_phrase.lower() in used.lower() or used.lower() in new_phrase.lower():
                return True
        return False

    for used in used_phrases:
        used_words = set(used.lower().split())

        if len(new_words) == 0 or len(used_words) == 0:
            continue

        intersection = len(new_words.intersection(used_words))
        union = len(new_words.union(used_words))
        similarity = intersection / union if union > 0 else 0

        if similarity >= similarity_threshold:
            return True

    return False


def filter_similar_phrases(phrases, history, similarity_threshold=0.6):
    """Filter out phrases that are too similar to previously used ones"""
    used_phrases = [p.get("english", "") for p in history.get("phrases", [])]
    unique_phrases = []

    for phrase in phrases:
        english_text = phrase.get("english", "")

        if not is_phrase_similar(english_text, used_phrases, similarity_threshold):
            unique_phrases.append(phrase)
        else:
            print(f"[filter] ⚠️ Skipping similar: {english_text[:50]}...")

    return unique_phrases


def add_phrases_to_history(phrases, category):
    """Add new phrases to history"""
    history = load_phrase_history()
    for phrase in phrases:
        history["phrases"].append({
            "english": phrase["english"],
            "spanish": phrase["hebrew"],
            "category": category,
            "generated_at": datetime.now().isoformat()
        })
    save_phrase_history(history)
    print(f"[history] Added {len(phrases)} phrases to history (total: {len(history['phrases'])})")


# ============== CONTENT GENERATION ==============

def calculate_phrases_needed(target_minutes: int) -> int:
    """
    Calculate how many phrases needed for target video duration.
    Average phrase takes ~5 seconds (English ~2s + pause 0.5s + Hebrew ~2.5s)
    For 10 minutes (600 seconds): 600 / 5 = ~120 phrases
    """
    avg_phrase_duration = 5.0  # seconds
    total_seconds = target_minutes * 60
    return int(total_seconds / avg_phrase_duration)


def generate_phrases_for_longform(category_english: str, num_phrases: int) -> list:
    """Generate unique bilingual phrases for long-form video"""

    category_hebrew = CATEGORIES_HEBREW[category_english]

    history = load_phrase_history()
    used_phrases = [p.get("english", "") for p in history.get("phrases", [])]

    viral_style = random.choice(VIRAL_STYLES)

    # Generate in batches to avoid API limits and ensure quality
    all_phrases = []
    batch_size = 20
    max_attempts = 5

    for batch_num in range((num_phrases + batch_size - 1) // batch_size):
        remaining = num_phrases - len(all_phrases)
        current_batch_size = min(batch_size, remaining)

        if current_batch_size <= 0:
            break

        for attempt in range(max_attempts):
            try:
                import requests
                url = "https://gen.pollinations.ai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
                    "Content-Type": "application/json"
                }

                exclusion_note = ""
                if used_phrases:
                    recent = used_phrases[-30:] if len(used_phrases) > 30 else used_phrases
                    exclusion_note = f"\n\nAVOID these phrases (already used): {recent}"

                prompt = f"""Create {current_batch_size * 2} unique {category_english} phrases for English speakers learning Hebrew.

Style: Make each phrase feel like a {viral_style} - something people would want to share!

IMPORTANT RULES FOR NATURAL SPEECH:
1. Keep phrases SHORT (5-12 words max per language)
2. Add NATURAL PAUSES using commas (e.g., "Dream big, start small")
3. Use punctuation for breathing room in TTS
4. Avoid long run-on sentences
5. Each phrase should be speakable in 3-5 seconds
6. Use everyday vocabulary - avoid exotic or rare words
7. Avoid complex grammar - keep it simple and practical
8. Vary sentence structure for natural flow

For each phrase:
1. English phrase (with commas for natural pauses)
2. Hebrew translation
3. Pronunciation guide (phonetic spelling for English speakers)
CRITICAL: Every translation MUST be in Hebrew. NEVER use German, Spanish, or any other language. Only Hebrew.

Return as JSON array:
[{{"english": "...", "hebrew": "...", "pronunciation": "..."}}]

IMPORTANT: Create FRESH, UNIQUE phrases that haven't been used before.{exclusion_note}"""

                payload = {
                    "model": AI_MODEL,
                    "messages": [
                        {"role": "system", "content": "You are a viral Hebrew teacher creating engaging educational content for YouTube. Create short, natural phrases with pauses."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 1.0
                }

                response = requests.post(url, headers=headers, json=payload, timeout=90)
                response.raise_for_status()

                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()

                # Extract JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                phrases = json.loads(content)

                # Filter by similarity
                filtered_phrases = filter_similar_phrases(phrases, history)

                # Filter by length and exact duplicates
                unique_phrases = []
                for phrase in filtered_phrases:
                    if len(phrase["english"].split()) > 15:
                        continue
                    if not is_phrase_used(phrase["english"]):
                        unique_phrases.append(phrase)

                # Add valid phrases
                for phrase in unique_phrases:
                    if len(all_phrases) < num_phrases:
                        all_phrases.append(phrase)

                if len(all_phrases) >= num_phrases:
                    break

            except Exception as e:
                print(f"[content] Batch {batch_num + 1}, Attempt {attempt + 1} failed: {e}")

        # Small delay between batches
        if len(all_phrases) < num_phrases:
            import time
            time.sleep(1)

    # Trim to exact count and save to history
    final_phrases = all_phrases[:num_phrases]
    if final_phrases:
        add_phrases_to_history(final_phrases, category_english)

    print(f"[content] Generated {len(final_phrases)} phrases for long-form video")
    return final_phrases


def get_fresh_fallback_phrases(category: str, num_phrases: int) -> list:
    """Get fallback phrases, filtering out used ones with similarity check"""

    all_fallbacks = {
        "Motivation": [
            {"english": "Believe in yourself.", "hebrew": "תאמין בעצמך.", "pronunciation": "ta-ah-MEEN be-atz-ME-cha"},
            {"english": "You are capable of amazing things.", "hebrew": "אתה מסוגל לדברים מדהימים.", "pronunciation": "a-TA me-SU-gol le-dva-RIM me-da-HEE-mim"},
            {"english": "Dream big, start small.", "hebrew": "חלום בגדול, התחל בקטן.", "pronunciation": "cha-LOM be-ga-DOL, hit-CHAL be-ka-TAN"},
            {"english": "Your future is created by your actions.", "hebrew": "העתיד שלך נוצר מהמעשים שלך.", "pronunciation": "ha-a-TEED shel-CHA no-TZAR me-ha-ma-a-SEEM shel-CHA"},
            {"english": "Never give up on your dreams.", "hebrew": "לעולם אל תוותר על החלומות שלך.", "pronunciation": "le-O-LAM al te-va-TER al ha-cha-lo-MOT shel-CHA"},
            {"english": "Small steps lead to big changes.", "hebrew": "צעדים קטנים מובילים לשינויים גדולים.", "pronunciation": "tsa-A-DIM kta-NIM mo-vi-LIM le-shi-nu-YIM gdo-LIM"},
            {"english": "You are stronger than you think.", "hebrew": "אתה חזק יותר ממה שאתה חושב.", "pronunciation": "a-TA cha-ZAK yo-TER mi-ma she-a-TA cho-shev"},
        ],
        "Love": [
            {"english": "Love yourself first.", "hebrew": "תאהב את עצמך קודם.", "pronunciation": "te-a-HAV et atz-me-CHA ko-DEM"},
            {"english": "Love makes everything possible.", "hebrew": "אהבה עושה הכל אפשרי.", "pronunciation": "a-ha-VA o-SET ha-KOL ef-sha-RI"},
            {"english": "My heart beats for you.", "hebrew": "הלב שלי פועם בשבילך.", "pronunciation": "ha-LEV she-LI po-EM bish-vi-LECHA"},
            {"english": "You are my everything.", "hebrew": "אתה הכל בשבילי.", "pronunciation": "a-TA ha-KOL bish-vi-LI"},
            {"english": "Together forever, hand in hand.", "hebrew": "ביחד לנצח, יד ביד.", "pronunciation": "ya-CHAD le-ne-TZACH, yad be-yad"},
        ],
        "Success": [
            {"english": "Success comes from hard work.", "hebrew": "הצלחה באה מעבודה קשה.", "pronunciation": "hatz-la-CHA ba-A me-a-vo-DA ka-SHA"},
            {"english": "Keep going, you're getting there.", "hebrew": "תמשיך, אתה כמעט שם.", "pronunciation": "tam-SHICH, a-TA kim-AT sham"},
            {"english": "Winners never quit.", "hebrew": "מנצחים אף פעם לא מוותרים.", "pronunciation": "me-na-tz-CHIM af pa-AM lo me-va-t-RIM"},
            {"english": "Your effort will pay off.", "hebrew": "המאמץ שלך ישתלם.", "pronunciation": "ha-ma-AM-TZ shel-CHA yish-ta-LEM"},
        ],
        "Wisdom": [
            {"english": "Knowledge is power.", "hebrew": "ידע הוא כוח.", "pronunciation": "de-AT hu ko-ACH"},
            {"english": "Learn from yesterday, live for today.", "hebrew": "למד מאתמול, חי להיום.", "pronunciation": "le-MAD me-et-MOL, che-YE le-ha-YOM"},
            {"english": "Think before you act.", "hebrew": "חשוב לפני שאתה פועל.", "pronunciation": "cha-SHOV lif-NE she-a-TA po-EL"},
            {"english": "Experience is the best teacher.", "hebrew": "הניסיון הוא המורה הטוב ביותר.", "pronunciation": "ha-ni-sa-YON hu ha-mo-RE ha-TOV be-YO-TER"},
        ],
        "Happiness": [
            {"english": "Happiness is a choice.", "hebrew": "האושר הוא בחירה.", "pronunciation": "ha-O-SHER hu bchi-RA"},
            {"english": "Find joy in the little things.", "hebrew": "מצא שמחה בדברים הקטנים.", "pronunciation": "m-TZA sim-CHA ba-dva-RIM ha-kta-NIM"},
            {"english": "Smile, it makes others happy.", "hebrew": "חייך, זה משמח אחרים.", "pronunciation": "cha-YECH, ze me-sa-ME-ACH a-che-RIM"},
            {"english": "Today is a gift.", "hebrew": "היום הוא מתנה.", "pronunciation": "ha-YOM hu ma-ta-NA"},
            {"english": "Be better than yesterday.", "hebrew": "היה טוב יותר מאתמול.", "pronunciation": "he-YE tov yo-TER me-et-MOL"},
            {"english": "Grow through what you go through.", "hebrew": "גדל דרך מה שאתה עובר.", "pronunciation": "g-DAL de-REch ma she-a-TA o-VER"},
            {"english": "Invest in yourself daily.", "hebrew": "השקע בעצמך כל יום.", "pronunciation": "hash-KA be-atz-mE-CHA kol yom"},
        ],
        "Gratitude": [
            {"english": "Thank you for everything.", "hebrew": "תודה על הכל.", "pronunciation": "to-DA al ha-KOL"},
            {"english": "I appreciate your help.", "hebrew": "אני מעריך את העזרה שלך.", "pronunciation": "a-NI ma-a-RICH et ha-ez-RA shel-CHA"},
            {"english": "Grateful for this moment.", "hebrew": "מודה על הרגע הזה.", "pronunciation": "mo-DE al ha-RE-ga ha-ZE"},
        ],
        "Friendship": [
            {"english": "Friends forever, no matter what.", "hebrew": "חברים לנצח, מה שלא יהיה.", "pronunciation": "cha-ve-RIM le-ne-TZACH, ma she-lo yih-YE"},
            {"english": "You are my best friend.", "hebrew": "אתה החבר הכי טוב שלי.", "pronunciation": "a-TA ha-cha-VER ha-chi tov she-LI"},
            {"english": "True friends stick together.", "hebrew": "חברים אמיתיים נשארים יחד.", "pronunciation": "cha-ve-RIM a-mi-ti-IM nish-a-RIM ya-CHAD"},
        ],
        "Hope": [
            {"english": "There is always hope.", "hebrew": "תמיד יש תקווה.", "pronunciation": "ta-MID yesh tik-VA"},
            {"english": "Better days are coming.", "hebrew": "ימים טובים יותר מגיעים.", "pronunciation": "ya-MIM to-VIM yo-TER me-gi-IM"},
            {"english": "Keep faith, keep going.", "hebrew": "שמור על אמונה, תמשיך.", "pronunciation": "sh-MOR al e-mu-NA, tam-SHICH"},
        ],
        "Creativity": [
            {"english": "Create something beautiful today.", "hebrew": "צור משהו יפה היום.", "pronunciation": "tZOR ma-she-HU ya-FE ha-YOM"},
            {"english": "Your imagination is unlimited.", "hebrew": "הדמיון שלך בלתי מוגבל.", "pronunciation": "ha-di-mya-ON shel-CHA bil-tI mu-g-BAL"},
            {"english": "Art comes from the heart.", "hebrew": "אמנות באה מהלב.", "pronunciation": "o-ma-NUT ba-A me-ha-LEV"},
            {"english": "Express yourself freely.", "hebrew": "בטא את עצמך בחופשיות.", "pronunciation": "ba-TA et atz-me-CHA be-chof-shi-YUT"},
            {"english": "Innovation starts with curiosity.", "hebrew": "חדשנות מתחילה בסקרנות.", "pronunciation": "chi-da-sho-NUT match-i-IL be-sak-ra-NUT"},
            {"english": "Find peace within yourself.", "hebrew": "מצא שלווה בתוך עצמך.", "pronunciation": "m-TZA shal-VA be-toch atz-me-CHA"},
            {"english": "Breathe, relax, let go.", "hebrew": "נשום, תירגע, תשחרר.", "pronunciation": "n-SHOM, tir-GA, tish-RER"},
            {"english": "Calm mind, happy heart.", "hebrew": "מוח רגוע, לב שמח.", "pronunciation": "mo-ACH ra-GU-A, lev sa-ME-ACH"},
        ],
        "Confidence": [
            {"english": "You are enough, just as you are.", "hebrew": "אתה מספיק, בדיוק כמו שאתה.", "pronunciation": "a-TA mas-PIK, bid-YUK k-mO she-a-TA"},
            {"english": "Stand tall, speak up.", "hebrew": "עמוד זקוף, דבר בקול.", "pronunciation": "a-MOD za-KUF, da-BER be-KOL"},
            {"english": "Believe in your abilities.", "hebrew": "תאמין ביכולות שלך.", "pronunciation": "ta-a-MIN be-yecho-LOT shel-CHA"},
        ],
        "Perseverance": [
            {"english": "Never give up, keep pushing.", "hebrew": "לעולם אל תוותר, תמשיך לדחוף.", "pronunciation": "le-O-LAM al te-va-TER, tam-SHICH lid-CHOF"},
            {"english": "Storms make trees take deeper roots.", "hebrew": "סערות גורמות לעצים להשריש עמוק יותר.", "pronunciation": "se-a-ROT gor-MOT la-etz-IM le-hash-RISH a-MOK yo-TER"},
            {"english": "Patience and persistence win.", "hebrew": "סבלנות והתמדה מנצחות.", "pronunciation": "sav-la-NUT ve-hat-m-da me-na-tz-CHOT"},
        ],
        "Inspiration": [
            {"english": "Let your light shine bright.", "hebrew": "תן לאור שלך לזרוח בבהירות.", "pronunciation": "ten la-OR shel-CHA liz-RACH be-bi-ru-T"},
            {"english": "Inspire others by your actions.", "hebrew": "השראה לאחרים במעשיך.", "pronunciation": "hash-RA le-a-che-RIM be-ma-a-se-CHA"},
            {"english": "Be the change you want to see.", "hebrew": "היה השינוי שאתה רוצה לראות.", "pronunciation": "he-YE ha-shi-NU-I she-a-TA ro-TZE lir-OT"},
            {"english": "Choose positivity every day.", "hebrew": "בחר חיוביות כל יום.", "pronunciation": "b-CHAR chiyu-VI-yut kol yom"},
            {"english": "Good vibes only.", "hebrew": "רק וייבים טובים.", "pronunciation": "rak VAIV-im to-VIM"},
            {"english": "Life is what you make it.", "hebrew": "החיים הם מה שאתה עושה מהם.", "pronunciation": "ha-cha-YIM hem ma she-a-TA o-SE me-hem"},
        ],
        "Courage": [
            {"english": "Be brave, take the first step.", "hebrew": "היה אמיץ, קח את הצעד הראשון.", "pronunciation": "he-YE a-MITZ, kach et ha-tsa-AD ha-ri-SHON"},
            {"english": "Courage is not the absence of fear.", "hebrew": "אומץ הוא לא היעדר פחד.", "pronunciation": "o-METZ hu lo he-e-DAR pa-CHAD"},
            {"english": "Face your fears head on.", "hebrew": "התמודד עם הפחדים שלך פנים אל פנים.", "pronunciation": "hit-mo-DED im ha-pa-cha-DIM shel-CHA pa-NIM el pa-NIM"},
        ],
        "Kindness": [
            {"english": "Be kind to everyone you meet.", "hebrew": "היה טוב לכל מי שאתה פוגש.", "pronunciation": "he-YE tov le-chol mi she-a-TA po-GESH"},
            {"english": "Kindness costs nothing, means everything.", "hebrew": "טוב לב לא עולה כלום, שווה הכל.", "pronunciation": "toV lev lo o-LE k-lUM, sha-VE ha-KOL"},
            {"english": "Spread kindness wherever you go.", "hebrew": "הפץ טוב לב לכל מקום.", "pronunciation": "ha-FETZ toV lev le-chol ma-KOM"},
        ],
        "Patience": [
            {"english": "Good things take time.", "hebrew": "דברים טובים דורשים זמן.", "pronunciation": "dva-RIM to-VIM dor-SHIM z-MAN"},
            {"english": "Wait patiently, trust the process.", "hebrew": "חכה בסבלנות, סמוך על התהליך.", "pronunciation": "cha-KE be-sav-la-NUT, s-MOCH al ha-ta-ha-LICH"},
            {"english": "Rome wasn't built in a day.", "hebrew": "רומא לא נבנתה ביום אחד.", "pronunciation": "RO-ma lo niv-ne-TA be-yom e-CHAD"},
        ],
        "Forgiveness": [
            {"english": "Forgive and set yourself free.", "hebrew": "סלח ושחרר את עצמך.", "pronunciation": "s-LACH ve-sha-RER et atz-me-CHA"},
            {"english": "Let go of grudges, find peace.", "hebrew": "עזוב את הטינה, מצא שלום.", "pronunciation": "a-ZOV et ha-ti-NA, m-TZA shaLOM"},
            {"english": "Forgiveness is a gift to yourself.", "hebrew": "סליחה היא מתנה לעצמך.", "pronunciation": "sli-CH-A hi ma-ta-NA le-atz-me-CHA"},
        ],
        "Strength": [
            {"english": "You are stronger than you know.", "hebrew": "אתה חזק יותר ממה שאתה יודע.", "pronunciation": "a-TA cha-ZAK yo-TER mi-ma she-a-TA yo-DE-A"},
            {"english": "Inner strength comes from within.", "hebrew": "כוח פנימי בא מבפנים.", "pronunciation": "kO-ACH pni-MI ba me-bi-FNIM"},
            {"english": "Challenges make you stronger.", "hebrew": "אתגרים הופכים אותך לחזק יותר.", "pronunciation": "et-gar-IM hof-CHIM ot-CHA le-cha-ZAK yo-TER"},
        ],
        "Joy": [
            {"english": "Find joy in every moment.", "hebrew": "מצא שמחה בכל רגע.", "pronunciation": "m-TZA sim-CHA be-chol RE-ga"},
            {"english": "Joy is contagious, spread it.", "hebrew": "שמחה מדבקת, הפץ אותה.", "pronunciation": "sim-CHA ma-da-VE-KET, ha-FETZ o-TA"},
            {"english": "Dance like nobody's watching.", "hebrew": "רקוד כאילו אף אחד לא צופה.", "pronunciation": "r-KOD ke-i-LU af e-CHAD lo tzo-FE"},
        ],
        "Balance": [
            {"english": "Find balance in your life.", "hebrew": "מצא איזון בחיים שלך.", "pronunciation": "m-TZA i-ZUN ba-cha-YIM shel-CHA"},
            {"english": "Work hard, rest well.", "hebrew": "עבוד קשה, נוח היטב.", "pronunciation": "a-VOD ka-SHA, nu-ACH he-TEV"},
            {"english": "Too much of anything is not good.", "hebrew": "יותר מדי מכל דבר זה לא טוב.", "pronunciation": "yo-TER mi-DA mi-kol da-VAR ze lo tov"},
        ],
        "Growth": [
            {"english": "Growth happens outside your comfort zone.", "hebrew": "צמיחה מתרחשת מחוץ לאזור הנוחות.", "pronunciation": "tchi-MA mit-ra-CHESH me-chuTZ le-e-ZOR ha-no-CHUT"},
            {"english": "Embrace change, grow stronger.", "hebrew": "חבק שינוי, גדל חזק יותר.", "pronunciation": "cha-BEK shi-NU-I, g-DAL cha-ZAK yo-TER"},
            {"english": "Every challenge is a chance to grow.", "hebrew": "כל אתגר הוא הזדמנות לגדול.", "pronunciation": "kol et-GAR hu hiz-da-m-NUT li-g-DOL"},
        ],
        "Purpose": [
            {"english": "Find your purpose, follow it.", "hebrew": "מצא את המטרה שלך, עקוב אחריה.", "pronunciation": "m-TZA et ha-mat-a-RA shel-CHA, a-KOV a-cha-REHA"},
            {"english": "Your life has meaning.", "hebrew": "לחיים שלך יש משמעות.", "pronunciation": "le-cha-YIM shel-CHA yesh mash-ma-UT"},
            {"english": "Live with intention, not accident.", "hebrew": "חיה בכוונה, לא במקרה.", "pronunciation": "che-YE be-ka-va-NA, lo be-mik-RE"},
        ],
        "Mindfulness": [
            {"english": "Be present in this moment.", "hebrew": "היה נוכח ברגע הזה.", "pronunciation": "he-YE no-ched ba-RE-ga ha-ZE"},
            {"english": "Breathe deeply, stay grounded.", "hebrew": "נשום עמוק, הישאר מקורקע.", "pronunciation": "n-SHOM a-MOK, hish-a-RER me-ku-RA"},
            {"english": "Notice the little things around you.", "hebrew": "שימו לב לדברים הקטנים סביבך.", "pronunciation": "si-MU lev la-dva-RIM ha-kta-NIM se-vi-VECHA"},
        ],
    }
    fallbacks = all_fallbacks.get(category, all_fallbacks["Motivation"])

    history = load_phrase_history()
    fresh_phrases = []
    for p in fallbacks:
        if not is_phrase_used(p["english"]) and not is_phrase_similar(p["english"], [h.get("english", "") for h in history.get("phrases", [])]):
            fresh_phrases.append(p)

    if len(fresh_phrases) < num_phrases:
        for cat, cat_fallbacks in all_fallbacks.items():
            if cat != category:
                for p in cat_fallbacks:
                    if not is_phrase_used(p["english"]) and not is_phrase_similar(p["english"], [h.get("english", "") for h in history.get("phrases", [])]):
                        fresh_phrases.append(p)
                    if len(fresh_phrases) >= num_phrases:
                        break
            if len(fresh_phrases) >= num_phrases:
                break

    return fresh_phrases[:num_phrases]


# ============== AUDIO GENERATION ==============

async def generate_single_audio(text: str, voice: str, output_path: str):
    """Generate audio using Edge TTS"""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"  TTS error: {e}")
        return False


def generate_all_audio(phrases: list, output_dir: str):
    """Generate audio for all phrases with proper timing"""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_files = []

    for i, phrase in enumerate(phrases):
        english_file = output_dir / f"english_{i}.mp3"
        hebrew_file = output_dir / f"hebrew_{i}.mp3"
        combined_file = output_dir / f"combined_{i}.mp3"

        if (i + 1) % 20 == 0:
            print(f"  Generating audio {i+1}/{len(phrases)}...")

        # Generate English audio
        en_success = asyncio.run(generate_single_audio(phrase["english"], ENGLISH_VOICE, str(english_file)))
        if not en_success:
            cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2", str(english_file)]
            subprocess.run(cmd, capture_output=True)

        # Generate Hebrew audio
        he_success = asyncio.run(generate_single_audio(phrase["hebrew"], HEBREW_VOICE, str(hebrew_file)))
        if not he_success:
            cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2", str(hebrew_file)]
            subprocess.run(cmd, capture_output=True)

        # Get ACTUAL durations
        en_duration = get_audio_duration(str(english_file))
        he_duration = get_audio_duration(str(hebrew_file))

        # Add pause between English and Hebrew
        pause_between = 0.5
        total_duration = en_duration + pause_between + he_duration

        # Combine audio files
        cmd = [
            "ffmpeg", "-y",
            "-i", str(english_file),
            "-i", str(hebrew_file),
            "-filter_complex", f"[0:a][1:a]concat=n=2:v=0:a=1[out]",
            "-map", "[out]",
            str(combined_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            concat_file = output_dir / f"concat_{i}.txt"
            with open(concat_file, "w", encoding="utf-8") as f:
                f.write(f"file '{english_file.as_posix()}'\n")
                f.write(f"file '{hebrew_file.as_posix()}'\n")

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
            "hebrew": str(hebrew_file),
            "combined": str(combined_file),
            "duration": actual_duration,
            "en_duration": en_duration,
            "he_duration": he_duration
        })

    print(f"\n[audio] ✓ Generated {len(audio_files)} phrase audios")
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
    pronunciation = phrase_data.get("pronunciation", "")

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
    cta_text = "60 ESSENTIAL PHRASES"
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

def generate_title_description(category_english: str, category_hebrew: str, phrases: list, duration_minutes: float, output_dir: str):
    """Generate viral YouTube title and description with all phrases - COMBINED in one file"""
    
    # Generate viral title variations
    duration_label = f"{int(round(duration_minutes))}" if duration_minutes >= 10 else f"{duration_minutes:.0f}"
    titles = [
        f"Learn Hebrew in {duration_label} Minutes | {category_english} Phrases Every Beginner NEEDS to Know! ({category_hebrew})",
        f"60 Hebrew Phrases for {category_english} | Speak Hebrew Like a Native! ({category_hebrew})",
        f"Master Hebrew {category_english} | 60 Essential Hebrew Phrases with Pronunciation | Velocity Hebrew",
        f"Hebrew Learning Made Easy | {category_english} Vocabulary | {duration_label} Minute Lesson",
        f"Speak Hebrew Fluently | {category_english} Phrases | English + Hebrew + Pronunciation",
    ]

    # Generate comprehensive description
    description = f"""🇮🇱 Learn Hebrew with VELOCITY HEBREW! 🇮🇱

In this video, you'll learn 60 essential Hebrew phrases about {category_english} ({category_hebrew}).
Perfect for beginners and intermediate learners!

📚 WHAT YOU'LL LEARN:
• 60 practical {category_english} phrases in Hebrew
• Correct pronunciation guide
• Natural pauses for speaking practice
• Common expressions used by native speakers

⏱️ VIDEO TIMESTAMPS:
"""

    # Add timestamps for each phrase (every 10 phrases grouped)
    avg_phrase_duration = duration_minutes * 60 / len(phrases)
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
        description += f"""
{i}. {phrase['english']}
   Hebrew: {phrase['hebrew']}
   Pronunciation: {phrase['pronunciation']}
"""

    description += f"""
🎯 PERFECT FOR:
• Hebrew beginners wanting to expand vocabulary
• Intermediate learners practicing pronunciation
• Anyone interested in Hebrew
• Language enthusiasts and polyglots
• Students preparing for exams

💡 TIPS FOR LEARNING:
1. Repeat each phrase out loud
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
• Basic Hebrew Greetings

#LearnHebrew #HebrewPhrases #HebrewLanguage #{category_english.replace(' ', '')} #Hebrew #HebrewForBeginners #SpeakHebrew #HebrewVocabulary #Pronunciation #LanguageLearning #Hebrew101 #HebrewLesson

---
© VELOCITY HEBREW - Making Hebrew learning accessible to everyone!
"""

    # Write to COMBINED file (title + description in one)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Combined YouTube upload file (title + description)
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
            "Learn Hebrew",
            "Hebrew Phrases",
            "Hebrew Language",
            category_english,
            "VELOCITY HEBREW",
            "Hebrew for Beginners",
            "Speak Hebrew",
            "Hebrew Vocabulary",
            "Pronunciation",
            "Language Learning",
            "Hebrew 101",
            "Hebrew Lesson"
        ]
        f.write(", ".join(tags) + "\n")

    # Metadata JSON (for easy parsing)
    metadata = {
        "recommended_titles": titles,
        "selected_title": titles[0],
        "description": description,
        "category_english": category_english,
        "category_hebrew": category_hebrew,
        "phrases_count": len(phrases),
        "duration_minutes": round(duration_minutes, 2),
        "tags": tags
    }

    with open(output_dir / "video_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n[metadata] ✓ Generated YouTube upload files")
    print(f"  📄 youtube_upload_info.txt (title + description + tags)")
    print(f"  📄 video_metadata.json")

    return metadata


# ============== VIDEO CREATION WITH TRANSITIONS ==============

def create_video_from_images_audio(image_files: list, audio_files: list, combined_audio: str, output_file: str):
    """Create video from images and audio with PERFECT synchronization"""

    print(f"\n[video] Creating long-form video from {len(image_files)} images...")
    print(f"[video] Embedding audio in each clip for frame-perfect sync...")

    temp_clips = []

    for i, (img_path, audio_info) in enumerate(zip(image_files, audio_files)):
        duration = audio_info['duration']
        print(f"  Image {i+1}/{len(image_files)}: {duration:.2f}s (EN: {audio_info.get('en_duration', 0):.1f}s + ES: {audio_info.get('he_duration', 0):.1f}s)")

        temp_clip = Path(output_file).parent / f"temp_clip_{i:02d}.mp4"
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
            "-preset", "medium",
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
        category_english = random.choice(CATEGORIES_ENGLISH)

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
    parser.add_argument("--phrases", type=int, default=TARGET_PHRASES, help="Number of phrases to generate (determines video length, ~5.5s per phrase. 60 phrases = ~5.5 mins)")
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
    print(f"  • Estimated Duration: ~{args.phrases * 5.5 / 60:.1f} minutes")
    print(f"  • Phrase History: PERMANENT (never deletes)")
    print("="*80)

    # Note: History tracking is built-in. Check output/history/all_generated_phrases.json
    generate_longform_video(category_english=args.category, target_phrases=args.phrases)