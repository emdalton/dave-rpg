"""
tests/conftest.py — DAVE RPG Engine Test Suite Shared Fixtures

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Test tier overview
------------------
Tier 1 (default, no flags):
    No LLM calls. Tests run against an in-memory-equivalent SQLite database.
    Covers db.py, context.py, engine mechanics (_apply_outcome, activity expiry,
    wander suppression), and passive state / clock mechanics.

Tier 2 (--llm flag):
    Real LLM calls with structural / mechanical assertions.
    Pass 2 contract tests: validate JSON structure, field ranges, and
    referential integrity. Does not evaluate prose quality.
    Requires: ANTHROPIC_API_KEY environment variable.

Tier 3 (--llm-eval flag):
    Real LLM calls + a second evaluator (judge) LLM call per test.
    Evaluates Pass 1 intent accuracy and Pass 3 prose quality against rubrics.
    Requires: ANTHROPIC_API_KEY. Expensive — run infrequently.

All test databases are built from the canonical schema/schema.sql so that
schema changes automatically propagate to the test suite.
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from engine.db import Database
from engine.llm.base import LLMClient

# ---------------------------------------------------------------------------
# Path to the canonical schema — applied to every fresh test database.
# ---------------------------------------------------------------------------
_SCHEMA_SQL_PATH = Path(__file__).parent.parent / "schema" / "schema.sql"


# =============================================================================
# Custom CLI flags and marker registration
# =============================================================================

def pytest_addoption(parser):
    """Register custom command-line options for LLM test tiers."""
    parser.addoption(
        "--llm",
        action="store_true",
        default=False,
        help=(
            "Run @pytest.mark.llm tests: real LLM calls with structural assertions. "
            "Requires ANTHROPIC_API_KEY."
        ),
    )
    parser.addoption(
        "--llm-eval",
        action="store_true",
        default=False,
        help=(
            "Run @pytest.mark.llm_eval tests: real LLM + LLM-as-judge evaluation. "
            "Slow and API-expensive. Requires ANTHROPIC_API_KEY."
        ),
    )


def pytest_configure(config):
    """Register custom markers so pytest does not warn about unknown marks."""
    config.addinivalue_line(
        "markers",
        "llm: Real LLM call with structural/mechanical assertions. "
        "Opt in with --llm. Requires ANTHROPIC_API_KEY.",
    )
    config.addinivalue_line(
        "markers",
        "llm_eval: Real LLM call + LLM-as-judge quality evaluation. "
        "Opt in with --llm-eval. Slow and expensive.",
    )


def pytest_collection_modifyitems(config, items):
    """
    Skip LLM-tier tests unless the corresponding flag was passed.

    llm_eval is checked before llm so that a test marked with both
    markers is treated as llm_eval (the more restrictive tier).
    """
    skip_llm = pytest.mark.skip(
        reason="LLM structural tests skipped by default. Pass --llm to enable."
    )
    skip_llm_eval = pytest.mark.skip(
        reason=(
            "LLM evaluation tests skipped by default. "
            "Pass --llm-eval to enable (expensive)."
        )
    )

    for item in items:
        if "llm_eval" in item.keywords:
            if not config.getoption("--llm-eval"):
                item.add_marker(skip_llm_eval)
        elif "llm" in item.keywords:
            if not config.getoption("--llm"):
                item.add_marker(skip_llm)


# =============================================================================
# MockLLMClient
# =============================================================================

class MockLLMClient(LLMClient):
    """
    Configurable mock LLM client for Tier 1 (no-LLM) tests.

    Returns pre-configured responses without making any API calls.
    All calls are recorded so tests can assert on call counts and prompt content.

    Response configuration options
    --------------------------------
    Pass a list:         responses returned in order (wraps at end of list)
    Pass a dict:         keyed by call index (int) or "default" for a fallback
    Pass a str or dict:  that value returned for every call
    Pass None:           returns '{}' for every call

    Examples
    --------
    # Two specific responses then loop:
    mock = MockLLMClient([json.dumps(PASS1_MINIMAL), json.dumps(PASS2_MINIMAL), PASS3_PROSE])

    # Same response every time:
    mock = MockLLMClient(json.dumps(PASS2_MINIMAL))

    # Index-keyed:
    mock = MockLLMClient({0: json.dumps(PASS1_MINIMAL), "default": json.dumps(PASS2_MINIMAL)})
    """

    def __init__(self, responses=None):
        self._responses = responses
        self._call_log: list[str] = []   # full prompt strings, in call order
        self._call_count: int = 0

    def call(self, prompt: str) -> str:
        """Return the next configured response and record the prompt."""
        self._call_log.append(prompt)
        idx = self._call_count
        self._call_count += 1
        resp = self._pick_response(idx)
        if isinstance(resp, dict):
            return json.dumps(resp)
        return str(resp) if resp is not None else "{}"

    def _pick_response(self, idx: int):
        r = self._responses
        if r is None:
            return "{}"
        if isinstance(r, list):
            return r[idx % len(r)]
        if isinstance(r, dict):
            if idx in r:
                return r[idx]
            return r.get("default", "{}")
        # Single value (str, dict, etc.) — returned every time.
        return r

    @property
    def call_log(self) -> list[str]:
        """Snapshot of all prompts received, in order."""
        return list(self._call_log)

    @property
    def call_count(self) -> int:
        """Total number of LLM calls made."""
        return self._call_count


# =============================================================================
# Database fixtures
# =============================================================================

@pytest.fixture(scope="session")
def schema_sql() -> str:
    """
    Return the contents of schema/schema.sql as a string.

    Session-scoped: the schema file is read once and reused for all tests.
    If the schema changes mid-run (unusual), restart the test session.
    """
    return _SCHEMA_SQL_PATH.read_text(encoding="utf-8")


@pytest.fixture
def tmp_db(schema_sql) -> Database:
    """
    Yield a Database instance backed by a fresh temporary file.

    Setup:
      1. Create a named temporary file (ensures Database's path-existence
         check passes and that foreign keys + WAL mode work as in production).
      2. Apply schema.sql via executescript() (unavailable on Database directly).
      3. Apply the minimal test-world seed from tests/fixtures/seed.py.
      4. Open a Database instance and yield it.

    Teardown:
      5. Close the Database connection.
      6. Delete the temporary file.

    Function-scoped (default) so each test starts with a clean database.
    """
    from tests.fixtures.seed import apply_test_seed

    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)   # release the OS-level file descriptor; sqlite3 opens its own

    try:
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_sql)
        apply_test_seed(conn)
        conn.close()

        db = Database(path)
        yield db
        db.close()
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


# =============================================================================
# LLM and engine fixtures
# =============================================================================

@pytest.fixture
def mock_llm():
    """
    Return a MockLLMClient pre-loaded with minimal valid responses for a
    standard three-pass turn: Pass 1 → Pass 2 → Pass 3.

    Tests that need specific LLM responses should construct their own
    MockLLMClient directly rather than relying on this fixture.
    """
    from tests.fixtures.responses import PASS1_MINIMAL, PASS2_MINIMAL, PASS3_PROSE
    return MockLLMClient([
        json.dumps(PASS1_MINIMAL),   # call 0 → Pass 1 intent parsing
        json.dumps(PASS2_MINIMAL),   # call 1 → Pass 2 adjudication
        PASS3_PROSE,                  # call 2 → Pass 3 prose rendering
    ])


@pytest.fixture
def test_engine(tmp_db, mock_llm):
    """
    Return a fully initialised GameEngine wired to the test database and the
    mock LLM client.

    engine.llm.get_llm_client() is patched during __init__ so no API
    credentials are needed. After construction, engine.llm is also replaced
    directly as a belt-and-suspenders measure.

    Tests that call engine methods (e.g. _apply_outcome, _check_npc_wandering)
    should use this fixture rather than constructing GameEngine themselves.
    """
    from engine.engine import GameEngine

    with patch("engine.llm.get_llm_client", return_value=mock_llm):
        engine = GameEngine(db=tmp_db, game_id=1)

    engine.llm = mock_llm
    return engine
