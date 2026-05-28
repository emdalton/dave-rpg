"""
tests/test_pass1_eval.py — Pass 1 Intent Parsing Evaluation Tests (Tier 3: --llm-eval)

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

These tests run a real Pass 1 LLM call and then send the output to a second
"judge" LLM call that evaluates intent parsing quality against a rubric.

Pass 1 is well-suited to LLM-as-judge evaluation because:
  - The output is structured JSON (easy to pass to a judge)
  - The criteria are rule-based (did it resolve the pronoun correctly? did it
    pick the right action_type? does it reference a valid location id?)
  - Some criteria require semantic judgment that mechanical checks cannot make
    (e.g. "is 'converse' a reasonable mapping for 'chat with the guard'?")

Test design
-----------
Each test provides a specific player input string + context and asserts that:
  1. The real Pass 1 output is valid JSON with required fields (structural check,
     reused from the validate module).
  2. The judge LLM rates the output at or above a pass threshold on the
     PASS1_RUBRIC criteria.

Both failures are reported separately so debugging is clear: structural
failures indicate prompt engineering problems; rubric failures indicate
interpretation or intent-resolution problems.

To run these tests:
    pytest --llm-eval

Requires:
    ANTHROPIC_API_KEY environment variable
    These tests are expensive (2 LLM calls per test). Run infrequently.

Extension guidance
------------------
To add a new Pass 1 evaluation test case:
  1. Define a player_input string and an optional expected action_type or
     target for assertion context.
  2. Call _eval_pass1_output(self, db, player_input) → (action_record, verdict).
  3. Assert verdict["verdict"] == "pass" and log any failing criteria.
  4. Optionally add a mechanical assertion for specific fields (e.g. move
     actions must have a non-null target_location_id).

Consider adding cases that cover:
  - Pronoun resolution: "look at her" when only one female NPC is present
  - Ambiguous destination: "go upstairs" when there is no 'stairs' in known_locations
  - Multi-word action: "slowly walk over to the guard and greet him"
  - Dialect / abbreviation: "wanna go check out the hall"
"""

import json
import os
import pytest

from engine.context import build_pass1_packet
from engine.llm import get_llm_client
from engine.db import Database

from tests.fixtures.eval_rubrics import build_pass1_eval_prompt, PASS1_RUBRIC
from tests.fixtures.responses import EVALUATOR_RESPONSE_SCHEMA


# =============================================================================
# Pass 1 evaluation tests
# =============================================================================

@pytest.mark.llm_eval
class TestPass1Eval:
    """
    Each test calls real Pass 1, then judges the output with a second LLM call.
    The judge model is configured via DAVE_EVAL_MODEL (defaults to
    claude-haiku-4-5-20251001 for cost efficiency).
    """

    @pytest.fixture(autouse=True)
    def _llm_clients(self):
        """Primary LLM (for Pass 1) and evaluator LLM (for judging)."""
        import os
        from engine import config as cfg

        self.pass1_llm = get_llm_client()

        # Allow a separate, cheaper model for evaluation calls.
        eval_model = os.environ.get("DAVE_EVAL_MODEL", "claude-haiku-4-5-20251001")
        original_model = os.environ.get("DAVE_CLAUDE_MODEL", cfg.CLAUDE_MODEL)

        # Temporarily swap the model for the evaluator client.
        os.environ["DAVE_CLAUDE_MODEL"] = eval_model
        self.eval_llm = get_llm_client()
        os.environ["DAVE_CLAUDE_MODEL"] = original_model

    def _run_pass1(self, db: Database, player_input: str) -> dict:
        """Build a Pass 1 context packet and call the real LLM."""
        from engine.engine import PASS1_PROMPT_TEMPLATE
        packet = build_pass1_packet(db=db, game_id=1, player_input=player_input)
        prompt = PASS1_PROMPT_TEMPLATE.format(
            context_json=json.dumps(packet, indent=2),
            player_input=player_input,
        )
        return self.pass1_llm.call_json(prompt)

    def _judge_pass1_output(
        self, player_input: str, context_packet: dict, action_record: dict
    ) -> dict:
        """Call the judge LLM and parse its evaluation response."""
        eval_prompt = build_pass1_eval_prompt(
            player_input=player_input,
            context_packet=context_packet,
            action_record=action_record,
        )
        raw = self.eval_llm.call_json(eval_prompt)
        return raw

    # -----------------------------------------------------------------------
    # Test cases
    # -----------------------------------------------------------------------

    def test_simple_speak_action(self, tmp_db: Database):
        """
        'Say hello to the guard' — the most basic speech action.
        Pass 1 should produce action_type='speak' with target_character_id=2 (Guard).
        """
        player_input = "Say hello to the guard."
        action_record = self._run_pass1(db=tmp_db, player_input=player_input)

        # Structural check
        assert "action_type" in action_record, "action_type must be present"
        assert action_record["action_type"] in (
            "speak", "interact"
        ), f"Expected speak or interact, got {action_record['action_type']!r}"

        # Evaluator check
        from engine.context import build_pass1_packet
        context_packet = build_pass1_packet(
            db=tmp_db, game_id=1, player_input=player_input
        )
        verdict = self._judge_pass1_output(player_input, context_packet, action_record)
        _assert_verdict(verdict, player_input, action_record)

    def test_move_action_resolves_location_name(self, tmp_db: Database):
        """
        'Walk to the Hall' — Pass 1 should resolve 'Hall' to location_id=2.
        Movement phrasing must produce action_type='move' with a non-null target_location_id.
        """
        player_input = "Walk to the Hall."
        action_record = self._run_pass1(db=tmp_db, player_input=player_input)

        assert action_record.get("action_type") == "move", \
            f"Expected action_type='move', got {action_record.get('action_type')!r}"
        assert action_record.get("target_location_id") is not None, \
            "Move action must have a non-null target_location_id"
        assert action_record["target_location_id"] == 2, \
            "Pass 1 should resolve 'Hall' to location_id=2"

        from engine.context import build_pass1_packet
        context_packet = build_pass1_packet(
            db=tmp_db, game_id=1, player_input=player_input
        )
        verdict = self._judge_pass1_output(player_input, context_packet, action_record)
        _assert_verdict(verdict, player_input, action_record)

    # -----------------------------------------------------------------------
    # Add more test cases below following the same pattern.
    # Suggested additions (see module docstring for details):
    #   - Pronoun resolution
    #   - Ambiguous destination
    #   - Multi-word/natural action phrasing
    #   - Dialect / abbreviation
    # -----------------------------------------------------------------------


# =============================================================================
# Verdict assertion helper
# =============================================================================

def _assert_verdict(verdict: dict, player_input: str, action_record: dict) -> None:
    """
    Assert that the judge LLM returned a 'pass' verdict and log details on failure.

    Formats a detailed failure message that shows which criteria failed,
    making it easy to diagnose whether the problem is in Pass 1's intent
    parsing or in the rubric/judge itself.
    """
    assert isinstance(verdict, dict), \
        f"Judge response should be a dict, got {type(verdict)}"
    assert "verdict" in verdict, f"Judge response missing 'verdict' key: {verdict}"
    assert "criteria" in verdict, f"Judge response missing 'criteria' key: {verdict}"

    failing_criteria = [
        name for name, passed in verdict.get("criteria", {}).items() if not passed
    ]

    assert verdict["verdict"] == "pass", (
        f"Pass 1 output failed evaluation for input: {player_input!r}\n"
        f"Failing criteria: {failing_criteria}\n"
        f"Judge notes: {verdict.get('notes', '(none)')}\n"
        f"Score: {verdict.get('score', 'N/A')}\n"
        f"Action record: {json.dumps(action_record, indent=2)}"
    )
