"""
tests/test_pass3_eval.py — Pass 3 Prose Rendering Evaluation Tests (Tier 3: --llm-eval)

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

These tests run a real Pass 3 LLM call and then send the output to a second
"judge" LLM call that evaluates prose quality against the PASS3_RUBRIC.

Pass 3 is the hardest pass to test mechanically because:
  - The output is prose, not structured JSON
  - Quality criteria are qualitative (appropriate length, no verbal tics,
    second person, genre-appropriate register)
  - The same criterion can be satisfied by many different phrasings

LLM-as-judge is the right tool here. The judge evaluates:
  - Is the prose in second person?
  - Does it accurately reflect the outcome facts?
  - Is it within the expected length range (3–6 sentences)?
  - Does it avoid mechanical exposition (floats, delta values)?
  - Does it avoid the known verbal tic pattern?
  - Is it genre-appropriate?

Test design
-----------
Each test:
  1. Sets up a known DB state and a known outcome dict (so we know exactly what
     facts the prose should reflect).
  2. Runs a real Pass 3 call.
  3. Passes the outcome + prose to the judge LLM with the PASS3_RUBRIC.
  4. Asserts the judge returns 'pass'.

To run these tests:
    pytest --llm-eval

Requires:
    ANTHROPIC_API_KEY environment variable
    These tests are expensive (2 LLM calls per test). Run infrequently.

Extension guidance
------------------
To add a new Pass 3 evaluation test:
  1. Define an outcome dict (or use one from tests/fixtures/responses.py).
  2. Optionally modify the DB state so the outcome reflects an interesting scene.
  3. Call _run_pass3(db, outcome) → prose.
  4. Call _judge_pass3_output(outcome, prose) → verdict.
  5. Call _assert_verdict(verdict, outcome, prose).
  6. Optionally add mechanical assertions (e.g. assert 'you' in prose.lower()).

Consider adding cases that cover:
  - Opening scene prose (OPENING_SCENE_PROMPT_TEMPLATE vs PASS3_PROMPT_TEMPLATE)
  - NPC speech rendering (check that NPCs speak in character register)
  - Multi-character scene (several characters present at once)
  - Involuntary event prose (hairball, sneeze)
  - The verbal tic check specifically (run many samples, look for pattern)
"""

import json
import os
import pytest

from engine.context import build_pass3_packet
from engine.llm import get_llm_client
from engine.db import Database

from tests.fixtures.eval_rubrics import build_pass3_eval_prompt, PASS3_RUBRIC
from tests.fixtures.responses import (
    PASS2_MINIMAL,
    PASS2_WITH_ATTITUDE_DELTA,
    PASS2_WITH_EMOTIONAL_UPDATE,
)


# =============================================================================
# Pass 3 evaluation tests
# =============================================================================

@pytest.mark.llm_eval
class TestPass3Eval:
    """
    Each test calls real Pass 3, then judges the prose with a second LLM call.
    """

    @pytest.fixture(autouse=True)
    def _llm_clients(self):
        """Primary LLM (for Pass 3) and evaluator LLM (for judging)."""
        import os
        from engine import config as cfg

        self.pass3_llm = get_llm_client()

        eval_model = os.environ.get("DAVE_EVAL_MODEL", "claude-haiku-4-5-20251001")
        original_model = os.environ.get("DAVE_CLAUDE_MODEL", cfg.CLAUDE_MODEL)
        os.environ["DAVE_CLAUDE_MODEL"] = eval_model
        self.eval_llm = get_llm_client()
        os.environ["DAVE_CLAUDE_MODEL"] = original_model

    def _run_pass3(self, db: Database, outcome: dict) -> str:
        """Build a Pass 3 context packet and call the real LLM."""
        from engine.engine import PASS3_PROMPT_TEMPLATE
        packet = build_pass3_packet(db=db, game_id=1, outcome=outcome)
        prompt = PASS3_PROMPT_TEMPLATE.format(
            context_json=json.dumps(packet, indent=2)
        )
        return self.pass3_llm.call(prompt)

    def _judge_pass3_output(
        self, outcome: dict, prose: str,
        game_genre: str = "adventure", game_tone: str = "neutral"
    ) -> dict:
        """Call the judge LLM and parse its evaluation response."""
        eval_prompt = build_pass3_eval_prompt(
            outcome=outcome, prose=prose,
            game_genre=game_genre, game_tone=game_tone,
        )
        return self.eval_llm.call_json(eval_prompt)

    # -----------------------------------------------------------------------
    # Test cases
    # -----------------------------------------------------------------------

    def test_ambient_outcome_prose(self, tmp_db: Database):
        """
        A minimal ambient outcome (no state changes) should produce prose that
        is second-person, length-appropriate, and genre-consistent.
        """
        prose = self._run_pass3(db=tmp_db, outcome=PASS2_MINIMAL)

        # Mechanical checks (fast, no LLM)
        assert len(prose) > 20, "Prose should not be a trivially short stub"
        assert "you" in prose.lower() or "your" in prose.lower(), \
            "Prose should use second-person voice"

        # Judge evaluation
        verdict = self._judge_pass3_output(PASS2_MINIMAL, prose)
        _assert_verdict(verdict, PASS2_MINIMAL, prose)

    def test_emotional_state_change_reflected_in_prose(self, tmp_db: Database):
        """
        When the outcome includes an emotional_state_update for the Guard,
        the prose should reflect the Guard's changed demeanour without
        directly stating the mechanical change.
        """
        prose = self._run_pass3(db=tmp_db, outcome=PASS2_WITH_EMOTIONAL_UPDATE)

        # Mechanical check: the prose should not expose the raw emotional_state string
        # as a bare mechanical label (though it may paraphrase it).
        assert "emotional_state" not in prose.lower(), \
            "Prose should not expose the field name 'emotional_state'"

        verdict = self._judge_pass3_output(PASS2_WITH_EMOTIONAL_UPDATE, prose)
        _assert_verdict(verdict, PASS2_WITH_EMOTIONAL_UPDATE, prose)

    def test_no_verbal_tic_pattern(self, tmp_db: Database):
        """
        Checks for the known verbal tic: '[verb] with the [air/manner] of someone who'.
        This is a Pass 3 specific regression test; add to rubric notes if it recurs.
        """
        prose = self._run_pass3(db=tmp_db, outcome=PASS2_MINIMAL)

        # Direct mechanical check for the known tic pattern.
        tic_indicators = ["with the air of someone who", "with the manner of someone who"]
        for indicator in tic_indicators:
            assert indicator not in prose.lower(), (
                f"Verbal tic detected in prose: {indicator!r}\n"
                f"Full prose: {prose}"
            )

    # -----------------------------------------------------------------------
    # Add more test cases below following the same pattern.
    # See module docstring for suggested extensions.
    # -----------------------------------------------------------------------


# =============================================================================
# Verdict assertion helper
# =============================================================================

def _assert_verdict(verdict: dict, outcome: dict, prose: str) -> None:
    """
    Assert that the judge LLM returned a 'pass' verdict and log details on failure.
    """
    assert isinstance(verdict, dict), \
        f"Judge response should be a dict, got {type(verdict)}"
    assert "verdict" in verdict, f"Judge response missing 'verdict' key: {verdict}"

    failing_criteria = [
        name for name, passed in verdict.get("criteria", {}).items() if not passed
    ]

    assert verdict["verdict"] == "pass", (
        f"Pass 3 prose failed evaluation.\n"
        f"Failing criteria: {failing_criteria}\n"
        f"Judge notes: {verdict.get('notes', '(none)')}\n"
        f"Score: {verdict.get('score', 'N/A')}\n"
        f"Prose: {prose!r}\n"
        f"Outcome narrative_beat: {outcome.get('narrative_beat', '(none)')!r}"
    )
