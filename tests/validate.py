"""
tests/validate.py — Pass 2 Output Validation Functions

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Shared validation logic for Pass 2 (adjudication) output. Used in two contexts:

1. test_pass2_contract.py — Tier 2 LLM tests that run a real Pass 2 call and
   check the output against this module's validators.

2. Future §3 engine implementation — The engine's planned pre-apply validation
   and retry layer (documented in implementation_status.md §3) will reuse
   these exact functions. Writing them here first means §3 is partly done
   before its engine session begins.

Design
------
validate_pass2_output() is the main entry point. It runs all checks and returns
a list of error strings. An empty list means the output is valid. Callers decide
what to do with errors (raise in tests; retry or strip in the engine).

Each sub-validator is a separate function so the engine can call them
individually — for example, to validate only location_change entries before
applying them, while still applying the rest of the outcome.

All validators receive:
  - The relevant slice of the outcome dict
  - A Database instance (for referential integrity checks)
  - The game_id (for scoping DB queries)

Nothing in this module modifies the database; all calls are read-only.
"""

from __future__ import annotations

import logging
from typing import Any

from engine.db import Database

logger = logging.getLogger(__name__)


# =============================================================================
# Required output fields
# =============================================================================

# Fields that must be present in every Pass 2 response. The engine relies on
# all of these being present (even as empty lists); absence indicates a
# structural failure in the LLM response.
REQUIRED_PASS2_FIELDS: frozenset[str] = frozenset({
    "outcome_type",
    "narrative_beat",
    "elapsed_minutes",
    "attitude_deltas",
    "internal_state_deltas",
    "emotional_state_updates",
    "location_change",
    "item_changes",
    "new_location_details",
    "faction_reputation_changes",
    "pending_intent_updates",
    "activity_updates",
    "npc_initiated_actions",
    "new_characters",
    "narrative_point_delta",
    "adjudication_notes",
})

# Valid outcome_type values. The engine does not gate behaviour on this field,
# but it is used for logging and future filtering. Out-of-vocabulary values
# suggest prompt drift.
VALID_OUTCOME_TYPES: frozenset[str] = frozenset({
    "success", "partial_success", "failure", "complication",
    "ambient", "social", "narrative",
})


# =============================================================================
# Main entry point
# =============================================================================

def validate_pass2_output(
    outcome: dict[str, Any],
    db: Database,
    game_id: int,
) -> list[str]:
    """
    Validate a Pass 2 adjudication outcome dict.

    Runs all checks and collects errors rather than raising on the first one,
    so callers get a complete picture of all problems in one call.

    Args:
        outcome:  The Pass 2 output dict (already parsed from JSON).
        db:       Open Database instance for referential integrity queries.
        game_id:  The active game's id (for scoping character/faction lookups).

    Returns:
        A list of human-readable error strings. Empty list = valid.
    """
    errors: list[str] = []

    errors.extend(_check_required_fields(outcome))
    errors.extend(_check_outcome_type(outcome))
    errors.extend(_check_elapsed_minutes(outcome))
    errors.extend(_check_attitude_deltas(outcome.get("attitude_deltas") or [], db, game_id))
    errors.extend(_check_internal_state_deltas(outcome.get("internal_state_deltas") or [], db, game_id))
    errors.extend(_check_emotional_state_updates(outcome.get("emotional_state_updates") or [], db, game_id))
    errors.extend(_check_location_changes(outcome.get("location_change") or [], db, game_id))
    errors.extend(_check_faction_reputation_changes(outcome.get("faction_reputation_changes") or [], db, game_id))
    errors.extend(_check_activity_updates(outcome.get("activity_updates") or [], db, game_id))

    return errors


# =============================================================================
# Individual validators
# =============================================================================

def _check_required_fields(outcome: dict) -> list[str]:
    """Return errors for any required top-level fields that are absent."""
    errors = []
    for field in REQUIRED_PASS2_FIELDS:
        if field not in outcome:
            errors.append(f"Missing required field: {field!r}")
    return errors


def _check_outcome_type(outcome: dict) -> list[str]:
    """Warn if outcome_type is not in the expected vocabulary."""
    errors = []
    ot = outcome.get("outcome_type")
    if ot is not None and ot not in VALID_OUTCOME_TYPES:
        # Not a hard error — the engine doesn't gate on this — but worth flagging.
        errors.append(
            f"Unexpected outcome_type {ot!r}. "
            f"Expected one of: {sorted(VALID_OUTCOME_TYPES)}"
        )
    return errors


def _check_elapsed_minutes(outcome: dict) -> list[str]:
    """elapsed_minutes must be a non-negative number."""
    errors = []
    em = outcome.get("elapsed_minutes")
    if em is None:
        errors.append("elapsed_minutes is missing or null.")
    elif not isinstance(em, (int, float)):
        errors.append(f"elapsed_minutes must be a number, got {type(em).__name__}: {em!r}")
    elif em < 0:
        errors.append(f"elapsed_minutes must be >= 0, got {em}")
    return errors


def _check_attitude_deltas(deltas: list, db: Database, game_id: int) -> list[str]:
    """
    Each attitude_delta must reference characters that exist in the DB and
    supply a delta in [-2.0, 2.0] (wide range to allow dramatic swings while
    catching obviously wrong values like 100.0).
    """
    errors = []
    for i, delta in enumerate(deltas):
        prefix = f"attitude_deltas[{i}]"
        for field in ("character_id", "target_id", "delta"):
            if field not in delta:
                errors.append(f"{prefix}: missing field {field!r}")
        try:
            char_id = int(delta["character_id"])
            target_id = int(delta["target_id"])
            d = float(delta["delta"])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{prefix}: cannot parse fields — {exc}")
            continue

        if db.get_character(char_id) is None:
            errors.append(f"{prefix}: character_id={char_id} does not exist")
        if db.get_character(target_id) is None:
            errors.append(f"{prefix}: target_id={target_id} does not exist")
        if not (-2.0 <= d <= 2.0):
            errors.append(f"{prefix}: delta={d} is out of plausible range [-2.0, 2.0]")

    return errors


def _check_internal_state_deltas(deltas: list, db: Database, game_id: int) -> list[str]:
    """
    Each internal_state_delta must reference an existing character and a
    plausible delta magnitude.
    """
    errors = []
    for i, delta in enumerate(deltas):
        prefix = f"internal_state_deltas[{i}]"
        for field in ("character_id", "state_name", "delta"):
            if field not in delta:
                errors.append(f"{prefix}: missing field {field!r}")
        try:
            char_id = int(delta["character_id"])
            d = float(delta["delta"])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{prefix}: cannot parse fields — {exc}")
            continue

        if db.get_character(char_id) is None:
            errors.append(f"{prefix}: character_id={char_id} does not exist")
        if not (-1.0 <= d <= 1.0):
            errors.append(
                f"{prefix}: delta={d} is out of range [-1.0, 1.0]. "
                "Internal states are clamped to [0.0, 1.0]; single-turn deltas "
                "larger than 1.0 almost certainly indicate a prompt engineering problem."
            )

    return errors


def _check_emotional_state_updates(updates: list, db: Database, game_id: int) -> list[str]:
    """emotional_state must be a non-empty string for an existing character."""
    errors = []
    for i, update in enumerate(updates):
        prefix = f"emotional_state_updates[{i}]"
        try:
            char_id = int(update["character_id"])
            state = str(update["emotional_state"])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{prefix}: cannot parse fields — {exc}")
            continue

        if db.get_character(char_id) is None:
            errors.append(f"{prefix}: character_id={char_id} does not exist")
        if not state.strip():
            errors.append(f"{prefix}: emotional_state is empty")

    return errors


def _check_location_changes(changes: list, db: Database, game_id: int) -> list[str]:
    """
    Each location_change must reference an existing character and a location
    that is adjacent (passable connection) to their current location.

    This mirrors the engine's Guard 1 and Guard 2 in _apply_outcome().
    """
    errors = []
    # Normalise single-dict to list (backwards compat mirror of engine code).
    if isinstance(changes, dict):
        changes = [changes]

    for i, change in enumerate(changes):
        prefix = f"location_change[{i}]"
        try:
            char_id = int(change["character_id"])
            new_loc_id = int(change["new_location_id"])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{prefix}: cannot parse fields — {exc}")
            continue

        char = db.get_character(char_id)
        if char is None:
            errors.append(f"{prefix}: character_id={char_id} does not exist")
            continue

        if db.get_location(new_loc_id) is None:
            errors.append(
                f"{prefix}: new_location_id={new_loc_id} does not exist in DB "
                "(LLM may have hallucinated a location from prose context)"
            )
            continue

        from_loc_id = char["current_location_id"]
        if from_loc_id is not None and from_loc_id != new_loc_id:
            if not db.is_location_connected(from_loc_id, new_loc_id):
                errors.append(
                    f"{prefix}: loc {from_loc_id} → {new_loc_id} is not a passable "
                    "connection for character_id={char_id}"
                )

    return errors


def _check_faction_reputation_changes(changes: list, db: Database, game_id: int) -> list[str]:
    """
    Each faction_reputation_change must reference an existing character and a
    known faction (by name within this game_id), with a delta in [-1.0, 1.0].
    """
    errors = []
    for i, change in enumerate(changes):
        prefix = f"faction_reputation_changes[{i}]"
        try:
            char_id = int(change["character_id"])
            fname = str(change["faction_name"])
            d = float(change["delta"])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{prefix}: cannot parse fields — {exc}")
            continue

        if db.get_character(char_id) is None:
            errors.append(f"{prefix}: character_id={char_id} does not exist")

        faction = db.get_or_create_faction(game_id, fname)
        if faction is None:
            errors.append(
                f"{prefix}: faction {fname!r} not found for game_id={game_id} "
                "and could not be created"
            )

        if not (-1.0 <= d <= 1.0):
            errors.append(
                f"{prefix}: delta={d} is out of range [-1.0, 1.0]. "
                "Reputation is clamped to [0.0, 1.0]; a single-turn delta "
                "> 1.0 is almost certainly a model error."
            )

    return errors


def _check_activity_updates(updates: list, db: Database, game_id: int) -> list[str]:
    """
    Each activity_update must reference an existing character. If activity is
    set (not None), confidence must be in [0.0, 1.0] and renewable must be 0 or 1.
    """
    errors = []
    for i, update in enumerate(updates):
        prefix = f"activity_updates[{i}]"
        try:
            char_id = int(update["character_id"])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{prefix}: cannot parse character_id — {exc}")
            continue

        if db.get_character(char_id) is None:
            errors.append(f"{prefix}: character_id={char_id} does not exist")

        activity = update.get("activity")
        if activity is not None:
            # confidence is optional but must be in range if present.
            confidence = update.get("confidence")
            if confidence is not None:
                try:
                    c = float(confidence)
                    if not (0.0 <= c <= 1.0):
                        errors.append(
                            f"{prefix}: confidence={c} out of range [0.0, 1.0]"
                        )
                except (TypeError, ValueError):
                    errors.append(
                        f"{prefix}: confidence={confidence!r} is not a float"
                    )

            renewable = update.get("renewable", 0)
            if renewable not in (0, 1, True, False):
                errors.append(
                    f"{prefix}: renewable={renewable!r} must be 0 or 1"
                )

    return errors
