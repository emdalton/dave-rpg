"""
tests/test_engine.py — Engine Mechanics Tests (Tier 1: mock LLM)

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Tests the three main mechanical subsystems of GameEngine that are independent
of LLM output quality:

1. _apply_outcome() — processes each Pass 2 output field type and writes
   the resulting state changes to the database.

2. _check_activity_expiry() — mechanically clears expired NPC activities
   before each turn, with correct handling of the confidence/renewable/duration
   logic.

3. _check_npc_wandering() — applies the three suppression conditions that
   prevent an NPC from wandering even when their wander_probability would fire.

All tests use the test_engine fixture, which provides a fully initialised
GameEngine backed by the test database and a MockLLMClient. No real LLM calls
are made; _apply_outcome() and the expiry/wander methods are called directly.

Test world reference
--------------------
character id=1  Hero   (player,    location=1)
character id=2  Guard  (npc_active, location=1, wander_prob=1.0, range=[1,2])
character id=3  Hermit (npc_active, location=2, wander_prob=0.0)
"""

import pytest

from engine.engine import GameEngine


# Minimal action_record for _apply_outcome calls.
# route=None → is_routed_move is False → player location_change is processed normally.
_ACTION = {"route": None, "action_type": "speak"}


# =============================================================================
# _apply_outcome — attitude_deltas
# =============================================================================

class TestApplyOutcomeAttitudeDeltas:
    def test_applies_attitude_delta(self, test_engine: GameEngine):
        from tests.fixtures.responses import PASS2_WITH_ATTITUDE_DELTA
        test_engine._apply_outcome(_ACTION, PASS2_WITH_ATTITUDE_DELTA)
        # Guard's attitude toward Hero should have increased from 0.0 by 0.10.
        attitude = test_engine.db.get_attitude_toward(
            character_id=2, target_id=1, attitude_type="surface"
        )
        assert attitude == pytest.approx(0.10)

    def test_malformed_delta_is_skipped(self, test_engine: GameEngine):
        outcome = {
            **_empty_outcome(),
            "attitude_deltas": [{"character_id": "not_an_int", "delta": 0.1}],
        }
        # Should not raise; malformed entries are logged and skipped.
        test_engine._apply_outcome(_ACTION, outcome)


# =============================================================================
# _apply_outcome — internal_state_deltas
# =============================================================================

class TestApplyOutcomeStateDeltas:
    def test_applies_state_delta(self, test_engine: GameEngine):
        from tests.fixtures.responses import PASS2_WITH_STATE_DELTA
        test_engine._apply_outcome(_ACTION, PASS2_WITH_STATE_DELTA)
        state = test_engine.db.get_internal_state(character_id=1, state_name="boredom")
        # 0.10 − 0.05 = 0.05
        assert state["value"] == pytest.approx(0.05)

    def test_state_delta_clamped_at_zero(self, test_engine: GameEngine):
        outcome = {
            **_empty_outcome(),
            "internal_state_deltas": [
                {"character_id": 1, "state_name": "boredom", "delta": -10.0}
            ],
        }
        test_engine._apply_outcome(_ACTION, outcome)
        state = test_engine.db.get_internal_state(character_id=1, state_name="boredom")
        assert state["value"] == pytest.approx(0.0)


# =============================================================================
# _apply_outcome — emotional_state_updates
# =============================================================================

class TestApplyOutcomeEmotionalState:
    def test_updates_emotional_state(self, test_engine: GameEngine):
        from tests.fixtures.responses import PASS2_WITH_EMOTIONAL_UPDATE
        test_engine._apply_outcome(_ACTION, PASS2_WITH_EMOTIONAL_UPDATE)
        guard = test_engine.db.get_character(character_id=2)
        assert guard["emotional_state"] == "suspicious"


# =============================================================================
# _apply_outcome — location_change
# =============================================================================

class TestApplyOutcomeLocationChange:
    def test_moves_player_to_adjacent_location(self, test_engine: GameEngine):
        from tests.fixtures.responses import PASS2_WITH_LOCATION_CHANGE
        test_engine._apply_outcome(_ACTION, PASS2_WITH_LOCATION_CHANGE)
        hero = test_engine.db.get_character(character_id=1)
        assert hero["current_location_id"] == 2, \
            "Hero should have moved to Hall (location 2)"

    def test_non_existent_location_is_rejected(self, test_engine: GameEngine):
        from tests.fixtures.responses import PASS2_WITH_INVALID_LOCATION_CHANGE
        test_engine._apply_outcome(_ACTION, PASS2_WITH_INVALID_LOCATION_CHANGE)
        hero = test_engine.db.get_character(character_id=1)
        # Hero should remain at Antechamber (location 1) — invalid move was discarded.
        assert hero["current_location_id"] == 1, \
            "Hero should stay at Antechamber when location_change targets non-existent location"

    def test_non_adjacent_location_is_rejected(self, test_engine: GameEngine):
        # Manually add a third location but no connection to it, then
        # ask Pass 2 to move Hero there.
        test_engine.db._execute(
            "INSERT INTO location (id, game_id, name, location_type, "
            "social_setting, witness_count, situation_flags) "
            "VALUES (99, 1, 'Secret Chamber', 'vault', 'private', 0, '[]')"
        )
        outcome = {
            **_empty_outcome(),
            "location_change": [{"character_id": 1, "new_location_id": 99}],
        }
        test_engine._apply_outcome(_ACTION, outcome)
        hero = test_engine.db.get_character(character_id=1)
        assert hero["current_location_id"] == 1, \
            "Hero should stay at Antechamber when location_change is not adjacent"


# =============================================================================
# _apply_outcome — faction_reputation_changes
# =============================================================================

class TestApplyOutcomeFactionRep:
    def test_applies_faction_reputation_delta(self, test_engine: GameEngine):
        from tests.fixtures.responses import PASS2_WITH_FACTION_REP
        test_engine._apply_outcome(_ACTION, PASS2_WITH_FACTION_REP)
        faction = test_engine.db.get_or_create_faction(game_id=1, name="town_guard")
        row = test_engine.db._row(
            "SELECT reputation FROM character_faction_reputation "
            "WHERE character_id=1 AND faction_id=?",
            (faction["id"],),
        )
        assert row["reputation"] == pytest.approx(0.75)  # 0.70 + 0.05


# =============================================================================
# _apply_outcome — pending_intent_updates
# =============================================================================

class TestApplyOutcomePendingIntent:
    def test_sets_pending_intent(self, test_engine: GameEngine):
        from tests.fixtures.responses import PASS2_WITH_PENDING_INTENT
        test_engine._apply_outcome(_ACTION, PASS2_WITH_PENDING_INTENT)
        guard = test_engine.db.get_character(character_id=2)
        assert guard["pending_intent"] is not None
        assert "favour" in guard["pending_intent"]

    def test_clears_pending_intent(self, test_engine: GameEngine):
        # First set it, then clear it.
        test_engine.db.update_character_pending_intent(
            character_id=2, intent_text="some obligation"
        )
        from tests.fixtures.responses import PASS2_CLEAR_PENDING_INTENT
        test_engine._apply_outcome(_ACTION, PASS2_CLEAR_PENDING_INTENT)
        guard = test_engine.db.get_character(character_id=2)
        assert guard["pending_intent"] is None


# =============================================================================
# _apply_outcome — activity_updates
# =============================================================================

class TestApplyOutcomeActivity:
    def test_sets_activity(self, test_engine: GameEngine):
        from tests.fixtures.responses import PASS2_WITH_ACTIVITY_SET
        test_engine._apply_outcome(_ACTION, PASS2_WITH_ACTIVITY_SET)
        guard = test_engine.db.get_character(character_id=2)
        assert guard["current_activity"] == "standing watch at the entrance"
        assert guard["activity_estimated_duration"] == 30
        assert guard["activity_duration_confidence"] == pytest.approx(0.80)

    def test_clears_activity(self, test_engine: GameEngine):
        # Set an activity, then clear it via Pass 2 outcome.
        test_engine.db.set_character_activity(
            character_id=2, activity="on patrol", started_at=180,
            duration_minutes=20, confidence=0.90, renewable=0,
        )
        from tests.fixtures.responses import PASS2_WITH_ACTIVITY_CLEAR
        test_engine._apply_outcome(_ACTION, PASS2_WITH_ACTIVITY_CLEAR)
        guard = test_engine.db.get_character(character_id=2)
        assert guard["current_activity"] is None

    def test_activity_confidence_is_clamped(self, test_engine: GameEngine):
        # confidence > 1.0 in outcome should be clamped to 1.0
        outcome = {
            **_empty_outcome(),
            "activity_updates": [
                {
                    "character_id": 2,
                    "activity": "extreme confidence activity",
                    "duration_minutes": 10,
                    "confidence": 5.0,   # should be clamped to 1.0
                    "renewable": 0,
                }
            ],
        }
        test_engine._apply_outcome(_ACTION, outcome)
        guard = test_engine.db.get_character(character_id=2)
        assert guard["activity_duration_confidence"] == pytest.approx(1.0)


# =============================================================================
# _apply_outcome — new_characters (lazy NPC creation)
# =============================================================================

class TestApplyOutcomeNewCharacters:
    def test_creates_new_npc(self, test_engine: GameEngine):
        from tests.fixtures.responses import PASS2_WITH_NEW_CHARACTER
        test_engine._apply_outcome(_ACTION, PASS2_WITH_NEW_CHARACTER)
        row = test_engine.db._row(
            "SELECT id FROM character WHERE game_id=1 AND name='Mysterious Stranger'"
        )
        assert row is not None, "Mysterious Stranger should have been created"

    def test_does_not_create_duplicate(self, test_engine: GameEngine):
        from tests.fixtures.responses import PASS2_WITH_NEW_CHARACTER
        test_engine._apply_outcome(_ACTION, PASS2_WITH_NEW_CHARACTER)
        test_engine._apply_outcome(_ACTION, PASS2_WITH_NEW_CHARACTER)  # second call
        rows = test_engine.db._rows(
            "SELECT id FROM character WHERE game_id=1 AND name='Mysterious Stranger'"
        )
        assert len(rows) == 1, "Duplicate NPC creation should be prevented"


# =============================================================================
# _check_activity_expiry
# =============================================================================

class TestActivityExpiry:
    def _set_guard_activity(self, db, started_at, duration, confidence, renewable):
        db.set_character_activity(
            character_id=2, activity="test activity",
            started_at=started_at, duration_minutes=duration,
            confidence=confidence, renewable=renewable,
        )

    def test_expired_activity_is_cleared(self, test_engine: GameEngine):
        # Activity started at 180, duration 10 min, confidence 0.90.
        # Clock is at 180 (from test DB seed); advance it past expiry first.
        self._set_guard_activity(test_engine.db, 180, 10, 0.90, 0)
        # Move the game clock to 191 (180 + 10 + 1 → past expiry)
        test_engine.db.advance_game_clock(instance_id=1, elapsed_minutes=11)
        test_engine._check_activity_expiry()
        guard = test_engine.db.get_character(character_id=2)
        assert guard["current_activity"] is None, \
            "Expired high-confidence non-renewable activity should be auto-cleared"

    def test_non_expired_activity_is_kept(self, test_engine: GameEngine):
        # Activity started at 180, duration 60 min, confidence 0.90.
        # Clock is still at 180 → 180 + 60 = 240 > 180 → not expired.
        self._set_guard_activity(test_engine.db, 180, 60, 0.90, 0)
        test_engine._check_activity_expiry()
        guard = test_engine.db.get_character(character_id=2)
        assert guard["current_activity"] == "test activity", \
            "Non-expired activity should not be cleared by _check_activity_expiry"

    def test_renewable_activity_is_not_auto_cleared(self, test_engine: GameEngine):
        # renewable=1: engine must never auto-clear, even if past duration.
        self._set_guard_activity(test_engine.db, 180, 5, 0.99, 1)
        test_engine.db.advance_game_clock(instance_id=1, elapsed_minutes=60)
        test_engine._check_activity_expiry()
        guard = test_engine.db.get_character(character_id=2)
        assert guard["current_activity"] == "test activity", \
            "Renewable activity should never be auto-cleared by the engine"

    def test_low_confidence_activity_is_not_auto_cleared(self, test_engine: GameEngine):
        # confidence < ACTIVITY_AUTO_CLEAR_CONFIDENCE (0.60) → only Pass 2 may clear.
        self._set_guard_activity(test_engine.db, 180, 5, 0.30, 0)
        test_engine.db.advance_game_clock(instance_id=1, elapsed_minutes=60)
        test_engine._check_activity_expiry()
        guard = test_engine.db.get_character(character_id=2)
        assert guard["current_activity"] == "test activity", \
            "Low-confidence activity should not be auto-cleared by the engine"


# =============================================================================
# _check_npc_wandering — suppression conditions
# =============================================================================

class TestNPCWanderSuppression:
    """
    Guard has wander_probability=1.0 and wander_range=[1,2] in the test world.
    Without suppression, _check_npc_wandering() will always move Guard to Hall (2).
    With suppression active, Guard stays at Antechamber (1).

    Each test activates one suppression condition and verifies Guard stays put.
    The final test verifies Guard actually moves when no suppression is in effect
    (confirms the positive case works, validating the suppression tests are not
    trivially passing because the wander mechanism itself is broken).
    """

    def test_pending_intent_suppresses_wander(self, test_engine: GameEngine):
        # Suppression 1: pending social obligation.
        test_engine.db.update_character_pending_intent(
            character_id=2, intent_text="owes Hero a favour"
        )
        test_engine._check_npc_wandering()
        guard = test_engine.db.get_character(character_id=2)
        assert guard["current_location_id"] == 1, \
            "Guard should not wander when pending_intent is set"

    def test_high_sleepiness_suppresses_wander(self, test_engine: GameEngine):
        # Suppression 2: sleepiness >= WANDER_SLEEPINESS_THRESHOLD (default 0.60).
        test_engine.db.update_internal_state(
            character_id=2, state_name="sleepiness", new_value=0.80
        )
        test_engine._check_npc_wandering()
        guard = test_engine.db.get_character(character_id=2)
        assert guard["current_location_id"] == 1, \
            "Guard should not wander when sleepiness is above threshold"

    def test_active_activity_suppresses_wander(self, test_engine: GameEngine):
        # Suppression 3: non-expired current_activity.
        # Set a 60-minute activity at the current clock time (180) → won't expire.
        test_engine.db.set_character_activity(
            character_id=2, activity="standing watch", started_at=180,
            duration_minutes=60, confidence=0.90, renewable=0,
        )
        test_engine._check_npc_wandering()
        guard = test_engine.db.get_character(character_id=2)
        assert guard["current_location_id"] == 1, \
            "Guard should not wander while current_activity is in progress"

    def test_guard_wanders_when_no_suppression(self, test_engine: GameEngine):
        # Positive control: no suppression conditions → Guard should move to Hall (2).
        # Guard has wander_probability=1.0 so the roll always fires.
        # Guard's sleepiness is 0.50 (below 0.60 threshold), no pending_intent,
        # no current_activity — all suppressions are inactive.
        test_engine._check_npc_wandering()
        guard = test_engine.db.get_character(character_id=2)
        assert guard["current_location_id"] == 2, \
            "Guard with wander_prob=1.0 and no suppression should move to Hall"

    def test_expired_activity_does_not_suppress_wander(self, test_engine: GameEngine):
        # An activity that meets all auto-expiry criteria (high confidence, non-renewable,
        # past its duration) should NOT suppress wandering.
        # Set activity started at 100, duration=10 min, confidence=0.90.
        # Current clock is 180 → 100 + 10 = 110 <= 180 → expired.
        test_engine.db.set_character_activity(
            character_id=2, activity="old patrol", started_at=100,
            duration_minutes=10, confidence=0.90, renewable=0,
        )
        test_engine._check_npc_wandering()
        guard = test_engine.db.get_character(character_id=2)
        assert guard["current_location_id"] == 2, \
            "Guard should wander when current_activity has already expired"


# =============================================================================
# Helpers
# =============================================================================

def _empty_outcome() -> dict:
    """Return a Pass 2 outcome dict with all list fields empty and minimal metadata."""
    from tests.fixtures.responses import PASS2_MINIMAL
    return dict(PASS2_MINIMAL)
