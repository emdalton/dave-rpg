"""
engine/engine.py — DAVE RPG Engine Main Game Loop

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

The GameEngine class drives one complete play session. It connects the database,
the LLM client, and the context packet assembler into a turn loop that:

    1. Checks for involuntary events (hairballs, etc.) before processing input
    2. Runs Pass 1 (intent parsing) to convert player text to a structured action
    3. Runs Pass 2 (adjudication) to determine outcome and all DB changes
    4. Writes all outcome changes to the database
    5. Runs Pass 3 (prose rendering) to produce player-facing narrative
    6. Displays the prose and loops

The engine is intentionally thin: it orchestrates the passes and writes results,
but all world knowledge lives in the database and all reasoning happens in the LLM.
The engine never infers or hardcodes game logic.

Exit conditions:
    - Player types 'quit', 'exit', or 'q'
    - A KeyboardInterrupt (Ctrl-C) is caught cleanly

Logging:
    Set the DAVE_LOG_LEVEL environment variable to DEBUG for full pass-level
    tracing including raw prompts and responses. INFO (the default) logs
    turn summaries and any involuntary events.
"""

import json
import logging
import os
import sys
import textwrap

from engine import config
from engine.context import build_pass1_packet, build_pass2_packet, build_pass3_packet
from engine.db import Database
from engine.llm import get_llm_client
from engine.llm.base import LLMClient, LLMError, LLMJSONError

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt templates
# =============================================================================

# Each pass template wraps the JSON context packet with natural-language
# instructions. The {context_json} placeholder is replaced at runtime with the
# serialised context packet. Pass-specific requirements are spelled out here
# rather than buried in the context packet so that the model sees them as
# instructions, not as data.

PASS1_PROMPT_TEMPLATE = """\
You are the intent parser for the DAVE RPG Engine. Your only job is to convert
the player's raw input into a structured action record.

Rules:
- Return a single JSON object. No prose, no explanation, no markdown fences.
- Resolve pronoun references and ambiguous names using the context provided.
- If the input is ambiguous, choose the most plausible interpretation given
  the player's current location and recent actions.
- Valid action types: move, interact, speak, examine, take, drop, use, wait,
  involuntary (used only when the action is not player-initiated).

Required output fields:
  action_type   (string, one of the types above)
  verb          (string, the player's intended verb in plain English)
  target        (string or null, the primary object or character of the action)
  target_id     (integer or null, resolved database id if determinable)
  location_id   (integer, the player's current location)
  detail        (string or null, any additional qualifying information)
  raw_input     (string, the player's unmodified input text)

Context:
{context_json}
"""

PASS2_PROMPT_TEMPLATE = """\
You are the adjudication layer for the DAVE RPG Engine. Your job is to determine
what happens as a result of the action below, given the full game state.

Rules:
- Return a single JSON object. No prose, no explanation, no markdown fences.
- Apply all psychological frameworks consistently: OCEAN traits influence
  likelihood of various reactions; MST goals drive NPC priorities; Maslow
  hierarchy overrides when survival or safety needs are at stake.
- Hidden motivation is provided for your adjudication but must NOT appear in
  the narrative_beat or any player-visible field.
- If involuntary events are listed under involuntary_events_this_turn, they
  occur this turn regardless of player intent. Incorporate them into the outcome.
- State deltas (attitude, internal state) must be floats in valid range.
  Attitude deltas: typically small (−0.15 to +0.15 per interaction).
  Internal state deltas: constrained to the range that would move the value
  meaningfully without being implausible (e.g. a single grooming raises
  hairball_pressure by 0.04–0.10).

Required output fields:
  outcome_type         (string: success | partial_success | failure | involuntary | ambient)
  narrative_beat       (string: 1–2 sentences describing what happened, player-visible,
                        no hidden information)
  attitude_deltas      (list of {character_id, target_id, delta, attitude_type})
  internal_state_deltas (list of {character_id, state_name, delta})
  emotional_state_updates (list of {character_id, emotional_state})
  location_change      (object {character_id, new_location_id} or null)
  item_changes         (list of {item_id, field, new_value} for any item updates)
  new_location_details (list of {location_id, detail, invalidation_condition} for
                        any new details generated by lazy world expansion)
  narrative_point_delta (integer, typically 0; positive for dramatically significant turns)
  adjudication_notes   (string: brief private notes on reasoning, not player-visible)

Context:
{context_json}
"""

PASS3_PROMPT_TEMPLATE = """\
You are the prose renderer for the DAVE RPG Engine. Your job is to turn the
adjudicated outcome below into vivid, engaging player-facing prose.

Rules:
- Return only prose. No JSON, no metadata, no headers.
- Write from the player character's perspective and sensory experience.
- Apply the speech_filter exactly: for the I Am a Cat module, human speech
  should be rendered as the cat perceives it (tone, volume, body language,
  and occasional word "breakthrough" per the filter config) — not as literal
  transcription. Cat vocalisations are the player's expressive medium.
- Match the game tone precisely (e.g. comedic_absurdist for I Am a Cat).
- Do not reveal hidden motivation or any information outside the player
  character's direct perception.
- Length: 2–5 sentences for routine actions; up to a short paragraph for
  dramatically significant moments. Involuntary events warrant their own beat.

Context:
{context_json}
"""


# =============================================================================
# GameEngine
# =============================================================================

class GameEngine:
    """
    Orchestrates a complete play session for one game_id.

    The engine owns the LLM client and drives the turn loop. The Database
    instance is passed in from outside so the caller can manage its lifecycle
    (and run it as a context manager if desired).

    Attributes:
        db:       The open Database instance.
        game_id:  The active game's id.
        llm:      The configured LLM client.
        _game:    Cached game record (loaded once at startup).
        _player:  Cached player character record (refreshed each turn).
    """

    def __init__(self, db: Database, game_id: int) -> None:
        """
        Initialise the engine for a specific game.

        Args:
            db:      An open Database instance with the schema applied.
            game_id: The id of the game to run. Must exist in the game table.

        Raises:
            ValueError: If game_id does not exist or has no player character.
            LLMError:   If the configured LLM backend cannot be initialised.
        """
        self.db = db
        self.game_id = game_id

        # Validate game and player exist before doing anything else.
        self._game = db.get_game(game_id)
        if self._game is None:
            raise ValueError(
                f"No game found with id={game_id}. "
                f"Have you run the seed.sql for this module?"
            )

        self._player = db.get_player_character(game_id)
        if self._player is None:
            raise ValueError(
                f"No player character found for game_id={game_id}. "
                f"Check that the seed data includes a character with role='player'."
            )

        # Initialise the LLM client (validates config, opens connection).
        self.llm: LLMClient = get_llm_client()

        logger.info(
            "GameEngine ready: game=%d (%s) player=%s backend=%s",
            game_id,
            self._game.get("title", "untitled"),
            self._player["name"],
            config.LLM_BACKEND,
        )

    # -------------------------------------------------------------------------
    # Main loop
    # -------------------------------------------------------------------------

    def run(self) -> None:
        """
        Enter the turn loop. Runs until the player quits or KeyboardInterrupt.

        Each iteration:
            1. Check and fire any involuntary events
            2. Read player input
            3. Run Pass 1 (intent parsing)
            4. Run Pass 2 (adjudication)
            5. Write all DB changes from the outcome
            6. Run Pass 3 (prose rendering)
            7. Display prose to the player
        """
        print(f"\n=== {self._game.get('title', 'DAVE RPG')} ===\n")
        print(f"You are {self._player['name']}.\n")

        while True:
            # Refresh the player record at the top of each turn so location
            # and emotional state are always current.
            self._player = self.db.get_player_character(self.game_id)

            # ------------------------------------------------------------------
            # Step 1: Check involuntary events
            # ------------------------------------------------------------------
            involuntary_fired = self._check_involuntary_events()

            # ------------------------------------------------------------------
            # Step 2: Read player input
            # ------------------------------------------------------------------
            try:
                raw_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nFarewell.")
                break

            if not raw_input:
                continue

            if raw_input.lower() in ("quit", "exit", "q"):
                print("\nFarewell.")
                break

            # ------------------------------------------------------------------
            # Steps 3–6: Three-pass processing
            # ------------------------------------------------------------------
            try:
                prose = self._process_turn(raw_input, involuntary_fired)
            except LLMJSONError as exc:
                logger.error("LLM JSON parse failure: %s", exc)
                print("\n[The engine could not parse the LLM response. Please try again.]\n")
                continue
            except LLMError as exc:
                logger.error("LLM error: %s", exc)
                print(f"\n[LLM error: {exc}]\n")
                continue

            # ------------------------------------------------------------------
            # Step 7: Display prose
            # ------------------------------------------------------------------
            print()
            print(textwrap.fill(prose, width=80))
            print()

    # -------------------------------------------------------------------------
    # Turn processing
    # -------------------------------------------------------------------------

    def _process_turn(
        self,
        raw_input: str,
        involuntary_fired: list[dict],
    ) -> str:
        """
        Run all three LLM passes for one turn and return the prose output.

        Writes all adjudication results to the database before Pass 3 runs,
        so the database always reflects the current world state.

        Args:
            raw_input:         The player's raw text input for this turn.
            involuntary_fired: Involuntary event state dicts that fired this turn.

        Returns:
            The rendered prose string for display to the player.
        """
        # Pass 1 — Intent Parsing
        pass1_packet = build_pass1_packet(self.db, self.game_id, raw_input)
        pass1_prompt = PASS1_PROMPT_TEMPLATE.format(
            context_json=json.dumps(pass1_packet, indent=2)
        )
        logger.debug("Pass 1 prompt:\n%s", pass1_prompt)

        action_record = self.llm.call_json(pass1_prompt)
        logger.info("Pass 1 result: action_type=%s target=%s",
                    action_record.get("action_type"), action_record.get("target"))

        # Pass 2 — Outcome Adjudication
        pass2_packet = build_pass2_packet(
            self.db, self.game_id, action_record,
            involuntary_events=involuntary_fired,
        )
        pass2_prompt = PASS2_PROMPT_TEMPLATE.format(
            context_json=json.dumps(pass2_packet, indent=2)
        )
        logger.debug("Pass 2 prompt:\n%s", pass2_prompt)

        outcome = self.llm.call_json(pass2_prompt)
        logger.info(
            "Pass 2 result: outcome_type=%s narrative_beat=%.80s",
            outcome.get("outcome_type"),
            outcome.get("narrative_beat", ""),
        )

        # Write all adjudication results to the database.
        self._apply_outcome(action_record, outcome)

        # Pass 3 — Prose Rendering
        # Refresh the player record so the prose renderer sees the post-outcome state.
        self._player = self.db.get_player_character(self.game_id)

        pass3_packet = build_pass3_packet(self.db, self.game_id, outcome)
        pass3_prompt = PASS3_PROMPT_TEMPLATE.format(
            context_json=json.dumps(pass3_packet, indent=2)
        )
        logger.debug("Pass 3 prompt:\n%s", pass3_prompt)

        prose = self.llm.call(pass3_prompt)
        logger.debug("Pass 3 prose: %.120s", prose)
        return prose

    # -------------------------------------------------------------------------
    # Involuntary event checking
    # -------------------------------------------------------------------------

    def _check_involuntary_events(self) -> list[dict]:
        """
        Check all characters in this game for involuntary events and return
        those that fire this turn.

        Called at the top of every turn, before player input is read. If one
        or more events fire, they are passed to Pass 2 so the LLM can
        incorporate them into the adjudicated outcome.

        Returns:
            A list of internal_state dicts (with character_name) for each
            event that fired this turn. Empty list if none fired.
        """
        candidates = self.db.get_involuntary_states(self.game_id)
        fired = []
        for state in candidates:
            if self.db.roll_involuntary_event(state):
                fired.append(state)
                logger.info(
                    "Involuntary event: %s / %s (value=%.3f)",
                    state.get("character_name"),
                    state["state_name"],
                    state["value"],
                )
        return fired

    # -------------------------------------------------------------------------
    # Outcome application (DB writes)
    # -------------------------------------------------------------------------

    def _apply_outcome(self, action_record: dict, outcome: dict) -> None:
        """
        Write all adjudication results from the outcome dict to the database.

        This method is the only place where the engine writes game state. It
        processes each field of the outcome in a defined order and logs any
        unexpected fields for debugging.

        Args:
            action_record: The Pass 1 action record (used for logging context).
            outcome:       The Pass 2 adjudication outcome dict.
        """
        # ------------------------------------------------------------------
        # Attitude deltas
        # ------------------------------------------------------------------
        for delta in outcome.get("attitude_deltas") or []:
            try:
                self.db.update_attitude(
                    character_id=int(delta["character_id"]),
                    target_id=int(delta["target_id"]),
                    delta=float(delta["delta"]),
                    attitude_type=delta.get("attitude_type", "surface"),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping malformed attitude_delta %r: %s", delta, exc)

        # ------------------------------------------------------------------
        # Internal state deltas
        # ------------------------------------------------------------------
        for delta in outcome.get("internal_state_deltas") or []:
            try:
                self.db.apply_internal_state_delta(
                    character_id=int(delta["character_id"]),
                    state_name=str(delta["state_name"]),
                    delta=float(delta["delta"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping malformed internal_state_delta %r: %s", delta, exc)

        # ------------------------------------------------------------------
        # Emotional state updates
        # ------------------------------------------------------------------
        for update in outcome.get("emotional_state_updates") or []:
            try:
                self.db.update_character_emotional_state(
                    character_id=int(update["character_id"]),
                    emotional_state=str(update["emotional_state"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping malformed emotional_state_update %r: %s", update, exc)

        # ------------------------------------------------------------------
        # Character location change
        # ------------------------------------------------------------------
        loc_change = outcome.get("location_change")
        if loc_change:
            try:
                self.db.update_character_location(
                    character_id=int(loc_change["character_id"]),
                    new_location_id=int(loc_change["new_location_id"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping malformed location_change %r: %s", loc_change, exc)

        # ------------------------------------------------------------------
        # Item changes
        # ------------------------------------------------------------------
        # The outcome specifies item changes as a list of {item_id, field, new_value}.
        # We apply them as direct UPDATE statements. Only a narrow set of fields
        # is permitted to prevent the LLM from making unintended schema changes.
        _ALLOWED_ITEM_FIELDS = {"is_visible", "quality", "held_by_character_id", "location_id"}
        for change in outcome.get("item_changes") or []:
            try:
                field = str(change["field"])
                if field not in _ALLOWED_ITEM_FIELDS:
                    logger.warning(
                        "Ignoring item_change for disallowed field %r (item_id=%s)",
                        field, change.get("item_id"),
                    )
                    continue
                # Use a parameterised query; field name is validated above.
                self.db._execute(  # noqa: SLF001 — direct access justified here
                    f"UPDATE item SET {field} = ?, updated_at = datetime('now') WHERE id = ?",
                    (change["new_value"], int(change["item_id"])),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping malformed item_change %r: %s", change, exc)

        # ------------------------------------------------------------------
        # New location details (lazy world generation results)
        # ------------------------------------------------------------------
        for detail_spec in outcome.get("new_location_details") or []:
            try:
                self.db.add_location_detail(
                    location_id=int(detail_spec["location_id"]),
                    detail=str(detail_spec["detail"]),
                    invalidation_condition=detail_spec.get("invalidation_condition"),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed new_location_detail %r: %s", detail_spec, exc
                )

        # ------------------------------------------------------------------
        # Narrative points
        # ------------------------------------------------------------------
        point_delta = outcome.get("narrative_point_delta", 0)
        if point_delta and self._player:
            try:
                self.db.update_narrative_points(
                    character_id=self._player["id"],
                    delta=int(point_delta),
                )
            except (TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed narrative_point_delta %r: %s", point_delta, exc
                )

        # ------------------------------------------------------------------
        # Action log
        # ------------------------------------------------------------------
        self.db.write_action_log(
            game_id=self.game_id,
            character_id=self._player["id"] if self._player else 0,
            action_json=action_record,
            narrative_beat=outcome.get("narrative_beat"),
        )

        # ------------------------------------------------------------------
        # Interaction history (increment for each NPC present at the location)
        # ------------------------------------------------------------------
        if self._player:
            location_id = self._player["current_location_id"]
            others = self.db.get_characters_at_location(
                location_id, exclude_character_id=self._player["id"]
            )
            for other in others:
                self.db.update_interaction_history(
                    character_a_id=self._player["id"],
                    character_b_id=other["id"],
                    increment_count=True,
                )

        logger.info(
            "Outcome applied: type=%s attitudes=%d states=%d locations=%d items=%d details=%d",
            outcome.get("outcome_type"),
            len(outcome.get("attitude_deltas") or []),
            len(outcome.get("internal_state_deltas") or []),
            1 if outcome.get("location_change") else 0,
            len(outcome.get("item_changes") or []),
            len(outcome.get("new_location_details") or []),
        )


# =============================================================================
# Entry point helper
# =============================================================================

def main() -> None:
    """
    Command-line entry point. Reads configuration from environment variables,
    validates it, opens the database, and starts the engine.

    Typical invocation:
        DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python -m engine

    For debug-level logging:
        DAVE_LOG_LEVEL=DEBUG DAVE_DB_PATH=... python -m engine
    """
    # Configure logging before anything else.
    log_level = os.environ.get("DAVE_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )

    # Validate configuration (will raise ValueError with a clear message on
    # any problem, e.g. missing API key or unknown backend).
    try:
        config.validate()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Default game_id to 1; a future CLI arg parser could override this.
    game_id = int(os.environ.get("DAVE_GAME_ID", "1"))

    try:
        with Database(config.DB_PATH) as db:
            engine = GameEngine(db, game_id=game_id)
            engine.run()
    except FileNotFoundError as exc:
        print(f"Database not found: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"Engine initialisation error: {exc}", file=sys.stderr)
        sys.exit(1)
    except LLMError as exc:
        print(f"LLM error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
