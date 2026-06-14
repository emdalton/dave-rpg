"""
tests/test_hidden_hostel.py — Hidden Hostel Module Integration Tests (Tier 1)

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Tier 1 (no LLM) tests that validate engine mechanics against the Hidden Hostel
test world module. The Hidden Hostel is a five-location liminal fantasy inn
designed to exercise every implemented engine feature in a single module.

Why a separate module for tests?
---------------------------------
The default tmp_db fixture uses a minimal two-location test world that is
deliberately sparse. The Hidden Hostel provides:
  - A staircase connection (connection_type='stairs'), which has caused
    pathfinding issues in practice.
  - An impassable connection (Room B, id=5), to test the block path.
  - Multiple wander suppression conditions in a single world:
      * The Scholar (id=4): pending_intent set → Suppression 1
      * Marta (id=2): active timed activity → Suppression 3
      * Gin-chan (id=6): sleepiness >= 0.72 → Suppression 2
  - Activity expiry: Marta's meal activity (started=1140, duration=90)
    expires at clock time 1230. The Old Soldier's activity (started=1170,
    duration=60) expires at 1230.
  - Hidden motivation access control: The Scholar (id=4) has hidden_motivation
    set and access_hidden_motivation=0 — should not appear in Pass 1 context.
  - Faction membership: the Traveller (id=1) has rep in hosts_of_the_hostel.
  - Passive state drift across three characters.
  - Negative attitude: The Old Soldier (id=5) → Traveller (id=1) at -0.30.
  - A pre-seeded location_detail for the Common Room, testing the lazy-gen
    retrieval path (detail exists; engine should not re-generate it).

Feature coverage map (see seed.sql header for full list):
  §A  Staircase connection traversal (Common Room → Upper Corridor)
  §B  Impassable connection (Upper Corridor → Room B)
  §C  Wander suppression: pending_intent (Scholar)
  §D  Wander suppression: active timed activity (Marta)
  §E  Wander suppression: sleepiness threshold (Gin-chan)
  §F  Activity expiry: non-renewable activity clears when time passes
  §G  Activity expiry: renewable activity does NOT auto-clear
  §H  Hidden motivation access control (Scholar, access_hidden_motivation=0)
  §I  Faction reputation present in DB for the Traveller
  §J  Passive state drift: curiosity, fatigue, sleepiness
  §K  Negative attitude reads correctly (Old Soldier → Traveller)
  §L  Attitude delta application and clamping
  §M  Pre-seeded location_detail retrieval (Common Room)

Test world character IDs (from seed.sql):
    1  The Traveller  — player, Common Room (1)
    2  Marta          — npc_active, Kitchen (2); active meal prep activity
    3  The Wanderer   — npc_active, Common Room (1); wander_prob=0.75, range=[1,2,3]
    4  The Scholar    — npc_active, Room A (4); pending_intent set; hidden_motivation
    5  The Old Soldier— npc_active, Upper Corridor (3); active sharpening activity
    6  Gin-chan       — npc_active, Common Room (1); sleepiness=0.72

Location IDs:
    1  Common Room   (public)
    2  Kitchen       (semi_private)
    3  Upper Corridor (semi_private)
    4  Room A        (private)
    5  Room B        (private, locked/impassable from 3)

Connection IDs (location_a_id < location_b_id):
    1↔2  door,   passable
    1↔3  stairs, passable
    3↔4  door,   passable
    3↔5  door,   impassable (locked)

Game instance: id=1, start_time=1200 (8:00 PM)
"""

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from engine.db import Database
from engine import config

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).parent.parent
_SCHEMA_SQL_PATH = _REPO_ROOT / "schema" / "schema.sql"
_HOSTEL_SEED_PATH = _REPO_ROOT / "modules" / "hidden_hostel" / "seed.sql"


# =============================================================================
# Fixture: tmp_hostel_db
# =============================================================================

@pytest.fixture(scope="session")
def hostel_schema_sql() -> str:
    """
    Return the contents of schema/schema.sql as a string.
    Session-scoped: read once and reused across all Hidden Hostel tests.
    """
    return _SCHEMA_SQL_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def hostel_seed_sql() -> str:
    """
    Return the contents of modules/hidden_hostel/seed.sql as a string.
    Session-scoped: read once and reused across all Hidden Hostel tests.
    """
    return _HOSTEL_SEED_PATH.read_text(encoding="utf-8")


@pytest.fixture
def tmp_hostel_db(hostel_schema_sql, hostel_seed_sql) -> Database:
    """
    Yield a Database instance loaded with the Hidden Hostel module.

    Setup:
      1. Create a named temporary file (sqlite3 foreign-key mode requires a
         path, not :memory:, so that WAL mode and FK enforcement work as in
         production).
      2. Apply schema.sql via executescript().
      3. Apply modules/hidden_hostel/seed.sql via executescript().
      4. Open a Database instance and yield it.

    Teardown:
      5. Close the Database connection.
      6. Delete the temporary file.

    Function-scoped (default) so each test starts with a clean database that
    exactly matches the seeded state — no cross-test mutation.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        conn = sqlite3.connect(path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(hostel_schema_sql)
        conn.executescript(hostel_seed_sql)
        conn.close()

        db = Database(path)
        yield db
        db.close()
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


@pytest.fixture
def hostel_engine(tmp_hostel_db):
    """
    Return a GameEngine wired to the Hidden Hostel database with a mock LLM.

    Patches engine.llm.get_llm_client() so no API credentials are required.
    The mock LLM is configured with minimal valid three-pass responses so that
    any test that triggers the full turn loop does not error on LLM calls.

    Tests that only call engine helpers (_check_npc_wandering, etc.) and not
    the full loop can use this fixture without worrying about mock response
    content.
    """
    from tests.conftest import MockLLMClient
    from engine.engine import GameEngine

    # Minimal valid responses for a single three-pass turn.
    mock_pass1 = json.dumps({
        "action_type": "wait",
        "verb": "wait",
        "target": None,
        "target_id": None,
        "location_id": 1,
        "detail": None,
        "raw_input": "wait",
    })
    mock_pass2 = json.dumps({
        "outcome_type": "ambient",
        "narrative_beat": "Nothing happens.",
        "elapsed_minutes": 1,
        "attitude_deltas": [],
        "internal_state_deltas": [],
        "emotional_state_updates": [],
        "location_change": [],
        "item_changes": [],
        "new_location_details": [],
        "faction_reputation_changes": [],
        "pending_intent_updates": [],
        "activity_updates": [],
        "npc_initiated_actions": [],
        "new_characters": [],
        "narrative_point_delta": 0,
        "adjudication_notes": "Test stub.",
    })
    mock_pass3 = "You wait."

    mock_llm = MockLLMClient([mock_pass1, mock_pass2, mock_pass3])

    with patch("engine.llm.get_llm_client", return_value=mock_llm):
        engine = GameEngine(db=tmp_hostel_db, game_id=1)
    engine.llm = mock_llm
    return engine


# =============================================================================
# §A — Staircase connection: pathfinding traversal
# =============================================================================

class TestStaircaseConnection:
    """
    The Common Room (1) ↔ Upper Corridor (3) connection has connection_type='stairs'.
    This configuration has caused pathfinding issues in practice (session 15
    regression). These tests confirm the staircase is traversable and that the
    engine handles it correctly during BFS path resolution.
    """

    def test_staircase_connection_is_passable(self, tmp_hostel_db: Database):
        """The staircase connection between rooms 1 and 3 must be passable."""
        connections = tmp_hostel_db.get_location_connections(location_id=1)
        neighbour_ids = {conn["neighbour_id"] for conn in connections}
        assert 3 in neighbour_ids, (
            "Upper Corridor (3) should be reachable from Common Room (1) via stairs"
        )

    def test_staircase_connection_type(self, tmp_hostel_db: Database):
        """Confirm the 1↔3 connection is typed as 'stairs'."""
        connections = tmp_hostel_db.get_location_connections(location_id=1)
        stair_conn = next(
            (c for c in connections if c["neighbour_id"] == 3), None
        )
        assert stair_conn is not None, "Staircase connection not found"
        assert stair_conn.get("connection_type") == "stairs", (
            f"Expected connection_type='stairs', got {stair_conn.get('connection_type')!r}"
        )

    def test_pathfinding_traverses_staircase(self, hostel_engine):
        """
        BFS pathfinding from Common Room (1) to Upper Corridor (3) must succeed.

        _resolve_multistep_move() is the BFS layer. The Traveller starts at the
        Common Room; the Upper Corridor is one staircase step away. The test
        marks the destination as visited first (bypassing the quick-move guard)
        then calls the pathfinder directly.
        """
        player_id = hostel_engine._player["id"]  # Traveller, id=1
        # Mark Upper Corridor as visited so the quick-move guard doesn't block.
        hostel_engine.db.mark_location_visited(player_id, 3)

        result = hostel_engine._resolve_multistep_move(target_location_id=3)
        assert result["reachable"] is True, (
            f"Pathfinding to Upper Corridor (3) via stairs should succeed; "
            f"got reachable=False: {result.get('no_path_reason')}"
        )
        assert result["effective_destination_id"] == 3

    def test_pathfinding_adjacent_staircase_skips_visited_guard(self, hostel_engine):
        """
        Adjacent moves bypass the visited-location guard even without a visit record.

        The Traveller has not visited the Upper Corridor yet at session start.
        Because it is directly adjacent (one step), _resolve_multistep_move
        should succeed regardless.
        """
        result = hostel_engine._resolve_multistep_move(target_location_id=3)
        assert result["reachable"] is True, (
            "Adjacent staircase move should succeed even without a prior visit"
        )


# =============================================================================
# §B — Impassable connection: Room B (3↔5, is_passable=0)
# =============================================================================

class TestImpassableConnection:
    """
    Room B (5) is connected to Upper Corridor (3) by a locked door
    (is_passable=0). The engine must reject any attempt to path through it.
    """

    def test_room_b_not_reachable_from_upper_corridor(self, tmp_hostel_db: Database):
        """Room B must not appear in the passable neighbours of Upper Corridor."""
        connections = tmp_hostel_db.get_location_connections(location_id=3)
        neighbour_ids = {conn["neighbour_id"] for conn in connections}
        assert 5 not in neighbour_ids, (
            "Room B (5) should not appear as a passable neighbour of Upper Corridor (3)"
        )

    def test_pathfinding_blocked_to_room_b(self, hostel_engine):
        """
        BFS pathfinding from Common Room to Room B must fail — no passable route.

        Even after visiting all intermediate rooms, Room B is behind an impassable
        connection and should return reachable=False.
        """
        player_id = hostel_engine._player["id"]
        # Give the Traveller a visit record for Upper Corridor and Room B
        # (simulating a previous session where they somehow reached the corridor).
        hostel_engine.db.mark_location_visited(player_id, 3)
        hostel_engine.db.mark_location_visited(player_id, 5)

        result = hostel_engine._resolve_multistep_move(target_location_id=5)
        assert result["reachable"] is False, (
            "Pathfinding to Room B (behind impassable connection) should fail"
        )

    def test_impassable_connection_exists_in_db(self, tmp_hostel_db: Database):
        """
        The 3↔5 connection exists in the DB but is_passable=0.

        get_location_connections() filters to passable only, so the connection
        should not appear there. Confirm via a direct DB query that the row
        exists with is_passable=0.
        """
        row = tmp_hostel_db._row(
            "SELECT is_passable FROM location_connection "
            "WHERE (location_a_id=3 AND location_b_id=5) "
            "   OR (location_a_id=5 AND location_b_id=3)"
        )
        assert row is not None, "The 3↔5 connection row should exist in location_connection"
        assert row["is_passable"] == 0, (
            f"Expected is_passable=0 for the locked Room B connection, got {row['is_passable']}"
        )


# =============================================================================
# §C — Wander suppression: pending_intent (The Scholar)
# =============================================================================

class TestWanderSuppressionPendingIntent:
    """
    The Scholar (id=4) has pending_intent set in the seed ('needs to respond
    to the Traveller's question'). Suppression 1 in _check_npc_wandering()
    should prevent the Scholar from wandering even with a non-zero wander
    probability.

    These tests call _check_npc_wandering() directly rather than going through
    the full turn loop, so they are deterministic without mocking random().
    """

    def test_scholar_has_pending_intent(self, tmp_hostel_db: Database):
        """Confirm The Scholar has a non-null pending_intent in the seed."""
        scholar = tmp_hostel_db.get_character(4)
        assert scholar is not None
        assert scholar.get("pending_intent"), (
            "The Scholar should have pending_intent set in the seed"
        )

    def test_scholar_not_moved_by_wander(self, hostel_engine):
        """
        _check_npc_wandering() must not move The Scholar.

        We run the wander check 20 times — even with a high wander probability,
        the Scholar's pending_intent should suppress every roll. If the Scholar
        moves even once, suppression is broken.
        """
        original_loc = hostel_engine.db.get_character(4)["current_location_id"]
        for _ in range(20):
            hostel_engine._check_npc_wandering()
        final_loc = hostel_engine.db.get_character(4)["current_location_id"]
        assert final_loc == original_loc, (
            f"The Scholar moved from loc {original_loc} to {final_loc} "
            f"despite having pending_intent — Suppression 1 is broken"
        )


# =============================================================================
# §D — Wander suppression: active timed activity (Marta)
# =============================================================================

class TestWanderSuppressionActivity:
    """
    Marta (id=2) is mid-activity (preparing a meal, started=1140, duration=90,
    confidence=0.72, renewable=0). The game clock starts at 1200. The activity
    expires at 1140+90=1230, which is 30 minutes in the future. Suppression 3
    should hold until the clock reaches 1230.
    """

    def test_marta_has_active_activity(self, tmp_hostel_db: Database):
        """Confirm Marta has current_activity set at seed time."""
        marta = tmp_hostel_db.get_character(2)
        assert marta is not None
        assert marta.get("current_activity"), (
            "Marta should have current_activity set in the seed"
        )
        assert marta.get("activity_estimated_duration") == 90
        assert marta.get("activity_renewable") == 0

    def test_marta_not_moved_while_activity_active(self, hostel_engine):
        """
        _check_npc_wandering() must not move Marta while her activity is active.

        Clock is at 1200; activity expires at 1230. Marta should be suppressed.
        Running 20 iterations confirms suppression holds deterministically.
        """
        original_loc = hostel_engine.db.get_character(2)["current_location_id"]
        for _ in range(20):
            hostel_engine._check_npc_wandering()
        final_loc = hostel_engine.db.get_character(2)["current_location_id"]
        assert final_loc == original_loc, (
            f"Marta moved from loc {original_loc} to {final_loc} while "
            f"her meal activity was still active — Suppression 3 is broken"
        )


# =============================================================================
# §E — Wander suppression: sleepiness threshold (Gin-chan)
# =============================================================================

class TestWanderSuppressionSleepiness:
    """
    Gin-chan (id=6) has sleepiness=0.72 at seed time. The wander suppression
    threshold is config.WANDER_SLEEPINESS_THRESHOLD (default 0.60). Gin-chan
    is above the threshold and should be suppressed.
    """

    def test_ginchan_sleepiness_above_threshold(self, tmp_hostel_db: Database):
        """Confirm Gin-chan's seeded sleepiness exceeds the suppression threshold."""
        state = tmp_hostel_db.get_internal_state(
            character_id=6, state_name="sleepiness"
        )
        assert state is not None, "Gin-chan should have a sleepiness internal_state"
        assert state["value"] >= config.WANDER_SLEEPINESS_THRESHOLD, (
            f"Gin-chan sleepiness={state['value']:.3f} should be >= "
            f"WANDER_SLEEPINESS_THRESHOLD={config.WANDER_SLEEPINESS_THRESHOLD}"
        )

    def test_ginchan_not_moved_when_sleepy(self, hostel_engine):
        """
        _check_npc_wandering() must not move Gin-chan when sleepiness >= threshold.

        Gin-chan is in the Common Room (1) with wander_range=[1,2,3]. The wander
        roll fires, but Suppression 2 should prevent any move.
        """
        original_loc = hostel_engine.db.get_character(6)["current_location_id"]
        for _ in range(20):
            hostel_engine._check_npc_wandering()
        final_loc = hostel_engine.db.get_character(6)["current_location_id"]
        assert final_loc == original_loc, (
            f"Gin-chan moved from loc {original_loc} to {final_loc} "
            f"despite sleepiness above threshold — Suppression 2 is broken"
        )

    def test_ginchan_can_wander_when_not_sleepy(self, hostel_engine):
        """
        When Gin-chan's sleepiness is forced below threshold, wandering is permitted.

        This test proves Suppression 2 is the reason Gin-chan stays put — not
        some other condition — by confirming movement becomes possible once the
        sleepiness value drops below the threshold. We set sleepiness to 0.10
        and run 50 iterations; with wander_probability > 0, at least one move
        should occur.
        """
        hostel_engine.db.update_internal_state(
            character_id=6, state_name="sleepiness", new_value=0.10
        )
        # Also ensure Gin-chan has no other suppression active (no pending_intent,
        # no current_activity — confirmed by seed, but set explicitly for clarity).
        hostel_engine.db._execute(
            "UPDATE character SET pending_intent=NULL WHERE id=6"
        )
        original_loc = hostel_engine.db.get_character(6)["current_location_id"]

        moved = False
        for _ in range(50):
            hostel_engine._check_npc_wandering()
            new_loc = hostel_engine.db.get_character(6)["current_location_id"]
            if new_loc != original_loc:
                moved = True
                break

        assert moved, (
            "Gin-chan should be able to wander once sleepiness drops below the "
            "threshold (50 attempts, non-zero wander_probability)"
        )


# =============================================================================
# §F — Activity expiry: non-renewable activity auto-clears
# =============================================================================

class TestActivityExpiry:
    """
    _check_activity_expiry() clears current_activity for NPCs whose timed,
    non-renewable, high-confidence activity has expired.

    Marta: started=1140, duration=90, confidence=0.72, renewable=0.
    Expires at 1140+90=1230. Clock at seed start=1200.
    The Old Soldier: started=1170, duration=60, confidence=0.80, renewable=0.
    Expires at 1170+60=1230.

    ACTIVITY_AUTO_CLEAR_CONFIDENCE default=0.60. Both activities have
    confidence above this threshold.
    """

    def test_activity_does_not_expire_before_time(self, hostel_engine):
        """
        At clock=1200 (30 minutes before Marta's expiry), _check_activity_expiry
        must not clear Marta's activity.
        """
        hostel_engine._check_activity_expiry()
        marta = hostel_engine.db.get_character(2)
        assert marta.get("current_activity") is not None, (
            "Marta's activity should still be active at clock=1200 "
            "(expires at 1230)"
        )

    def test_activity_expires_after_duration(self, hostel_engine):
        """
        After advancing the clock past expiry, _check_activity_expiry must
        clear Marta's current_activity.
        """
        instance = hostel_engine.db.get_active_instance(game_id=1)
        # Advance clock past expiry: 1230 + 1 = 1231 > 1140+90=1230
        hostel_engine.db.advance_game_clock(instance["id"], elapsed_minutes=31)
        hostel_engine._check_activity_expiry()

        marta = hostel_engine.db.get_character(2)
        assert marta.get("current_activity") is None, (
            "Marta's activity should have been cleared after the clock passed "
            "activity_started_at + activity_estimated_duration"
        )

    def test_activity_expiry_frees_wander_suppression(self, hostel_engine):
        """
        After an NPC's timed activity expires, Suppression 3 no longer applies
        and the NPC becomes eligible to wander.

        Marta has wander_probability=0.0 (she is the keeper and never leaves),
        so we verify this on The Old Soldier (id=5) instead. The Old Soldier's
        sharpening activity (started=1170, duration=60) expires at 1230. We
        advance the clock past expiry, clear the activity, then confirm movement
        becomes possible given a high wander_probability.

        The Old Soldier is seeded in the Upper Corridor (3) with wander_range
        not explicitly set in the seed — we set both wander_probability and
        wander_range directly here so the test controls the parameters cleanly.
        """
        instance = hostel_engine.db.get_active_instance(game_id=1)
        hostel_engine.db.advance_game_clock(instance["id"], elapsed_minutes=31)
        hostel_engine._check_activity_expiry()

        # Confirm Old Soldier's activity was cleared.
        old_soldier = hostel_engine.db.get_character(5)
        assert old_soldier.get("current_activity") is None, (
            "Old Soldier's sharpening activity should have expired and been cleared"
        )

        # Set a high wander_probability and wander_range so movement is observable.
        hostel_engine.db._execute(
            "UPDATE character SET wander_probability=1.0, wander_range='[1,3]' WHERE id=5"
        )

        original_loc = hostel_engine.db.get_character(5)["current_location_id"]
        moved = False
        for _ in range(50):
            hostel_engine._check_npc_wandering()
            new_loc = hostel_engine.db.get_character(5)["current_location_id"]
            if new_loc != original_loc:
                moved = True
                break

        assert moved, (
            "The Old Soldier should be able to wander after their activity expires "
            "— 50 attempts with wander_probability=1.0"
        )

    def test_renewable_activity_not_auto_cleared(self, hostel_engine):
        """
        A renewable activity must never be auto-cleared by _check_activity_expiry,
        even after its estimated duration has passed.

        We insert a renewable test activity on The Wanderer (id=3), advance the
        clock past its duration, and confirm it is not cleared.
        """
        hostel_engine.db.set_character_activity(
            character_id=3,
            activity="sitting by the fire, keeping watch",
            started_at=1200,
            duration_minutes=5,
            confidence=0.90,
            renewable=1,
        )
        instance = hostel_engine.db.get_active_instance(game_id=1)
        hostel_engine.db.advance_game_clock(instance["id"], elapsed_minutes=10)
        hostel_engine._check_activity_expiry()

        wanderer = hostel_engine.db.get_character(3)
        assert wanderer.get("current_activity") is not None, (
            "A renewable activity should not be auto-cleared by _check_activity_expiry "
            "even after its estimated duration has passed"
        )


# =============================================================================
# §H — Hidden motivation access control (The Scholar)
# =============================================================================

class TestHiddenMotivationAccessControl:
    """
    The Scholar (id=4) has hidden_motivation set and access_hidden_motivation=0.
    When building the Pass 1 context packet, hidden motivation must never appear.
    When building Pass 2 with include_hidden=True (the default for NPC profiles),
    The Scholar's hidden_motivation must also be absent because access_hidden_motivation=0.
    """

    def test_scholar_has_hidden_motivation_in_db(self, tmp_hostel_db: Database):
        """Confirm The Scholar has a non-null hidden_motivation field in the DB."""
        scholar = tmp_hostel_db.get_character(4)
        assert scholar.get("hidden_motivation"), (
            "The Scholar should have hidden_motivation set in the seed"
        )
        assert scholar.get("access_hidden_motivation") == 0, (
            "The Scholar's access_hidden_motivation should be 0 (concealed)"
        )

    def test_hidden_motivation_absent_from_pass1_packet(self, tmp_hostel_db: Database):
        """
        The Pass 1 context packet must not expose hidden_motivation for any NPC.

        Pass 1 only includes minimal player context — no NPC profiles at all —
        so hidden motivation cannot appear there by design. This test confirms
        the packet structure contains no 'hidden_motivation' key anywhere.
        """
        from engine.context import build_pass1_packet
        packet = build_pass1_packet(tmp_hostel_db, game_id=1, player_input="look around")
        packet_str = json.dumps(packet)
        assert "hidden_motivation" not in packet_str, (
            "Pass 1 packet must not expose hidden_motivation under any key"
        )

    def test_hidden_motivation_absent_from_pass2_npc_profile(
        self, tmp_hostel_db: Database
    ):
        """
        When build_pass2_packet builds NPC profiles, The Scholar's hidden_motivation
        must be absent because access_hidden_motivation=0.

        The _build_character_profile helper respects access_hidden_motivation:
        even when include_hidden=True, hidden_motivation is only included when
        character.access_hidden_motivation is truthy.
        """
        from engine.context import build_pass2_packet
        action_record = {
            "action_type": "wait",
            "verb": "wait",
            "target": None,
            "target_id": None,
            "location_id": 1,
            "detail": None,
            "raw_input": "wait",
        }
        packet = build_pass2_packet(tmp_hostel_db, game_id=1, action_record=action_record)
        packet_str = json.dumps(packet)

        # The Scholar's hidden_motivation text should not appear anywhere.
        scholar = tmp_hostel_db.get_character(4)
        hidden_text = scholar.get("hidden_motivation", "")
        if hidden_text:
            # Only assert absence if hidden_motivation has actual content.
            assert hidden_text not in packet_str, (
                "The Scholar's hidden_motivation text must not appear in the "
                "Pass 2 packet when access_hidden_motivation=0"
            )


# =============================================================================
# §I — Faction reputation
# =============================================================================

class TestFactionReputation:
    """
    The Traveller (id=1) has a reputation record in the 'hosts_of_the_hostel'
    faction (rep=0.40). This verifies the faction system is wired up in the
    module and that the engine can read the reputation correctly.
    """

    def test_faction_exists(self, tmp_hostel_db: Database):
        """The 'hosts_of_the_hostel' faction must exist for game_id=1."""
        faction = tmp_hostel_db.get_or_create_faction(
            game_id=1, name="hosts_of_the_hostel"
        )
        assert faction is not None, "hosts_of_the_hostel faction should exist"

    def test_traveller_has_faction_reputation(self, tmp_hostel_db: Database):
        """The Traveller should have a reputation record in the faction."""
        faction = tmp_hostel_db.get_or_create_faction(
            game_id=1, name="hosts_of_the_hostel"
        )
        row = tmp_hostel_db._row(
            "SELECT reputation FROM character_faction_reputation "
            "WHERE character_id=1 AND faction_id=?",
            (faction["id"],),
        )
        assert row is not None, (
            "The Traveller should have a character_faction_reputation row for "
            "hosts_of_the_hostel"
        )
        assert abs(row["reputation"] - 0.40) < 1e-4, (
            f"Expected Traveller reputation≈0.40, got {row['reputation']}"
        )

    def test_marta_has_high_faction_reputation(self, tmp_hostel_db: Database):
        """Marta (the host) should have reputation≈0.90 in the faction."""
        faction = tmp_hostel_db.get_or_create_faction(
            game_id=1, name="hosts_of_the_hostel"
        )
        row = tmp_hostel_db._row(
            "SELECT reputation FROM character_faction_reputation "
            "WHERE character_id=2 AND faction_id=?",
            (faction["id"],),
        )
        assert row is not None, "Marta should have a faction_reputation row"
        assert abs(row["reputation"] - 0.90) < 1e-4, (
            f"Expected Marta reputation≈0.90, got {row['reputation']}"
        )


# =============================================================================
# §J — Passive state drift
# =============================================================================

class TestPassiveStateDrift:
    """
    Verify that tick_passive_states() correctly drifts the three Hidden Hostel
    internal states that have non-null passive_rate_per_minute:

      Traveller curiosity  (+0.001/min): positive drift from 0.40
      Marta fatigue        (+0.002/min): positive drift from 0.55
      Gin-chan sleepiness  (-0.001/min): negative drift from 0.72
    """

    def test_traveller_curiosity_increases(self, tmp_hostel_db: Database):
        """30 minutes of drift should increase curiosity by 0.001 × 30 = 0.030."""
        tmp_hostel_db.tick_passive_states(game_id=1, elapsed_minutes=30.0)
        state = tmp_hostel_db.get_internal_state(character_id=1, state_name="curiosity")
        assert state is not None, "Traveller curiosity state not found"
        assert state["value"] == pytest.approx(0.430, abs=1e-5), (
            f"Expected curiosity≈0.430 after 30 min, got {state['value']:.5f}"
        )

    def test_marta_fatigue_increases(self, tmp_hostel_db: Database):
        """30 minutes of drift should increase fatigue by 0.002 × 30 = 0.060."""
        tmp_hostel_db.tick_passive_states(game_id=1, elapsed_minutes=30.0)
        state = tmp_hostel_db.get_internal_state(character_id=2, state_name="fatigue")
        assert state is not None, "Marta fatigue state not found"
        assert state["value"] == pytest.approx(0.610, abs=1e-5), (
            f"Expected fatigue≈0.610 after 30 min, got {state['value']:.5f}"
        )

    def test_ginchan_sleepiness_decreases(self, tmp_hostel_db: Database):
        """30 minutes of drift should decrease sleepiness by 0.001 × 30 = 0.030."""
        tmp_hostel_db.tick_passive_states(game_id=1, elapsed_minutes=30.0)
        state = tmp_hostel_db.get_internal_state(character_id=6, state_name="sleepiness")
        assert state is not None, "Gin-chan sleepiness state not found"
        assert state["value"] == pytest.approx(0.690, abs=1e-5), (
            f"Expected sleepiness≈0.690 after 30 min, got {state['value']:.5f}"
        )

    def test_drift_clamps_at_one(self, tmp_hostel_db: Database):
        """A state that would exceed 1.0 is clamped to exactly 1.0."""
        tmp_hostel_db.update_internal_state(
            character_id=1, state_name="curiosity", new_value=0.999
        )
        tmp_hostel_db.tick_passive_states(game_id=1, elapsed_minutes=100.0)
        state = tmp_hostel_db.get_internal_state(character_id=1, state_name="curiosity")
        assert state["value"] == pytest.approx(1.0), (
            "Curiosity drift should clamp at 1.0, not exceed it"
        )

    def test_drift_clamps_at_zero(self, tmp_hostel_db: Database):
        """A state that would go below 0.0 is clamped to exactly 0.0."""
        tmp_hostel_db.update_internal_state(
            character_id=6, state_name="sleepiness", new_value=0.001
        )
        tmp_hostel_db.tick_passive_states(game_id=1, elapsed_minutes=100.0)
        state = tmp_hostel_db.get_internal_state(character_id=6, state_name="sleepiness")
        assert state["value"] == pytest.approx(0.0), (
            "Sleepiness drift should clamp at 0.0, not go negative"
        )


# =============================================================================
# §K, §L — Attitudes (negative reads + delta application and clamping)
# =============================================================================

class TestAttitudes:
    """
    The Hidden Hostel seeds two attitude directions of particular interest:
      The Old Soldier (id=5) → Traveller (id=1): −0.30 (hostile)
      Gin-chan (id=6) → Traveller (id=1): +0.50 (warm)

    These cover the negative-attitude read path (§K) and the attitude delta
    application path including clamping (§L).
    """

    def test_old_soldier_negative_attitude(self, tmp_hostel_db: Database):
        """The Old Soldier's surface attitude toward the Traveller should be −0.30."""
        attitudes = tmp_hostel_db.get_character_attitudes(
            character_id=5, include_hidden=False
        )
        toward_traveller = next(
            (a for a in attitudes if a["target_id"] == 1 and a["attitude_type"] == "surface"),
            None,
        )
        assert toward_traveller is not None, (
            "The Old Soldier should have a surface attitude toward the Traveller"
        )
        assert toward_traveller["attitude"] == pytest.approx(-0.30, abs=1e-4), (
            f"Expected attitude≈−0.30, got {toward_traveller['attitude']:.4f}"
        )

    def test_ginchan_positive_attitude(self, tmp_hostel_db: Database):
        """Gin-chan's surface attitude toward the Traveller should be +0.50."""
        attitudes = tmp_hostel_db.get_character_attitudes(
            character_id=6, include_hidden=False
        )
        toward_traveller = next(
            (a for a in attitudes if a["target_id"] == 1 and a["attitude_type"] == "surface"),
            None,
        )
        assert toward_traveller is not None
        assert toward_traveller["attitude"] == pytest.approx(0.50, abs=1e-4)

    def test_attitude_delta_applied(self, tmp_hostel_db: Database):
        """
        update_attitude() with a positive delta on the Old Soldier's hostile
        attitude should raise it toward zero.
        """
        tmp_hostel_db.update_attitude(
            character_id=5, target_id=1, delta=0.10, attitude_type="surface"
        )
        attitudes = tmp_hostel_db.get_character_attitudes(5, include_hidden=False)
        toward_traveller = next(
            (a for a in attitudes if a["target_id"] == 1 and a["attitude_type"] == "surface"),
            None,
        )
        assert toward_traveller is not None
        assert toward_traveller["attitude"] == pytest.approx(-0.20, abs=1e-4), (
            f"Expected −0.30 + 0.10 = −0.20, got {toward_traveller['attitude']:.4f}"
        )

    def test_attitude_delta_clamps_at_positive_one(self, tmp_hostel_db: Database):
        """A large positive delta must not push attitude above 1.0."""
        tmp_hostel_db.update_attitude(
            character_id=6, target_id=1, delta=0.80, attitude_type="surface"
        )
        attitudes = tmp_hostel_db.get_character_attitudes(6, include_hidden=False)
        toward_traveller = next(
            (a for a in attitudes if a["target_id"] == 1 and a["attitude_type"] == "surface"),
            None,
        )
        assert toward_traveller is not None
        assert toward_traveller["attitude"] == pytest.approx(1.0), (
            "Attitude clamped at 1.0; 0.50 + 0.80 = 1.30 should clamp to 1.0"
        )

    def test_attitude_delta_clamps_at_negative_one(self, tmp_hostel_db: Database):
        """A large negative delta must not push attitude below −1.0."""
        tmp_hostel_db.update_attitude(
            character_id=5, target_id=1, delta=-0.80, attitude_type="surface"
        )
        attitudes = tmp_hostel_db.get_character_attitudes(5, include_hidden=False)
        toward_traveller = next(
            (a for a in attitudes if a["target_id"] == 1 and a["attitude_type"] == "surface"),
            None,
        )
        assert toward_traveller is not None
        assert toward_traveller["attitude"] == pytest.approx(-1.0), (
            "Attitude clamped at −1.0; −0.30 + (−0.80) = −1.10 should clamp to −1.0"
        )


# =============================================================================
# §M — Pre-seeded location_detail (lazy generation retrieval path)
# =============================================================================

class TestLocationDetail:
    """
    The Common Room (1) has a pre-seeded location_detail in the seed. This
    exercises the retrieval path for lazy world generation: when a detail
    already exists for a location, the engine should find it rather than
    generating a new one.

    These tests verify only the DB state, not engine prose generation (which
    is an LLM concern and belongs in Tier 2/3 tests).
    """

    def test_common_room_has_seeded_detail(self, tmp_hostel_db: Database):
        """The Common Room (1) should have at least one location_detail record."""
        details = tmp_hostel_db.get_location_details(location_id=1)
        assert details, (
            "The Common Room should have at least one location_detail in the seed "
            "(pre-seeded to exercise the lazy generation retrieval path)"
        )

    def test_common_room_detail_text_non_empty(self, tmp_hostel_db: Database):
        """The seeded Common Room detail must have non-empty text content."""
        details = tmp_hostel_db.get_location_details(location_id=1)
        assert details, "No detail records found for Common Room"
        first = details[0]
        # The location_detail table uses the column name 'detail' (see schema.sql).
        text = first.get("detail") or ""
        assert text.strip(), (
            "The pre-seeded location_detail for the Common Room must not be empty"
        )

    def test_kitchen_has_no_seeded_detail(self, tmp_hostel_db: Database):
        """
        The Kitchen (2) has no pre-seeded detail — it is generated lazily on
        first visit. Confirm the DB starts clean for that location.
        """
        details = tmp_hostel_db.get_location_details(location_id=2)
        assert not details, (
            "The Kitchen should have no location_detail in the seed "
            "(it is a lazy-generation target)"
        )

# =============================================================================
# Character Goals
# =============================================================================

class TestCharacterGoals:
    """
    Verify that character_goal records are seeded correctly for Hidden Hostel
    NPCs. These tests cover the Ford-Nichols Motivational Systems Theory (MST)
    goal records that inform Pass 2 adjudication.

    Each test checks goal presence and field values; they do not exercise LLM
    behaviour. Goal-driven LLM behaviour is covered in the Tier 2 scenario test
    (test_scenario_entrance.py::test_063_marta_offers_rolls_proactively).
    """

    def test_marta_has_resource_provision_goal(self, tmp_hostel_db: Database):
        """
        Marta's resource_provision goal (surface, approach, person_environment)
        should be seeded. This goal provides the motivational ground truth that
        makes her proactive hospitality — offering food before guests ask —
        consistent with her character, not just a hard-coded pending_intent.
        Priority must be at least 0.65 (behaviorally salient alongside belonging
        at 0.80 and resource_acquisition at 0.65).
        """
        goals = tmp_hostel_db.get_character_goals(character_id=2, include_hidden=False)
        goal_names = [g["goal_name"] for g in goals]
        assert "resource_provision" in goal_names, (
            f"Marta (id=2) should have a resource_provision goal; "
            f"found goals: {goal_names}"
        )
        rp = next(g for g in goals if g["goal_name"] == "resource_provision")
        assert rp["goal_type"] == "surface", (
            "Marta's resource_provision goal should be surface (openly expressed)"
        )
        assert rp["orientation"] == "approach", (
            "resource_provision should be an approach goal (moving toward, not away)"
        )
        assert rp["scope"] == "person_environment", (
            "resource_provision is directed outward at others, not within-person"
        )
        assert rp["priority"] >= 0.65, (
            f"resource_provision priority should be >= 0.65; got {rp['priority']}"
        )

    def test_marta_goal_set_is_complete(self, tmp_hostel_db: Database):
        """
        Marta should have all three seeded goals: belonging, resource_acquisition,
        resource_provision. This guards against partial seed failures.
        """
        goals = tmp_hostel_db.get_character_goals(character_id=2, include_hidden=False)
        goal_names = {g["goal_name"] for g in goals}
        for expected in ("belonging", "resource_acquisition", "resource_provision"):
            assert expected in goal_names, (
                f"Marta goal set incomplete — missing {expected!r}; "
                f"found: {goal_names}"
            )

    def test_wanderer_has_exploration_goal(self, tmp_hostel_db: Database):
        """
        The Wanderer's dominant goal (exploration, priority 0.88) should be
        seeded. This guards the motivational basis for their cross-world movement
        behaviour and confirms the goal table is populated correctly for NPCs
        other than Marta.
        """
        goals = tmp_hostel_db.get_character_goals(character_id=3, include_hidden=False)
        goal_names = [g["goal_name"] for g in goals]
        assert "exploration" in goal_names, (
            f"The Wanderer (id=3) should have an exploration goal; "
            f"found: {goal_names}"
        )
        exp = next(g for g in goals if g["goal_name"] == "exploration")
        assert exp["priority"] >= 0.85, (
            f"Wanderer exploration priority should be dominant (>= 0.85); "
            f"got {exp['priority']}"
        )

    def test_scholar_has_hidden_safety_goal(self, tmp_hostel_db: Database):
        """
        The Scholar's safety goal is hidden (goal_type='hidden'). When
        include_hidden=False, it must not appear. When include_hidden=True
        it must appear. This mirrors the access control pattern for
        hidden_motivation and ensures the goal visibility flag works correctly.
        """
        surface_goals = tmp_hostel_db.get_character_goals(
            character_id=4, include_hidden=False
        )
        surface_names = [g["goal_name"] for g in surface_goals]
        assert "safety" not in surface_names, (
            "Scholar's hidden safety goal must not appear when include_hidden=False"
        )

        all_goals = tmp_hostel_db.get_character_goals(
            character_id=4, include_hidden=True
        )
        all_names = [g["goal_name"] for g in all_goals]
        assert "safety" in all_names, (
            "Scholar's hidden safety goal must appear when include_hidden=True"
        )
