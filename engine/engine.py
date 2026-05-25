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
- For move actions: look up the destination name in known_locations and set
  target_id to the matching location id. Do NOT leave target_id null when
  the destination appears in known_locations, even if it is far away.
  The engine handles multi-step pathfinding — your only job is to resolve
  the name to the correct integer id.

Required output fields:
  action_type   (string, one of the types above)
  verb          (string, the player's intended verb in plain English)
  target        (string or null, the primary object or character of the action)
  target_id     (integer or null, resolved database id if determinable;
                 for move actions this MUST be the location id from known_locations)
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
- characters_nearby lists characters in adjacent locations with minimal profiles.
  Use species and emotional_state to reason about whether the player character
  can detect them through walls (sound, smell, etc.). A playful cat is audible;
  a deeply asleep human is not. What the player character can perceive depends
  on their species and the nearby character's current state — apply your
  knowledge of the game world and the player character's sensory capabilities.
  Do not treat nearby characters as present; they are in an adjacent room.
- NPC ACTIONS ARE AUTHORITATIVE: only describe NPCs acting, speaking, or
  reacting in the narrative_beat if they appear in characters_at_location.
  Do not attribute actions or reactions to NPCs who are not listed there.
  If an NPC is in characters_nearby (adjacent room), they may be audible or
  detectable by smell, but do not describe them as present, visible, or
  physically interacting with the scene.
- LOCATION IS AUTHORITATIVE: player.current_location_id in the context packet
  is the ground truth for where the player is. Do not infer location from
  narrative_beat text in recent_actions — those are prose summaries and may
  describe events that occurred elsewhere. If a location_change is needed,
  the new_location_id must be the id of a location that exists in the database
  and is reachable from the player's current location. Never move a character
  to a location id that was not present in the context packet.
- MULTI-STEP MOVEMENT: If action_record contains a "route" key, the engine has
  already resolved the player's path and pre-moved the player to
  route.effective_destination_id. The player is already there — do NOT issue a
  location_change for the player character. Your job is to adjudicate what
  happens upon arrival (or at the interruption point, if route.interrupted is
  true). NPC location_changes are still yours to issue as normal.
  If route.interrupted is true, route.interruption describes what stopped the
  player (NPCs present and/or existing items at that location). Adjudicate the
  encounter there; the player did not reach their intended destination.
  If route.interrupted is false, adjudicate the arrival at the destination.
  The narrative_beat for a routed move should briefly name the rooms passed
  through (from route.path_location_names) before describing the arrival.

Required output fields:
  outcome_type         (string: success | partial_success | failure | involuntary | ambient)
  narrative_beat       (string: 1–2 sentences describing what happened, player-visible,
                        no hidden information. For routed moves, briefly list rooms
                        passed through, then describe arrival or interruption.)
  elapsed_minutes      (integer: estimated in-game minutes this action took. Use your
                        knowledge of the game world and action type to estimate realistically.
                        Examples: examining an item ~1 min, moving one room ~1–2 min,
                        a short conversation ~3–5 min, grooming ~5–10 min,
                        a nap ~20–60 min, waiting ~5–15 min. Minimum 1.)
  attitude_deltas      (list of {{character_id, target_id, delta, attitude_type}})
  internal_state_deltas (list of {{character_id, state_name, delta}})
  emotional_state_updates (list of {{character_id, emotional_state}})
  location_change      (list of {{character_id, new_location_id}}; one entry per
                        character that moves this turn; empty list if no one moves.
                        new_location_id MUST be in current_location.adjacent_locations
                        in the context packet — never a location that is not listed
                        there. Do NOT include the player in this list for routed moves.
                        MOVEMENT CONSISTENCY: if your narrative_beat describes any
                        character moving, fleeing, following, or otherwise changing
                        location, that character MUST appear in this list with a valid
                        new_location_id. The engine updates DB location records from
                        this list only — it does not read prose. A character described
                        as having moved but absent from location_change will remain in
                        their old location in the database, causing incorrect state.
                        NPC AUTHORITY: only issue location_change entries for NPCs who
                        appear in characters_at_location in the context packet. Do not
                        move NPCs who are not listed there — they are not present.)
  item_changes         (list of {{item_id, field, new_value}} for any item updates)
  new_location_details (list of {{location_id, detail, invalidation_condition}} for
                        any new details generated by lazy world expansion. Do NOT
                        generate details for intermediate locations on a routed move —
                        only for the effective destination.)
  faction_reputation_changes (list of {{character_id, faction_name, delta, reason}}
                        for any changes to faction standing. faction_name must match
                        an existing faction slug in this module (e.g.
                        'bennet_family'). delta is a signed float, typically
                        ±0.03 to ±0.15. reason is a short string written to the
                        notes field. Empty list if no faction standing changed.
                        Only include this field for modules that use factions;
                        omit or return [] for modules like I Am a Cat.)
  pending_intent_updates (list of {{character_id, pending_intent}} for any changes
                        to NPC working-memory obligations. pending_intent is a
                        short string describing the unfulfilled social obligation,
                        or null to clear the intent when the obligation is fulfilled
                        or abandoned. Only include NPCs whose pending_intent changed
                        this turn. Empty list if no NPC intents changed.)
  narrative_point_delta (integer, typically 0; positive for dramatically significant turns)
  adjudication_notes   (string: brief private notes on reasoning, not player-visible)

Context:
{context_json}
"""

OPENING_SCENE_PROMPT_TEMPLATE = """\
You are the prose renderer for the DAVE RPG Engine. Your job is to write the
opening scene description for this session — before any player action has occurred.

Rules:
- Return only prose. No JSON, no metadata, no headers.
- Write in second person: the player character is "you", not named by name.
- Write from the player character's perspective and sensory experience.
- Describe where the player character is, what they can immediately sense
  (sight, sound, smell, touch as appropriate), and their current emotional
  and physical state as established in the context.
- Introduce any other characters who are present at the starting location.
- Apply the speech_filter if relevant, and match the game tone precisely.
- Do not reveal hidden motivation or any information outside the player
  character's direct perception.
- Length: a short paragraph (3–5 sentences). This is an establishing shot,
  not an action sequence.
- Pronouns: use the pronouns supplied in the `characters_referenced` list.
- NPC presence is authoritative: only describe characters who appear in
  `characters_present`.
- Navigation: weave a brief, natural mention of the immediately available
  exits into the scene — a doorway, a staircase, a passage ahead — so the
  player understands where they can go from here. Use the `adjacent_locations`
  list. If a location has is_passable=false, convey the barrier in tone
  (a closed door, a passage not meant for guests) rather than stating it as
  a rule. Keep this light; the goal is orientation, not a door inventory.

Context:
{context_json}
"""

PASS3_PROMPT_TEMPLATE = """\
You are the prose renderer for the DAVE RPG Engine. Your job is to turn the
adjudicated outcome below into vivid, engaging player-facing prose.

Rules:
- Return only prose. No JSON, no metadata, no headers.
- Write in second person: the player character is "you", not named by name.
- Write from the player character's perspective and sensory experience.
- Apply the speech_filter exactly: for the I Am a Cat module, human speech
  should be rendered as the cat perceives it (tone, volume, body language,
  and occasional word "breakthrough" per the filter config) — not as literal
  transcription. Cat vocalisations are the player's expressive medium.
- Match the game tone precisely (e.g. comedic_absurdist for I Am a Cat,
  ironic_observational for Meryton).
- Do not reveal hidden motivation or any information outside the player
  character's direct perception.
- Length: keep prose tight. Aim for 3–4 sentences for routine actions;
  a short paragraph (5–6 sentences maximum) only for dramatically significant
  moments. The ironic_observational register rewards restraint — overwriting
  dilutes the effect. Involuntary events warrant their own brief beat.
- Do not repeat atmospheric or environmental details (candlelight, smells,
  ambient sounds) that have already been established in the recent narrative.
  Vary your imagery; if you have described the candlelight once, let it stand.
- Pronouns: use the pronouns supplied in the `characters_referenced` list for
  any named character. Each entry gives an array of case–form pairs (nominative,
  accusative, genitive, and any additional cases for the module's language).
  Do NOT infer pronouns from a character's name or species — use only what is
  provided. If a character does not appear in `characters_referenced`, or their
  pronouns field is null, infer from context as a fallback.
- NPC presence is authoritative: the `characters_present` list contains every
  character physically at the player's location according to the game engine.
  Only describe NPCs as present, acting, or reacting if they appear in
  `characters_present`. Do NOT invent NPC presence, movement, or reactions for
  characters who are not listed there. If the outcome's narrative_beat mentions
  an NPC but they are absent from `characters_present`, describe the outcome
  from the player's perspective without referencing that NPC directly.
- Navigation: if the player has just moved to a new location (the outcome
  includes a location_change for the player), weave a brief, natural mention
  of the available exits into the arrival prose — a door, a corridor, the
  direction back. Use the `adjacent_locations` list. If a location has
  is_passable=false, convey the barrier in tone rather than stating it as a
  rule. Keep this light; one natural phrase is enough.

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

        # Locate the active game_instance (v5+). May be None for pre-v5 databases
        # or unseeded modules; the engine degrades gracefully (no clock, no passive
        # ticks) rather than refusing to start.
        instance = db.get_active_instance(game_id)
        if instance is None:
            logger.warning(
                "No ready/active game_instance found for game_id=%d. "
                "Clock and passive state ticks will be disabled. "
                "Run seed_instance.sql to enable these features.",
                game_id,
            )
        else:
            # Validate the sentinel values have been replaced by real data.
            if instance["start_time_minutes"] == -1 or instance["current_time_minutes"] == -1:
                logger.warning(
                    "game_instance id=%d has unseeded time values (-1). "
                    "Clock and passive state ticks will be disabled.",
                    instance["id"],
                )
                instance = None
            else:
                # Transition instance to 'active' now that a session is starting.
                db.set_instance_status(instance["id"], "active")

        self._instance = instance  # None if pre-v5 or unseeded

        # Initialise the LLM client (validates config, opens connection).
        self.llm: LLMClient = get_llm_client()

        logger.info(
            "GameEngine ready: game=%d (%s) player=%s backend=%s instance=%s",
            game_id,
            self._game.get("name", "untitled"),
            self._player["name"],
            config.LLM_BACKEND,
            instance["id"] if instance else "none",
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
        print(f"\n=== {self._game.get('name', 'DAVE RPG')} ===\n")
        try:
            opening = self._render_opening_scene()
            print(textwrap.fill(opening, width=80))
        except (LLMError, LLMJSONError) as exc:
            # Degrade gracefully: fall back to bare name if opening render fails.
            logger.warning("Opening scene render failed (%s); using fallback.", exc)
            print(f"You are {self._player['name']}.")
        print()

        while True:
            # Refresh the player record at the top of each turn so location
            # and emotional state are always current.
            self._player = self.db.get_player_character(self.game_id)

            # ------------------------------------------------------------------
            # Step 1: Check involuntary events and NPC wandering
            # ------------------------------------------------------------------
            involuntary_fired = self._check_involuntary_events()
            # Move NPCs that roll for autonomous wandering this turn.
            # This happens before Pass 1 so that by the time the context packet
            # is assembled, NPCs are already at their new locations.
            self._check_npc_wandering()

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

        # ------------------------------------------------------------------
        # Exit summary: game time, player boredom, token totals.
        # All reported at INFO so they appear in normal (non-debug) runs.
        # ------------------------------------------------------------------

        # Game clock summary (v5+).
        if self._instance is not None:
            try:
                current_min = self.db.get_game_clock(self._instance["id"])
                start_min   = self._instance.get("start_time_minutes", 0)
                elapsed_min = current_min - start_min
                from engine.db import _format_game_time
                logger.info(
                    "Game time on exit: %s  (started %s, %d min elapsed)",
                    _format_game_time(current_min),
                    _format_game_time(start_min),
                    elapsed_min,
                )
            except (ValueError, KeyError):
                pass  # pre-v5 database or unseeded instance; skip gracefully

        # Player boredom at exit — the primary pressure state for I Am a Cat.
        # Reports the raw float and a brief qualitative label so the player
        # has an intuitive sense of how the session went without needing to
        # understand the internal scale. Other modules may track different
        # primary states; boredom is not hardcoded — it is simply the first
        # named state checked. Future: generalise via a module-level config
        # field that names the primary outcome state.
        if self._player is not None:
            boredom_state = self.db.get_internal_state(self._player["id"], "boredom")
            if boredom_state is not None:
                boredom = boredom_state["value"]
                if boredom < 0.20:
                    label = "not bored at all"
                elif boredom < 0.40:
                    label = "mildly bored"
                elif boredom < 0.60:
                    label = "noticeably bored"
                elif boredom < 0.80:
                    label = "quite bored"
                else:
                    label = "severely bored"
                logger.info(
                    "Toulouse boredom at exit: %.3f (%s)",
                    boredom,
                    label,
                )

        # Token totals and cost estimate (Claude backend only).
        if hasattr(self.llm, "token_totals"):
            totals = self.llm.token_totals()
            cost = totals.get("cost_usd")
            if cost is not None:
                logger.info(
                    "Session token totals: input=%d output=%d total=%d  est. cost=$%.4f USD",
                    totals["input_tokens"],
                    totals["output_tokens"],
                    totals["total"],
                    cost,
                )
            else:
                logger.info(
                    "Session token totals: input=%d output=%d total=%d  (cost unknown — model not in pricing table)",
                    totals["input_tokens"],
                    totals["output_tokens"],
                    totals["total"],
                )

    # -------------------------------------------------------------------------
    # Opening scene
    # -------------------------------------------------------------------------

    def _render_opening_scene(self) -> str:
        """
        Generate the opening prose for a new session by running a single
        Pass 3 call with a synthetic scene-open outcome.

        No Pass 1 or Pass 2 is run; no state is changed. The prose is derived
        entirely from the player's starting location, description, emotional
        state, and the other characters present at that location — all of which
        are already in the DB at session start.

        Returns:
            Rendered opening prose string.

        Raises:
            LLMError:     If the LLM call fails.
            LLMJSONError: If the response cannot be parsed (should not occur
                          since Pass 3 returns plain prose, but included for
                          defensive completeness).
        """
        # Synthetic outcome: no state changes, just a cue for the prose renderer.
        synthetic_outcome = {
            "outcome_type": "ambient",
            "narrative_beat": (
                "The scene opens. Establish the player character's starting position, "
                "immediate sensory environment, and emotional state. "
                "This is the first moment of the session; no action has yet occurred."
            ),
            "elapsed_minutes": 0,
            "attitude_deltas": [],
            "internal_state_deltas": [],
            "emotional_state_updates": [],
            "location_change": [],
            "item_changes": [],
            "new_location_details": [],
            "faction_reputation_changes": [],
            "pending_intent_updates": [],
            "narrative_point_delta": 0,
            "adjudication_notes": "Opening scene render — no state changes.",
        }

        pass3_packet = build_pass3_packet(self.db, self.game_id, synthetic_outcome)
        prompt = OPENING_SCENE_PROMPT_TEMPLATE.format(
            context_json=json.dumps(pass3_packet, indent=2)
        )
        logger.debug("Opening scene prompt:\n%s", prompt)

        prose = self.llm.call(prompt)
        logger.debug("Opening scene prose: %.120s", prose)
        return prose

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
        logger.info(
            "Pass 1 result: action_type=%s target=%s target_id=%s",
            action_record.get("action_type"),
            action_record.get("target"),
            action_record.get("target_id"),
        )

        # ------------------------------------------------------------------
        # Named-location movement: resolve path and pre-apply move before
        # building the Pass 2 packet.
        #
        # ALL named-location moves (adjacent or multi-step) go through
        # _resolve_multistep_move. This pre-applies the player's new location
        # to the DB before Pass 2 runs, so the context packet is accurate and
        # the player's location is reliably updated regardless of whether Pass 2
        # happens to return a location_change entry.
        #
        # The previous design sent adjacent moves through Pass 2 to issue the
        # location_change, but Pass 2 does not always return one (Haiku in
        # particular omits it on simple single-step moves), leaving the DB
        # stale and breaking adjacency checks on subsequent turns.
        # ------------------------------------------------------------------
        if (
            action_record.get("action_type") == "move"
            and action_record.get("target_id") is not None
        ):
            target_id = int(action_record["target_id"])
            current_loc = self._player["current_location_id"]

            if target_id != current_loc:
                route = self._resolve_multistep_move(target_id)
                action_record["route"] = route

                if not route["reachable"]:
                    logger.info(
                        "Move blocked: %s", route.get("no_path_reason")
                    )
                    return route["no_path_reason"] or "There's no way to get there from here."

        # Pass 2 — Outcome Adjudication
        instance_id = self._instance["id"] if self._instance else None
        pass2_packet = build_pass2_packet(
            self.db, self.game_id, action_record,
            involuntary_events=involuntary_fired,
            instance_id=instance_id,
        )
        pass2_prompt = PASS2_PROMPT_TEMPLATE.format(
            context_json=json.dumps(pass2_packet, indent=2)
        )
        logger.debug("Pass 2 prompt:\n%s", pass2_prompt)

        outcome = self.llm.call_json(pass2_prompt)
        logger.info(
            "Pass 2 result: outcome_type=%s elapsed_minutes=%s narrative_beat=%.80s",
            outcome.get("outcome_type"),
            outcome.get("elapsed_minutes"),
            outcome.get("narrative_beat", ""),
        )

        # Write all adjudication results to the database.
        self._apply_outcome(action_record, outcome)

        # ------------------------------------------------------------------
        # Advance game clock and tick passive states (v5+).
        # Done after _apply_outcome so that Pass 2's explicit internal_state
        # deltas are already written before the passive tick runs. This means
        # the passive tick operates on post-adjudication values, which is the
        # correct order: adjudication first, background drift second.
        # ------------------------------------------------------------------
        if self._instance is not None:
            elapsed = outcome.get("elapsed_minutes")
            if isinstance(elapsed, (int, float)) and elapsed > 0:
                self.db.advance_game_clock(self._instance["id"], int(elapsed))
                self.db.tick_passive_states(self.game_id, float(elapsed))
            else:
                logger.warning(
                    "Pass 2 outcome missing valid elapsed_minutes (got %r); "
                    "clock not advanced this turn.",
                    elapsed,
                )

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
    # Multi-step movement resolution
    # -------------------------------------------------------------------------

    def _resolve_multistep_move(
        self, target_location_id: int
    ) -> dict:
        """
        Resolve a move action whose destination is not adjacent to the player.

        This method is the engine's pathfinding layer. It:
            1. Verifies the destination has been visited (quick-move restriction).
            2. Finds the shortest path via passable connections (BFS).
            3. Checks each intermediate location for interruptions:
               - Any NPC present at an intermediate is a hard interruption.
               - Existing visible items at an intermediate are flagged as
                 soft interruptions and passed to Pass 2 for adjudication.
               - No lazy world generation is triggered at intermediate locations.
            4. Pre-applies the move: updates the player's location in the DB
               to the effective destination before Pass 2 runs, so the context
               packet reflects current world state.

        Returns a route info dict that is injected into the action_record so
        Pass 2 knows the player has already been moved and what happened en route.
        The dict always has the following keys:

            reachable            (bool)  False if no path exists or destination
                                         not visited; no move is applied.
            intended_destination_id (int)
            effective_destination_id (int)  May differ from intended if interrupted.
            path_taken           (list[int])  Full path including start and
                                              effective destination.
            path_location_names  (list[str])  Human-readable names for prose.
            interrupted          (bool)
            interruption         (dict or None)  If interrupted: keys are
                                  'location_id', 'location_name', 'npcs'
                                  (list of {id, name}), 'items' (list of
                                  {id, name, description}).
            no_path_reason       (str or None)  Set when reachable=False.
        """
        player_id = self._player["id"]
        current_loc_id = self._player["current_location_id"]

        # ------------------------------------------------------------------
        # Quick-move restriction: destination must have been visited.
        #
        # Exception: if the target is directly adjacent (one passable step
        # away from the current location), the visited check is skipped.
        # This lets the player move into any neighbouring room they haven't
        # been to yet — which is how exploration works. The visited-location
        # requirement only makes sense for multi-step BFS pathfinding, where
        # the engine needs to know the player recognises the named destination.
        # ------------------------------------------------------------------
        adjacent_ids = {
            conn["neighbour_id"]
            for conn in self.db.get_location_connections(current_loc_id)
        }
        is_adjacent = target_location_id in adjacent_ids

        if not is_adjacent and not self.db.is_location_visited(player_id, target_location_id):
            dest = self.db.get_location(target_location_id)
            dest_name = dest["name"] if dest else f"location {target_location_id}"
            logger.info(
                "Quick-move blocked: player has not visited %s (id=%d)",
                dest_name, target_location_id,
            )
            return {
                "reachable": False,
                "intended_destination_id": target_location_id,
                "effective_destination_id": current_loc_id,
                "path_taken": [current_loc_id],
                "path_location_names": [],
                "interrupted": False,
                "interruption": None,
                "no_path_reason": f"You haven't been to {dest_name} yet.",
            }

        # ------------------------------------------------------------------
        # BFS pathfinding.
        # ------------------------------------------------------------------
        steps = self.db.find_path(current_loc_id, target_location_id)
        if steps is None:
            logger.info(
                "No passable path from loc=%d to loc=%d",
                current_loc_id, target_location_id,
            )
            return {
                "reachable": False,
                "intended_destination_id": target_location_id,
                "effective_destination_id": current_loc_id,
                "path_taken": [current_loc_id],
                "path_location_names": [],
                "interrupted": False,
                "interruption": None,
                "no_path_reason": "No passable route exists to that location.",
            }

        # Full path including the starting location.
        full_path = [current_loc_id] + steps

        # ------------------------------------------------------------------
        # Interruption check: examine each intermediate location (every step
        # except the final destination) for NPCs and existing items.
        # ------------------------------------------------------------------
        intermediate_ids = steps[:-1]  # all steps except the destination
        interruption = None
        effective_destination_id = target_location_id

        for loc_id in intermediate_ids:
            npcs = self.db.get_characters_at_location(
                loc_id, exclude_character_id=player_id
            )
            items = self.db.get_items_at_location(
                loc_id, visible_only=True
            )

            if npcs or items:
                # Interruption at this location. The player stops here.
                loc = self.db.get_location(loc_id)
                interruption = {
                    "location_id": loc_id,
                    "location_name": loc["name"] if loc else f"location {loc_id}",
                    # NPCs always constitute a hard stop; listed for Pass 2.
                    "npcs": [
                        {"id": n["id"], "name": n["name"]} for n in npcs
                    ],
                    # Existing items are flagged for Pass 2 to adjudicate
                    # whether they are distracting given the character's MST
                    # goals and Maslow state. No lazy generation here.
                    "items": [
                        {
                            "id": item["id"],
                            "name": item["name"],
                            "description": item["description"],
                        }
                        for item in items
                    ],
                }
                effective_destination_id = loc_id
                # Trim the path to the interruption point.
                interrupt_idx = full_path.index(loc_id)
                full_path = full_path[: interrupt_idx + 1]
                logger.info(
                    "Route interrupted at loc=%d (%s): %d NPC(s), %d item(s)",
                    loc_id,
                    interruption["location_name"],
                    len(npcs),
                    len(items),
                )
                break

        # ------------------------------------------------------------------
        # Pre-apply the move: update the player's location in the DB.
        # Pass 2 context will now reflect the effective destination.
        # ------------------------------------------------------------------
        self.db.update_character_location(player_id, effective_destination_id)
        self.db.mark_location_visited(player_id, effective_destination_id)
        self._player = self.db.get_player_character(self.game_id)

        # Resolve location names for the path (for prose rendering).
        path_names = []
        for loc_id in full_path:
            loc = self.db.get_location(loc_id)
            path_names.append(loc["name"] if loc else f"location {loc_id}")

        logger.info(
            "Multi-step move: %s → %s (intended: %s)%s",
            path_names[0] if path_names else "?",
            path_names[-1] if path_names else "?",
            self.db.get_location(target_location_id)["name"]
            if self.db.get_location(target_location_id) else target_location_id,
            " [INTERRUPTED]" if interruption else "",
        )

        return {
            "reachable": True,
            "intended_destination_id": target_location_id,
            "effective_destination_id": effective_destination_id,
            "path_taken": full_path,
            "path_location_names": path_names,
            "interrupted": interruption is not None,
            "interruption": interruption,
            "no_path_reason": None,
        }

    # -------------------------------------------------------------------------
    # NPC autonomous wandering
    # -------------------------------------------------------------------------

    def _check_npc_wandering(self) -> None:
        """
        Apply autonomous background movement to NPCs with wander_probability > 0.

        Called once per turn, before player input is read, after involuntary
        events are checked. For each eligible NPC the engine:

            1. Rolls random() against wander_probability to decide whether the
               NPC moves this turn.
            2. If moving, finds passable adjacent locations that are also within
               the NPC's wander_range.
            3. Picks one at random and moves the NPC there.

        This is engine-driven, not LLM-driven. Reactive NPC movement (e.g.
        a human who wakes and walks to the kitchen in response to a noise)
        is handled by the LLM in Pass 2 outcome location_change entries.
        This method handles only ambient background drift between turns.

        Nothing is written to the action log or returned — this movement is
        silent from the player's perspective unless they observe the NPC in
        its new position.
        """
        import random as _random  # module-level import would shadow stdlib elsewhere

        npcs = self.db.get_wandering_npcs(self.game_id)
        for npc in npcs:
            # ------------------------------------------------------------------
            # Wander suppressions (checked before rolling).
            # These represent states where wandering off is socially or
            # physically implausible — engine-enforced convention, not a
            # capability check.
            # ------------------------------------------------------------------

            # Suppression 1: pending social obligation.
            # "It just Isn't Done" to simply wander off when you owe someone
            # a response, have agreed to something, or are mid-conversation.
            if npc.get("pending_intent"):
                logger.debug(
                    "NPC wander suppressed (pending_intent): %s (id=%d)",
                    npc["name"], npc["id"],
                )
                continue

            # Suppression 2: sleepiness above threshold.
            # An NPC who is drowsy enough stays put regardless of wander_probability.
            # The threshold is WANDER_SLEEPINESS_THRESHOLD in config.py (default 0.60).
            sleepiness_state = self.db.get_internal_state(npc["id"], "sleepiness")
            if (
                sleepiness_state is not None
                and sleepiness_state["value"] >= config.WANDER_SLEEPINESS_THRESHOLD
            ):
                logger.debug(
                    "NPC wander suppressed (sleepiness=%.3f >= %.2f): %s (id=%d)",
                    sleepiness_state["value"],
                    config.WANDER_SLEEPINESS_THRESHOLD,
                    npc["name"],
                    npc["id"],
                )
                continue

            # Roll for movement this turn.
            if _random.random() >= npc["wander_probability"]:
                continue

            # Get passable adjacent locations that are also in this NPC's
            # wander_range. wander_range is already parsed to a list by
            # get_wandering_npcs().
            wander_range = set(npc["wander_range"])
            current_loc = npc["current_location_id"]
            connections = self.db.get_location_connections(current_loc)

            valid_destinations = [
                conn["neighbour_id"]
                for conn in connections
                if conn["neighbour_id"] in wander_range
            ]

            if not valid_destinations:
                # NPC is in a dead-end relative to their wander_range — do nothing.
                logger.debug(
                    "NPC %d (%s) at loc=%d: no valid wander destinations",
                    npc["id"], npc["name"], current_loc,
                )
                continue

            destination = _random.choice(valid_destinations)
            self.db.update_character_location(
                character_id=npc["id"],
                new_location_id=destination,
            )
            logger.info(
                "NPC wander: %s (id=%d) loc %d → %d",
                npc["name"], npc["id"], current_loc, destination,
            )

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
        # Character location changes (list; one entry per character moving)
        # ------------------------------------------------------------------
        # The outcome returns location_change as a list so that multiple
        # characters can move in a single turn (e.g. player enters a room
        # and startles an NPC who flees). We validate each move against the
        # location_connection table before applying it.
        #
        # Exception: if action_record contains a "route" key, the engine has
        # already pre-moved the player via _resolve_multistep_move(). Any
        # LLM-issued location_change for the player character is skipped to
        # prevent double-movement. NPC entries are still processed normally.
        is_routed_move = bool(action_record.get("route"))
        player_id = self._player["id"] if self._player else None

        loc_changes = outcome.get("location_change") or []
        # Backwards-compatibility: some LLM responses may still return a single
        # object rather than a list. Normalise to a list.
        if isinstance(loc_changes, dict):
            loc_changes = [loc_changes]

        for loc_change in loc_changes:
            try:
                char_id = int(loc_change["character_id"])
                new_loc_id = int(loc_change["new_location_id"])

                # Skip player location_change on routed moves — already applied.
                if is_routed_move and char_id == player_id:
                    logger.debug(
                        "Skipping LLM location_change for player (routed move already applied)"
                    )
                    continue

                # Determine the character's current location for adjacency check.
                if self._player and char_id == player_id:
                    from_loc_id = self._player["current_location_id"]
                else:
                    char = self.db.get_character(char_id)
                    from_loc_id = char["current_location_id"] if char else None

                # Guard 1: target location must exist in the DB.
                if self.db.get_location(new_loc_id) is None:
                    logger.warning(
                        "Ignoring location_change for char=%d to non-existent "
                        "location_id=%d (LLM may have hallucinated from prose)",
                        char_id, new_loc_id,
                    )
                    continue

                # Guard 2: target location must be adjacent (passable connection).
                if from_loc_id is not None and from_loc_id != new_loc_id:
                    if not self.db.is_location_connected(from_loc_id, new_loc_id):
                        logger.warning(
                            "Ignoring location_change for char=%d: loc %d → %d "
                            "is not a passable connection",
                            char_id, from_loc_id, new_loc_id,
                        )
                        continue

                self.db.update_character_location(
                    character_id=char_id,
                    new_location_id=new_loc_id,
                )
                # Mark the new location as visited for the player character.
                if char_id == player_id:
                    self.db.mark_location_visited(char_id, new_loc_id)
                logger.info(
                    "Character %d moved: loc %d → %d",
                    char_id, from_loc_id if from_loc_id else -1, new_loc_id,
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
                    f"UPDATE item SET {field} = ? WHERE id = ?",
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
        # Faction reputation changes (v7+)
        # ------------------------------------------------------------------
        # Each entry specifies a faction by name (slug) rather than id so that
        # Pass 2 doesn't need to know database ids. We look up the faction by
        # (game_id, name) and call update_faction_reputation.
        for change in outcome.get("faction_reputation_changes") or []:
            try:
                char_id   = int(change["character_id"])
                fname     = str(change["faction_name"])
                delta     = float(change["delta"])
                reason    = change.get("reason")

                faction = self.db.get_or_create_faction(self.game_id, fname)
                if faction is None:
                    logger.warning(
                        "Skipping faction_reputation_change: faction %r not found "
                        "for game_id=%d", fname, self.game_id,
                    )
                    continue

                self.db.update_faction_reputation(
                    character_id=char_id,
                    faction_id=faction["id"],
                    delta=delta,
                    reason=reason,
                )
                logger.info(
                    "Faction reputation: char=%d faction=%r %+.3f (%s)",
                    char_id, fname, delta, reason or "no reason given",
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed faction_reputation_change %r: %s", change, exc
                )

        # ------------------------------------------------------------------
        # Pending intent updates (v7+)
        # ------------------------------------------------------------------
        # Pass 2 issues these when an NPC acquires or discharges a social
        # obligation (e.g. Darcy is asked a question and now owes a response;
        # or Bingley says goodbye and clears his pending_intent).
        for update in outcome.get("pending_intent_updates") or []:
            try:
                char_id = int(update["character_id"])
                intent  = update.get("pending_intent")  # str or None
                self.db.update_character_pending_intent(
                    character_id=char_id,
                    intent_text=intent,
                )
                logger.info(
                    "pending_intent: char=%d → %r",
                    char_id,
                    (intent[:60] if intent else None),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed pending_intent_update %r: %s", update, exc
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
            "Outcome applied: type=%s attitudes=%d states=%d moves=%d "
            "items=%d details=%d faction_reps=%d pending_intents=%d",
            outcome.get("outcome_type"),
            len(outcome.get("attitude_deltas") or []),
            len(outcome.get("internal_state_deltas") or []),
            len(loc_changes),
            len(outcome.get("item_changes") or []),
            len(outcome.get("new_location_details") or []),
            len(outcome.get("faction_reputation_changes") or []),
            len(outcome.get("pending_intent_updates") or []),
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
