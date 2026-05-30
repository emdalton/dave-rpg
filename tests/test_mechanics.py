"""
tests/test_mechanics.py — Engine Mechanics Tests (Tier 1: no LLM)

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Tests for the engine's mechanical subsystems that do not require a full
GameEngine instance: passive state drift, the in-game clock, BFS pathfinding,
and the database utility function for time formatting.

These tests operate directly on db.py methods and the engine's pathfinding
helper rather than through the GameEngine class. They are fast, deterministic,
and require no LLM setup.
"""

import pytest

from engine.db import Database, _format_game_time


# =============================================================================
# Time formatting utility
# =============================================================================

class TestFormatGameTime:
    """_format_game_time converts minutes-past-midnight to a human-readable string."""

    def test_midnight(self):
        assert _format_game_time(0) == "12:00 AM"

    def test_3am(self):
        assert _format_game_time(180) == "3:00 AM"

    def test_noon(self):
        assert _format_game_time(720) == "12:00 PM"

    def test_half_past_hour(self):
        assert _format_game_time(150) == "2:30 AM"

    def test_handles_past_midnight_wrap(self):
        # 1440 minutes = exactly 24 hours → wraps to midnight
        assert _format_game_time(1440) == "12:00 AM"

    def test_handles_values_past_1440(self):
        # 1500 = 1440 + 60 → 1:00 AM on the next day
        assert _format_game_time(1500) == "1:00 AM"


# =============================================================================
# Passive state drift (db.tick_passive_states)
# =============================================================================

class TestPassiveStateDrift:
    """
    tick_passive_states() applies passive_rate_per_minute × elapsed_minutes
    to all internal_state rows with a non-null passive_rate_per_minute,
    clamping the result to [0.0, 1.0].
    """

    def test_zero_elapsed_minutes_changes_nothing(self, tmp_db: Database):
        before = tmp_db.get_internal_state(character_id=1, state_name="boredom")
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=0.0)
        after = tmp_db.get_internal_state(character_id=1, state_name="boredom")
        assert before["value"] == pytest.approx(after["value"])

    def test_positive_rate_increases_value(self, tmp_db: Database):
        # boredom rate=+0.002/min; 20 min → 0.10 + 0.04 = 0.14
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=20.0)
        state = tmp_db.get_internal_state(character_id=1, state_name="boredom")
        assert state["value"] == pytest.approx(0.14, abs=1e-6)

    def test_negative_rate_decreases_value(self, tmp_db: Database):
        # sleepiness rate=−0.003/min; 20 min → 0.50 − 0.06 = 0.44
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=20.0)
        state = tmp_db.get_internal_state(character_id=2, state_name="sleepiness")
        assert state["value"] == pytest.approx(0.44, abs=1e-6)

    def test_drift_does_not_exceed_one(self, tmp_db: Database):
        tmp_db.update_internal_state(character_id=1, state_name="boredom", new_value=0.999)
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=100.0)
        state = tmp_db.get_internal_state(character_id=1, state_name="boredom")
        assert state["value"] == pytest.approx(1.0)

    def test_drift_does_not_go_below_zero(self, tmp_db: Database):
        tmp_db.update_internal_state(character_id=2, state_name="sleepiness", new_value=0.001)
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=100.0)
        state = tmp_db.get_internal_state(character_id=2, state_name="sleepiness")
        assert state["value"] == pytest.approx(0.0)

    def test_only_states_with_non_null_rate_are_drifted(self, tmp_db: Database):
        # Add a state with NULL passive_rate_per_minute; it should not drift.
        tmp_db._execute(
            "INSERT INTO internal_state (character_id, state_name, value, passive_rate_per_minute) "
            "VALUES (1, 'courage', 0.50, NULL)"
        )
        tmp_db.tick_passive_states(game_id=1, elapsed_minutes=50.0)
        state = tmp_db.get_internal_state(character_id=1, state_name="courage")
        assert state["value"] == pytest.approx(0.50), \
            "State with NULL passive_rate_per_minute should not drift"


# =============================================================================
# In-game clock
# =============================================================================

class TestClock:
    def test_initial_clock_value(self, tmp_db: Database):
        t = tmp_db.get_game_clock(instance_id=1)
        assert t == 180, "Test world seeds clock at 3:00 AM (180 min)"

    def test_advance_clock_adds_minutes(self, tmp_db: Database):
        tmp_db.advance_game_clock(instance_id=1, elapsed_minutes=30)
        assert tmp_db.get_game_clock(instance_id=1) == 210

    def test_clock_accumulates_across_multiple_advances(self, tmp_db: Database):
        tmp_db.advance_game_clock(instance_id=1, elapsed_minutes=5)
        tmp_db.advance_game_clock(instance_id=1, elapsed_minutes=10)
        tmp_db.advance_game_clock(instance_id=1, elapsed_minutes=15)
        assert tmp_db.get_game_clock(instance_id=1) == 210

    def test_zero_elapsed_does_not_change_clock(self, tmp_db: Database):
        tmp_db.advance_game_clock(instance_id=1, elapsed_minutes=0)
        assert tmp_db.get_game_clock(instance_id=1) == 180

    def test_get_active_instance(self, tmp_db: Database):
        instance = tmp_db.get_active_instance(game_id=1)
        assert instance is not None
        # start_time_minutes and current_time_minutes should both be 180
        # (the engine will have already transitioned it to 'active', which
        # the test_engine fixture does; using tmp_db directly it stays 'ready')
        assert instance["start_time_minutes"] == 180


# =============================================================================
# BFS pathfinding
# =============================================================================

class TestBFSPathfinding:
    """
    _resolve_multistep_move() is the engine's BFS pathfinder. It computes the
    shortest path from the player's current location to the named destination,
    traversing only passable connections.

    In the test world, there are only two locations (Antechamber ↔ Hall), so
    the pathfinding tests validate:
      - Direct adjacency returns a one-step route
      - An unreachable destination returns an appropriate failure result
      - A destination the player is already at is handled gracefully

    These tests call the engine method directly via the test_engine fixture,
    which has the full GameEngine context (player, db, game_id) needed for
    pathfinding.
    """

    def test_path_to_adjacent_location(self, test_engine):
        # Hero is at Antechamber (1); Hall (2) is directly adjacent.
        # Return keys: reachable, path_taken, effective_destination_id,
        # path_location_names, interrupted, interruption, no_path_reason.
        result = test_engine._resolve_multistep_move(target_location_id=2)
        assert result.get("reachable") is True, \
            "Pathfinding to an adjacent location should be reachable"
        assert result.get("effective_destination_id") == 2, \
            "Effective destination should be Hall (2)"
        assert 2 in result.get("path_taken", []), \
            "path_taken should include Hall (2)"

    def test_path_to_unreachable_location(self, test_engine):
        # Add an isolated location with no connections.
        test_engine.db._execute(
            "INSERT INTO location (id, game_id, name, location_type, "
            "social_setting, witness_count, situation_flags) "
            "VALUES (50, 1, 'Isolated Tower', 'tower', 'private', 0, '[]')"
        )
        result = test_engine._resolve_multistep_move(target_location_id=50)
        assert result.get("reachable") is False, \
            "Pathfinding to an unreachable location should return reachable=False"

    def test_path_to_current_location(self, test_engine):
        # Hero is already at Antechamber (1); requesting a path there.
        # Should handle gracefully — not a crash condition.
        result = test_engine._resolve_multistep_move(target_location_id=1)
        assert isinstance(result, dict), \
            "_resolve_multistep_move should always return a dict"
