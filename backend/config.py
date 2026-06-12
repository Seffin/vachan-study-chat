"""
Vachan Study Bible Chatbot — Central Configuration Module
All environment variables, constants, thresholds, and mappings live here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =====================================================================
# 📂 DIRECTORY PATHS
# =====================================================================

# This config file lives at backend/config.py
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.join(BACKEND_DIR, "api")
STATIC_DATA_DIR = os.path.join(BACKEND_DIR, "static_data")
DATA_DIR = os.path.join(BACKEND_DIR, "data")

# =====================================================================
# 🌐 SERVER CONFIGURATION
# =====================================================================

HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
RELOAD = os.environ.get("RELOAD", "True").lower() == "true"

# =====================================================================
# 🧠 LLM API KEYS & MODELS
# =====================================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_API_KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEYS", "").split(",") if k.strip()]

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
LLM_TEMPERATURE = float(os.environ.get("OPENAI_TEMPERATURE", "0.1"))

# =====================================================================
# 📖 BIBLE API CONFIGURATION
# =====================================================================

BIBLE_API_KEY = os.environ.get("BIBLE_API_KEY")
BIBLE_API_URL = os.environ.get("BIBLE_API_URL", "https://rest.api.bible").rstrip("/")
BIBLE_ID = os.environ.get("BIBLE_ID", "de4e12af7af57f50-02")

# =====================================================================
# 🗄️ MONGODB CONFIGURATION
# =====================================================================

MONGO_URI = os.environ.get("MONGO_URI")
DB_NAME = "vachan_study"

# =====================================================================
# 📊 CORS ORIGINS
# =====================================================================

ALLOWED_ORIGINS_DEFAULT = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.1.101:3000",
]
ALLOWED_ORIGINS_EXTRA = os.environ.get("ALLOWED_ORIGINS", "")

def get_allowed_origins() -> list:
    origins = ALLOWED_ORIGINS_DEFAULT.copy()
    if ALLOWED_ORIGINS_EXTRA:
        origins.extend([o.strip() for o in ALLOWED_ORIGINS_EXTRA.split(",") if o.strip()])
    return origins

# =====================================================================
# 🔢 RETRIEVAL THRESHOLDS
# =====================================================================

# Cross-encoder / re-ranker confidence thresholds
RERANK_HIGH_THRESHOLD = 0.85     # Direct dataset return (no LLM needed)
RERANK_MEDIUM_THRESHOLD = 0.50   # LLM verification zone
# Below MEDIUM = no match, fall through to translation/AI

# Legacy vector search thresholds (kept for backward compatibility)
VECTOR_SCORE_SEMANTIC_THRESHOLD = 6      # For SemanticRetriever (word overlap)
VECTOR_SCORE_COSINE_THRESHOLD = 0.35     # For cosine distance (lower = closer)

# =====================================================================
# 📊 RATE LIMITING (GEMINI FREE TIER)
# =====================================================================

RATE_LIMIT_RPM = 15         # Requests per minute
RATE_LIMIT_RPD = 1500       # Requests per day
TOKEN_BUDGET_DEFAULT = 1000000

# Token file location (Vercel uses /tmp)
if os.environ.get("VERCEL") == "1" or os.environ.get("VERCEL_ENV"):
    TOKENS_FILE = "/tmp/tokens.json"
elif os.path.exists(DATA_DIR) and not os.access(DATA_DIR, os.W_OK):
    TOKENS_FILE = "/tmp/tokens.json"
else:
    TOKENS_FILE = os.path.join(DATA_DIR, "tokens.json")

# =====================================================================
# 🌍 LANGUAGE MAP
# =====================================================================

LANGUAGE_MAP = {
    'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
    'zh-cn': 'Chinese (Simplified)', 'zh-tw': 'Chinese (Traditional)',
    'hi': 'Hindi', 'ar': 'Arabic', 'ru': 'Russian', 'pt': 'Portuguese',
    'ja': 'Japanese', 'ko': 'Korean', 'it': 'Italian', 'nl': 'Dutch',
    'tr': 'Turkish', 'pl': 'Polish', 'vi': 'Vietnamese',
    'ml': 'Malayalam', 'ta': 'Tamil', 'te': 'Telugu',
    'kn': 'Kannada', 'bn': 'Bengali', 'ur': 'Urdu',
    'gu': 'Gujarati', 'mr': 'Marathi'
}

# =====================================================================
# 📚 BIBLE BOOK CODE MAPPING
# =====================================================================

BOOK_CODE_MAP = {
    "GENESIS": "GEN", "EXODUS": "EXO", "LEVITICUS": "LEV", "NUMBERS": "NUM", "DEUTERONOMY": "DEU",
    "JOSHUA": "JOS", "JUDGES": "JDG", "RUTH": "RUT", "1SAMUEL": "1SA", "2SAMUEL": "2SA",
    "1KINGS": "1KI", "2KINGS": "2KI", "1CHRONICLES": "1CH", "2CHRONICLES": "2CH", "EZRA": "EZR",
    "NEHEMIAH": "NEH", "ESTHER": "EST", "JOB": "JOB", "PSALMS": "PSA", "PSALM": "PSA", "PROVERBS": "PRO",
    "ECCLESIASTES": "ECC", "SONGOFSOLOMON": "SNG", "SONGOFSONGS": "SNG", "CANTICLES": "SNG",
    "ISAIAH": "ISA", "JEREMIAH": "JER", "LAMENTATIONS": "LAM", "EZEKIEL": "EZK", "DANIEL": "DAN",
    "HOSEA": "HOS", "JOEL": "JOL", "AMOS": "AMO", "OBADIAH": "OBA", "JONAH": "JON",
    "MICAH": "MIC", "NAHUM": "NAM", "HABAKKUK": "HAB", "ZEPHANIAH": "ZEP", "HAGGAI": "HAG",
    "ZECHARIAH": "ZEC", "MALACHI": "MAL",
    "MATTHEW": "MAT", "MARK": "MRK", "LUKE": "LUK", "JOHN": "JHN", "ACTS": "ACT",
    "ROMANS": "ROM", "1CORINTHIANS": "1CO", "2CORINTHIANS": "2CO", "GALATIANS": "GAL",
    "EPHESIANS": "EPH", "PHILIPPIANS": "PHP", "COLOSSIANS": "COL", "1THESSALONIANS": "1TH",
    "2THESSALONIANS": "2TH", "1TIMOTHY": "1TI", "2TIMOTHY": "2TI", "TITUS": "TIT",
    "PHILEMON": "PHM", "HEBREWS": "HEB", "JAMES": "JAS", "1PETER": "1PE", "2PETER": "2PE",
    "1JOHN": "1JN", "2JOHN": "2JN", "3JOHN": "3JN", "JUDE": "JUD", "REVELATION": "REV", "APOCALYPSE": "REV"
}

def normalize_book_code(book: str) -> str:
    """Converts full book names to 3-letter codes."""
    book_clean = book.upper().replace(" ", "").replace("_", "").strip()
    return BOOK_CODE_MAP.get(book_clean, book_clean[:3])

# =====================================================================
# 📝 DISCLAIMERS
# =====================================================================

DISCLAIMER_UNFOLDING = "🤖 *This response based on the unfoldingWord dataset.*"
DISCLAIMER_AI = "🤖 *This is an AI-generated response based on the unfoldingWord dataset.*"
ALL_DISCLAIMERS = [
    DISCLAIMER_UNFOLDING,
    DISCLAIMER_AI,
    "⚠️ *This is an AI-generated response based on the unfoldingWord dataset.*",
    "🤖 *This response based on the unfoldingWord dataset.*"
]

# =====================================================================
# 📖 OFFLINE BOOK OVERVIEWS
# =====================================================================

OFFLINE_OVERVIEWS = {
    "MAT": "📖 **Overview of Matthew:** The Gospel of Matthew serves as a legal and theological bridge between the Old and New Testaments. It emphasizes Jesus as the promised Messiah, tracing His royal lineage back to Abraham and David, and highlights the Kingdom of Heaven through key teachings like the Sermon on the Mount.",
    "GEN": "📖 **Overview of Genesis:** Genesis is the book of beginnings. It documents the creation of the universe, the fall of humanity, and the covenant origin of God's chosen people through Abraham, Isaac, Jacob, and Joseph.",
    "LEV": "📖 **Overview of Leviticus:** Leviticus is a handbook for priests and worshipers, focusing on the holiness of God and the purification of His people. It details sacrificial offerings, priestly consecration, laws of clean and unclean, the Day of Atonement, and the holiness code."
}
