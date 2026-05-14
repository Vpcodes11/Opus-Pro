import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"

# Create dirs
for d in [UPLOAD_DIR, OUTPUT_DIR, TEMP_DIR]:
    d.mkdir(exist_ok=True)

# Video output presets
PRESETS = {
    "tiktok": {"width": 1080, "height": 1920, "label": "TikTok / Reels (9:16)"},
    "youtube_shorts": {"width": 1080, "height": 1920, "label": "YouTube Shorts (9:16)"},
    "square": {"width": 1080, "height": 1080, "label": "Square (1:1)"},
    "landscape": {"width": 1920, "height": 1080, "label": "Landscape (16:9)"},
}

DEFAULT_PRESET = "tiktok"
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920  # 9:16 vertical

# Clip settings
MIN_CLIP_DURATION = 15   # seconds
MAX_CLIP_DURATION = 90   # seconds
MAX_CLIPS = 8

# Whisper API file size limit (25MB)
WHISPER_MAX_FILE_SIZE = 24 * 1024 * 1024  # 24MB to be safe
AUDIO_CHUNK_DURATION = 600  # 10 minutes per chunk

# Caption styles
CAPTION_STYLES = {
    "tiktok": {
        "font": "Inter",
        "fontsize": 82,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000FFFF", # Yellow
        "outline_color": "&H00000000",
        "back_color": "&H80000000",
        "bold": True,
        "outline": 6,
        "alignment": 2,
        "margin_v": 200,
    },
    "minimal": {
        "font": "Inter",
        "fontsize": 72,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000FF00", # Green
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "bold": True,
        "outline": 4,
        "alignment": 2,
        "margin_v": 220,
    },
    "viral": {
        "font": "Outfit", # Modern rounded font
        "fontsize": 94,
        "primary_color": "&H00FFFFFF",
        "highlight_color": "&H0000D4FF", # Gold/Orange
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "bold": True,
        "outline": 8,
        "alignment": 2,
        "margin_v": 180,
    },
    "neon": {
        "font": "Inter",
        "fontsize": 80,
        "primary_color": "&H0000FF00",
        "highlight_color": "&H00FF00FF",
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "bold": True,
        "outline": 5,
        "alignment": 2,
        "margin_v": 190,
    },
}

DEFAULT_CAPTION_STYLE = "viral"

# API Keys (stored in .env file, never committed to git)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEFAULT_PROVIDER = "groq"
