"""
tests/test_web_user_db.py — Web Frontend User Database Tests (Tier 1)

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Tier 1 (no LLM) tests for web/user_db.py. These cover the registration,
authentication, slot management, turn tracking, and budget calculation logic
that enforces the alpha cost controls.

Why this matters:
    The turn limit and slot cap are the primary mechanisms protecting against
    unbounded inference costs during alpha testing. A regression here could
    result in real financial exposure. These tests must be kept current with
    any changes to web/user_db.py or web/config.py cost parameters.

Coverage:
    §A  Schema initialisation — idempotent; tables and indexes created
    §B  Registration — success, duplicate username, validation errors,
        slot cap enforcement
    §C  Authentication — correct credentials, wrong password, unknown user,
        inactive account
    §D  Slot management — user_count, slots_available, cap boundary
    §E  Turn tracking — record_turn increments, exhaustion at MAX_TURNS,
        get_turn_status fields
    §F  Budget tracking — _compute_cost arithmetic, record_tokens accumulation,
        budget_exhausted flag, get_budget_status fields
    §G  get_user_by_id — present, absent
"""

import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Web config is imported by user_db; patch MAX_USERS and MAX_TURNS
# to small sentinel values so tests don't depend on production constants.
import web.config as web_config
from web.user_db import UserDatabase, _compute_cost


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tmp_user_db(tmp_path) -> UserDatabase:
    """
    Yield a UserDatabase instance backed by a fresh temporary SQLite file.
    Schema is applied once during setup. The file is discarded after each test.
    """
    db_path = str(tmp_path / "test_users.db")
    db = UserDatabase(db_path)
    db.init_schema()
    return db


@pytest.fixture
def db_with_users(tmp_user_db) -> UserDatabase:
    """
    UserDatabase pre-populated with two registered accounts:
        - "alice" / "password_alice1"
        - "bob"   / "password_bob999"
    Both accounts are active and have zero turns used.
    """
    tmp_user_db.register("alice", "password_alice1")
    tmp_user_db.register("bob", "password_bob999")
    return tmp_user_db


# =============================================================================
# §A — Schema initialisation
# =============================================================================

class TestSchemaInit:
    """init_schema() creates the expected tables and indexes."""

    def test_user_table_exists(self, tmp_user_db):
        """The user table must exist after init_schema()."""
        conn = sqlite3.connect(tmp_user_db._path)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user'"
        ).fetchone()
        conn.close()
        assert row is not None, "user table was not created"

    def test_username_index_exists(self, tmp_user_db):
        """The idx_user_username index must exist."""
        conn = sqlite3.connect(tmp_user_db._path)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='idx_user_username'"
        ).fetchone()
        conn.close()
        assert row is not None, "idx_user_username index was not created"

    def test_init_schema_is_idempotent(self, tmp_user_db):
        """Calling init_schema() twice must not raise or duplicate anything."""
        tmp_user_db.init_schema()   # second call
        count = tmp_user_db.user_count()
        assert count == 0   # no phantom rows

    def test_new_db_has_turns_used_column(self, tmp_user_db):
        """The turns_used column (alpha turn limit) must exist on the user table."""
        conn = sqlite3.connect(tmp_user_db._path)
        cols = [row[1] for row in conn.execute("PRAGMA table_info(user)").fetchall()]
        conn.close()
        assert "turns_used" in cols, "turns_used column missing from user table"

    def test_new_db_has_budget_exhausted_column(self, tmp_user_db):
        """The budget_exhausted column must exist on the user table."""
        conn = sqlite3.connect(tmp_user_db._path)
        cols = [row[1] for row in conn.execute("PRAGMA table_info(user)").fetchall()]
        conn.close()
        assert "budget_exhausted" in cols


# =============================================================================
# §B — Registration
# =============================================================================

class TestRegistration:
    """register() creates accounts and enforces validation rules."""

    def test_register_success(self, tmp_user_db):
        """Valid credentials return (True, '')."""
        ok, reason = tmp_user_db.register("alice", "strongpass1")
        assert ok is True
        assert reason == ""

    def test_register_creates_row(self, tmp_user_db):
        """After registration the user row exists with is_active=1."""
        tmp_user_db.register("alice", "strongpass1")
        assert tmp_user_db.user_count() == 1

    def test_register_duplicate_username(self, tmp_user_db):
        """A second registration with the same username must fail."""
        tmp_user_db.register("alice", "strongpass1")
        ok, reason = tmp_user_db.register("alice", "different_pass")
        assert ok is False
        assert "taken" in reason.lower()

    def test_register_username_too_short(self, tmp_user_db):
        """Usernames under 3 characters must be rejected."""
        ok, reason = tmp_user_db.register("ab", "strongpass1")
        assert ok is False
        assert "3" in reason   # error message mentions the minimum

    def test_register_username_too_long(self, tmp_user_db):
        """Usernames over 32 characters must be rejected."""
        ok, reason = tmp_user_db.register("a" * 33, "strongpass1")
        assert ok is False
        assert "32" in reason

    def test_register_username_invalid_chars(self, tmp_user_db):
        """Usernames with non-alphanumeric, non-underscore characters must be rejected."""
        ok, reason = tmp_user_db.register("alice@host", "strongpass1")
        assert ok is False
        assert "letters" in reason.lower() or "only" in reason.lower()

    def test_register_password_too_short(self, tmp_user_db):
        """Passwords under 8 characters must be rejected."""
        ok, reason = tmp_user_db.register("alice", "short")
        assert ok is False
        assert "8" in reason

    def test_register_username_with_underscore_allowed(self, tmp_user_db):
        """Underscores are a permitted character in usernames."""
        ok, reason = tmp_user_db.register("alice_smith", "strongpass1")
        assert ok is True, f"underscore username rejected: {reason}"

    def test_register_strips_whitespace(self, tmp_user_db):
        """Leading/trailing whitespace in the username is stripped before validation."""
        ok, reason = tmp_user_db.register("  alice  ", "strongpass1")
        assert ok is True, f"whitespace stripping failed: {reason}"
        # Stored without whitespace
        user = tmp_user_db.authenticate("alice", "strongpass1")
        assert user is not None

    def test_register_slot_cap_enforced(self, tmp_user_db):
        """Registration must fail with 'no_slots' once MAX_USERS is reached."""
        with patch.object(web_config, "MAX_USERS", 2):
            tmp_user_db.register("user1", "password111")
            tmp_user_db.register("user2", "password222")
            ok, reason = tmp_user_db.register("user3", "password333")
        assert ok is False
        assert reason == "no_slots"

    def test_register_does_not_count_inactive_toward_slot_cap(self, tmp_user_db):
        """An inactive (soft-deleted) user should not count toward the slot cap."""
        with patch.object(web_config, "MAX_USERS", 1):
            tmp_user_db.register("alice", "strongpass1")
            # Soft-delete alice
            conn = sqlite3.connect(tmp_user_db._path)
            conn.execute("UPDATE user SET is_active=0 WHERE username='alice'")
            conn.commit()
            conn.close()
            # Slot should now be free
            ok, reason = tmp_user_db.register("bob", "strongpass2")
        assert ok is True, f"inactive user incorrectly counted toward slot cap: {reason}"


# =============================================================================
# §C — Authentication
# =============================================================================

class TestAuthentication:
    """authenticate() returns a user row on success, None on failure."""

    def test_authenticate_correct_credentials(self, db_with_users):
        """Correct username and password return a non-None row."""
        user = db_with_users.authenticate("alice", "password_alice1")
        assert user is not None
        assert user["username"] == "alice"

    def test_authenticate_wrong_password(self, db_with_users):
        """Wrong password returns None."""
        user = db_with_users.authenticate("alice", "wrongpassword")
        assert user is None

    def test_authenticate_unknown_username(self, db_with_users):
        """An unregistered username returns None."""
        user = db_with_users.authenticate("nobody", "somepassword")
        assert user is None

    def test_authenticate_inactive_account(self, db_with_users):
        """A soft-deleted (is_active=0) account must not authenticate."""
        conn = sqlite3.connect(db_with_users._path)
        conn.execute("UPDATE user SET is_active=0 WHERE username='alice'")
        conn.commit()
        conn.close()
        user = db_with_users.authenticate("alice", "password_alice1")
        assert user is None

    def test_authenticate_returns_id(self, db_with_users):
        """The returned row must include the user's integer id."""
        user = db_with_users.authenticate("bob", "password_bob999")
        assert "id" in user.keys()
        assert isinstance(user["id"], int)


# =============================================================================
# §D — Slot management
# =============================================================================

class TestSlotManagement:
    """user_count() and slots_available() reflect the current registration state."""

    def test_user_count_empty(self, tmp_user_db):
        """An empty database has a user count of zero."""
        assert tmp_user_db.user_count() == 0

    def test_user_count_after_registration(self, db_with_users):
        """user_count returns the number of active registered accounts."""
        assert db_with_users.user_count() == 2

    def test_slots_available_when_under_cap(self, tmp_user_db):
        """slots_available() returns True when under MAX_USERS."""
        with patch.object(web_config, "MAX_USERS", 5):
            assert tmp_user_db.slots_available() is True

    def test_slots_available_at_cap(self, tmp_user_db):
        """slots_available() returns False when the cap is exactly reached."""
        with patch.object(web_config, "MAX_USERS", 1):
            tmp_user_db.register("alice", "strongpass1")
            assert tmp_user_db.slots_available() is False

    def test_slots_available_counts_only_active(self, db_with_users):
        """slots_available() counts only is_active=1 rows."""
        with patch.object(web_config, "MAX_USERS", 2):
            # Both slots full
            assert db_with_users.slots_available() is False
            # Soft-delete one
            conn = sqlite3.connect(db_with_users._path)
            conn.execute("UPDATE user SET is_active=0 WHERE username='alice'")
            conn.commit()
            conn.close()
            assert db_with_users.slots_available() is True


# =============================================================================
# §E — Turn tracking
# =============================================================================

class TestTurnTracking:
    """record_turn() and get_turn_status() manage the alpha turn limit."""

    def _get_user_id(self, db: UserDatabase, username: str) -> int:
        user = db.authenticate(username, "password_alice1")
        return user["id"]

    @pytest.fixture
    def alice_id(self, db_with_users) -> int:
        user = db_with_users.authenticate("alice", "password_alice1")
        return user["id"]

    def test_initial_turns_used_is_zero(self, db_with_users, alice_id):
        """A new user starts with zero turns used."""
        status = db_with_users.get_turn_status(alice_id)
        assert status["turns_used"] == 0

    def test_turns_remaining_equals_max_at_start(self, db_with_users, alice_id):
        """turns_remaining equals MAX_TURNS for a fresh account."""
        with patch.object(web_config, "MAX_TURNS", 50):
            status = db_with_users.get_turn_status(alice_id)
        assert status["turns_remaining"] == 50

    def test_record_turn_increments_count(self, db_with_users, alice_id):
        """Each call to record_turn() increments turns_used by exactly one."""
        db_with_users.record_turn(alice_id)
        db_with_users.record_turn(alice_id)
        status = db_with_users.get_turn_status(alice_id)
        assert status["turns_used"] == 2

    def test_turns_remaining_decrements(self, db_with_users, alice_id):
        """turns_remaining decreases as turns are recorded."""
        with patch.object(web_config, "MAX_TURNS", 10):
            db_with_users.record_turn(alice_id)
            db_with_users.record_turn(alice_id)
            status = db_with_users.get_turn_status(alice_id)
        assert status["turns_remaining"] == 8

    def test_exhausted_false_before_limit(self, db_with_users, alice_id):
        """exhausted is False when turns_used < MAX_TURNS."""
        with patch.object(web_config, "MAX_TURNS", 5):
            for _ in range(4):
                db_with_users.record_turn(alice_id)
            status = db_with_users.get_turn_status(alice_id)
        assert status["exhausted"] is False

    def test_exhausted_true_at_limit(self, db_with_users, alice_id):
        """exhausted is True when turns_used reaches MAX_TURNS."""
        with patch.object(web_config, "MAX_TURNS", 3):
            for _ in range(3):
                db_with_users.record_turn(alice_id)
            status = db_with_users.get_turn_status(alice_id)
        assert status["exhausted"] is True

    def test_turns_remaining_floored_at_zero(self, db_with_users, alice_id):
        """turns_remaining never goes below zero even if turns_used exceeds MAX_TURNS."""
        with patch.object(web_config, "MAX_TURNS", 2):
            for _ in range(5):   # record more than the limit
                db_with_users.record_turn(alice_id)
            status = db_with_users.get_turn_status(alice_id)
        assert status["turns_remaining"] == 0

    def test_get_turn_status_unknown_user(self, tmp_user_db):
        """get_turn_status() for a non-existent user_id returns safe zero values."""
        status = tmp_user_db.get_turn_status(9999)
        assert status["turns_used"] == 0
        assert status["exhausted"] is False

    def test_turn_counts_are_per_user(self, db_with_users):
        """Turn counts are independent per user — recording for alice does not affect bob."""
        alice = db_with_users.authenticate("alice", "password_alice1")
        bob   = db_with_users.authenticate("bob", "password_bob999")
        db_with_users.record_turn(alice["id"])
        db_with_users.record_turn(alice["id"])
        assert db_with_users.get_turn_status(bob["id"])["turns_used"] == 0

    def test_get_turn_status_max_turns_field(self, db_with_users, alice_id):
        """get_turn_status() includes the max_turns configuration value."""
        with patch.object(web_config, "MAX_TURNS", 42):
            status = db_with_users.get_turn_status(alice_id)
        assert status["max_turns"] == 42


# =============================================================================
# §F — Budget tracking
# =============================================================================

class TestBudgetTracking:
    """record_tokens(), get_budget_status(), and _compute_cost() are correct."""

    @pytest.fixture
    def alice_id(self, db_with_users) -> int:
        user = db_with_users.authenticate("alice", "password_alice1")
        return user["id"]

    # ---- _compute_cost unit tests (pure arithmetic, no DB) ----

    def test_compute_cost_zero_tokens(self):
        """Zero tokens produce zero cost."""
        assert _compute_cost(0, 0) == 0.0

    def test_compute_cost_one_million_input(self):
        """1 million input tokens costs exactly PRICE_INPUT_PER_M euros."""
        cost = _compute_cost(1_000_000, 0)
        assert abs(cost - web_config.PRICE_INPUT_PER_M) < 1e-9

    def test_compute_cost_one_million_output(self):
        """1 million output tokens costs exactly PRICE_OUTPUT_PER_M euros."""
        cost = _compute_cost(0, 1_000_000)
        assert abs(cost - web_config.PRICE_OUTPUT_PER_M) < 1e-9

    def test_compute_cost_mixed(self):
        """Mixed token counts produce the correct weighted sum."""
        # At default Mistral Small pricing: 0.15/M input, 0.35/M output
        # 500k input + 200k output = 0.075 + 0.070 = 0.145
        expected = (500_000 / 1_000_000 * web_config.PRICE_INPUT_PER_M
                    + 200_000 / 1_000_000 * web_config.PRICE_OUTPUT_PER_M)
        assert abs(_compute_cost(500_000, 200_000) - expected) < 1e-9

    # ---- record_tokens + get_budget_status DB tests ----

    def test_initial_budget_status(self, db_with_users, alice_id):
        """A fresh account has zero tokens and is not exhausted."""
        status = db_with_users.get_budget_status(alice_id)
        assert status["tokens_input"]  == 0
        assert status["tokens_output"] == 0
        assert status["cost_eur"]      == 0.0
        assert status["exhausted"]     is False

    def test_record_tokens_accumulates(self, db_with_users, alice_id):
        """Multiple record_tokens calls accumulate correctly."""
        db_with_users.record_tokens(alice_id, 1000, 500)
        db_with_users.record_tokens(alice_id, 2000, 1000)
        status = db_with_users.get_budget_status(alice_id)
        assert status["tokens_input"]  == 3000
        assert status["tokens_output"] == 1500

    def test_budget_not_exhausted_below_limit(self, db_with_users, alice_id):
        """budget_exhausted stays False when cost is below BUDGET_EUROS."""
        # Record a small number of tokens — far below the €1 limit
        db_with_users.record_tokens(alice_id, 100, 50)
        status = db_with_users.get_budget_status(alice_id)
        assert status["exhausted"] is False

    def test_budget_exhausted_at_limit(self, db_with_users, alice_id):
        """budget_exhausted becomes True when accumulated cost reaches BUDGET_EUROS."""
        # At default pricing (€0.15/M in, €0.35/M out), reaching €1.00 requires
        # roughly 2M input + 2M output. Use patched limit of €0.001 to avoid
        # inserting millions of tokens in a unit test.
        with patch.object(web_config, "BUDGET_EUROS", 0.001):
            # €0.15/M * 10000 tokens = €0.0015 > €0.001
            db_with_users.record_tokens(alice_id, 10_000, 0)
            status = db_with_users.get_budget_status(alice_id)
        assert status["exhausted"] is True

    def test_budget_exhausted_flag_persists_in_db(self, db_with_users, alice_id):
        """Once budget_exhausted=1 is written to the DB it persists on re-query."""
        with patch.object(web_config, "BUDGET_EUROS", 0.001):
            db_with_users.record_tokens(alice_id, 10_000, 0)
        # Re-query without patching — the DB flag should be set regardless
        conn = sqlite3.connect(db_with_users._path)
        row = conn.execute(
            "SELECT budget_exhausted FROM user WHERE id=?", (alice_id,)
        ).fetchone()
        conn.close()
        assert row[0] == 1

    def test_remaining_eur_decreases(self, db_with_users, alice_id):
        """remaining_eur decreases as tokens are recorded."""
        with patch.object(web_config, "BUDGET_EUROS", 1.0):
            initial = db_with_users.get_budget_status(alice_id)["remaining_eur"]
            db_with_users.record_tokens(alice_id, 100_000, 0)
            after = db_with_users.get_budget_status(alice_id)["remaining_eur"]
        assert after < initial

    def test_remaining_eur_floored_at_zero(self, db_with_users, alice_id):
        """remaining_eur is never negative."""
        with patch.object(web_config, "BUDGET_EUROS", 0.001):
            db_with_users.record_tokens(alice_id, 1_000_000, 0)
            status = db_with_users.get_budget_status(alice_id)
        assert status["remaining_eur"] == 0.0

    def test_budget_status_unknown_user(self, tmp_user_db):
        """get_budget_status() for a non-existent user_id returns safe zero values."""
        status = tmp_user_db.get_budget_status(9999)
        assert status["tokens_input"]  == 0
        assert status["exhausted"]     is False
        assert status["remaining_eur"] == web_config.BUDGET_EUROS

    def test_token_counts_are_per_user(self, db_with_users):
        """Token counts are independent per user."""
        alice = db_with_users.authenticate("alice", "password_alice1")
        bob   = db_with_users.authenticate("bob",   "password_bob999")
        db_with_users.record_tokens(alice["id"], 5000, 2000)
        status = db_with_users.get_budget_status(bob["id"])
        assert status["tokens_input"]  == 0
        assert status["tokens_output"] == 0


# =============================================================================
# §G — get_user_by_id
# =============================================================================

class TestGetUserById:
    """get_user_by_id() returns the row for valid active users, None otherwise."""

    def test_get_user_by_id_found(self, db_with_users):
        """Returns the correct row for an existing active user."""
        user = db_with_users.authenticate("alice", "password_alice1")
        row  = db_with_users.get_user_by_id(user["id"])
        assert row is not None
        assert row["username"] == "alice"

    def test_get_user_by_id_not_found(self, tmp_user_db):
        """Returns None for a non-existent id."""
        assert tmp_user_db.get_user_by_id(9999) is None

    def test_get_user_by_id_inactive(self, db_with_users):
        """Returns None for an inactive (soft-deleted) user."""
        user = db_with_users.authenticate("alice", "password_alice1")
        conn = sqlite3.connect(db_with_users._path)
        conn.execute("UPDATE user SET is_active=0 WHERE id=?", (user["id"],))
        conn.commit()
        conn.close()
        assert db_with_users.get_user_by_id(user["id"]) is None
