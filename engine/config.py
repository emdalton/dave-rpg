"""
engine/config.py — DAVE RPG Engine Configuration

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

All runtime configuration lives here. The engine reads this module at startup;
nothing else in the codebase hardcodes model names, API keys, or tunable
parameters. To swap LLM backends, change LLM_BACKEND and the corresponding
settings below — no other files need to change.

Configuration can be overridden by environment variables (see each constant
for the corresponding env var name). This allows deployment without modifying
source files.
"""

import os


# =============================================================================
# LLM BACKEND SELECTION
# =============================================================================

# Which LLM backend to use. The engine imports the corresponding implementation
# from engine/llm/ and uses it for all three passes.
#
# Supported values:
#   "claude"    — Anthropic Claude via the anthropic SDK (Phase 1 / prototyping)
#   "ollama"    — Local model via Ollama HTTP API (Phase 2 / local production)
#   "scaleway"  — Scaleway Generative APIs (OpenAI-compatible; cloud production)
#
# Override with env var: DAVE_LLM_BACKEND
LLM_BACKEND: str = os.environ.get("DAVE_LLM_BACKEND", "claude")


# =============================================================================
# CLAUDE SETTINGS (used when LLM_BACKEND == "claude")
# =============================================================================

# Anthropic API key. Never hardcode this; always use the environment variable.
# Override with env var: ANTHROPIC_API_KEY
CLAUDE_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")

# Model string. Haiku is the Phase 1 game loop target — close in capability to
# the Phase 2 local model (Mistral/Salamandra 7B) and much cheaper to run.
# Sonnet is used separately as a construction tool (seeding, ground-truth
# adjudication examples) but should not be the default for play sessions.
# Override with env var: DAVE_CLAUDE_MODEL
CLAUDE_MODEL: str = os.environ.get("DAVE_CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# Maximum tokens the model may generate per call. Prose rendering is the most
# verbose pass; adjudication produces structured JSON and needs less.
# Override with env var: DAVE_CLAUDE_MAX_TOKENS
CLAUDE_MAX_TOKENS: int = int(os.environ.get("DAVE_CLAUDE_MAX_TOKENS", "2048"))


# =============================================================================
# OLLAMA SETTINGS (used when LLM_BACKEND == "ollama")
# =============================================================================

# Base URL for the Ollama HTTP API.
# Override with env var: DAVE_OLLAMA_BASE_URL
OLLAMA_BASE_URL: str = os.environ.get("DAVE_OLLAMA_BASE_URL", "http://localhost:11434")

# Model name as registered in Ollama (e.g. "mistral", "llama3.3").
# Override with env var: DAVE_OLLAMA_MODEL
OLLAMA_MODEL: str = os.environ.get("DAVE_OLLAMA_MODEL", "mistral")

# Request timeout in seconds for Ollama calls. Local inference can be slow
# on modest hardware; set this higher if you see timeout errors.
# Override with env var: DAVE_OLLAMA_TIMEOUT
OLLAMA_TIMEOUT: int = int(os.environ.get("DAVE_OLLAMA_TIMEOUT", "120"))


# =============================================================================
# SCALEWAY SETTINGS (used when LLM_BACKEND == "scaleway")
# =============================================================================

# Scaleway IAM API key. Obtain from the Scaleway console under
# IAM → API Keys. Never hardcode this; always use the environment variable.
# The canonical Scaleway env var name is SCW_SECRET_KEY; DAVE_SCALEWAY_API_KEY
# takes precedence if both are set, allowing per-project overrides.
# Override with env var: DAVE_SCALEWAY_API_KEY (falls back to SCW_SECRET_KEY)
SCALEWAY_API_KEY: str = (
    os.environ.get("DAVE_SCALEWAY_API_KEY")
    or os.environ.get("SCW_SECRET_KEY", "")
)

# Base URL for Scaleway's OpenAI-compatible Generative APIs endpoint.
# This should not normally need changing unless Scaleway updates their API path.
# Override with env var: DAVE_SCALEWAY_BASE_URL
SCALEWAY_BASE_URL: str = os.environ.get(
    "DAVE_SCALEWAY_BASE_URL", "https://api.scaleway.ai/v1"
)

# Model name as listed in the Scaleway console. Default is Mistral Small 3.2,
# their smallest and cheapest chat model (€0.15/M input, €0.35/M output as of
# 2026-06). Override to switch to a larger model without changing code, e.g.:
#   DAVE_SCALEWAY_MODEL=qwen3.5-397b-a17b-instruct-fp8
# Override with env var: DAVE_SCALEWAY_MODEL
SCALEWAY_MODEL: str = os.environ.get(
    "DAVE_SCALEWAY_MODEL", "mistral-small-3.2-24b-instruct-2506"
)

# Maximum tokens the model may generate per call.
# Override with env var: DAVE_SCALEWAY_MAX_TOKENS
SCALEWAY_MAX_TOKENS: int = int(os.environ.get("DAVE_SCALEWAY_MAX_TOKENS", "2048"))

# Request timeout in seconds for Scaleway API calls.
# Override with env var: DAVE_SCALEWAY_TIMEOUT
SCALEWAY_TIMEOUT: int = int(os.environ.get("DAVE_SCALEWAY_TIMEOUT", "60"))


# =============================================================================
# ENGINE PARAMETERS
# =============================================================================

# Number of recent action_log entries to include in Pass 1 (intent parsing)
# context packets. More context helps disambiguation; fewer saves tokens.
PASS1_RECENT_ACTIONS: int = int(os.environ.get("DAVE_PASS1_RECENT_ACTIONS", "5"))

# Number of valid location_detail entries to include per location in Pass 2
# (adjudication) context packets. Capped to keep packets lean.
PASS2_MAX_LOCATION_DETAILS: int = int(os.environ.get("DAVE_PASS2_MAX_LOCATION_DETAILS", "10"))

# Maximum number of items to include per location in context packets.
# Only visible items are included; this caps the list further if a location
# is very cluttered.
PASS2_MAX_ITEMS: int = int(os.environ.get("DAVE_PASS2_MAX_ITEMS", "12"))

# Maximum retry attempts when an LLM call returns malformed JSON.
# After this many failures the engine raises an exception rather than
# silently producing bad output.
LLM_MAX_RETRIES: int = int(os.environ.get("DAVE_LLM_MAX_RETRIES", "3"))

# Number of action_log entries to retain before pruning older rows.
# Pass 1 only needs recent context; this keeps the table from growing
# unboundedly over a long play session.
ACTION_LOG_MAX_ROWS: int = int(os.environ.get("DAVE_ACTION_LOG_MAX_ROWS", "50"))

# Probability scale cap for involuntary events. Per-turn probability is
# computed as min(state_value * trigger_param, INVOLUNTARY_MAX_PROB).
# This prevents a maxed-out state from making an event certain every turn,
# preserving narrative unpredictability.
INVOLUNTARY_MAX_PROB: float = float(os.environ.get("DAVE_INVOLUNTARY_MAX_PROB", "0.25"))

# Sleepiness threshold above which the NPC wander roll is suppressed.
# An NPC with sleepiness >= this value is too drowsy to wander autonomously;
# the engine skips their wander roll for the turn. This complements the
# pending_intent suppression: both represent states where wandering 'just
# isn't done'. Typical value: 0.60. 0.0 disables the suppression entirely.
# Override with env var: DAVE_WANDER_SLEEPINESS_THRESHOLD
WANDER_SLEEPINESS_THRESHOLD: float = float(
    os.environ.get("DAVE_WANDER_SLEEPINESS_THRESHOLD", "0.60")
)

# Confidence threshold above which a non-renewable, time-expired activity is
# cleared mechanically by the engine without requiring an explicit Pass 2 clear.
# Activities with confidence < this threshold, or with renewable=1, are never
# auto-cleared — only Pass 2 may remove them via 'activity_updates' in the
# outcome JSON. Typical value: 0.60. Set to 1.01 to disable auto-clearing
# entirely (forces all clears through Pass 2).
# Override with env var: DAVE_ACTIVITY_AUTO_CLEAR_CONFIDENCE
ACTIVITY_AUTO_CLEAR_CONFIDENCE: float = float(
    os.environ.get("DAVE_ACTIVITY_AUTO_CLEAR_CONFIDENCE", "0.60")
)


# =============================================================================
# DATABASE
# =============================================================================

# Path to the SQLite database file. Relative paths are resolved from the
# working directory at engine startup. Override for a specific module:
#   DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python -m engine
# Override with env var: DAVE_DB_PATH
DB_PATH: str = os.environ.get("DAVE_DB_PATH", "game.db")


# =============================================================================
# VALIDATION
# =============================================================================

def validate() -> None:
    """
    Check that required configuration is present and internally consistent.
    Called at engine startup before any database or LLM connections are made.
    Raises ValueError with a descriptive message on the first problem found.
    """
    if LLM_BACKEND not in ("claude", "ollama", "scaleway"):
        raise ValueError(
            f"LLM_BACKEND must be 'claude', 'ollama', or 'scaleway', got: {LLM_BACKEND!r}. "
            f"Set the DAVE_LLM_BACKEND environment variable."
        )

    if LLM_BACKEND == "claude" and not CLAUDE_API_KEY:
        raise ValueError(
            "CLAUDE_API_KEY is not set. Export your Anthropic API key as the "
            "ANTHROPIC_API_KEY environment variable before starting the engine."
        )

    if LLM_BACKEND == "ollama" and not OLLAMA_BASE_URL:
        raise ValueError(
            "DAVE_OLLAMA_BASE_URL is not set. Set it to your Ollama server URL "
            "(default: http://localhost:11434)."
        )

    if LLM_BACKEND == "scaleway" and not SCALEWAY_API_KEY:
        raise ValueError(
            "Scaleway API key is not set. Export your key as SCW_SECRET_KEY "
            "(or DAVE_SCALEWAY_API_KEY) before starting the engine."
        )

    if LLM_MAX_RETRIES < 1:
        raise ValueError(
            f"DAVE_LLM_MAX_RETRIES must be at least 1, got: {LLM_MAX_RETRIES}."
        )

    if not (0.0 < INVOLUNTARY_MAX_PROB <= 1.0):
        raise ValueError(
            f"DAVE_INVOLUNTARY_MAX_PROB must be between 0.0 (exclusive) and 1.0 "
            f"(inclusive), got: {INVOLUNTARY_MAX_PROB}."
        )
