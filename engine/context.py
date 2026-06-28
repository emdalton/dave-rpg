"""
engine/context.py — DAVE RPG Engine Context Packet Assembly

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Each of the three LLM passes receives a "context packet" — a structured dict
that is serialised to JSON and embedded in the prompt. This module builds
those packets from the database, keeping each pass lean by including only what
it needs.

    Pass 1 (Intent Parsing)    — minimal: player input + player state + recent history
    Pass 2 (Outcome Adjudication) — full: all characters, location, world params, hidden data
    Pass 3 (Prose Rendering)   — minimal: adjudication outcome + speech filter + tone

The three public functions follow a consistent signature pattern:

    build_pass1_packet(db, game_id, player_input) -> dict
    build_pass2_packet(db, game_id, action_record) -> dict
    build_pass3_packet(db, game_id, outcome) -> dict

All three return plain Python dicts. The caller (engine.py) is responsible for
serialising to JSON and injecting into the prompt template.

Design principle: context packets are built fresh from the database on every
call. The LLM never carries state between turns; the database is the only
source of truth.
"""

import json
import logging
from typing import Any

from engine import config
from engine.db import Database, _format_game_time

logger = logging.getLogger(__name__)


# =============================================================================
# Pass 1 — Intent Parsing
# =============================================================================

def build_pass1_packet(
    db: Database,
    game_id: int,
    player_input: str,
) -> dict[str, Any]:
    """
    Build the context packet for Pass 1 (intent parsing).

    Pass 1 converts raw player text into a structured action record. It needs
    enough context to disambiguate references ("it", "them", "the thing over
    there") but should not include full adjudication data — that is expensive
    and unnecessary at this stage.

    Included:
    - player_input: the raw text from the player
    - game: genre, tone, and speech_filter (for parsing feline/unusual speech)
    - player: name, species, current location, emotional state
    - location: name and brief description of where the player currently is
    - recent_actions: last N action log entries (N from config.PASS1_RECENT_ACTIONS)

    Not included in Pass 1:
    - NPC full profiles (adjudication concern)
    - Internal state floats (adjudication concern)
    - Attitude matrices (adjudication concern)
    - Hidden motivation (never shown to Pass 1)

    Args:
        db: Open Database instance.
        game_id: The active game's id.
        player_input: The raw string the player typed this turn.

    Returns:
        A dict ready to be JSON-serialised for the Pass 1 prompt.
    """
    # ------------------------------------------------------------------
    # Game world parameters (genre, tone, speech filter)
    # ------------------------------------------------------------------
    game = db.get_game(game_id)
    if game is None:
        raise ValueError(f"No game found with id={game_id}")

    game_summary = {
        "genre": game["genre"],
        "tone": game["tone"],
        # The speech filter tells Pass 1 how to interpret non-standard
        # player expressions (cat vocalisations, vocabulary breakthroughs, etc.)
        "speech_filter": game["speech_filter"],
    }

    # ------------------------------------------------------------------
    # Player character (basic info only)
    # ------------------------------------------------------------------
    player = db.get_player_character(game_id)
    if player is None:
        raise ValueError(f"No player character found for game_id={game_id}")

    player_summary = {
        "id": player["id"],
        "name": player["name"],
        "species": player["species"],
        "emotional_state": player["emotional_state"],
        "current_location_id": player["current_location_id"],
    }

    # ------------------------------------------------------------------
    # Current location (name and description only; no items or details)
    # ------------------------------------------------------------------
    location = db.get_location(player["current_location_id"])
    location_summary = {
        "id": location["id"],
        "name": location["name"],
        "description": location["description_skeleton"],
    } if location else {}

    # ------------------------------------------------------------------
    # Location directory: all locations by id and name.
    # Pass 1 uses this to resolve destination names in move commands
    # (e.g. "kitchen" → id=3) so the engine can invoke multi-step
    # pathfinding. Without this, Pass 1 has no way to emit a numeric
    # target_id for locations the player names explicitly.
    # ------------------------------------------------------------------
    known_locations = [
        {"id": loc["id"], "name": loc["name"]}
        for loc in db.get_all_locations()
    ]

    # ------------------------------------------------------------------
    # Character directory: all non-player characters by id, name, species.
    # Pass 1 uses this to resolve character references in player input
    # (e.g. "spook", "the cat", "mama") to their database IDs so that
    # target_character_id can be set correctly without a full DB lookup.
    # Species is included to help disambiguate references like "the cat"
    # or "the bird" when more than one character of that species exists.
    # ------------------------------------------------------------------
    known_characters = [
        {"id": char["id"], "name": char["name"], "species": char["species"]}
        for char in db.get_all_npcs()
    ]

    # ------------------------------------------------------------------
    # Recent action log (last N entries, oldest first)
    # ------------------------------------------------------------------
    recent_actions = db.get_recent_actions(game_id, limit=config.PASS1_RECENT_ACTIONS)
    # Include only the fields the model needs for disambiguation; the full
    # adjudication JSON is noise at this stage.
    recent_summaries = [
        {
            "turn": entry["id"],
            "character_id": entry["character_id"],
            "action": entry["action_json"],
            "narrative_beat": entry["narrative_beat"],
        }
        for entry in recent_actions
    ]

    packet = {
        "pass": 1,
        "description": (
            "Parse the player's input into a structured action record. "
            "Use the context below to resolve references and intent. "
            "Return only a JSON object — no prose."
        ),
        "player_input": player_input,
        "game": game_summary,
        "player": player_summary,
        "current_location": location_summary,
        # All locations in the game, for resolving destination names → IDs.
        "known_locations": known_locations,
        # All NPCs in the game, for resolving character references → IDs.
        "known_characters": known_characters,
        "recent_actions": recent_summaries,
    }

    logger.debug(
        "Pass 1 packet built: game=%d player=%d location=%d "
        "known_locations=%d known_characters=%d recent_actions=%d",
        game_id,
        player["id"],
        player["current_location_id"],
        len(known_locations),
        len(known_characters),
        len(recent_summaries),
    )
    return packet


# =============================================================================
# Pass 2 — Outcome Adjudication
# =============================================================================

def build_pass2_packet(
    db: Database,
    game_id: int,
    action_record: dict[str, Any],
    involuntary_events: list[dict] | None = None,
    instance_id: int | None = None,
) -> dict[str, Any]:
    """
    Build the context packet for Pass 2 (outcome adjudication).

    Pass 2 is the full adjudication pass. The LLM receives everything it needs
    to determine what happens: who did what, who witnessed it, how every
    character feels about everyone else, and what the location looks like. It
    returns a structured outcome JSON that the engine writes to the database
    before any prose is generated.

    Hidden motivation and hidden attitudes are included here (they are
    adjudication-layer information, not player-visible information). The prose
    rendering pass (Pass 3) never receives hidden data.

    Included:
    - action_record: the structured output from Pass 1
    - game: full world parameters (cultural_norms, speech_filter, etc.)
    - player: full profile (OCEAN, goals including hidden, skills, internal states)
    - location: full context (description, details, items, witness count)
    - characters_present: full profile for each NPC at the location, including
      attitudes toward the player and toward each other, goals (hidden included),
      and interaction history with the player
    - involuntary_events: any involuntary events that fired this turn (these are
      injected into adjudication as additional constraints on the outcome)

    Not included in Pass 2:
    - Raw player_input (already parsed into action_record)
    - Characters at other locations (not relevant to this turn's outcome)

    Args:
        db: Open Database instance.
        game_id: The active game's id.
        action_record: The structured action dict produced by Pass 1.
        involuntary_events: Optional list of involuntary event state dicts that
            fired this turn (from db.get_involuntary_states + roll_involuntary_event).
            May be None or empty if no involuntary events fired.

    Returns:
        A dict ready to be JSON-serialised for the Pass 2 prompt.
    """
    # ------------------------------------------------------------------
    # Game world parameters (full)
    # ------------------------------------------------------------------
    game = db.get_game(game_id)
    if game is None:
        raise ValueError(f"No game found with id={game_id}")

    # ------------------------------------------------------------------
    # Player character (full profile)
    # ------------------------------------------------------------------
    player = db.get_player_character(game_id)
    if player is None:
        raise ValueError(f"No player character found for game_id={game_id}")

    player_profile = _build_character_profile(db, player, include_hidden=True)

    # Faction reputations (v7+): how each faction in this module currently
    # regards the player character. Included only when faction rows exist for
    # this game; the I Am a Cat module has none and this will be an empty list.
    # The faction_description is included so Pass 2 can reason about what kinds
    # of actions raise or lower standing with each faction.
    player_profile["faction_reputations"] = db.get_character_faction_reputations(
        player["id"]
    )

    # Player inventory (v9+): items currently held by the player character,
    # joined with slot information. Empty list for modules without an item
    # system or when the player holds nothing. Gives Pass 2 the information
    # needed to adjudicate item-related actions (offering tea, claiming a book,
    # handing something to an NPC) and to generate item_instantiations for
    # newly claimed items.
    player_profile["inventory"] = db.get_character_inventory(player["id"])

    # ------------------------------------------------------------------
    # Current location (full: description, details, items)
    # ------------------------------------------------------------------
    location_id = player["current_location_id"]
    location = db.get_location(location_id)
    location_context = _build_location_context(db, location_id)

    # ------------------------------------------------------------------
    # Other characters at this location (full profiles)
    # ------------------------------------------------------------------
    present_chars = db.get_characters_at_location(
        location_id, exclude_character_id=player["id"]
    )
    characters_present = []
    for char in present_chars:
        char_profile = _build_character_profile(db, char, include_hidden=True)

        # Attitude this character holds toward the player character.
        char_profile["attitude_toward_player"] = {
            "surface": db.get_attitude_toward(char["id"], player["id"], "surface"),
            "hidden": db.get_attitude_toward(char["id"], player["id"], "hidden"),
        }

        # Player's attitude toward this character.
        char_profile["player_attitude_toward_this_character"] = {
            "surface": db.get_attitude_toward(player["id"], char["id"], "surface"),
            "hidden": db.get_attitude_toward(player["id"], char["id"], "hidden"),
        }

        # Rolling interaction history between this character and the player.
        history = db.get_interaction_history(player["id"], char["id"])
        char_profile["interaction_history"] = history if history else {}

        characters_present.append(char_profile)

    # ------------------------------------------------------------------
    # Characters in adjacent locations (nearby but not present)
    # Gives Pass 2 enough information to reason about what the player
    # character can hear, smell, or otherwise sense through walls.
    # Profile is intentionally minimal — species and emotional_state are
    # the key cues for detectability. The LLM infers whether the player
    # character notices them (a playful cat is audible; a deeply asleep
    # human is not). Full profiles are reserved for characters_present.
    # ------------------------------------------------------------------
    adjacent_connections = db.get_location_connections(location_id)
    characters_nearby = []
    for conn in adjacent_connections:
        adj_loc_id = conn["neighbour_id"]
        adj_loc = db.get_location(adj_loc_id)
        adj_chars = db.get_characters_at_location(
            adj_loc_id, exclude_character_id=player["id"]
        )
        for char in adj_chars:
            characters_nearby.append({
                "id":              char["id"],
                "name":            char["name"],
                "species":         char["species"],
                "emotional_state": char["emotional_state"],
                "location_id":     adj_loc_id,
                "location_name":   adj_loc["name"] if adj_loc else "unknown",
            })

    # ------------------------------------------------------------------
    # Involuntary events that fired this turn
    # ------------------------------------------------------------------
    inv_event_summaries = []
    if involuntary_events:
        for state in involuntary_events:
            inv_event_summaries.append({
                "character_id": state["character_id"],
                "character_name": state.get("character_name"),
                "state_name": state["state_name"],
                "value": state["value"],
                "event_description": state.get("involuntary_event_description"),
            })

    # ------------------------------------------------------------------
    # In-game clock (v5+)
    # Gives Pass 2 the current time of day so it can reason about
    # time-sensitive behaviour (NPC sleep depth, time-of-day plausibility,
    # how long an action took in context). Optional: only included when an
    # instance_id is provided and the instance has a valid clock value.
    # ------------------------------------------------------------------
    current_game_time: dict | None = None
    if instance_id is not None:
        try:
            minutes = db.get_game_clock(instance_id)
            current_game_time = {
                "minutes_past_midnight": minutes,
                "label": _format_game_time(minutes),
            }
        except ValueError:
            # Unseeded sentinel or missing instance — omit the clock field
            # rather than crashing. The engine logs the underlying error.
            logger.warning(
                "Could not fetch game clock for instance_id=%d; "
                "current_game_time omitted from Pass 2 packet.",
                instance_id,
            )

    packet = {
        "pass": 2,
        "description": (
            "Adjudicate the outcome of the action below. Consider the full "
            "context of character psychology, world state, and any involuntary "
            "events. Return only a JSON outcome object — no prose."
        ),
        "action_record": action_record,
        "game": game,
        "player": player_profile,
        "current_location": location_context,
        "characters_present": characters_present,
        "characters_nearby": characters_nearby,
        "involuntary_events_this_turn": inv_event_summaries,
    }

    # Add clock only when available (backwards-compatible with pre-v5 databases).
    if current_game_time is not None:
        packet["current_game_time"] = current_game_time

    logger.debug(
        "Pass 2 packet built: game=%d player=%d location=%d "
        "chars_present=%d chars_nearby=%d involuntary=%d inventory=%d",
        game_id,
        player["id"],
        location_id,
        len(characters_present),
        len(characters_nearby),
        len(inv_event_summaries),
        len(player_profile.get("inventory", [])),
    )
    return packet


# =============================================================================
# Pass 3 — Prose Rendering
# =============================================================================

def build_pass3_packet(
    db: Database,
    game_id: int,
    outcome: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the context packet for Pass 3 (prose rendering).

    Pass 3 converts the structured adjudication outcome into player-facing
    prose. It needs the narrative beat, the game's tone and speech filter, and
    the player character's perspective — but NOT the full adjudication context
    that was needed in Pass 2.

    Hidden motivation and hidden attitudes are NOT included here. The prose
    renderer should only describe what the player's character perceives and
    experiences. The adjudication outcome already encodes which information
    should surface in the narrative.

    The speech_filter is particularly important for modules like I Am a Cat,
    where human speech must be filtered through feline comprehension (tone and
    body language over literal meaning) and cat vocalisations are the player's
    expressive medium.

    Included:
    - outcome: the structured dict from Pass 2
    - game: genre, tone, speech_filter, cultural_norms (world flavour)
    - player: name, species, emotional_state (perspective anchor)
    - current_location: name and description (setting anchor)

    Not included in Pass 3:
    - Hidden motivation or hidden attitudes (adjudication-only)
    - NPC full profiles (the outcome already describes what happened)

    Included selectively:
    - player_internal_states: {state_name: value} for prose-mode states only.
      Pass 3 uses this to weave high-value states (≥ 0.60) into the prose as
      organic physical sensation (hunger as a stomach growl, etc.). NPC internal
      states are not included — NPC behaviour is adjudicated in Pass 2.

    Args:
        db: Open Database instance.
        game_id: The active game's id.
        outcome: The structured outcome dict produced by Pass 2.

    Returns:
        A dict ready to be JSON-serialised for the Pass 3 prompt.
    """
    # ------------------------------------------------------------------
    # Game world parameters (tone, speech filter, cultural flavour)
    # ------------------------------------------------------------------
    game = db.get_game(game_id)
    if game is None:
        raise ValueError(f"No game found with id={game_id}")

    game_summary = {
        "genre": game["genre"],
        "tone": game["tone"],
        "speech_filter": game["speech_filter"],
        # Cultural norms carry world-specific prose flavour (e.g. clutter
        # descriptions, treat discovery chance) that the renderer may use.
        "cultural_norms": game["cultural_norms"],
    }

    # ------------------------------------------------------------------
    # Player character (perspective anchor only)
    # ------------------------------------------------------------------
    player = db.get_player_character(game_id)
    if player is None:
        raise ValueError(f"No player character found for game_id={game_id}")

    player_summary = {
        "id": player["id"],
        "name": player["name"],
        "species": player["species"],
        "emotional_state": player["emotional_state"],
        # description is null until the player has defined their character.
        # Pass 3 (and the opening scene renderer) use this to decide whether
        # to invite self-description via the mirror.
        "description": player["description"],
    }

    # ------------------------------------------------------------------
    # Current location (setting anchor)
    # ------------------------------------------------------------------
    location = db.get_location(player["current_location_id"])
    location_summary = {
        "id": location["id"],
        "name": location["name"],
        "description": location["description_skeleton"],
    } if location else {}

    # ------------------------------------------------------------------
    # Characters referenced in this outcome
    # Extract all character IDs that appear in any outcome array so that
    # Pass 3 has explicit gender and pronoun data. Without this the LLM
    # infers pronouns from names and species, producing inconsistent results
    # across turns. The player is excluded — their pronouns are already
    # implicit in the second-person narrative voice.
    # ------------------------------------------------------------------
    referenced_ids: set[int] = set()

    # attitude_deltas carries both actor and target; collect both
    for entry in outcome.get("attitude_deltas") or []:
        for key in ("character_id", "target_id"):
            try:
                referenced_ids.add(int(entry[key]))
            except (KeyError, TypeError, ValueError):
                pass

    # remaining outcome arrays carry only character_id
    for array_key in ("internal_state_deltas", "emotional_state_updates", "location_change"):
        for entry in outcome.get(array_key) or []:
            try:
                referenced_ids.add(int(entry["character_id"]))
            except (KeyError, TypeError, ValueError):
                pass

    # Remove the player — they speak in second person and need no pronoun entry
    referenced_ids.discard(player["id"])

    characters_referenced: list[dict] = []
    for char_id in sorted(referenced_ids):
        char = db.get_character(char_id)
        if char is None:
            continue
        # Include only the fields needed for prose: name, gender, pronouns.
        # The pronouns field is stored as a JSON string; parse it so the LLM
        # receives a structured array rather than an escaped string.
        raw_pronouns = char.get("pronouns")
        try:
            parsed_pronouns = json.loads(raw_pronouns) if raw_pronouns else None
        except (TypeError, ValueError):
            parsed_pronouns = None

        characters_referenced.append({
            "id": char_id,
            "name": char["name"],
            "gender": char.get("gender"),
            "pronouns": parsed_pronouns,
        })

    # ------------------------------------------------------------------
    # Characters physically present at the player's current location
    #
    # The engine — not the LLM — owns location state. Pass 3 must only
    # describe NPCs as present, acting, or reacting if they appear in this
    # list. Describing an NPC who is elsewhere, or inventing NPC movement
    # that was not in the outcome's location_change array, contradicts the
    # database and breaks continuity on subsequent turns.
    # ------------------------------------------------------------------
    location_id = player["current_location_id"]
    present_npcs = db.get_characters_at_location(
        location_id, exclude_character_id=player["id"]
    )
    characters_present = [
        {
            "id": npc["id"],
            "name": npc["name"],
            "species": npc["species"],
            "emotional_state": npc["emotional_state"],
            # current_activity is the authoritative engine record of what this
            # NPC is doing right now (e.g. 'dancing with Mr. Bingley'). null
            # means the engine has no recorded activity — Pass 3 must not invent
            # one. See the NPC activity rule in PASS3_PROMPT_TEMPLATE.
            "current_activity": npc.get("current_activity"),
        }
        for npc in present_npcs
    ]

    # ------------------------------------------------------------------
    # Adjacent locations (navigation anchor)
    #
    # Included so Pass 3 can weave a natural sense of exits into arrival
    # prose — "the ballroom door stands just ahead", "the staircase descends
    # behind you". The renderer uses this for flavour only; it must not
    # invent movement or imply the player has gone anywhere not recorded in
    # the outcome's location_change array.
    #
    # passage_note is included when non-null: it describes a barrier type
    # (locked / convention-closed) the LLM should reflect in tone.
    # ------------------------------------------------------------------
    connections = db.get_location_connections(location_id)
    adjacent_locations: list[dict] = []
    for conn in connections:
        neighbour = db.get_location(conn["neighbour_id"])
        if neighbour is None:
            continue
        entry: dict = {
            "name": neighbour["name"],
            "is_passable": conn["is_passable"],
        }
        if conn.get("passage_note"):
            entry["passage_note"] = conn["passage_note"]
        adjacent_locations.append(entry)

    # ------------------------------------------------------------------
    # Player internal states (prose-mode only)
    #
    # States with display_mode='prose' are passed to Pass 3 so the renderer
    # can weave high-value states into the prose as organic physical sensation
    # — a stomach growl for high hunger, heavy eyelids for high sleepiness.
    # Only 'prose' display_mode states are included; 'numeric' states are
    # dev tools and must not appear in player-facing prose.
    # ------------------------------------------------------------------
    player_states_raw = db.get_internal_states(player["id"])
    player_internal_states = {
        s["state_name"]: s["value"]
        for s in player_states_raw
        if s.get("display_mode") == "prose"
    }

    packet = {
        "pass": 3,
        "description": (
            "Render the adjudicated outcome as engaging player-facing prose. "
            "Maintain the game's tone and apply the speech filter as specified. "
            "Write from the player character's perspective and sensory experience. "
            "Return only the prose — no JSON, no metadata."
        ),
        "outcome": outcome,
        "game": game_summary,
        "player": player_summary,
        "current_location": location_summary,
        "adjacent_locations": adjacent_locations,
        "characters_present": characters_present,
        "characters_referenced": characters_referenced,
        "player_internal_states": player_internal_states,
    }

    logger.debug(
        "Pass 3 packet built: game=%d player=%d chars_present=%d "
        "chars_referenced=%d adjacent=%d internal_states=%d",
        game_id,
        player["id"],
        len(characters_present),
        len(characters_referenced),
        len(adjacent_locations),
        len(player_internal_states),
    )
    return packet


# =============================================================================
# Internal helpers
# =============================================================================

def _build_character_profile(
    db: Database,
    character: dict[str, Any],
    include_hidden: bool = False,
) -> dict[str, Any]:
    """
    Assemble a full character profile dict from the database.

    Used by both pass 2 (player and NPCs) and any future pass that needs
    a rich character representation. Always includes: OCEAN traits, surface
    goals, skills, internal states, and current emotional state. Optionally
    includes hidden goals and hidden attitudes when include_hidden=True.

    Args:
        db: Open Database instance.
        character: The character row dict (from get_character or similar).
        include_hidden: Whether to include hidden goals and hidden attitudes.
                        Should be True for adjudication, False for prose rendering.

    Returns:
        A dict with all character profile fields for the context packet.
    """
    char_id = character["id"]

    # OCEAN personality traits (floats, 0.0–1.0).
    # Schema columns are prefixed with ocean_ to avoid reserved-word collisions.
    ocean = {
        "openness": character["ocean_openness"],
        "conscientiousness": character["ocean_conscientiousness"],
        "extraversion": character["ocean_extraversion"],
        "agreeableness": character["ocean_agreeableness"],
        "neuroticism": character["ocean_neuroticism"],
    }

    # Goals: include hidden goals only for adjudication pass.
    goals = db.get_character_goals(char_id, include_hidden=include_hidden)

    # Skills, including intrinsic_motivation where present.
    skills = db.get_character_skills(char_id)

    # Internal states (all named float states for this character).
    internal_states = db.get_internal_states(char_id)
    # Reformat for clarity in the context packet: keyed by state_name.
    states_by_name = {
        s["state_name"]: {
            "value": s["value"],
            "display_mode": s["display_mode"],
            # Include involuntary event metadata so adjudication knows which
            # states can fire involuntary events — relevant even when none fired.
            "is_involuntary": s["is_involuntary"],
        }
        for s in internal_states
    }

    # Attitudes toward other characters (surface always; hidden only if requested).
    attitudes = db.get_character_attitudes(char_id, include_hidden=include_hidden)

    profile = {
        "id": char_id,
        "name": character["name"],
        "role": character["role"],
        "species": character["species"],
        "description": character["description"],
        "emotional_state": character["emotional_state"],
        "current_location_id": character["current_location_id"],
        "personality": ocean,
        # MST capability and context beliefs (what this character thinks they
        # can do, and what they believe about the world around them).
        "capability_beliefs": character["capability_beliefs"],
        "context_beliefs": character["context_beliefs"],
        "goals": goals,
        "skills": skills,
        "internal_states": states_by_name,
        "attitudes": attitudes,
        "narrative_points": character["narrative_points"],
    }

    # Surface motivation is always present. Hidden motivation included only
    # when the access_hidden_motivation flag permits it and we're in the
    # adjudication pass.
    profile["surface_motivation"] = character.get("surface_motivation")
    if include_hidden and character.get("access_hidden_motivation"):
        profile["hidden_motivation"] = character.get("hidden_motivation")

    # speech_filter (v9+): per-character natural-language instruction to Pass 3
    # on how this character's communication should be rendered. None means no
    # filter for this character (the game-level filter may still apply).
    # Included in Pass 2 so adjudication knows which characters communicate
    # non-verbally (npc_object role) or unintelligibly, and can author
    # narrative_beat text accordingly.
    profile["speech_filter"] = character.get("speech_filter")

    # Inventory (v10+): items currently held by this character. Included so
    # Pass 2 can reference item ids when emitting item_transfers (e.g. an NPC
    # giving an item to the player requires a valid item_id). Compact format:
    # id, name, and slot only — full description is not needed for adjudication.
    inventory_rows = db.get_character_inventory(char_id)
    profile["inventory"] = [
        {"id": row["id"], "name": row["name"], "slot": row.get("slot")}
        for row in inventory_rows
    ]

    # pending_intent (v7+): working-memory slot for unfulfilled social
    # obligations. Included in Pass 2 profiles so the LLM knows which NPCs
    # are mid-obligation and can adjudicate their behaviour accordingly.
    # None when the character has no outstanding intent.
    profile["pending_intent"] = character.get("pending_intent")

    # current_activity (v8+): timed activity system. Tells Pass 2 what this
    # character is currently doing and how committed they are to continuing it.
    # Distinct from pending_intent — activity persists through commitment
    # fulfillment and is what actually holds an NPC in place mid-dance,
    # mid-conversation, mid-card-game, etc.
    #
    # activity_duration_confidence and activity_renewable are included so
    # Pass 2 can make informed decisions about whether to override or clear
    # the activity (e.g., a low-confidence activity is fair game to interrupt;
    # a high-confidence renewable one requires a stronger narrative reason).
    profile["current_activity"] = character.get("current_activity")
    if character.get("current_activity") is not None:
        profile["activity_duration_confidence"] = character.get(
            "activity_duration_confidence"
        )
        profile["activity_renewable"] = character.get("activity_renewable", 0)

    return profile


def _surface_contents(db: Database, item_id: int, depth: int, max_depth: int = 3) -> list[dict]:
    """
    Recursively collect items resting on a surface item, down to max_depth.

    Items on open surfaces (surface: true) are always visible — a roll on a
    plate on a table is in plain sight. The recursion continues through nested
    surface items (a plate on a tray on a table) but stops at:
      - closed containers (container: true) — contents not visible without opening
      - max_depth, to prevent pathological nesting from ballooning context

    Each entry in the returned list is a compact dict: id, name, is_confirmed,
    location_description, and (if the item is itself a surface) its own contents.
    Properties are included so Pass 2 can recognize further surfaces.

    Args:
        db:        Open Database instance.
        item_id:   The id of the surface item whose contents to fetch.
        depth:     Current recursion depth (starts at 1 for direct children).
        max_depth: Stop recursing beyond this depth.
    """
    children = db.get_items_in_container(item_id)
    result = []
    for c in children:
        entry: dict[str, Any] = {
            "id": c["id"],
            "name": c["name"],
            "properties": c["properties"],
            "is_confirmed": c["is_confirmed"],
            "location_description": c.get("location_description"),
        }
        # Recurse into nested surfaces; stop at closed containers or depth limit.
        if depth < max_depth and c["properties"].get("surface"):
            entry["contents"] = _surface_contents(db, c["id"], depth + 1, max_depth)
        result.append(entry)
    return result


def _build_location_context(
    db: Database,
    location_id: int,
) -> dict[str, Any]:
    """
    Assemble the full location context dict for a given location.

    Includes the location record, valid generated details (up to
    PASS2_MAX_LOCATION_DETAILS), and visible items (up to PASS2_MAX_ITEMS).
    The caps prevent context packets from ballooning in heavily explored
    or cluttered locations.

    Args:
        db: Open Database instance.
        location_id: The id of the location to describe.

    Returns:
        A dict with location, details, and items fields.
    """
    location = db.get_location(location_id)
    if location is None:
        return {"id": location_id, "error": "Location not found"}

    details = db.get_location_details(
        location_id, max_results=config.PASS2_MAX_LOCATION_DETAILS
    )
    items = db.get_items_at_location(
        location_id,
        max_results=config.PASS2_MAX_ITEMS,
    )

    # Compact item representation for the context packet.
    # properties is already parsed to a dict by get_items_at_location.
    #
    # Surface items (surface: true — plate, tray, table) show their contents
    # recursively: items on a plate on a table are all visible at once because
    # surfaces don't obstruct visibility. The recursion stops at closed containers
    # (container: true) and at MAX_SURFACE_DEPTH to prevent runaway nesting.
    #
    # Closed containers (container: true — pack, canister, box) do NOT show
    # contents — you cannot see inside a closed container without opening it.
    _MAX_SURFACE_DEPTH = 3
    item_summaries = []
    for item in items:
        summary = {
            "id": item["id"],
            "name": item["name"],
            "description": item["description"],
            "properties": item["properties"],
            "is_confirmed": item["is_confirmed"],
            "location_description": item.get("location_description"),
        }
        if item["properties"].get("surface"):
            summary["contents"] = _surface_contents(db, item["id"], depth=1)
        item_summaries.append(summary)

    # Adjacent locations: explicitly connected neighbours, passable only.
    # Pass 2 uses this to validate movement actions and to inform the LLM
    # about which exits actually exist from the current location.
    # Neighbour names are included so the LLM can refer to them in prose.
    connections = db.get_location_connections(location_id)
    adjacent_locations = []
    for conn in connections:
        neighbour = db.get_location(conn["neighbour_id"])
        entry = {
            "location_id": conn["neighbour_id"],
            "name": neighbour["name"] if neighbour else "unknown",
            "connection_type": conn["connection_type"],
        }
        # passage_note (v7+): semantic barrier description for Pass 2.
        # Distinguishes physically locked passages from convention-closed ones.
        # Omitted from context when null (no special note needed).
        if conn.get("passage_note"):
            entry["passage_note"] = conn["passage_note"]
        adjacent_locations.append(entry)

    return {
        "id": location["id"],
        "name": location["name"],
        "description": location["description_skeleton"],
        "witness_count": location["witness_count"],
        "situation_flags": location["situation_flags"],
        "generated_details": [d["detail"] for d in details],
        "items": item_summaries,
        # Reachable exits from this location (passable connections only).
        # location_change in the outcome must target one of these location_ids
        # (or remain at the current location).
        "adjacent_locations": adjacent_locations,
    }
