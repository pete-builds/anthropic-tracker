"""Configuration constants and paths."""

from pathlib import Path

# Greenhouse public API (no auth required)
GREENHOUSE_API_URL = "https://boards-api.greenhouse.io/v1/boards/anthropic/jobs"
GREENHOUSE_CONTENT_URL = GREENHOUSE_API_URL + "?content=true"
GREENHOUSE_DEPARTMENTS_URL = "https://boards-api.greenhouse.io/v1/boards/anthropic/departments"
GREENHOUSE_OFFICES_URL = "https://boards-api.greenhouse.io/v1/boards/anthropic/offices"

# HTTP settings
USER_AGENT = "anthropic-tracker/0.1.0 (hiring metrics tracker)"
REQUEST_TIMEOUT = 30
MAX_RETRIES = 2
RETRY_BACKOFF = 1.0  # seconds, doubled each retry
SALARY_FETCH_DELAY = 0.5  # seconds between individual job fetches

# Data storage
DEFAULT_DATA_DIR = Path.home() / ".anthropic-tracker"
DB_FILENAME = "tracker.db"

# Alert thresholds
FREEZE_THRESHOLD_PCT = 20  # total roles drop >20% = possible hiring freeze
SURGE_THRESHOLD_PCT = 50  # department grows >50% in a week
MASS_REMOVAL_THRESHOLD = 30  # >30 roles removed in a single day
SALARY_SHIFT_THRESHOLD_PCT = 10  # median salary changes >10%

# Schema version
CURRENT_SCHEMA_VERSION = 1


def get_db_path(db_path: str | None = None) -> Path:
    """Resolve database file path."""
    if db_path:
        return Path(db_path)
    DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DATA_DIR / DB_FILENAME
