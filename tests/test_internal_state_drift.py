"""
tests/test_internal_state_drift.py — Internal State Drift and Prose Surfacing Tests

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Two test classes:

TestPass3InternalStatePacket (Tier 1 — no LLM)
    Structural verification that build_pass3_packet() includes
    player_internal_states in the context packet. These tests exercise
    the context.py change and require no LLM calls.

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

from engine.context import build_pass3_packet
from engine.db import Database
from engine.engine import GameEngine

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
