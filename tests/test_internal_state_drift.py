"""
tests/test_internal_state_drift.py — Internal State Drift and Prose Surfacing Tests

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Four test classes, in ascending LLM cost order:

TestTickPassiveStatesMath (Tier 1 — no LLM)
    Unit tests for db.tick_passive_states(). Verifies the drift formula:
        new_value = clamp(value + passive_rate_per_minute * elapsed_minutes, 0.0, 1.0)
    Covers: positive rates, negative rates, sequential tick accumulation,
    upper and lower clamping, null-rate states (untouched), and zero-minute
    noop. Uses the standard test fixture DB (tmp_db / seed.py).

TestPass2InternalStateContext (Tier 1 — no LLM)
    Structural verification that build_pass2_packet() includes internal_states
    in the player profile and in NPC profiles (characters_present). Also
    verifies that post-tick values are reflected in freshly built packets,
    confirming that context.py reads live DB state at packet-build time.
    Uses the standard test fixture DB (tmp_db / seed.py).

TestPass3InternalStatePacket (Tier 1 — no LLM)
    Structural verification that build_pass3_packet() includes
    player_internal_states in the context packet and that the display_mode
    filter correctly excludes 'numeric' states. Uses a Hidden Hostel DB
    (hostel_db), which seeds hunger on The Traveller for realistic values.

TestInternalStateDriftScenario (Tier 2 — requires --llm)
    Sequential scenario tests covering:

    PC hunger surfacing:
      - Player arrives hungry (seeded hunger=0.65; set to 0.75 for the test)
      - Pass 3 weaves a hunger reminder into unrelated-action prose
      - Eating a roll reduces hunger value in the DB

    NPC spontaneous eating:
      - Wanderer's hunger state set to 0.85 and rolls placed in the Common Room
      - Player takes a neutral turn
      - Pass 2 notices the high-hunger NPC and edible food co-located, and
        autonomously has the Wanderer eat — recording npc_initiated_actions and
        emitting an internal_state_delta
      - Wanderer's hunger value in the DB decreases

    DESIGN NOTE — NPC spontaneous behaviour:
    The NPC eating test is intentionally less deterministic than pending_intent-
    driven tests. It verifies the AUTONOMOUS NPC BEHAVIOR rule added to the Pass
    2 prompt, which is the general mechanism for emergent NPC action without
    explicit pending_intent (analogous to a cat pouncing when curiosity peaks, a
    dancer stepping forward at the right social moment, etc.). If this test fails
    non-deterministically, the correct response is to investigate whether the
    Pass 2 prompt instruction is clear enough, not to add a pending_intent.

Test ordering
-------------
Methods in TestInternalStateDriftScenario run in definition order against a
shared module-scoped DB. Earlier tests are prerequisites for later ones.

Run commands
------------
    pytest tests/test_internal_state_drift.py           # Tier 1 only
    pytest tests/test_internal_state_drift.py --llm     # Tier 1 + Tier 2
"""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from engine.context import build_pass2_packet, build_pass3_packet
from engine.db import Database
from engine.engine import GameEngine
from tests.fixtures.responses import PASS1_MINIMAL

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
_SCHEMA_SQL = _REPO_ROOT / "schema" / "schema.sql"
_HOSTEL_SEED = _REPO_ROOT / "modules" / "hidden_hostel" / "seed.sql"

# Hunger cue words: any of these in the prose satisfies the surfacing assertion.
# The list covers physical sensation language (hollow, gnaw, growl, etc.) as
# well as direct state words (hungry, hunger). Pass 3 may use any of these.
_HUNGER_CUES = {
    "hunger", "hungry", "stomach", "growl", "hollow", "gnaw", "gnawing",
    "empty", "pang", "famished", "eat", "food", "roll",
}


# =============================================================================
# Shared DB-building helper
# =============================================================================

def _build_hostel_db(path: str) -> None:
    """Build a Hidden Hostel database from schema + seed at the given path."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_SCHEMA_SQL.read_text(encoding="utf-8"))
    conn.executescript(_HOSTEL_SEED.read_text(encoding="utf-8"))
    conn.close()


# =============================================================================
# Tier 1 fixture (function-scoped — independent of the Tier 2 scenario)
# =============================================================================

@pytest.fixture
def hostel_db():
    """
    Build a fresh Hidden Hostel DB for Tier 1 structural tests.
    Function-scoped so each test gets a clean state.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        _build_hostel_db(path)
        db = Database(path)
        yield db
        db.close()
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


# =============================================================================
# Tier 2 fixtures (module-scoped — shared sequential scenario)
# =============================================================================

@pytest.fixture(scope="module")
def drift_db():
    """
    Build a Hidden Hostel database for the sequential Tier 2 scenario.
    Module-scoped so state accumulates across test methods.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        _build_hostel_db(path)
        db = Database(path)
        yield db
        db.close()
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


@pytest.fixture(scope="module")
def drift_engine(drift_db):
    """
    GameEngine instance against the module-scoped drift_db.
    Requires ANTHROPIC_API_KEY in the environment.
    """
    return GameEngine(db=drift_db, game_id=1)


# =============================================================================
# Turn helpers
# =============================================================================

def take_turn(engine: GameEngine, player_input: str) -> str:
    """
    Run one complete turn: check expiry, wander, refresh player, process turn.
    Returns the prose output string.
    """
    engine._check_activity_expiry()
    engine._check_npc_wandering()
    engine._player = engine.db.get_player_character(engine.game_id)
    return engine._process_turn(player_input, involuntary_fired=[])


def get_player(engine: GameEngine) -> dict:
    """Return a fresh player record from the DB."""
    return engine.db.get_player_character(engine.game_id)


def get_hunger(db: Database, character_id: int) -> float | None:
    """Return the current hunger value for a character, or None if not set."""
    state = db.get_internal_state(character_id, "hunger")
    return state["value"] if state else None


# =============================================================================
# Tier 1: tick_passive_states() math
# =============================================================================

class TestTickPassiveStatesMath:
    """
    Tier 1 (no LLM): unit tests for db.tick_passive_states().

    Verifies the drift formula applied each turn:
        new_value = clamp(value + passive_rate_per_minute * elapsed_minutes, 0.0, 1.0)

    Uses the standard test fixture world (tmp_db from conftest.py / seed.py):
      - Hero  (char_id=1): boredom    = 0.10, passive_rate = +0.002/min
      - Guard (char_id=2): sleepiness = 0.50, passive_rate = −0.003/min

    Each method receives a function-scoped tmp_db so every test starts
    from the clean seeded values with no cross-test contamination.
    """

    def test_010_positive_rate_accumulates(self, tmp_db: Database):
        """
        A positive passive_rate_per_minute raises the state value by
        (rate × elapsed_minutes) after a single tick.

        Hero boredom: 0.10 + 0.002 × 10 min = 0.12.
        """
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=10)
        state = tmp_db.get_internal_state(1, "boredom")
        assert state is not None, "Hero boredom state should exist after tick"
        assert state["value"] == pytest.approx(0.12, abs=1e-6), (
            f"After 10 min at rate +0.002/min, boredom should be 0.12; "
            f"got {state['value']:.6f}"
        )

    def test_020_negative_rate_decays(self, tmp_db: Database):
        """
        A negative passive_rate_per_minute lowers the state value by
        abs(rate × elapsed_minutes) after a single tick.

        Guard sleepiness: 0.50 − 0.003 × 10 min = 0.47.
        """
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=10)
        state = tmp_db.get_internal_state(2, "sleepiness")
        assert state is not None, "Guard sleepiness state should exist after tick"
        assert state["value"] == pytest.approx(0.47, abs=1e-6), (
            f"After 10 min at rate −0.003/min, sleepiness should be 0.47; "
            f"got {state['value']:.6f}"
        )

    def test_030_sequential_ticks_accumulate_linearly(self, tmp_db: Database):
        """
        Two 5-minute ticks produce the same final value as one 10-minute tick.
        Drift is linear and additive across calls.

        Hero boredom: 0.10 → 0.11 (first 5 min) → 0.12 (second 5 min).
        The intermediate value is also asserted so any compounding error is
        caught at the right tick boundary.
        """
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=5)
        after_first = tmp_db.get_internal_state(1, "boredom")["value"]
        assert after_first == pytest.approx(0.10 + 0.002 * 5, abs=1e-6), (
            f"After first 5-min tick: expected 0.11, got {after_first:.6f}"
        )

        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=5)
        after_second = tmp_db.get_internal_state(1, "boredom")["value"]
        assert after_second == pytest.approx(0.12, abs=1e-6), (
            f"After second 5-min tick: expected 0.12, got {after_second:.6f}"
        )

    def test_040_value_clamped_at_maximum(self, tmp_db: Database):
        """
        A state value must never exceed 1.0, even when the unclamped result
        would. tick_passive_states() clamps every updated row to [0.0, 1.0].

        Set Hero boredom to 0.999, tick 1 min at +0.002/min → unclamped 1.001.
        Expected: 1.0.
        """
        tmp_db._execute(
            "UPDATE internal_state SET value = 0.999 "
            "WHERE character_id = 1 AND state_name = 'boredom'"
        )
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=1)
        state = tmp_db.get_internal_state(1, "boredom")
        assert state["value"] == pytest.approx(1.0, abs=1e-9), (
            f"Value should be clamped to 1.0; got {state['value']:.9f}"
        )

    def test_050_value_clamped_at_minimum(self, tmp_db: Database):
        """
        A state value must never go below 0.0, even when the unclamped result
        would be negative. tick_passive_states() clamps every updated row to
        [0.0, 1.0].

        Set Guard sleepiness to 0.001, tick 1 min at −0.003/min → unclamped −0.002.
        Expected: 0.0.
        """
        tmp_db._execute(
            "UPDATE internal_state SET value = 0.001 "
            "WHERE character_id = 2 AND state_name = 'sleepiness'"
        )
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=1)
        state = tmp_db.get_internal_state(2, "sleepiness")
        assert state["value"] == pytest.approx(0.0, abs=1e-9), (
            f"Value should be clamped to 0.0; got {state['value']:.9f}"
        )

    def test_060_null_rate_state_not_ticked(self, tmp_db: Database):
        """
        States with passive_rate_per_minute IS NULL must not be modified by
        tick_passive_states(). The tick query filters on IS NOT NULL.

        Insert a null-rate state for Hero, tick for 60 minutes, assert unchanged.
        """
        initial_value = 0.35
        tmp_db._execute(
            """INSERT INTO internal_state
               (character_id, state_name, value, passive_rate_per_minute)
               VALUES (1, 'null_rate_test', ?, NULL)""",
            (initial_value,),
        )
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=60)
        state = tmp_db.get_internal_state(1, "null_rate_test")
        assert state is not None, "Null-rate state should still exist after tick"
        assert state["value"] == pytest.approx(initial_value, abs=1e-9), (
            f"Null-rate state should be unchanged after tick; "
            f"expected {initial_value}, got {state['value']:.9f}"
        )
        # Clean up to avoid polluting other tests in this class.
        tmp_db._execute(
            "DELETE FROM internal_state "
            "WHERE character_id = 1 AND state_name = 'null_rate_test'"
        )

    def test_070_zero_elapsed_is_noop(self, tmp_db: Database):
        """
        Calling tick_passive_states() with elapsed_minutes=0 must leave all
        state values unchanged, regardless of their rate.

        A zero-minute tick can happen when Pass 2 returns elapsed_minutes=0
        for an instantaneous action. The engine must handle this safely.
        """
        boredom_before    = tmp_db.get_internal_state(1, "boredom")["value"]
        sleepiness_before = tmp_db.get_internal_state(2, "sleepiness")["value"]

        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=0)

        boredom_after    = tmp_db.get_internal_state(1, "boredom")["value"]
        sleepiness_after = tmp_db.get_internal_state(2, "sleepiness")["value"]

        assert boredom_after == pytest.approx(boredom_before, abs=1e-9), (
            "tick(0 min) must not change boredom"
        )
        assert sleepiness_after == pytest.approx(sleepiness_before, abs=1e-9), (
            "tick(0 min) must not change sleepiness"
        )


# =============================================================================
# Tier 1: Pass 2 context packet — internal state inclusion
# =============================================================================

class TestPass2InternalStateContext:
    """
    Tier 1 (no LLM): verify that build_pass2_packet() includes internal_states
    in both the player profile and in NPC profiles (characters_present).

    Pass 2 is the adjudication pass: it needs full physiological visibility so
    it can reason about NPC hunger, sleepiness, distress, etc. — and so the
    retry/validation layer can check state-influenced constraints. These tests
    confirm that the context assembly layer (context.py) wires this correctly
    without requiring any LLM call.

    Also verifies that post-tick values appear in freshly built packets,
    confirming that context.py reads live DB state at packet-build time rather
    than using a cached pre-tick snapshot.

    Uses the standard test fixture world (tmp_db from conftest.py / seed.py):
      - Hero  (char_id=1): player at location 1; boredom = 0.10
      - Guard (char_id=2): NPC at location 1;   sleepiness = 0.50
    Both characters are at the same location, so Guard appears in
    characters_present — the full-profile NPC list.
    """

    def test_010_player_profile_includes_internal_states(self, tmp_db: Database):
        """
        The player profile inside the Pass 2 packet must contain an
        'internal_states' key, with each state represented as a dict that
        includes at least a 'value' key.

        This is the Pass 2 counterpart to the Pass 3 structural test
        (TestPass3InternalStatePacket.test_010). Pass 2 adjudication must see
        the full internal state picture to reason about physiology correctly.
        """
        packet = build_pass2_packet(tmp_db, game_id=1, action_record=PASS1_MINIMAL)
        player = packet.get("player", {})
        assert "internal_states" in player, (
            "player profile in Pass 2 packet must include 'internal_states'. "
            f"Keys present: {list(player.keys())}"
        )
        states = player["internal_states"]
        assert "boredom" in states, (
            "Hero's seeded boredom state should appear in player.internal_states. "
            f"Keys present: {list(states.keys())}"
        )
        # The state entry must be a dict with at least a 'value' key.
        assert "value" in states["boredom"], (
            "Each entry in internal_states must include a 'value' key. "
            f"boredom entry: {states['boredom']}"
        )
        assert states["boredom"]["value"] == pytest.approx(0.10, abs=1e-6), (
            f"Hero boredom is seeded at 0.10; got {states['boredom']['value']:.6f}"
        )

    def test_020_npc_internal_states_in_characters_present(self, tmp_db: Database):
        """
        NPCs at the player's location appear in characters_present with full
        profiles. Their profiles must include 'internal_states' so Pass 2 can
        reason about NPC physiology (a hungry NPC eating opportunistically, a
        sleepy character disengaging, etc.).

        Guard (char_id=2) is seeded at location 1 with sleepiness=0.50.
        He should appear in characters_present with that state visible.
        """
        packet = build_pass2_packet(tmp_db, game_id=1, action_record=PASS1_MINIMAL)
        chars_present = packet.get("characters_present", [])
        guard_profile = next(
            (c for c in chars_present if c.get("id") == 2), None
        )
        assert guard_profile is not None, (
            "Guard (char_id=2) should appear in characters_present — he is "
            "seeded at location 1, the same location as the player character."
        )
        assert "internal_states" in guard_profile, (
            "Guard's Pass 2 profile must include 'internal_states'. "
            f"Keys present: {list(guard_profile.keys())}"
        )
        guard_states = guard_profile["internal_states"]
        assert "sleepiness" in guard_states, (
            "Guard's seeded sleepiness state should appear in his profile. "
            f"Keys present: {list(guard_states.keys())}"
        )
        assert guard_states["sleepiness"]["value"] == pytest.approx(0.50, abs=1e-6), (
            f"Guard sleepiness is seeded at 0.50; got {guard_states['sleepiness']['value']:.6f}"
        )

    def test_030_post_tick_values_reflected_in_packet(self, tmp_db: Database):
        """
        After tick_passive_states() advances the game clock's worth of drift,
        a freshly assembled Pass 2 packet must contain the updated values —
        not the pre-tick seed values stored at startup.

        This is the integration bridge between the tick math layer and the
        context assembly layer. It fails if context.py caches state at
        import time or at DB-open time rather than reading on each call.

        Hero boredom after 50 minutes: 0.10 + 0.002 × 50 = 0.20.
        """
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=50)
        expected = pytest.approx(0.10 + 0.002 * 50, abs=1e-6)  # 0.20

        packet = build_pass2_packet(tmp_db, game_id=1, action_record=PASS1_MINIMAL)
        player_states = packet["player"]["internal_states"]
        assert "boredom" in player_states, (
            "boredom must still be present in player.internal_states after tick"
        )
        actual = player_states["boredom"]["value"]
        assert actual == expected, (
            f"After 50-min tick at rate +0.002/min, boredom should be 0.20; "
            f"got {actual:.6f}. The packet must read live DB values, not a "
            "pre-tick snapshot."
        )


# =============================================================================
# Tier 1: Pass 3 packet structure
# =============================================================================

class TestPass3InternalStatePacket:
    """
    Tier 1 (no LLM): verify that build_pass3_packet() includes
    player_internal_states in the returned packet.

    The Hidden Hostel seeds hunger=0.65 for The Traveller (char_id=1) with
    display_mode='prose'. These tests confirm the context assembly layer
    exposes this to Pass 3 as required for prose surfacing.
    """

    def test_010_player_internal_states_key_present(self, hostel_db: Database):
        """
        build_pass3_packet() must include a 'player_internal_states' key.

        This is the structural contract introduced to support hunger (and
        other internal state) surfacing in Pass 3 prose. Without this key,
        Pass 3 has no visibility into player physiological state and cannot
        weave hunger or sleepiness cues into the narrative.
        """
        # Minimal dummy outcome — sufficient to build the packet without an
        # actual LLM adjudication step.
        dummy_outcome = {
            "outcome_type": "ambient",
            "narrative_beat": "Nothing happens.",
            "elapsed_minutes": 1,
            "attitude_deltas": [],
            "internal_state_deltas": [],
            "emotional_state_updates": [],
            "location_change": [],
            "item_changes": [],
            "item_transfers": [],
            "item_instantiations": [],
            "pending_intent_updates": [],
            "activity_updates": [],
            "npc_initiated_actions": [],
            "new_characters": [],
            "faction_reputation_changes": [],
            "player_character_update": None,
            "narrative_point_delta": 0,
            "adjudication_notes": "",
        }
        packet = build_pass3_packet(hostel_db, game_id=1, outcome=dummy_outcome)
        assert "player_internal_states" in packet, (
            "build_pass3_packet() must include 'player_internal_states' in the "
            "returned packet so Pass 3 can surface physiological state in prose. "
            f"Keys present: {list(packet.keys())}"
        )

    def test_020_hunger_in_player_internal_states(self, hostel_db: Database):
        """
        The Traveller's seeded hunger state (display_mode='prose') must appear
        in player_internal_states with a value close to the seeded 0.65.

        This confirms that (a) the DB query retrieves the correct record and
        (b) the display_mode filter correctly includes 'prose' states.
        """
        dummy_outcome = {
            "outcome_type": "ambient",
            "narrative_beat": "Nothing happens.",
            "elapsed_minutes": 1,
            "attitude_deltas": [],
            "internal_state_deltas": [],
            "emotional_state_updates": [],
            "location_change": [],
            "item_changes": [],
            "item_transfers": [],
            "item_instantiations": [],
            "pending_intent_updates": [],
            "activity_updates": [],
            "npc_initiated_actions": [],
            "new_characters": [],
            "faction_reputation_changes": [],
            "player_character_update": None,
            "narrative_point_delta": 0,
            "adjudication_notes": "",
        }
        packet = build_pass3_packet(hostel_db, game_id=1, outcome=dummy_outcome)
        states = packet.get("player_internal_states", {})
        assert "hunger" in states, (
            "Traveller's seeded hunger state (display_mode='prose') should appear "
            f"in player_internal_states. Got: {states}"
        )
        assert 0.60 <= states["hunger"] <= 0.70, (
            f"Seeded hunger value is 0.65; got {states['hunger']:.3f}. "
            "The value should be close to the seed value (passive drift may "
            "accumulate slightly if the clock has advanced, but not much)."
        )

    def test_030_display_mode_filter_excludes_numeric(self, hostel_db: Database):
        """
        States with display_mode='numeric' must NOT appear in
        player_internal_states. This test inserts a numeric-mode state directly
        and verifies the filter works correctly.

        'numeric' display mode is for dev/testing contexts; it must not appear
        in player-facing prose packets.
        """
        # Insert a numeric-mode state for the Traveller directly.
        hostel_db._execute(
            """INSERT INTO internal_state
               (character_id, state_name, value, display_mode)
               VALUES (1, 'test_numeric_state', 0.80, 'numeric')
               ON CONFLICT(character_id, state_name)
               DO UPDATE SET value = excluded.value,
                             display_mode = excluded.display_mode""",
        )
        dummy_outcome = {
            "outcome_type": "ambient",
            "narrative_beat": "Nothing happens.",
            "elapsed_minutes": 1,
            "attitude_deltas": [],
            "internal_state_deltas": [],
            "emotional_state_updates": [],
            "location_change": [],
            "item_changes": [],
            "item_transfers": [],
            "item_instantiations": [],
            "pending_intent_updates": [],
            "activity_updates": [],
            "npc_initiated_actions": [],
            "new_characters": [],
            "faction_reputation_changes": [],
            "player_character_update": None,
            "narrative_point_delta": 0,
            "adjudication_notes": "",
        }
        packet = build_pass3_packet(hostel_db, game_id=1, outcome=dummy_outcome)
        states = packet.get("player_internal_states", {})
        assert "test_numeric_state" not in states, (
            "States with display_mode='numeric' must be excluded from "
            f"player_internal_states. Got: {states}"
        )
        # 'hunger' (prose mode) should still be present.
        assert "hunger" in states, (
            "Prose-mode states must still be present after the numeric state "
            "is filtered out."
        )

        # Clean up the test state to avoid polluting other tests.
        hostel_db._execute(
            "DELETE FROM internal_state WHERE character_id=1 AND state_name='test_numeric_state'"
        )


# =============================================================================
# Tier 2: Full scenario (player hunger + NPC spontaneous eating)
# =============================================================================

@pytest.mark.llm
class TestInternalStateDriftScenario:
    """
    Sequential Tier 2 scenario. Tests run in definition order and share the
    module-scoped drift_db / drift_engine. Do not run methods individually.

    Scenario outline:
      010  Self-define and enter hostel → player at Common Room (1)
      020  Set player hunger to 0.75; take an unrelated turn;
           assert prose contains a hunger cue
      030  Go to kitchen; eat a roll directly from the tray;
           assert player hunger value decreases
      040  Bring tray of rolls to Common Room; assert rolls visible at loc 1
      050  Set Wanderer hunger to 0.85; take a neutral player turn;
           assert Wanderer hunger decreases (spontaneous NPC eating)
    """

    # ------------------------------------------------------------------
    # Checkpoint 010: Self-define and enter the hostel
    # ------------------------------------------------------------------

    def test_010_self_define_and_enter(
        self, drift_db: Database, drift_engine: GameEngine
    ):
        """
        Abbreviated entrance flow: one self-definition turn sets
        player.description, then the door admits the player to the Common Room.

        This is the minimal prerequisite for the hunger and NPC tests that follow.
        The door's pending_intent blocks entry until player.description is set;
        self-definition satisfies this condition.
        """
        # Self-define: a single clear turn should set player.description and
        # satisfy the Blue Door's entry precondition.
        take_turn(
            drift_engine,
            "I am a traveller, worn from a long road — dark hair, a practical "
            "coat, a heavy pack. I look at myself in the mirror.",
        )

        player_after_def = get_player(drift_engine)
        assert player_after_def["description"] is not None, (
            "player.description should be set after self-definition turn"
        )

        # Now enter the hostel.
        prose = take_turn(
            drift_engine,
            "push open the door and step into the common room",
        )
        assert prose, "Entry turn should return non-empty prose"

        player = get_player(drift_engine)
        assert player["current_location_id"] == 1, (
            f"Player should be in Common Room (1) after entering; "
            f"got location {player['current_location_id']}\n"
            f"Prose: {prose[:200]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 020: Hunger surfaces in unrelated-action prose
    # ------------------------------------------------------------------

    def test_020_hunger_surfaces_in_prose(
        self, drift_db: Database, drift_engine: GameEngine
    ):
        """
        When the player's hunger is clearly above the prose-surfacing threshold
        (set here to 0.75), Pass 3 should weave a brief physical hunger
        reminder into the prose even when the player's action has nothing to
        do with food.

        We set hunger to 0.75 directly (seeded value is 0.65; this ensures
        we're above the threshold reliably) then take a neutral turn.

        The assertion checks for any of the _HUNGER_CUES word list in the
        prose — "stomach", "growl", "hollow", "hungry", etc. Pass 3 has
        latitude in phrasing; the test verifies presence, not exact wording.
        """
        # Set player hunger to 0.75 (clearly above the 0.60 threshold).
        drift_db.update_internal_state(
            character_id=1,
            state_name="hunger",
            new_value=0.75,
        )

        # Confirm the DB write before calling the LLM.
        assert get_hunger(drift_db, 1) == pytest.approx(0.75), (
            "DB write of hunger=0.75 should persist before turn"
        )

        # Neutral action: examining the fire has nothing to do with eating.
        prose = take_turn(
            drift_engine,
            "I settle into one of the chairs by the hearth and watch the fire",
        )
        assert prose, "Turn should return non-empty prose"

        prose_lower = prose.lower()
        found_cues = [cue for cue in _HUNGER_CUES if cue in prose_lower]
        assert found_cues, (
            "Pass 3 should weave a hunger reminder into prose when "
            "player_internal_states contains hunger ≥ 0.60 and the action "
            "is unrelated to eating.\n"
            f"Expected any of: {sorted(_HUNGER_CUES)}\n"
            f"Prose: {prose}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 030: Eating reduces player hunger
    # ------------------------------------------------------------------

    def test_030_eating_reduces_player_hunger(
        self, drift_db: Database, drift_engine: GameEngine
    ):
        """
        When the player eats, Pass 2 should emit an internal_state_delta that
        reduces hunger. The engine applies this delta via apply_internal_state_delta
        and the DB value should be lower after the turn than before.

        The player goes to the kitchen and eats a roll directly from the tray.
        The tray is seeded at Kitchen (loc_id=2) and the rolls have
        properties={"edible": true}.

        We do not assert a specific delta — the amount Pass 2 assigns is
        module-appropriate (a single roll satisfying travel hunger partially).
        We assert only that the value decreased.
        """
        hunger_before = get_hunger(drift_db, 1)
        assert hunger_before is not None, "Player should have a hunger state"

        # Move to kitchen.
        take_turn(drift_engine, "go to the kitchen")

        # Eat a roll from the tray.
        prose = take_turn(
            drift_engine,
            "take a roll from the tray and eat it",
        )
        assert prose, "Eating turn should return non-empty prose"

        hunger_after = get_hunger(drift_db, 1)
        assert hunger_after is not None, "Hunger state should still exist after eating"
        assert hunger_after < hunger_before, (
            "Eating a roll should reduce player hunger via internal_state_delta.\n"
            f"Before: {hunger_before:.3f}, After: {hunger_after:.3f}\n"
            f"Prose: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 040: Bring rolls to the Common Room
    # ------------------------------------------------------------------

    def test_040_bring_rolls_to_common_room(
        self, drift_db: Database, drift_engine: GameEngine
    ):
        """
        For the NPC spontaneous eating test (050), edible food must be
        co-located with the Wanderer in the Common Room.

        The player carries the tray of hot rolls from the kitchen to the
        Common Room. We assert that at least one roll item ends up at
        location 1 (either the tray itself or individual rolls).

        This also advances the scenario naturally: arriving with food is a
        plausible iyashikei beat and primes the Common Room for the NPC test.
        """
        # We are currently in the kitchen from test_030. Carry the tray out.
        prose = take_turn(
            drift_engine,
            "take the tray of rolls and carry it to the common room",
        )
        assert prose, "Carrying tray should return prose"

        player = get_player(drift_engine)
        assert player["current_location_id"] == 1, (
            f"Player should be in Common Room after carrying tray; "
            f"got location {player['current_location_id']}\n"
            f"Prose: {prose[:200]}"
        )

        # Check that edible food is now accessible in the Common Room:
        # either the tray itself is at loc 1, or rolls are in the player's
        # inventory (player is at loc 1), or rolls are on a surface there.
        rolls_at_loc = drift_db._rows(
            """SELECT id, name, loc_id, char_id FROM item
               WHERE game_id = 1
               AND (loc_id = 1 OR char_id = 1)
               AND (name LIKE '%roll%' OR name LIKE '%tray%')""",
        )
        assert rolls_at_loc, (
            "After carrying the tray to the Common Room, at least one roll "
            "or the tray itself should be at location 1 or in the player's "
            f"inventory.\nProse: {prose[:300]}"
        )

    # ------------------------------------------------------------------
    # Checkpoint 050: NPC spontaneous eating
    # ------------------------------------------------------------------

    def test_050_npc_spontaneous_eating(
        self, drift_db: Database, drift_engine: GameEngine
    ):
        """
        When an NPC has a high internal state (hunger=0.85) AND there is
        an item at their location that could satisfy it (edible rolls), Pass 2
        should autonomously have the NPC act on the state — eating a roll,
        recording the action in npc_initiated_actions, and emitting an
        internal_state_delta.

        The Wanderer (char_id=3) is in the Common Room (his wander_range
        includes [1, 2]). We set his hunger to 0.85 and take a neutral player
        turn. Pass 2 should notice the high-hunger NPC and the available food
        and have him eat without requiring a pending_intent.

        DESIGN NOTE — inherent non-determinism:
        This test is less deterministic than pending_intent-driven tests by
        design. pending_intent is a guaranteed obligation; autonomous behavior
        from internal state is probabilistic — it depends on Pass 2's
        assessment of whether the state + context warrants action. This is the
        intended distinction: pending_intent for narrative-critical beats,
        autonomous behavior for background realism.

        If this test fails non-deterministically, the appropriate response is
        to review the AUTONOMOUS NPC BEHAVIOR prompt instruction and the Wanderer's
        OCEAN profile — not to add a pending_intent. The Wanderer's high
        extraversion (0.82) and agreeableness (0.72) should make eating in
        company a natural response to hunger.
        """
        # Ensure Wanderer is in the Common Room for this turn.
        # (His wander_range is [1, 2]; he may have wandered during prior turns.)
        wanderer = drift_db.get_character(3)
        if wanderer["current_location_id"] != 1:
            drift_db._execute(
                "UPDATE character SET current_location_id = 1 WHERE id = 3"
            )

        # Seed Wanderer hunger at 0.85 — clearly above the autonomous-action
        # threshold (0.75). update_internal_state uses UPSERT, so this creates
        # the row if the Wanderer has no prior hunger state (not seeded by default).
        drift_db.update_internal_state(
            character_id=3,
            state_name="hunger",
            new_value=0.85,
        )

        wanderer_hunger_before = get_hunger(drift_db, 3)
        assert wanderer_hunger_before == pytest.approx(0.85), (
            "Wanderer hunger should be 0.85 before the test turn"
        )

        # Neutral player action: not about food, not directed at the Wanderer.
        # This leaves Pass 2 free to adjudicate background NPC behaviour.
        prose = take_turn(
            drift_engine,
            "I sit quietly by the fire and rest, watching the room",
        )
        assert prose, "Turn should return non-empty prose"

        wanderer_hunger_after = get_hunger(drift_db, 3)
        assert wanderer_hunger_after is not None, (
            "Wanderer hunger state should still exist after the turn"
        )
        assert wanderer_hunger_after < wanderer_hunger_before, (
            "When the Wanderer has hunger=0.85 and edible food is present at "
            "his location, Pass 2 should autonomously have him eat — recording "
            "the action in npc_initiated_actions and emitting an "
            "internal_state_delta that reduces his hunger.\n"
            f"Before: {wanderer_hunger_before:.3f}, "
            f"After: {wanderer_hunger_after:.3f}\n"
            f"Prose: {prose[:400]}\n\n"
            "If this fails non-deterministically, review the AUTONOMOUS NPC "
            "BEHAVIOR rule in PASS2_PROMPT_TEMPLATE and ensure the Wanderer's "
            "profile (high extraversion 0.82, agreeableness 0.72) is visible "
            "in the Pass 2 context packet."
        )
