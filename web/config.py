"""
web/config.py — DAVE Web Frontend Configuration

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

All web-layer configuration lives here. Engine configuration (LLM backend,
model, API keys) remains in engine/config.py. This file covers only the
web frontend: user management, budget limits, CAPTCHA, and Flask settings.

All values can be overridden by environment variables at deployment time.
Never hardcode secrets here — use environment variables for anything sensitive.
"""

import os


# =============================================================================
# FLASK SETTINGS
# =============================================================================

# Secret key for signing session cookies. MUST be set to a strong random value
# in production. Generate one with: python -c "import secrets; print(secrets.token_hex(32))"
# Override with env var: DAVE_SECRET_KEY
SECRET_KEY: str = os.environ.get(
    "DAVE_SECRET_KEY",
    "dev-insecure-key-replace-in-production",
)

# Set to False in production (disables the interactive debugger and reloader).
# Override with env var: DAVE_DEBUG (set to "0" or "false" to disable)
DEBUG: bool = os.environ.get("DAVE_DEBUG", "1").lower() not in ("0", "false", "no")


# =============================================================================
# USER DATABASE
# =============================================================================

# Path to the SQLite database that stores user accounts and token budgets.
# Separate from all game databases, which are per-user and per-module.
# Override with env var: DAVE_USER_DB_PATH
USER_DB_PATH: str = os.environ.get("DAVE_USER_DB_PATH", "web/dave_users.db")

# Directory where per-user game database copies are stored.
# Each user gets their own copy of the module DB on first session start.
# Override with env var: DAVE_USER_DB_DIR
USER_DB_DIR: str = os.environ.get("DAVE_USER_DB_DIR", "user_dbs")


# =============================================================================
# USER SLOTS AND BUDGET
# =============================================================================

# Maximum number of registered users. Once this many accounts exist, the
# registration page shows a "contact me" message instead of the form.
# Override with env var: DAVE_MAX_USERS
MAX_USERS: int = int(os.environ.get("DAVE_MAX_USERS", "10"))

# Per-user turn limit for the alpha. When a user's turn count reaches this
# value their session is blocked and they see a contact message.
# Each turn = one player input processed through the full three-pass engine.
# Override with env var: DAVE_MAX_TURNS
MAX_TURNS: int = int(os.environ.get("DAVE_MAX_TURNS", "50"))

# Per-user token budget in euros. Tracked for future reference but not
# enforced as the primary gate during alpha — turns are the active limit.
# Override with env var: DAVE_BUDGET_EUROS
BUDGET_EUROS: float = float(os.environ.get("DAVE_BUDGET_EUROS", "1.0"))

# Token pricing for the default Scaleway model (Mistral Small 3.2).
# Used to compute running cost from token counts.
# Update these if the model or pricing changes.
# Override with env vars: DAVE_PRICE_INPUT_PER_M, DAVE_PRICE_OUTPUT_PER_M
PRICE_INPUT_PER_M: float = float(os.environ.get("DAVE_PRICE_INPUT_PER_M", "0.15"))
PRICE_OUTPUT_PER_M: float = float(os.environ.get("DAVE_PRICE_OUTPUT_PER_M", "0.35"))


# =============================================================================
# CLOUDFLARE TURNSTILE CAPTCHA
# =============================================================================
#
# Turnstile is used on the registration form to block bots without requiring
# the user to solve a puzzle. Get keys at https://dash.cloudflare.com/
# under Turnstile → Add site.
#
# For LOCAL DEVELOPMENT, use Cloudflare's published test keys which always pass:
#   Site key:   1x00000000000000000000AA
#   Secret key: 1x0000000000000000000000000000000AA
# These are public test values — safe to leave as defaults here. They will NOT
# work on a real domain; set production keys via environment variables.

TURNSTILE_SITE_KEY: str = os.environ.get(
    "DAVE_TURNSTILE_SITE_KEY",
    "1x00000000000000000000AA",  # Cloudflare test key — always passes locally
)

TURNSTILE_SECRET_KEY: str = os.environ.get(
    "DAVE_TURNSTILE_SECRET_KEY",
    "1x0000000000000000000000000000000AA",  # Cloudflare test secret — always passes
)

TURNSTILE_VERIFY_URL: str = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


# =============================================================================
# MODULE CONFIGURATION
# =============================================================================

# Available modules for selection on the lobby page.
#
# Each entry maps a display name to a dict with:
#   db           — path to the module's SQLite database (used as copy template)
#   reset_script — path to reset_instance.sql, run against the user's copy
#                  immediately after it is created to put it in a clean start
#                  state. This ensures the user always begins fresh regardless
#                  of the state the source DB was left in.
#   description  — one-line blurb shown to the player on the lobby page.
AVAILABLE_MODULES: dict = {
    "The Hidden Hostel": {
        "db":           "modules/hidden_hostel/hidden_hostel.db",
        "reset_script": "modules/hidden_hostel/reset_instance.sql",
        "game_id":      1,
        "description":  "A mini scenario providing access to all features.",
    },
    "I Am a Cat": {
        "db":           "modules/i_am_a_cat/i_am_a_cat.db",
        "reset_script": "modules/i_am_a_cat/reset_instance.sql",
        "game_id":      1,
        "description":  "An absurdist adventure of a bored cat at 3am.",
    },
    "The Meryton Assembly": {
        "db":           "modules/Meryton/meryton.db",
        "reset_script": "modules/Meryton/reset_instance.sql",
        "game_id":      2,
        "description":  "Elizabeth Bennet attends the Assembly to dance and socialize.",
    },
}

# Contact URL shown when the user limit is reached or budget is exhausted.
CONTACT_URL: str = os.environ.get(
    "DAVE_CONTACT_URL",
    "https://www.linkedin.com/in/elizabethdalton/",
)


# =============================================================================
# LINKEDIN CONTACT MESSAGE
# =============================================================================

SLOTS_FULL_MESSAGE: str = (
    "All testing slots are currently taken. If you're interested in trying DAVE, "
    "please get in touch via LinkedIn."
)

TURNS_EXHAUSTED_MESSAGE: str = (
    "You've used all {max_turns} turns in your alpha allocation. "
    "Thank you for testing DAVE! If you'd like to continue exploring, "
    "please get in touch via LinkedIn."
)

BUDGET_EXHAUSTED_MESSAGE: str = (
    "You've used your testing allocation for this session. "
    "If you'd like to continue exploring DAVE, please get in touch via LinkedIn."
)
