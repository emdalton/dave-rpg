"""
tests/test_db.py — Database Layer Tests (Tier 1: no LLM)

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Tests every significant method of engine/db.py against the minimal test world
defined in tests/fixtures/seed.py. No LLM calls are made; all tests exercise
direct database reads and writes.

Test world reference (see seed.py for authoritative definitions)
----------------------------------------------------------------
game_id=1, game_instance id=1, start/current_time=180 (3:00 AM)
character id=1  Hero   (player, location=1 Antechamber)
character id=2  Guard  (npc_active, location=1, wander_prob=1.0)
character id=3  Hermit (npc_active, location=2 Hall,  wander_prob=0.0)
location id=1   Antechamber
location id=2   Hall
connection      Antechamber ↔ Hall (passable)
faction id=1    town_guard
internal_state  Hero: boredom=0.10 (+0.002/min)
                Guard: sleepiness=0.50 (−0.003/min)
attitude        Hero→Guard surface=0.60
faction rep     Hero in town_guard=0.70
"""

import pytest

from engine.db import Database


# =============================================================================
# Schema version
# =============================================================================

class TestSchemaVersion:
    def test_schema_version_is_populated(self, tmp_db: Database):
        """MAX(version) should be at least 7 after applying schema.sql."""
        row = tmp_db._row("SELECT MAX(version) AS v FROM schema_version")
        assert row is not None
        assert row["v"] >= 7, "schema_version table should reflect schema.sql version"


# =============================================================================
# Game record
# =============================================================================

class TestGetGame:
    def test_returns_game_record(self, tmp_db: Database):
        game = tmp_db.get_game(game_id=1)
        assert game is not None
        assert game["name"] == "Test World"
        assert game["genre"] == "adventure"

    def test_json_fields_are_parsed(self, tmp_db: Database):
        game = tmp_db.get_game(game_id=1)
        # speech_filter, internal_state_display, and cultural_norms are stored
        # as JSON strings and must be returned as Python dicts.
        assert isinstance(game["speech_filter"], dict)
        assert isinstance(game["cultural_norms"], dict)

    def test_returns_none_for_unknown_id(self, tmp_db: Database):
        assert tmp_db.get_game(game_id=999) is None


# =============================================================================
# Character queries
# =============================================================================

class TestGetCharacter:
    def test_get_player_character(self, tmp_db: Database):
        player = tmp_db.get_player_character(game_id=1)
        assert player is not None
        assert player["name"] == "Hero"
        assert player["role"] == "player"

    def test_get_character_by_id(self, tmp_db: Database):
        guard = tmp_db.get_character(character_id=2)
        assert guard is not None
        assert guard["name"] == "Guard"

    def test_returns_none_for_unknown_character(self, tmp_db: Database):
        assert tmp_db.get_character(character_id=999) is None

    def test_get_characters_at_location(self, tmp_db: Database):
        chars = tmp_db.get_characters_at_location(location_id=1)
        names = {c["name"] for c in chars}
        assert "Hero" in names
        assert "Guard" in names
        assert "Hermit" not in names   # Hermit is in location 2

    def test_exclude_character_from_location_query(self, tmp_db: Database):
        chars = tmp_db.get_characters_at_location(location_id=1, exclude_character_id=1)
        names = {c["name"] for c in chars}
        assert "Hero" not in names
        assert "Guard" in names


# =============================================================================
# Internal states
# =============================================================================

class TestInternalStates:
    def test_get_internal_state(self, tmp_db: Database):
        state = tmp_db.get_internal_state(character_id=1, state_name="boredom")
        assert state is not None
        assert abs(state["value"] - 0.10) < 1e-9

    def test_get_internal_state_returns_none_for_unknown(self, tmp_db: Database):
        state = tmp_db.get_internal_state(character_id=1, state_name="nonexistent_state")
        assert state is None

    def test_update_internal_state(self, tmp_db: Database):
        tmp_db.update_internal_state(character_id=1, state_name="boredom", new_value=0.55)
        state = tmp_db.get_internal_state(character_id=1, state_name="boredom")
        assert abs(state["value"] - 0.55) < 1e-9

    def test_apply_internal_state_delta_clamps_at_max(self, tmp_db: Database):
        # Start at 0.10, add 2.0 → should clamp to 1.0
        new_value = tmp_db.apply_internal_state_delta(
            character_id=1, state_name="boredom", delta=2.0
        )
        assert new_value == pytest.approx(1.0)
        state = tmp_db.get_internal_state(character_id=1, state_name="boredom")
        assert state["value"] == pytest.approx(1.0)

    def test_apply_internal_state_delta_clamps_at_min(self, tmp_db: Database):
        # Start at 0.10, subtract 2.0 → should clamp to 0.0
        new_value = tmp_db.apply_internal_state_delta(
            character_id=1, state_name="boredom", delta=-2.0
        )
        assert new_value == pytest.approx(0.0)

    def test_apply_internal_state_delta_normal_range(self, tmp_db: Database):
        new_value = tmp_db.apply_internal_state_delta(
            character_id=1, state_name="boredom", delta=0.05
        )
        assert new_value == pytest.approx(0.15)


# =============================================================================
# Passive state decay
# =============================================================================

class TestPassiveStateDrift:
    def test_tick_increases_positive_rate_state(self, tmp_db: Database):
        # Hero boredom starts at 0.10 with rate +0.002/min
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=10.0)
        state = tmp_db.get_internal_state(character_id=1, state_name="boredom")
        # Expected: 0.10 + 0.002 * 10 = 0.12
        assert state["value"] == pytest.approx(0.12, abs=1e-6)

    def test_tick_decreases_negative_rate_state(self, tmp_db: Database):
        # Guard sleepiness starts at 0.50 with rate -0.003/min
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=10.0)
        state = tmp_db.get_internal_state(character_id=2, state_name="sleepiness")
        # Expected: 0.50 + (-0.003) * 10 = 0.47
        assert state["value"] == pytest.approx(0.47, abs=1e-6)

    def test_tick_clamps_at_maximum(self, tmp_db: Database):
        # Set boredom to 0.99 and tick by 100 minutes → should clamp at 1.0
        tmp_db.update_internal_state(character_id=1, state_name="boredom", new_value=0.99)
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=100.0)
        state = tmp_db.get_internal_state(character_id=1, state_name="boredom")
        assert state["value"] == pytest.approx(1.0)

    def test_tick_clamps_at_minimum(self, tmp_db: Database):
        # Set sleepiness to 0.01 and tick by 100 minutes → should clamp at 0.0
        tmp_db.update_internal_state(character_id=2, state_name="sleepiness", new_value=0.01)
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=100.0)
        state = tmp_db.get_internal_state(character_id=2, state_name="sleepiness")
        assert state["value"] == pytest.approx(0.0)


# =============================================================================
# In-game clock
# =============================================================================

class TestGameClock:
    def test_get_game_clock_returns_start_time(self, tmp_db: Database):
        # Seeded at current_time_minutes=180
        t = tmp_db.get_game_clock(instance_id=1)
        assert t == 180

    def test_advance_game_clock(self, tmp_db: Database):
        tmp_db.advance_game_clock(instance_id=1, elapsed_minutes=15)
        t = tmp_db.get_game_clock(instance_id=1)
        assert t == 195

    def test_advance_clock_accumulates(self, tmp_db: Database):
        tmp_db.advance_game_clock(instance_id=1, elapsed_minutes=10)
        tmp_db.advance_game_clock(instance_id=1, elapsed_minutes=5)
        t = tmp_db.get_game_clock(instance_id=1)
        assert t == 195


# =============================================================================
# Attitudes
# =============================================================================

class TestAttitudes:
    def test_get_attitude_toward(self, tmp_db: Database):
        attitude = tmp_db.get_attitude_toward(
            character_id=1, target_id=2, attitude_type="surface"
        )
        assert attitude == pytest.approx(0.60)

    def test_get_attitude_returns_zero_for_unknown_pair(self, tmp_db: Database):
        attitude = tmp_db.get_attitude_toward(
            character_id=2, target_id=3, attitude_type="surface"
        )
        assert attitude == pytest.approx(0.0)

    def test_update_attitude_applies_delta(self, tmp_db: Database):
        new_val = tmp_db.update_attitude(
            character_id=1, target_id=2, delta=0.10, attitude_type="surface"
        )
        assert new_val == pytest.approx(0.70)

    def test_update_attitude_clamps_at_max(self, tmp_db: Database):
        new_val = tmp_db.update_attitude(
            character_id=1, target_id=2, delta=2.0, attitude_type="surface"
        )
        assert new_val == pytest.approx(1.0)

    def test_update_attitude_clamps_at_min(self, tmp_db: Database):
        new_val = tmp_db.update_attitude(
            character_id=1, target_id=2, delta=-5.0, attitude_type="surface"
        )
        assert new_val == pytest.approx(-1.0)

    def test_update_attitude_creates_new_record(self, tmp_db: Database):
        # No existing attitude from Guard→Hero
        new_val = tmp_db.update_attitude(
            character_id=2, target_id=1, delta=0.20, attitude_type="surface"
        )
        assert new_val == pytest.approx(0.20)
        assert tmp_db.get_attitude_toward(2, 1, "surface") == pytest.approx(0.20)


# =============================================================================
# Faction reputation
# =============================================================================

class TestFactionReputation:
    def test_get_or_create_faction_existing(self, tmp_db: Database):
        faction = tmp_db.get_or_create_faction(game_id=1, name="town_guard")
        assert faction is not None
        assert faction["name"] == "town_guard"

    def test_get_or_create_faction_creates_new(self, tmp_db: Database):
        faction = tmp_db.get_or_create_faction(game_id=1, name="new_faction")
        assert faction is not None
        assert faction["name"] == "new_faction"
        # Calling again should return the same row, not create a duplicate.
        faction2 = tmp_db.get_or_create_faction(game_id=1, name="new_faction")
        assert faction["id"] == faction2["id"]

    def test_update_faction_reputation(self, tmp_db: Database):
        faction = tmp_db.get_or_create_faction(game_id=1, name="town_guard")
        tmp_db.update_faction_reputation(
            character_id=1, faction_id=faction["id"], delta=0.05, reason="test"
        )
        row = tmp_db._row(
            "SELECT reputation FROM character_faction_reputation "
            "WHERE character_id=1 AND faction_id=?",
            (faction["id"],),
        )
        assert row["reputation"] == pytest.approx(0.75)

    def test_faction_reputation_clamps_at_max(self, tmp_db: Database):
        faction = tmp_db.get_or_create_faction(game_id=1, name="town_guard")
        tmp_db.update_faction_reputation(
            character_id=1, faction_id=faction["id"], delta=10.0
        )
        row = tmp_db._row(
            "SELECT reputation FROM character_faction_reputation "
            "WHERE character_id=1 AND faction_id=?",
            (faction["id"],),
        )
        assert row["reputation"] == pytest.approx(1.0)

    def test_faction_reputation_clamps_at_min(self, tmp_db: Database):
        faction = tmp_db.get_or_create_faction(game_id=1, name="town_guard")
        tmp_db.update_faction_reputation(
            character_id=1, faction_id=faction["id"], delta=-10.0
        )
        row = tmp_db._row(
            "SELECT reputation FROM character_faction_reputation "
            "WHERE character_id=1 AND faction_id=?",
            (faction["id"],),
        )
        assert row["reputation"] == pytest.approx(0.0)


# =============================================================================
# Pending intent
# =============================================================================

class TestPendingIntent:
    def test_set_pending_intent(self, tmp_db: Database):
        tmp_db.update_character_pending_intent(
            character_id=2,
            intent_text="owes Hero a favour after she helped with the gate",
        )
        char = tmp_db.get_character(character_id=2)
        assert char["pending_intent"] == "owes Hero a favour after she helped with the gate"

    def test_clear_pending_intent(self, tmp_db: Database):
        # Set then clear
        tmp_db.update_character_pending_intent(
            character_id=2, intent_text="some obligation"
        )
        tmp_db.update_character_pending_intent(
            character_id=2, intent_text=None
        )
        char = tmp_db.get_character(character_id=2)
        assert char["pending_intent"] is None


# =============================================================================
# Timed activity system (v8)
# =============================================================================

class TestActivitySystem:
    def test_set_character_activity(self, tmp_db: Database):
        tmp_db.set_character_activity(
            character_id=2,
            activity="standing watch at the entrance",
            started_at=180,
            duration_minutes=30,
            confidence=0.80,
            renewable=0,
        )
        char = tmp_db.get_character(character_id=2)
        assert char["current_activity"] == "standing watch at the entrance"
        assert char["activity_started_at"] == 180
        assert char["activity_estimated_duration"] == 30
        assert char["activity_duration_confidence"] == pytest.approx(0.80)
        assert char["activity_renewable"] == 0

    def test_clear_character_activity(self, tmp_db: Database):
        tmp_db.set_character_activity(
            character_id=2, activity="on patrol", started_at=180,
            duration_minutes=20, confidence=0.90, renewable=0,
        )
        tmp_db.clear_character_activity(character_id=2)
        char = tmp_db.get_character(character_id=2)
        assert char["current_activity"] is None
        assert char["activity_started_at"] is None
        assert char["activity_estimated_duration"] is None

    def test_get_characters_with_expired_activities(self, tmp_db: Database):
        # Set Guard's activity: started at 180, duration 10 min, confidence 0.90
        tmp_db.set_character_activity(
            character_id=2, activity="expired patrol", started_at=180,
            duration_minutes=10, confidence=0.90, renewable=0,
        )
        # Query at current_time=195 (180 + 10 = 190 <= 195 → expired)
        expired = tmp_db.get_characters_with_expired_activities(
            game_id=1,
            current_time_minutes=195,
            confidence_threshold=0.60,
        )
        ids = [c["id"] for c in expired]
        assert 2 in ids   # Guard's activity has expired

    def test_non_expired_activity_not_returned(self, tmp_db: Database):
        # Set Guard's activity: started at 180, duration 60 min, confidence 0.90
        tmp_db.set_character_activity(
            character_id=2, activity="long patrol", started_at=180,
            duration_minutes=60, confidence=0.90, renewable=0,
        )
        # Query at current_time=195 (180 + 60 = 240 > 195 → not expired)
        expired = tmp_db.get_characters_with_expired_activities(
            game_id=1,
            current_time_minutes=195,
            confidence_threshold=0.60,
        )
        ids = [c["id"] for c in expired]
        assert 2 not in ids

    def test_renewable_activity_not_auto_expired(self, tmp_db: Database):
        # renewable=1: engine must never auto-expire this, even past duration
        tmp_db.set_character_activity(
            character_id=2, activity="perpetual watch", started_at=180,
            duration_minutes=5, confidence=0.99, renewable=1,
        )
        expired = tmp_db.get_characters_with_expired_activities(
            game_id=1,
            current_time_minutes=300,   # well past expiry
            confidence_threshold=0.60,
        )
        ids = [c["id"] for c in expired]
        assert 2 not in ids

    def test_low_confidence_activity_not_auto_expired(self, tmp_db: Database):
        # confidence < threshold: only Pass 2 may clear this activity
        tmp_db.set_character_activity(
            character_id=2, activity="uncertain duration task", started_at=180,
            duration_minutes=5, confidence=0.30, renewable=0,
        )
        expired = tmp_db.get_characters_with_expired_activities(
            game_id=1,
            current_time_minutes=300,
            confidence_threshold=0.60,   # 0.30 < 0.60 → not eligible
        )
        ids = [c["id"] for c in expired]
        assert 2 not in ids


# =============================================================================
# Location queries
# =============================================================================

class TestLocationQueries:
    def test_get_location(self, tmp_db: Database):
        loc = tmp_db.get_location(location_id=1)
        assert loc is not None
        assert loc["name"] == "Antechamber"

    def test_get_location_returns_none_for_unknown(self, tmp_db: Database):
        assert tmp_db.get_location(location_id=999) is None

    def test_is_location_connected(self, tmp_db: Database):
        # Antechamber (1) ↔ Hall (2) is connected and passable
        assert tmp_db.is_location_connected(1, 2) is True

    def test_is_location_connected_reverse(self, tmp_db: Database):
        # Adjacency is bidirectional
        assert tmp_db.is_location_connected(2, 1) is True

    def test_is_location_not_connected_to_itself(self, tmp_db: Database):
        # Self-connection is not seeded; should return False
        assert tmp_db.is_location_connected(1, 1) is False

    def test_get_location_connections_returns_neighbour(self, tmp_db: Database):
        conns = tmp_db.get_location_connections(location_id=1)
        neighbour_ids = [c["neighbour_id"] for c in conns]
        assert 2 in neighbour_ids


# =============================================================================
# Lazy character creation (v8+)
# =============================================================================

class TestCreateCharacter:
    def test_create_character_inserts_row(self, tmp_db: Database):
        char_id = tmp_db.create_character(
            game_id=1,
            name="Mysterious Stranger",
            role="npc_active",
            species="human",
            current_location_id=2,
            emotional_state="guarded",
        )
        # create_character() returns the full row dict, not just the id.
        assert char_id is not None
        char = tmp_db.get_character(char_id["id"])
        assert char["name"] == "Mysterious Stranger"
        assert char["current_location_id"] == 2

    def test_created_character_appears_in_location_query(self, tmp_db: Database):
        tmp_db.create_character(
            game_id=1,
            name="Wanderer",
            role="npc_background",
            species="human",
            current_location_id=1,
        )
        chars = tmp_db.get_characters_at_location(location_id=1)
        names = {c["name"] for c in chars}
        assert "Wanderer" in names


# =============================================================================
# Action log prose persistence (v13+)
# =============================================================================

# Minimal action record for write_action_log calls.
_ACTION_JSON = {"action_type": "examine", "target": "room", "raw_input": "look around"}


class TestActionLogProse:
    """
    Tests for update_action_log_prose() and get_recent_prose().

    These methods underpin the Pass 3 anti-repetition feature: prose is written
    back to the action_log row after Pass 3 completes, then fetched in
    subsequent turns to give the renderer visibility into recent imagery.
    """

    def test_get_recent_prose_empty_before_any_prose(self, tmp_db: Database):
        """Before any prose has been written, get_recent_prose returns []."""
        result = tmp_db.get_recent_prose(game_id=1)
        assert result == []

    def test_update_action_log_prose_writes_value(self, tmp_db: Database):
        """Prose written via update_action_log_prose is returned by get_recent_prose."""
        log_id = tmp_db.write_action_log(
            game_id=1, character_id=1, action_json=_ACTION_JSON
        )
        tmp_db.update_action_log_prose(log_id, "The antechamber is cold and still.")
        result = tmp_db.get_recent_prose(game_id=1)
        assert result == ["The antechamber is cold and still."]

    def test_get_recent_prose_excludes_null_rows(self, tmp_db: Database):
        """Rows where prose is NULL (the in-flight turn) are not returned."""
        # Create a row but do not write prose — simulates the current in-flight turn.
        tmp_db.write_action_log(
            game_id=1, character_id=1, action_json=_ACTION_JSON
        )
        result = tmp_db.get_recent_prose(game_id=1)
        assert result == []

    def test_get_recent_prose_chronological_order(self, tmp_db: Database):
        """Multiple prose entries are returned oldest-first."""
        for prose in ("First turn prose.", "Second turn prose.", "Third turn prose."):
            log_id = tmp_db.write_action_log(
                game_id=1, character_id=1, action_json=_ACTION_JSON
            )
            tmp_db.update_action_log_prose(log_id, prose)
        result = tmp_db.get_recent_prose(game_id=1)
        assert result == [
            "First turn prose.",
            "Second turn prose.",
            "Third turn prose.",
        ]

    def test_get_recent_prose_respects_limit(self, tmp_db: Database):
        """With limit=2, only the two most recent prose entries are returned."""
        for prose in ("Turn 1.", "Turn 2.", "Turn 3.", "Turn 4."):
            log_id = tmp_db.write_action_log(
                game_id=1, character_id=1, action_json=_ACTION_JSON
            )
            tmp_db.update_action_log_prose(log_id, prose)
        result = tmp_db.get_recent_prose(game_id=1, limit=2)
        assert result == ["Turn 3.", "Turn 4."]
