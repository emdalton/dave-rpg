"""
web/user_db.py — DAVE Web Frontend User Database

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Manages the SQLite database that tracks user accounts and token budgets.
This is entirely separate from the per-user game databases (which are copies
of module seed DBs). One UserDatabase instance is created at app startup and
shared across all requests via the Flask app object.

Schema:
    user        — one row per registered account; stores credentials and
                  accumulated token counts for budget tracking.

Budget tracking:
    Token counts (input + output) are accumulated per user. Cost is computed
    on demand as:
        cost_eur = (tokens_input / 1e6 * PRICE_INPUT_PER_M)
                 + (tokens_output / 1e6 * PRICE_OUTPUT_PER_M)
    When cost_eur >= BUDGET_EUROS the user is blocked from further play.

The 10-user slot limit is enforced by counting rows in the user table.
"""

import logging
import sqlite3
import threading
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

from web import config

logger = logging.getLogger(__name__)


# =============================================================================
# Schema
# =============================================================================

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS user (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    username         TEXT    UNIQUE NOT NULL,
    password_hash    TEXT    NOT NULL,
    created_at       TEXT    DEFAULT (datetime('now')),

    -- Accumulated token counts for budget tracking.
    -- Updated after every LLM call via record_tokens().
    tokens_input     INTEGER NOT NULL DEFAULT 0,
    tokens_output    INTEGER NOT NULL DEFAULT 0,

    -- Number of turns (player inputs) processed for this account.
    -- This is the primary alpha limit; see MAX_TURNS in web.config.
    turns_used       INTEGER NOT NULL DEFAULT 0,

    -- Set to 1 when the computed cost reaches BUDGET_EUROS.
    -- Tracked for reference during alpha but not the active enforcement gate.
    budget_exhausted INTEGER NOT NULL DEFAULT 0,

    -- Soft-delete / ban flag. Set to 1 to prevent login without deleting data.
    is_active        INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_user_username ON user(username);
"""


# =============================================================================
# UserDatabase
# =============================================================================

class UserDatabase:
    """
    Thin wrapper around the SQLite user database.

    Thread-safe via a per-connection threading.local pattern: each thread
    gets its own sqlite3 connection so that concurrent Flask requests do not
    share connection state. The database file itself is shared.

    Usage:
        user_db = UserDatabase("web/dave_users.db")
        user_db.init_schema()   # call once at app startup
    """

    def __init__(self, db_path: str) -> None:
        """
        Initialise the database wrapper. Does not open a connection yet.

        Args:
            db_path: Path to the SQLite file. Created if it does not exist.
        """
        self._path = db_path
        self._local = threading.local()

    # -------------------------------------------------------------------------
    # Connection management
    # -------------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        """
        Return the per-thread SQLite connection, opening it if needed.

        sqlite3 connections are not thread-safe; this pattern gives each
        thread its own connection to the shared database file.
        """
        conn = getattr(self._local, "conn", None)
        if conn is None:
            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")   # concurrent read safety
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    def init_schema(self) -> None:
        """
        Apply the schema DDL. Safe to call on every startup — all
        CREATE statements use IF NOT EXISTS.
        """
        conn = self._conn()
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        logger.info("User database schema applied: %s", self._path)

    # -------------------------------------------------------------------------
    # Slot management
    # -------------------------------------------------------------------------

    def user_count(self) -> int:
        """Return the number of registered (active) user accounts."""
        row = self._conn().execute(
            "SELECT COUNT(*) FROM user WHERE is_active = 1"
        ).fetchone()
        return row[0] if row else 0

    def slots_available(self) -> bool:
        """
        Return True if there is room for another user registration.
        Compares active user count against MAX_USERS from web.config.
        """
        return self.user_count() < config.MAX_USERS

    # -------------------------------------------------------------------------
    # Registration and login
    # -------------------------------------------------------------------------

    def register(self, username: str, password: str) -> tuple[bool, str]:
        """
        Create a new user account.

        Args:
            username: Desired username. Must be unique, 3–32 characters,
                      alphanumeric + underscores only (enforced here).
            password: Plain-text password (hashed before storage).

        Returns:
            (True, "") on success.
            (False, reason_string) on failure — reason is safe to show to the user.
        """
        username = username.strip()

        # Basic validation.
        if not username or len(username) < 3 or len(username) > 32:
            return False, "Username must be between 3 and 32 characters."
        if not username.replace("_", "").isalnum():
            return False, "Username may only contain letters, numbers, and underscores."
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters."

        # Slot check.
        if not self.slots_available():
            return False, "no_slots"

        password_hash = generate_password_hash(password)
        try:
            self._conn().execute(
                "INSERT INTO user (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
            self._conn().commit()
            logger.info("New user registered: %r", username)
            return True, ""
        except sqlite3.IntegrityError:
            return False, "That username is already taken."

    def authenticate(self, username: str, password: str) -> dict | None:
        """
        Verify credentials and return the user row if valid.

        Args:
            username: The submitted username.
            password: The submitted plain-text password.

        Returns:
            A sqlite3.Row (dict-like) for the matching active user, or None
            if credentials are invalid or the account is inactive.
        """
        row = self._conn().execute(
            "SELECT * FROM user WHERE username = ? AND is_active = 1",
            (username.strip(),),
        ).fetchone()

        if row is None:
            return None
        if not check_password_hash(row["password_hash"], password):
            return None
        return row

    def get_user_by_id(self, user_id: int) -> dict | None:
        """Return the user row for the given id, or None if not found."""
        return self._conn().execute(
            "SELECT * FROM user WHERE id = ? AND is_active = 1",
            (user_id,),
        ).fetchone()

    # -------------------------------------------------------------------------
    # Turn tracking (primary alpha limit)
    # -------------------------------------------------------------------------

    def record_turn(self, user_id: int) -> None:
        """
        Increment the turn counter for the given user.

        Called after each successful player turn (after engine.step() returns
        prose). Not called for the opening scene or Green Room exchanges, which
        are setup overhead rather than gameplay turns.
        """
        conn = self._conn()
        conn.execute(
            "UPDATE user SET turns_used = turns_used + 1 WHERE id = ?",
            (user_id,),
        )
        conn.commit()

    def get_turn_status(self, user_id: int) -> dict:
        """
        Return turn-count information for the given user.

        Returns a dict with keys:
            turns_used      (int)   — turns consumed so far
            turns_remaining (int)   — turns left before the limit
            max_turns       (int)   — configured limit (MAX_TURNS)
            exhausted       (bool)  — True if the limit has been reached
        """
        row = self._conn().execute(
            "SELECT turns_used FROM user WHERE id = ?",
            (user_id,),
        ).fetchone()

        used = row["turns_used"] if row else 0
        max_turns = config.MAX_TURNS
        return {
            "turns_used":      used,
            "turns_remaining": max(0, max_turns - used),
            "max_turns":       max_turns,
            "exhausted":       used >= max_turns,
        }

    # -------------------------------------------------------------------------
    # Token budget tracking (retained for future reference)
    # -------------------------------------------------------------------------

    def record_tokens(self, user_id: int, tokens_input: int, tokens_output: int) -> None:
        """
        Add token counts to the user's running totals and set budget_exhausted
        if the cumulative cost has reached the configured limit.

        Args:
            user_id:       The user's database id.
            tokens_input:  Number of input tokens used in this LLM call.
            tokens_output: Number of output tokens used in this LLM call.
        """
        conn = self._conn()
        conn.execute(
            """UPDATE user
               SET tokens_input  = tokens_input  + ?,
                   tokens_output = tokens_output + ?
               WHERE id = ?""",
            (tokens_input, tokens_output, user_id),
        )
        conn.commit()

        # Recompute cost and flag exhaustion if limit reached.
        row = conn.execute(
            "SELECT tokens_input, tokens_output FROM user WHERE id = ?",
            (user_id,),
        ).fetchone()

        if row:
            cost = _compute_cost(row["tokens_input"], row["tokens_output"])
            if cost >= config.BUDGET_EUROS:
                conn.execute(
                    "UPDATE user SET budget_exhausted = 1 WHERE id = ?",
                    (user_id,),
                )
                conn.commit()
                logger.info(
                    "Budget exhausted: user_id=%d cost=€%.4f limit=€%.2f",
                    user_id, cost, config.BUDGET_EUROS,
                )

    def get_budget_status(self, user_id: int) -> dict:
        """
        Return budget information for the given user.

        Returns a dict with keys:
            tokens_input    (int)   — accumulated input tokens
            tokens_output   (int)   — accumulated output tokens
            cost_eur        (float) — computed cost in euros
            budget_euros    (float) — configured limit
            exhausted       (bool)  — True if limit has been reached
            remaining_eur   (float) — euros remaining (0.0 if exhausted)
        """
        row = self._conn().execute(
            "SELECT tokens_input, tokens_output, budget_exhausted FROM user WHERE id = ?",
            (user_id,),
        ).fetchone()

        if row is None:
            return {
                "tokens_input": 0, "tokens_output": 0, "cost_eur": 0.0,
                "budget_euros": config.BUDGET_EUROS, "exhausted": False,
                "remaining_eur": config.BUDGET_EUROS,
            }

        cost = _compute_cost(row["tokens_input"], row["tokens_output"])
        exhausted = bool(row["budget_exhausted"]) or cost >= config.BUDGET_EUROS
        return {
            "tokens_input":  row["tokens_input"],
            "tokens_output": row["tokens_output"],
            "cost_eur":      round(cost, 4),
            "budget_euros":  config.BUDGET_EUROS,
            "exhausted":     exhausted,
            "remaining_eur": round(max(0.0, config.BUDGET_EUROS - cost), 4),
        }


# =============================================================================
# Cost computation helper
# =============================================================================

def _compute_cost(tokens_input: int, tokens_output: int) -> float:
    """
    Compute the cost in euros for the given token counts.

    Uses PRICE_INPUT_PER_M and PRICE_OUTPUT_PER_M from web.config.
    These default to Mistral Small 3.2 pricing as of 2026-06.
    """
    return (
        (tokens_input  / 1_000_000) * config.PRICE_INPUT_PER_M
        + (tokens_output / 1_000_000) * config.PRICE_OUTPUT_PER_M
    )
