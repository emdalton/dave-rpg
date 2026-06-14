"""
tests/fixtures/eval_rubrics.py — LLM-as-Judge Evaluation Rubrics

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Used by test_pass1_eval.py and test_pass3_eval.py (both @pytest.mark.llm_eval).
These tests run real LLM calls and then send the output to a second "judge"
LLM call that evaluates quality against a rubric.

Design principles
-----------------
- Rubrics evaluate structural and behavioral properties, not specific content.
  The judge should not penalise creative prose for choosing one synonym over
  another; it should penalise prose that speaks of the player character in
  third person when second person is required.
- Each criterion is a yes/no question. The judge returns a boolean per criterion
  and an overall verdict and score.
- Rubrics are plain dicts so they can be version-controlled and diffed.
- The prompt templates use f-strings; call the build_*_eval_prompt() functions
  to construct the complete evaluator prompt for a given test case.

Judge model recommendation
--------------------------
Use claude-haiku-4-5-20251001 for evaluation calls to keep costs low.
The judge is assessing structural and rule-following properties, not subtle
prose quality; Haiku is sufficient for this task. Set via DAVE_EVAL_MODEL env
var in the llm_eval test fixtures (see test_pass1_eval.py).
"""

import json


# =============================================================================
# Pass 1 rubric — Intent Parsing quality
# =============================================================================

PASS1_CRITERIA: dict[str, str] = {
    "valid_action_type": (
        "Does action_type belong to the valid set: "
        "move, interact, speak, examine, take, drop, use, wait, involuntary?"
    ),
    "verb_is_plain_english": (
        "Is the verb field a short, plain-English verb phrase (not a sentence)?"
    ),
    "move_has_target_location": (
        "If action_type is 'move', is target_location_id a non-null integer?"
    ),
    "speak_has_target_character": (
        "If action_type is 'speak' and the input addresses a specific character, "
        "is target_character_id a non-null integer?"
    ),
    "no_hallucinated_ids": (
        "Are all non-null id fields (target_character_id, target_item_id, "
        "target_location_id) integers, not strings or invented names?"
    ),
    "character_id_valid_in_context": (
        "If target_character_id is set, does its value appear as an 'id' in "
        "the known_characters list from the context packet? An id that is not "
        "present in known_characters is a hallucination. If no character is "
        "targeted (target_character_id is null), this criterion passes automatically."
    ),
    "inferred_goal_is_brief": (
        "Is inferred_goal a brief phrase (< 12 words) describing player intent, "
        "not a full sentence?"
    ),
}

PASS1_RUBRIC: dict = {
    "criteria": PASS1_CRITERIA,
    "pass_threshold": 0.80,   # fraction of criteria that must be True for a 'pass' verdict
    "notes": (
        "Pass 1 is purely structural. The judge must not penalise interpretation "
        "choices (e.g. whether 'chat with the guard' maps to 'speak' vs 'interact') "
        "unless the choice is clearly wrong given the input."
    ),
}


def build_pass1_eval_prompt(
    player_input: str,
    context_packet: dict,
    action_record: dict,
) -> str:
    """
    Build the complete evaluator prompt for a Pass 1 output.

    Args:
        player_input:   The raw text the player typed.
        context_packet: The Pass 1 context packet sent to the LLM.
        action_record:  The Pass 1 output dict to be evaluated.

    Returns:
        A prompt string for the judge LLM. The judge should return JSON matching
        EVALUATOR_RESPONSE_SCHEMA from tests/fixtures/responses.py.
    """
    criteria_block = "\n".join(
        f'  "{name}": {desc}' for name, desc in PASS1_CRITERIA.items()
    )
    return f"""\
You are evaluating the output of an intent-parsing LLM (Pass 1 of the DAVE RPG Engine).

PLAYER INPUT:
{player_input!r}

CONTEXT PACKET (abbreviated):
{json.dumps(context_packet, indent=2)[:800]}

PASS 1 OUTPUT TO EVALUATE:
{json.dumps(action_record, indent=2)}

CRITERIA (evaluate each as true/false):
{criteria_block}

Return a single JSON object with this exact structure:
{{
  "verdict": "pass" | "fail",
  "score": <float 0.0–1.0, fraction of criteria that are true>,
  "criteria": {{<criterion_name>: true | false, ...}},
  "notes": "<optional explanation>"
}}

Return only the JSON object. No prose, no markdown fences.
"""


# =============================================================================
# Pass 3 rubric — Prose Rendering quality
# =============================================================================

PASS3_CRITERIA: dict[str, str] = {
    "second_person": (
        "Is the prose consistently in second person "
        "('you', 'your') rather than third person?"
    ),
    "matches_outcome_facts": (
        "Does the prose accurately reflect the key facts in the outcome JSON "
        "(who did what, where, with what result)? It need not be exhaustive."
    ),
    "appropriate_length": (
        "Is the prose 3–6 sentences? (Reject both single-sentence stubs and "
        "multi-paragraph walls of text.)"
    ),
    "no_mechanical_exposition": (
        "Does the prose avoid directly stating mechanical values "
        "(e.g. 'your boredom increased by 0.05', 'attitude delta +0.10')?"
    ),
    "no_verbal_tic": (
        "Does the prose avoid the specific verbal tic pattern: "
        "'[action] with the [air/manner] of someone who [clause]'?"
    ),
    "genre_appropriate": (
        "Is the prose appropriate to the game's genre and tone "
        "(adventure, neutral)? No anachronisms, no inappropriate register shifts."
    ),
}

PASS3_RUBRIC: dict = {
    "criteria": PASS3_CRITERIA,
    "pass_threshold": 0.80,
    "notes": (
        "Pass 3 is qualitative. The judge must focus on rule-following "
        "(second person, no mechanical exposition, correct facts) rather than "
        "stylistic preference. Creative variation in sentence structure is expected "
        "and should not be penalised."
    ),
}


def build_pass3_eval_prompt(
    outcome: dict,
    prose: str,
    game_genre: str = "adventure",
    game_tone: str = "neutral",
) -> str:
    """
    Build the complete evaluator prompt for a Pass 3 prose output.

    Args:
        outcome:     The Pass 2 adjudication outcome dict the prose was rendered from.
        prose:       The Pass 3 prose string to evaluate.
        game_genre:  The module's genre string (from game record).
        game_tone:   The module's tone string (from game record).

    Returns:
        A prompt string for the judge LLM. The judge should return JSON matching
        EVALUATOR_RESPONSE_SCHEMA from tests/fixtures/responses.py.
    """
    criteria_block = "\n".join(
        f'  "{name}": {desc}' for name, desc in PASS3_CRITERIA.items()
    )
    return f"""\
You are evaluating the output of a prose-rendering LLM (Pass 3 of the DAVE RPG Engine).
Game genre: {game_genre}. Game tone: {game_tone}.

ADJUDICATION OUTCOME (the facts the prose should reflect):
{json.dumps(outcome, indent=2)[:600]}

PASS 3 PROSE TO EVALUATE:
{prose!r}

CRITERIA (evaluate each as true/false):
{criteria_block}

Return a single JSON object with this exact structure:
{{
  "verdict": "pass" | "fail",
  "score": <float 0.0–1.0, fraction of criteria that are true>,
  "criteria": {{<criterion_name>: true | false, ...}},
  "notes": "<optional explanation>"
}}

Return only the JSON object. No prose, no markdown fences.
"""
