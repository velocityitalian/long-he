"""VELOCITY LONGFORM - 16:9 chapter lesson, brand and motion constants."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

OUTPUT_DIR = BASE_DIR / "output"
LESSONS_DIR = OUTPUT_DIR / "lessons"
HISTORY_DIR = OUTPUT_DIR / "history"
SCENE_DIR = BASE_DIR / "scene"

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
FPS = 30

TARGET_CHAPTERS = 8
PHRASES_PER_CHAPTER = 7
TARGET_PHRASES = TARGET_CHAPTERS * PHRASES_PER_CHAPTER

# ---------------------------------------------------------------- brand

BRAND = "VELOCITY HEBREW"
BRAND_LOCKUP_TOP = "VELOCITY"
BRAND_LOCKUP_BOTTOM = "HEBREW"
HANDLE = "@velocityhebrew"
MASCOT_NAME = "Velo"

# ==== LANGUAGE PACK START ====
LANGUAGE = {'code': 'he',
 'name': 'Hebrew',
 'native_name': 'עברית',
 'history_key': 'hebrew',
 'english_voice': 'en-US-AvaNeural',
 'english_fallback_voice': 'en-US-GuyNeural',
 'native_voice': 'he-IL-HilaNeural',
 'native_fallback_voice': 'he-IL-AvriNeural',
 'native_engine': 'edge',
 'native_lang_code': 'he',
 'english_rate': '-4%',
 'native_rate': '-10%',
 'english_pitch': '+0Hz',
 'native_pitch': '+0Hz',
 'native_label': 'עברית',
 'translit_label': 'SAY IT LIKE',
 'flag': 'il',
 'greeting': 'שלום!',
 'encouragement': 'מעולה!',
 'rtl': True,
 'char_tiles': False,
 'script_font': 'Script.ttf',
 'glyphs': 'אבגדהוזחטיכלמנסעפצקרשת'}
# ==== LANGUAGE PACK END ====

# ==== CATEGORIES START ====
CATEGORIES = {'Motivation': 'מוטיבציה',
 'Love': 'אהבה',
 'Success': 'הצלחה',
 'Wisdom': 'חוכמה',
 'Happiness': 'אושר',
 'Self Improvement': 'שיפור עצמי',
 'Gratitude': 'הכרת תודה',
 'Friendship': 'חברות',
 'Hope': 'תקווה',
 'Creativity': 'יצירתיות',
 'Inner Peace': 'שלווה פנימית',
 'Confidence': 'ביטחון',
 'Perseverance': 'התמדה',
 'Inspiration': 'השראה',
 'Positive Life': 'חיים חיוביים',
 'Courage': 'אומץ',
 'Kindness': 'טוב לב',
 'Patience': 'סבלנות',
 'Forgiveness': 'סליחה',
 'Strength': 'כוח',
 'Joy': 'שמחה',
 'Balance': 'איזון',
 'Growth': 'צמיחה',
 'Purpose': 'מטרה',
 'Mindfulness': 'מיינדפולנס',
 'Travel & Airport': 'טיולים ושדות תעופה',
 'Ordering Food & Dining': 'הזמנת אוכל ואכילה במסעדות',
 'Shopping & Prices': 'קניות ומחירים',
 'Asking for Directions': 'בקשת הוראות הגעה',
 'Hotel & Accommodation': 'מלונות ואירוח',
 'Daily Routine': 'שגרת יום',
 'Meeting People & Greetings': 'פגישה עם אנשים וברכות',
 'Emergency & Health': 'חירום ובריאות',
 'Public Transportation': 'תחבורה ציבורית',
 'Work & Office': 'עבודה ומשרד',
 'Weather & Small Talk': 'מזג אוויר ושיחת חולין',
 'Coffee Shop & Bakery': 'בית קפה ומאפייה',
 'Family & Home': 'משפחה ובית',
 'Hobbies & Free Time': 'תחביבים ופנאי',
 'Dating & Romance': 'דייטינג ורומנטיקה',
 'Phone Calls & Messages': 'שיחות טלפון והודעות',
 'Banking & Money': 'בנקאות וכסף',
 'Doctor & Pharmacy': 'רופא ובית מרקחת',
 'Sports & Fitness': 'ספורט וכושר',
 'Celebrations & Parties': 'חגיגות ומסיבות',
 'Feelings & Emotions': 'רגשות ותחושות',
 'Agreeing & Disagreeing': 'הסכמה ואי-הסכמה',
 'Making Plans': 'תכנון פגישות',
 'Common Native Slang': 'סלנג מקומי נפוץ',
 'Cultural Traditions': 'מסורות תרבותיות'}
# ==== CATEGORIES END ====

CATEGORY_NAMES = list(CATEGORIES.keys())

AI_MODEL = os.getenv("AI_MODEL", "openai/gpt-5.4-nano")
AI_FALLBACK_MODEL = os.getenv("AI_FALLBACK_MODEL", "gemini-fast")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "")

# ---------------------------------------------------------------- timing (seconds)

INTRO_DURATION = 7.2
CHAPTER_INTRO_DURATION = 4.4
OUTRO_DURATION = 13.0

EN_CARD_IN = 0.70
GAP_EN_NATIVE = 0.60
NATIVE_CARD_LEAD = 0.40
GAP_BEFORE_REPEAT = 1.00
TAIL_HOLD = 1.30

# ---------------------------------------------------------------- palette

INK = "#30303A"
MUTED = "#8A8A8A"
CREAM = "#FFF8E7"
GREEN = "#58CC02"
GREEN_DARK = "#46A302"
GREEN_DEEP = "#3D8F00"
BLUE = "#1CB0F6"
PURPLE = "#7C5CFF"
ORANGE = "#FF7A00"
RED = "#FF4B4B"
YELLOW = "#F5A700"
TEAL = "#00A889"
PINK = "#E056A0"

# ==== HASHTAGS START ====
HASHTAGS = ['#learnhebrew',
 '#hebrewlessons',
 '#hebrewforbeginners',
 '#languagelearning',
 '#hebrewvocabulary',
 '#velocityhebrew',
 '#dailyhebrew',
 '#hebrew',
 '#learnlanguages',
 '#speakhebrew']
# ==== HASHTAGS END ====
