"""
tests/fixtures/responses.py — Canned LLM Response Fixtures

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

These fixtures serve two purposes:

1. Mock responses for Tier 1 (no-LLM) tests. The MockLLMClient in conftest.py
   returns these as if they had come from a real LLM backend.

2. Structural reference for Tier 2 (--llm) contract tests. validate.py checks
   real LLM output against the same schema these dicts embody.

Naming convention
-----------------
PASS1_MINIMAL     — Minimal valid Pass 1 action record (just required fields)
PASS2_MINIMAL     — Minimal valid Pass 2 adjudication outcome (empty effect lists)
PASS2_WITH_*      — Outcome variants that exercise specific output field handlers
PASS3_PROSE       — A short valid prose string (Pass 3 output is not JSON)

All character_id and location_id values match the test world in seed.py.
"""


# =============================================================================
# Pass 1 — Intent Parsing responses
# =============================================================================

# Minimal valid action record. Represents a simple speech action by Hero (id=1)
# directed at Guard (id=2).
PASS1_MINIMAL: dict = {
    "action_type": "speak",
    "verb": "greet",
    "target_character_id": 2,
    "target_item_id": None,
    "target_location_id": None,
    "inferred_goal": "establish friendly contact with the guard",
    "raw_input": "I say hello to the guard.",
}

# Move action: Hero moves from Antechamber (1) to Hall (2).
PASS1_MOVE: dict = {
    "action_type": "move",
    "verb": "walk",
    "target_character_id": None,
    "target_item_id": None,
    "target_location_id": 2,
    "inferred_goal": "reach the Hall",
    "raw_input": "walk to the hall",
}

# Examine action: Hero examines the Guard.
PASS1_EXAMINE: dict = {
    "action_type": "examine",
    "verb": "look at",
    "target_character_id": 2,
    "target_item_id": None,
    "target_location_id": None,
    "inferred_goal": "observe the guard's state",
    "raw_input": "look at the guard",
}


# =============================================================================
# Pass 2 — Outcome Adjudication responses
# =============================================================================

# Minimal valid outcome: no state changes, just metadata.
# All list fields must be present (empty lists are valid).
PASS2_MINIMAL: dict = {
    "outcome_type": "success",
    "narrative_beat": "Hero and Guard exchange a brief greeting.",
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
    "adjudication_notes": "Routine greeting; no significant effects.",
}

# Outcome with attitude delta: Guard's attitude toward Hero increases slightly.
PASS2_WITH_ATTITUDE_DELTA: dict = {
    **PASS2_MINIMAL,
    "attitude_deltas": [
        {
            "character_id": 2,      # Guard
            "target_id": 1,         # toward Hero
            "delta": 0.10,
            "attitude_type": "surface",
        }
    ],
    "narrative_beat": "The guard warms slightly to Hero's friendly greeting.",
    "adjudication_notes": "Guard's surface attitude toward Hero increases by 0.10.",
}

# Outcome with internal state delta: Hero's boredom decreases (interesting event).
PASS2_WITH_STATE_DELTA: dict = {
    **PASS2_MINIMAL,
    "internal_state_deltas": [
        {
            "character_id": 1,      # Hero
            "state_name": "boredom",
            "delta": -0.05,
        }
    ],
    "narrative_beat": "The interaction briefly relieves Hero's tedium.",
    "adjudication_notes": "Hero boredom reduced by 0.05.",
}

# Outcome with location_change: Hero moves from Antechamber (1) to Hall (2).
PASS2_WITH_LOCATION_CHANGE: dict = {
    **PASS2_MINIMAL,
    "location_change": [
        {
            "character_id": 1,          # Hero
            "new_location_id": 2,       # Hall (adjacent to Antechamber)
        }
    ],
    "narrative_beat": "Hero steps through the doorway into the Hall.",
    "adjudication_notes": "Hero moves from Antechamber to Hall.",
}

# Outcome with an INVALID location_change (non-adjacent destination).
# Used to verify the engine's adjacency guard ignores the move.
PASS2_WITH_INVALID_LOCATION_CHANGE: dict = {
    **PASS2_MINIMAL,
    "location_change": [
        {
            "character_id": 1,
            "new_location_id": 99,  # does not exist in test world
        }
    ],
    "narrative_beat": "Hero attempts to teleport somewhere that doesn't exist.",
    "adjudication_notes": "Hallucinated location — engine should discard.",
}

# Outcome with faction reputation change: Hero's standing with town_guard increases.
PASS2_WITH_FACTION_REP: dict = {
    **PASS2_MINIMAL,
    "faction_reputation_changes": [
        {
            "character_id": 1,
            "faction_name": "town_guard",
            "delta": 0.05,
            "reason": "Hero assisted the guard without being asked.",
        }
    ],
    "narrative_beat": "The guard is visibly pleased.",
    "adjudication_notes": "Hero's town_guard reputation +0.05.",
}

# Outcome with pending_intent update: Guard is given a social obligation.
PASS2_WITH_PENDING_INTENT: dict = {
    **PASS2_MINIMAL,
    "pending_intent_updates": [
        {
            "character_id": 2,      # Guard
            "pending_intent": "owes Hero a favour after she helped with the gate",
        }
    ],
    "narrative_beat": "The guard nods gratefully, clearly indebted.",
    "adjudication_notes": "Guard pending_intent set.",
}

# Outcome that clears a pending_intent (intent set to None / null).
PASS2_CLEAR_PENDING_INTENT: dict = {
    **PASS2_MINIMAL,
    "pending_intent_updates": [
        {
            "character_id": 2,
            "pending_intent": None,  # explicit clear
        }
    ],
    "narrative_beat": "The guard's debt is discharged.",
    "adjudication_notes": "Guard pending_intent cleared.",
}

# Outcome with activity update: Guard begins an activity.
PASS2_WITH_ACTIVITY_SET: dict = {
    **PASS2_MINIMAL,
    "activity_updates": [
        {
            "character_id": 2,
            "activity": "standing watch at the entrance",
            "duration_minutes": 30,
            "confidence": 0.80,
            "renewable": 0,
        }
    ],
    "narrative_beat": "The guard takes up a formal watch position.",
    "adjudication_notes": "Guard activity set: standing watch.",
}

# Outcome that explicitly clears an activity.
PASS2_WITH_ACTIVITY_CLEAR: dict = {
    **PASS2_MINIMAL,
    "activity_updates": [
        {
            "character_id": 2,
            "activity": None,   # explicit clear
        }
    ],
    "narrative_beat": "The guard relaxes from his post.",
    "adjudication_notes": "Guard activity cleared.",
}

# Outcome that triggers lazy NPC creation.
PASS2_WITH_NEW_CHARACTER: dict = {
    **PASS2_MINIMAL,
    "new_characters": [
        {
            "name": "Mysterious Stranger",
            "role": "npc_active",
            "species": "human",
            "gender": "unknown",
            "description": "A figure wrapped in a dark travelling cloak.",
            "current_location_id": 2,   # Hall
            "emotional_state": "guarded",
        }
    ],
    "narrative_beat": "A cloaked figure emerges from the shadows of the Hall.",
    "adjudication_notes": "New NPC created lazily: Mysterious Stranger.",
}

# Outcome with emotional state update for Guard.
PASS2_WITH_EMOTIONAL_UPDATE: dict = {
    **PASS2_MINIMAL,
    "emotional_state_updates": [
        {
            "character_id": 2,
            "emotional_state": "suspicious",
        }
    ],
    "narrative_beat": "The guard narrows his eyes.",
    "adjudication_notes": "Guard emotional state → suspicious.",
}


# =============================================================================
# Pass 3 — Prose Rendering responses
# =============================================================================

# A short valid prose string (Pass 3 output is plain text, not JSON).
PASS3_PROSE: str = (
    "You greet the guard with a nod. He returns it with the barest hint of "
    "warmth — the kind of warmth that costs a professional guard nothing, but "
    "means he has at least noticed you as a person rather than a liability."
)

# A longer opening scene prose sample, used in opening_scene tests.
PASS3_OPENING_PROSE: str = (
    "The antechamber is quiet, lit by a pair of wall-mounted torches whose "
    "light pools on the worn flagstones. The guard stands at the far wall, "
    "alert in the particular way of someone who has been on shift long enough "
    "to be bored but not yet long enough to be careless. Beyond the heavy "
    "door you can hear the distant murmur of the Hall."
)


# =============================================================================
# LLM evaluator judge response format
# (Used in test_pass1_eval.py and test_pass3_eval.py to parse judge output)
# =============================================================================

# The evaluator LLM should return JSON in this shape.
# Defined here so test files and rubrics share the same schema.
EVALUATOR_RESPONSE_SCHEMA: dict = {
    "verdict": "pass",          # "pass" | "fail"
    "score": 0.9,               # 0.0–1.0 overall quality score
    "criteria": {               # per-criterion results (criterion_name → bool)
        "example_criterion": True,
    },
    "notes": "Optional prose explanation of the verdict.",
}
