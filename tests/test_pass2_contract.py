"""
tests/test_pass2_contract.py — Pass 2 Output Contract Tests (Tier 2: --llm)

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

These tests run a real Pass 2 LLM call and assert structural/mechanical
properties of the response. They do NOT evaluate prose quality (that is
test_pass3_eval.py's job), and they do NOT assess whether the narrative
outcome is sensible (that requires human or LLM-as-judge evaluation).

What these tests verify
-----------------------
- The response is valid JSON with all required fields present
- Float values are within expected ranges
- Character IDs referenced in the output exist in the database
- Location changes point to adjacent, valid location IDs
- Activity confidence values are in [0.0, 1.0]
- Faction names referenced correspond to known or creatable factions

This is the "does the model respect the output contract?" tier. It uses
the shared validate_pass2_output() function from tests/validate.py, which
is also the planned implementation for the engine's §3 retry layer.

To run these tests:
    pytest --llm

Requires:
    ANTHROPIC_API_KEY environment variable
    The test database (created automatically by the tmp_db fixture)
"""

import json
import pytest

from engine.context import build_pass1_packet, build_pass2_packet
from engine.llm import get_llm_client
from engine.db import Database
from tests.validate import validate_pass2_output


# =============================================================================
# Contract tests
# =============================================================================

@pytest.mark.llm
class TestPass2Contract:
    """
    Each test in this class:
    1. Sets up a known DB state
    2. Builds a real Pass 2 context packet from that state
    3. Calls the real LLM (via the configured backend)
    4. Validates the structured output with validate_pass2_output()

    Tests use the minimal test world and a simple player action so the context
    packet is small and costs are kept low. These tests are not trying to
    exercise complex narrative scenarios — they are verifying structural contract.
    """

    @pytest.fixture(autouse=True)
    def _llm(self):
        """Shared LLM client for all tests in this class."""
        self.llm = get_llm_client()

    def _call_pass2(self, db: Database, action_record: dict) -> dict:
        """Build a Pass 2 context packet, call the LLM, and parse the response."""
        from engine.engine import PASS2_PROMPT_TEMPLATE
        packet = build_pass2_packet(db=db, game_id=1, action_record=action_record)
        prompt = PASS2_PROMPT_TEMPLATE.format(context_json=json.dumps(packet, indent=2))
        return self.llm.call_json(prompt)

    def test_speak_action_has_valid_structure(self, tmp_db: Database):
        """A simple speech action should return a structurally valid Pass 2 response."""
        from tests.fixtures.responses import PASS1_MINIMAL
        outcome = self._call_pass2(db=tmp_db, action_record=PASS1_MINIMAL)
        errors = validate_pass2_output(outcome, db=tmp_db, game_id=1)
        assert not errors, (
            f"Pass 2 output failed structural validation:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    def test_move_action_location_change_is_adjacent(self, tmp_db: Database):
        """A move action's location_change (if any) must point to an adjacent location."""
        from tests.fixtures.responses import PASS1_MOVE
        outcome = self._call_pass2(db=tmp_db, action_record=PASS1_MOVE)

        # Validate full output structure first.
        errors = validate_pass2_output(outcome, db=tmp_db, game_id=1)
        assert not errors, (
            "Pass 2 output for move action failed structural validation:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )

    def test_elapsed_minutes_is_plausible(self, tmp_db: Database):
        """elapsed_minutes should be a positive integer or float, not zero or enormous."""
        from tests.fixtures.responses import PASS1_MINIMAL
        outcome = self._call_pass2(db=tmp_db, action_record=PASS1_MINIMAL)
        em = outcome.get("elapsed_minutes", 0)
        assert isinstance(em, (int, float)), \
            f"elapsed_minutes should be numeric, got {type(em)}"
        assert 0 < em <= 60, \
            f"elapsed_minutes={em} is outside plausible range (0, 60] for a social action"

    def test_float_fields_are_in_range(self, tmp_db: Database):
        """
        All float fields in the output should be within their specified ranges.
        validate_pass2_output covers this, but this test makes it explicit.
        """
        from tests.fixtures.responses import PASS1_MINIMAL
        outcome = self._call_pass2(db=tmp_db, action_record=PASS1_MINIMAL)

        # Check attitude delta magnitudes
        for delta in outcome.get("attitude_deltas") or []:
            d = float(delta.get("delta", 0))
            assert -2.0 <= d <= 2.0, f"Attitude delta {d} out of range [-2.0, 2.0]"

        # Check internal state delta magnitudes
        for delta in outcome.get("internal_state_deltas") or []:
            d = float(delta.get("delta", 0))
            assert -1.0 <= d <= 1.0, f"State delta {d} out of range [-1.0, 1.0]"

        # Check activity confidence values
        for update in outcome.get("activity_updates") or []:
            if update.get("activity") is not None:
                c = update.get("confidence")
                if c is not None:
                    c = float(c)
                    assert 0.0 <= c <= 1.0, f"Activity confidence {c} out of range [0.0, 1.0]"
