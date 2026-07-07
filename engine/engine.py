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

import argparse
import json
import logging
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path

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
#
# BRACE ESCAPING — read this before editing any template:
# These strings are processed by Python's str.format(), which treats any
# single { or } as a placeholder. Literal braces that should appear in the
# prompt text — JSON examples, object shapes, set notation — must be doubled:
#   Write {{ and }} in the source; the player sees { and } in the prompt.
# The one real placeholder, {context_json}, stays as a single pair.
# Forgetting this causes an IndexError at runtime when the template is
# formatted. Search for {{ in the existing templates to see the pattern.

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
- Movement phrases: "move to X", "walk to X", "proceed to X", "head to X",
  "make our way to X", "lead to X", "go up to X", "as we go to X", and similar
  natural-language travel expressions should all resolve to action_type "move"
  with the destination id resolved from known_locations. Do not classify these
  as a different action type or leave target_id null when the destination is
  listed in known_locations.
- For actions that target a character (speak, interact, examine, take, drop,
  use, or any other action whose primary object is a person or creature): look
  up the character in known_characters and set target_character_id to the
  matching id. Use the species field to disambiguate when the player refers to
  a character by type ("the cat", "the bird", "the man") rather than by name.
  Do NOT leave target_character_id null when the character can be resolved from
  known_characters.

Required output fields:
  action_type         (string, one of the types above)
  verb                (string, the player's intended verb in plain English)
  target              (string or null, the primary object or character of the action)
  target_id           (integer or null, for move actions: the location id from
                       known_locations; null for all other action types)
  target_character_id (integer or null, resolved from known_characters when the
                       action targets a character; null for move and item actions)
  location_id         (integer, the player's current location)
  detail              (string or null, any additional qualifying information)
  raw_input           (string, the player's unmodified input text)

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
- SPEECH ACTS REQUIRE PRESENCE: if the player's action is a speak, interact,
  or any directed address toward a specific character, and that character
  appears in characters_nearby rather than characters_present, the speech act
  cannot complete. The targeted character is out of earshot and cannot hear,
  see, or respond. Adjudicate the outcome as the player calling out without
  receiving a response — no attitude deltas, no emotional_state changes, and
  no narrative response from that character. Describe only what the player
  can observe: their own words going unanswered. Do not route the speech to a
  different character as a substitute. Yelling across rooms to reach a nearby
  character is a future feature; for now, absence means no interaction.
- NPC ACTIONS ARE AUTHORITATIVE: only describe NPCs acting, speaking, or
  reacting in the narrative_beat if they appear in characters_present.
  Do not attribute actions or reactions to NPCs who are not listed there.
  If an NPC is in characters_nearby (adjacent room), they may be audible or
  detectable by smell, but do not describe them as present, visible, or
  physically interacting with the scene.
- PENDING INTENT IS MANDATORY: if an NPC at the current location has a
  non-null pending_intent, they MUST act on it this turn. This is not optional
  flavor — it is an unfulfilled obligation seeded by the module author or a
  prior turn's adjudication. The NPC must take the described action (speak,
  gesture, move, etc.) in your narrative_beat and in npc_initiated_actions,
  even if the player's action did not address them. Once the intent is
  fulfilled (or explicitly abandoned), clear it via pending_intent_updates
  with pending_intent: null. Do not let pending_intent persist across multiple
  turns without being acted on. If the NPC's intent involves speaking, they
  must produce actual dialogue — not a smile, a nod, or a description of
  their expression.
- TARGET PRIMACY: The player's action_record defines who is being addressed
  and what is happening. The primary outcome must resolve the player's intended
  action toward action_record.target. NPC pending_intent discharges are
  secondary events: they belong in npc_initiated_actions and may colour the
  narrative_beat as background action, but they must not replace or override
  the resolution of the player's action. If the player is speaking to
  Character A, do not make Character B's pending_intent the dominant narrative
  event of the turn. Both happen; the player's stated action takes precedence.
- AUTONOMOUS NPC BEHAVIOR: when an NPC at the current location has an internal
  state ≥ 0.75 that an available item or plausible action could satisfy, they
  may act on it without a pending_intent — a hungry NPC eats food that is
  visible at the location, a drowsy NPC dozes off in a comfortable chair, a
  character with a strong desire to dance moves toward an opening. This models
  realistic background behaviour and is the engine's general mechanism for
  emergent NPC action (analogous to a cat pouncing when curiosity peaks, or
  a young man asking for a dance when the social moment is right). If the NPC
  acts autonomously: record the action in npc_initiated_actions and emit the
  appropriate internal_state_delta. Apply OCEAN traits and MST goals as a
  filter: a highly conscientious NPC may suppress hunger to finish a task;
  a low-agreeableness NPC may not share food even when hungry. Do not force
  autonomous behaviour when the character's profile makes it implausible.
- NPC ARRIVAL AWARENESS: newly_arrived_npcs_this_turn lists any NPC who
  autonomously wandered into the player's current location this turn (background
  movement the engine applied before this turn's context was assembled — not
  something the player did). Judge, per NPC, whether their arrival is salient
  enough to mention in narrative_beat: a character entering a quiet room the
  player already occupies is hard to miss; the same arrival in a crowded space
  might reasonably go unremarked. Use the same AUTONOMOUS NPC BEHAVIOR judgment
  above to decide whether a newly-arrived NPC also acts on the encounter this
  turn — an unoccupied (current_activity null), sociable, or characteristically
  playful NPC finding themselves suddenly co-located with the player is a
  plausible moment for them to initiate contact (record it in
  npc_initiated_actions). Do NOT use pending_intent to represent a standing
  personality trait or general disposition ("always wants to play") — a
  non-null pending_intent suppresses that NPC's autonomous wandering on future
  turns (see PENDING INTENT IS MANDATORY above), so setting one permanently
  would silently freeze a character who is supposed to keep roaming. Only set
  pending_intent here for a genuine, situational follow-up this specific
  encounter creates (e.g. the NPC now wants the player to keep playing), the
  same way any other pending_intent is established, and clear it normally once
  it resolves.
- RELATIONSHIP REFERENCES: when the player refers to a character by relationship
  ("my cousin", "Charlotte's brother", "Sir William's daughter"), resolve the
  referent from the descriptions in the character profiles before acting. Do not
  substitute a more convenient or nearby character — honor the player's expressed
  intent. If the referent cannot be resolved from the descriptions, flag the
  ambiguity in adjudication_notes and ask the player to clarify rather than guess.
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
- SINGLE-HOP CEILING: if action_record does NOT contain a "route" key, the
  engine has not pre-resolved any path — you are adjudicating a freehand
  action, not a targeted move. In this case you may move the player at most
  one hop: to current_location itself (no move) or to a single location
  listed in current_location.adjacent_locations. You may NOT narrate the
  player arriving at, entering, or acting inside any location beyond that
  one hop, even if the player's phrasing implies traveling further (e.g. a
  compound command like "walk on them and sit on their face" that assumes
  the player already knows which room and bed to head for). Concretely: if
  reaching the player's evident goal would require passing through an
  intermediate location not in adjacent_locations, your narrative_beat must
  stop at what is reachable this turn — describe the player setting off,
  climbing, or reaching the nearest adjacent location, and treat the rest of
  the journey as unresolved (a natural fit for outcome_type "partial_success"
  or "failure"). Do NOT write a narrative_beat that describes full arrival
  at a distant room while location_change only encodes (or is only able to
  encode) one adjacent hop — the two must agree, and location_change's own
  adjacent_locations constraint (see above) is the ceiling on how far the
  narrative may travel this turn. A player who wants to reach a specific,
  named destination in one turn should get there via a targeted move action
  (which the engine resolves as a route, per MULTI-STEP MOVEMENT above);
  this rule exists for the case where they did not, and prevents the
  narrative from quietly promising more distance than the database records.

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
  item_changes         (list of {{item_id, field, new_value}} for non-location item
                        updates — permitted fields: is_confirmed, description,
                        is_visible, quality. Do NOT use item_changes to move an item;
                        use item_transfers instead.)
  item_transfers       (list of item movements for existing items. Use when the player
                        picks up, drops, or gives an item, or an NPC moves one.
                        Each entry must include:
                          item_id (integer, required — id of the item to move)
                          location_description (string — where it now sits, e.g.
                               "tucked into the front pocket", "set on the worktable")
                        Plus exactly ONE destination:
                          to_char_id (integer) — item goes to a character's inventory
                               (also include slot: right_hand, left_hand, both_hands,
                                mouth, worn, pocket, in_pack, carried)
                          to_loc_id (integer) — item dropped or placed at a location
                               (use when no specific surface or container is the target)
                          to_item_id (integer) — item placed ON a surface or INSIDE a
                               container: use this when the player puts something on a
                               plate, tray, table, worktable, or inside a bag or pack.
                               The target item's id comes from its entry in the
                               location's items list. Properties "surface": true means
                               items go on top; "container": true means items go inside.
                               ALWAYS prefer to_item_id over to_loc_id when the player
                               names a specific surface or container as the destination.
                        When to_loc_id is set, the engine marks the item is_confirmed=1
                        (the player placed it deliberately).
                        IMPORTANT — do NOT emit item_transfers for items already in a
                        character's inventory (char_id set) when that character simply
                        moves to a new location. Carried items travel with the character
                        automatically; no entry is needed until the character deliberately
                        puts the item down, hands it to someone, or places it on a surface.
                        BORROW / LOAN: when a player asks to borrow an item and the NPC
                        is willing, this is a physical handover — emit item_transfers with
                        to_char_id=player_id exactly as you would for a gift. The item
                        leaves the NPC's inventory. There is no separate loan flag yet;
                        treat willing loans the same as gifts in the DB.
                        ITEM CONSISTENCY: if your narrative_beat describes an item being
                        picked up, carried, moved, installed, given, or otherwise
                        physically handled, that handling MUST be reflected in
                        item_transfers or item_changes this same turn. The engine updates
                        DB item records from these fields only — it does not read prose.
                        An item described as moved, installed, or consumed but absent from
                        these fields will remain exactly where it was seeded, causing
                        incorrect state (e.g. a "replaced" component still lying in its
                        original location as if untouched, even though the narrative says
                        someone is now holding or has installed it). For an item
                        permanently installed into or consumed by a character (a
                        replacement part, a spent component, food that is eaten): emit an
                        item_transfers entry with to_char_id set to the installing or
                        consuming character, THEN an item_changes entry setting
                        is_visible=0 and updating description to reflect its
                        installed/consumed state. Do not leave a described-as-handled item
                        sitting unmoved and unaccounted for.
                        Empty list if no items moved this turn.)
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
  activity_updates     (list of {{character_id, activity, duration_minutes, confidence,
                        renewable}} for any changes to NPC current activities. Use this
                        when an NPC begins a new activity (e.g. starts dancing, sits
                        down to cards, commits to a conversation), updates an existing
                        one, or ends one. To end an activity, set activity to null.
                        duration_minutes: estimated minutes the activity will last, or
                        null for genuinely open-ended activities. confidence: float
                        0.0–1.0; how certain you are of the duration estimate (use low
                        values for social activities that depend on others' cooperation,
                        high values for solitary committed activities like card play).
                        renewable: 1 if the activity should persist past its estimated
                        duration until explicitly ended; 0 if the engine may auto-clear
                        it once the estimated time expires. The engine records
                        activity_started_at from the game clock at apply time — you
                        do not supply it.
                        DURATION CALIBRATION (Regency social events): a country dance
                        set lasts 20–30 minutes (multiple figures with the same partner);
                        a cotillion or reel 15–20 minutes; a brief social exchange 3–5
                        minutes; sitting down to cards 30–60 minutes with renewable=1.
                        When a dance commitment is established, set duration_minutes to
                        at least 20 for a standard country set.
                        DANCE COMMITMENT: when the player and an NPC commit to dance
                        together, set activity_updates for BOTH the player character
                        and the NPC partner with matching activity text, duration, and
                        confidence. Also set pending_intent on the NPC partner to record
                        the social obligation, so the commitment survives across turns.
                        Empty list if no NPC activities changed.
                        DO NOT include activity_updates for the player character — EXCEPT
                        when a dance commitment is established (see DANCE COMMITMENT above),
                        in which case include the player character in activity_updates.)
  npc_initiated_actions (list of {{character_id, action_description}} for any actions
                        an NPC independently initiates this turn that are narratively
                        significant but not captured by the other fields — e.g. an NPC
                        who speaks up unprompted, makes a gesture, or changes their
                        intent based on what they observed. These are included in the
                        action log for continuity but do not change any DB state
                        beyond what other fields already handle. Empty list if none.)
  new_characters       (list of new NPC records to create lazily when the player
                        references a plausible character not in the cast. Use this
                        when: the character shares a surname with someone present,
                        they would naturally be at this event, or they are a named
                        family member whose existence is established in descriptions.
                        Do NOT invent characters the player has not referenced or
                        whose presence is implausible. Each entry must include:
                          name (string, required),
                          description (brief prose placing them socially),
                          emotional_state (e.g. "excited", "pleasant"),
                          current_location_id (integer — where they plausibly are),
                          gender (string or null),
                          pronouns (list of [subject, object, possessive_det,
                                   possessive_pro, reflexive] or null).
                        OCEAN traits are optional; omit if unknown. The engine
                        will insert the character and they will appear in future
                        context packets as full cast members. Empty list if no
                        new characters are needed.)
  item_instantiations  (list of new items to create and place. Use when:
                          - the player describes carrying an item during self-definition
                          - the player claims a mid-play item ("I have a book in my pack")
                          - an NPC produces a new item that did not exist before
                        Each entry must include:
                          name (string, required — short canonical name)
                          description (string or null — prose appearance/condition)
                          properties (object — module-specific attributes, or {{}})
                          location_description (string or null — where it sits)
                          Exactly ONE placement:
                            character_id (integer) — item is held by a character
                            location_id  (integer) — item is at a location
                            container_item_id (integer) — item inside a container
                          slot (string, required if character_id set — examples:
                               right_hand, left_hand, worn, in_pack, carried)
                          is_confirmed (1 = real item, default; 0 = claimed but
                                        not yet fully adjudicated)
                        Do NOT instantiate items already in player.inventory.
                        To move an existing item, use item_transfers instead.
                        Empty list if no new items are created this turn.)
  player_character_update (object or null. Use when the player explicitly
                        describes themselves or corrects their appearance —
                        a self-introduction, a look in a mirror, a declared
                        physical attribute. Fields (all optional):
                          description (string) — prose description of the player
                              character as data (third-person); Pass 3 renders it
                              in second person.
                          gender (string or null)
                          pronouns (list of {{case, form}} objects or null)
                        Set to null if the player made no self-defining statements
                        this turn. Do not populate based on proximity to a mirror
                        alone — only populate when the player actively describes
                        themselves.)
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
  (sight, sound, smell, touch as appropriate). Do not describe their interior
  emotional state or infer their intentions — that belongs to the player.
- Introduce any other characters who are present at the starting location.
- Apply the speech_filter if relevant, and match the game tone precisely.
- Do not reveal hidden motivation or any information outside the player
  character's direct perception.
- Do NOT narrate the player taking any action — no reaching for handles, no
  stepping forward, no doors opening. The scene ends with the world as it is,
  not with the player moving or touching anything. Actions are the player's
  to choose.
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
- NPC pending_intents: where a character present has a pending_intent, render
  it as atmospheric physical action appropriate to their nature. An npc_object
  acts but does not speak — convey intent through what the player perceives
  (light, motion, physical presence), not through words or direct instruction.
  Do not state the intent; let it emerge from what the senses report.
- TIME AND ATMOSPHERE GROUNDING: `current_location.situation_flags` and
  `current_game_time` (when present) are authoritative facts about the
  world, not suggestions — this is the opening scene, so they are your ONLY
  source of truth for time of day and ambient condition; `description`
  alone is deliberately time-neutral and must not be used to infer it. Do
  not describe a time of day, weather, or ambient condition that
  contradicts them: a location flagged "night"/"humans_asleep" is never
  rendered as daytime; a location flagged "dark" is never rendered as
  sunlit. If neither field gives a cue for some ambient detail, invent
  plausibly — but never invent something that contradicts what is given.

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
- Length: prioritize restraint over coverage — a compact beat that lands
  cleanly outperforms a longer one that dilutes the moment. For a routine
  action, prose of roughly this length and density is correct:
  "You cross the room to the window and glance out at the street below.
  Nothing moves in the gray hour before dawn — just a parked car and a
  stray cat picking its way along a fence. You turn back toward the room's
  warmth, this errand answered as fully as it's going to be tonight."
  Do NOT pad a routine beat out with additional short sentences or
  fragments for rhythm — three short beats strung together ("Options.
  Considerations. The stairs await.") are not shorter than one sentence
  saying the same thing, and both count against the same length budget.
  Only expand toward a short paragraph — of roughly this length, and only
  when the outcome is genuinely dramatically significant (a nonzero
  narrative_point_delta, an involuntary event, or a major social or
  narrative turn) — like this:
  "You push through the door and the noise of the room hits you first —
  raised voices, a chair scraping back, someone's sharp intake of breath.
  The scene resolves in pieces: an overturned cup, a spreading stain, two
  people frozen mid-argument, both turning toward you at once. Whatever
  was happening a second ago has stopped, replaced by the sudden,
  uncomfortable attention of everyone in the room. Something here just
  changed, and it changed because you walked in."
  Match the density and pacing of these examples, not just their sentence
  count — a string of short fragments is not a substitute for genuine
  brevity. The ironic_observational register (and others like it) rewards
  restraint; overwriting dilutes the effect. Involuntary events warrant
  their own brief beat, not an additional paragraph.
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
- NPC activity is authoritative: each entry in `characters_present` has a
  `current_activity` field. If it is null, the engine has no recorded activity
  for that character — describe them as simply present (standing, watching,
  conversing in general), NOT as engaged in any specific action such as dancing,
  playing cards, or eating. Only describe an NPC as performing a specific activity
  if their `current_activity` field explicitly records it, or if the outcome's
  `narrative_beat` explicitly names them doing it this turn.
- Navigation: if the player has just moved to a new location (the outcome
  includes a location_change for the player), weave a brief, natural mention
  of the available exits into the arrival prose — a door, a corridor, the
  direction back. Use the `adjacent_locations` list. If a location has
  is_passable=false, convey the barrier in tone rather than stating it as a
  rule. Keep this light; one natural phrase is enough.
- INTERNAL STATES: if player_internal_states contains any state with value
  ≥ 0.60, weave a brief physical reminder into the prose — a hollow ache or
  stomach growl for high hunger, heavy eyelids for high sleepiness, a restless
  edge to your attention for high curiosity. This should read like organic
  first-person sensation, not a status report. One reminder per high state per
  turn; keep it to a clause or short phrase woven into an existing sentence,
  not a dedicated sentence of its own. Omit the reminder if the player's current
  action already directly addresses that state (eating while hungry, resting
  while sleepy, etc.) — the prose of that action already carries the weight.
- ANTI-REPETITION: the `recent_prose` field contains the rendered prose from
  the last 2–3 turns. Before writing, check it for repeated phrases, images,
  and sensory descriptors — then use different ones. This applies to ALL prose
  elements: atmospheric details, character descriptions, internal-state
  reminders, and figurative language. If recent turns have used "curiosity hums
  beneath your skin", reach for a different physical sensation entirely (a flicker
  of interest at the edge of your thoughts, a slight sharpening of attention,
  etc.). If the candlelight has been mentioned, let it stand. Variety is not
  optional — a skilled narrator does not repeat themselves turn after turn.
- TIME AND ATMOSPHERE GROUNDING: `current_location.situation_flags` and
  `current_game_time` (when present) are authoritative facts about the
  world, not suggestions. Do not describe a time of day, weather, or
  ambient condition that contradicts them: a location flagged
  "night"/"humans_asleep" is never rendered as daytime; a location flagged
  "dark" is never rendered as sunlit. If neither field gives a cue for some
  ambient detail, invent plausibly — but never invent something that
  contradicts what is given.

Context:
{context_json}
"""


GREEN_ROOM_EXTRACTION_PROMPT = """\
You are the character creation interpreter for the DAVE RPG Engine.
The player has described their character in free text. Your job is to extract
structured Fate Core character data from that description.

Rules:
- Return a single JSON object. No prose, no explanation, no markdown fences.
- High Concept: a single evocative phrase that sums up who the character is.
  Should be invokelable as a Fate Point advantage. Infer from the most
  prominent self-description if the player did not state one explicitly.
- Trouble: a single phrase describing the character's personal complication
  or vulnerability — the most natural target for compels. Infer if not stated.
- Aspects: additional defining phrases (relationships, notable competencies,
  signature possessions, background details). Standard Fate Core allows up to 3.
  Capture only those the player expressed; do not invent extras.
- Description: a third-person prose description of the character for the
  engine's internal record. Synthesise from the player's input; 2-3 sentences.
  Written as character data, not as player-facing prose.
- Skills: any specific skills or competencies the player mentioned. Open
  natural-language taxonomy — capture the terms the player used.
- confirmation_text: a warm 2-3 sentence summary of what you understood,
  written directly to the player (second person). Shown as confirmation before
  the game begins.

Required output fields:
  high_concept      (string)
  trouble           (string)
  aspects           (list of 0-3 strings)
  description       (string)
  skills            (list of strings, may be empty)
  confirmation_text (string)

Module context:
{module_context}

Player's character description:
{player_input}
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

    def __init__(
        self,
        db: Database,
        game_id: int,
        transcript_path: str | None = None,
    ) -> None:
        """
        Initialise the engine for a specific game.

        Args:
            db:              An open Database instance with the schema applied.
            game_id:         The id of the game to run. Must exist in the game table.
            transcript_path: Optional path to a transcript file. If provided,
                             all player-visible prose and player inputs are written
                             there in addition to being printed to stdout. The file
                             is created (or appended to) on first write and closed
                             when run() exits. If None, no transcript is saved.

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

        # Transcript file handle. Opened lazily on first write in run() so that
        # the file is not created if the engine errors before play begins.
        self._transcript_path: str | None = transcript_path
        self._transcript_file = None  # opened in run()

        logger.info(
            "GameEngine ready: game=%d (%s) player=%s backend=%s instance=%s",
            game_id,
            self._game.get("name", "untitled"),
            self._player["name"],
            config.LLM_BACKEND,
            instance["id"] if instance else "none",
        )

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _current_game_time(self) -> int:
        """
        Return the current in-game clock value in minutes, read live from the
        database.

        self._instance is loaded once at startup and is not updated as the
        clock advances — do not read current_time_minutes from it. Use this
        helper wherever a fresh clock value is needed (activity started_at,
        expiry checks, wander suppression).

        Returns 0 if no game_instance is configured (pre-v5 modules or
        unseeded databases), which safely disables time-based expiry.
        """
        if self._instance is None:
            return 0
        return self.db.get_game_clock(self._instance["id"])

    # -------------------------------------------------------------------------
    # Transcript helpers
    # -------------------------------------------------------------------------

    def _transcript_write(self, text: str) -> None:
        """
        Write a block of text to the transcript file.

        Opens the file on the first call (creating it and any parent directories
        if needed). Subsequent calls append to the same open handle. Does nothing
        if no transcript path was configured.

        Args:
            text: The text to append. A trailing newline is added if absent.
        """
        if self._transcript_path is None:
            return

        if self._transcript_file is None:
            transcript_path = Path(self._transcript_path)
            transcript_path.parent.mkdir(parents=True, exist_ok=True)
            # Open in append mode so multiple sessions can be captured to the
            # same file if the caller supplies a fixed path. The auto-generated
            # path in main() is always unique (timestamped), so append vs write
            # makes no practical difference there.
            self._transcript_file = open(transcript_path, "a", encoding="utf-8")  # noqa: WPS515
            logger.info("Transcript writing to: %s", transcript_path)

        if not text.endswith("\n"):
            text += "\n"
        self._transcript_file.write(text)
        self._transcript_file.flush()  # ensure each turn is persisted immediately

    def _transcript_close(self) -> None:
        """Close the transcript file if it is open. Safe to call multiple times."""
        if self._transcript_file is not None:
            self._transcript_file.close()
            self._transcript_file = None

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
        game_title = self._game.get('name', 'DAVE RPG')
        print(f"\n=== {game_title} ===\n")

        # ------------------------------------------------------------------
        # Green Room: pre-game character creation stage (v11+).
        # Runs when player_definition_mode == 'green_room' AND the player
        # has no existing character_aspect records. The aspects check makes
        # this stage idempotent — resuming a session after character creation
        # was completed in a prior run does not repeat it.
        # ------------------------------------------------------------------
        if self._game.get("player_definition_mode") == "green_room":
            existing_aspects = self.db.get_character_aspects(self._player["id"])
            if not existing_aspects:
                self._run_green_room()
                # Refresh player after the creation stage may have updated
                # the description field.
                self._player = self.db.get_player_character(self.game_id)

        try:
            opening = self._render_opening_scene()
            wrapped_opening = textwrap.fill(opening, width=80)
            print(wrapped_opening)
            self._transcript_write(f"=== {game_title} ===\n\n{wrapped_opening}")
        except (LLMError, LLMJSONError) as exc:
            # Degrade gracefully: fall back to bare name if opening render fails.
            logger.warning("Opening scene render failed (%s); using fallback.", exc)
            fallback = f"You are {self._player['name']}."
            print(fallback)
            self._transcript_write(f"=== {game_title} ===\n\n{fallback}")
        print()

        while True:
            # Refresh the player record at the top of each turn so location
            # and emotional state are always current.
            self._player = self.db.get_player_character(self.game_id)

            # ------------------------------------------------------------------
            # Step 1: Check involuntary events and NPC wandering
            # ------------------------------------------------------------------
            involuntary_fired = self._check_involuntary_events()
            # Clear any mechanically expired NPC activities before processing
            # the turn. This must run before wandering so that an NPC whose
            # dance just ended is no longer suppressed from wandering this turn.
            self._check_activity_expiry()
            # Move NPCs that roll for autonomous wandering this turn.
            # This happens before Pass 1 so that by the time the context packet
            # is assembled, NPCs are already at their new locations.
            newly_arrived_npcs = self._check_npc_wandering()

            # ------------------------------------------------------------------
            # Step 2: Read player input
            # ------------------------------------------------------------------
            try:
                raw_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nFarewell.")
                self._transcript_write("\n> [session ended]\n")
                break

            if not raw_input:
                continue

            # Capture the player's input in the transcript before processing.
            self._transcript_write(f"\n> {raw_input}")

            if raw_input.lower() in ("quit", "exit", "q"):
                print("\nFarewell.")
                self._transcript_write("\n> [session ended]\n")
                break

            # ------------------------------------------------------------------
            # Steps 3–6: Three-pass processing
            # ------------------------------------------------------------------
            try:
                prose = self._process_turn(raw_input, involuntary_fired, newly_arrived_npcs)
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
            wrapped_prose = textwrap.fill(prose, width=80)
            print()
            print(wrapped_prose)
            print()
            self._transcript_write(f"\n{wrapped_prose}")

        # ------------------------------------------------------------------
        # Close transcript (if open) before exit summary logging so the file
        # is fully written regardless of what happens in the summary block.
        # ------------------------------------------------------------------
        self._transcript_close()

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
            "item_transfers": [],
            "new_location_details": [],
            "faction_reputation_changes": [],
            "pending_intent_updates": [],
            "activity_updates": [],
            "npc_initiated_actions": [],
            "new_characters": [],
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

    def _check_pass3_length(
        self, prose: str, outcome: dict, action_log_id: int | None
    ) -> None:
        """
        Log a warning if rendered Pass 3 prose exceeds its word-count target.

        This is observability only — it never rejects, retries, or truncates
        prose. LLMs do not reliably self-count words or sentences while
        generating, so the actual length steering lives in the worked
        exemplar in PASS3_PROMPT_TEMPLATE's Length rule; this check exists so
        drift away from that steering shows up in the logs (grep for "Pass 3
        prose exceeded length target") instead of requiring a playtester to
        notice and a manual sentence count to confirm, as happened
        2026-07-05.

        Args:
            prose: The rendered Pass 3 output.
            outcome: The outcome dict this prose was rendered from (either a
                     real Pass 2 outcome or a synthetic one, e.g. from
                     _render_move_blocked). Used only to read
                     narrative_point_delta and outcome_type for the log line
                     and threshold choice.
            action_log_id: The action_log row this prose was written to, or
                           None for renders that don't write one (e.g. the
                           move-blocked path).
        """
        word_count = len(prose.split())
        is_significant = (outcome.get("narrative_point_delta") or 0) > 0
        threshold = (
            config.PASS3_LENGTH_THRESHOLD_SIGNIFICANT
            if is_significant
            else config.PASS3_LENGTH_THRESHOLD_ROUTINE
        )
        if word_count > threshold:
            logger.warning(
                "Pass 3 prose exceeded length target: %d words (threshold=%d, "
                "significant=%s, outcome_type=%s, action_log_id=%s)",
                word_count,
                threshold,
                is_significant,
                outcome.get("outcome_type"),
                action_log_id,
            )

    def _render_move_blocked(self, reason: str) -> str:
        """
        Run Pass 3 on a synthetic 'move blocked' outcome so the player receives
        module-appropriate prose rather than a raw engine constraint message.

        Called when _resolve_multistep_move() returns reachable=False. The raw
        no_path_reason string is used only as a narrative cue to Pass 3 — it is
        never shown to the player directly.

        No state is changed (elapsed_minutes=0, all delta lists empty). The
        player remains at their current location.

        Args:
            reason: The block reason from route["no_path_reason"], e.g.
                    "You haven't been to Supper Room yet."

        Returns:
            Rendered prose string from Pass 3.
        """
        synthetic_outcome = {
            "outcome_type": "failure",
            "narrative_beat": (
                f"The player attempts to move but is blocked: {reason} "
                "Render this as an in-world moment — the character realises "
                "they cannot navigate directly to the destination because they "
                "are not yet familiar with the route. Stay in character and in "
                "the module's tone. Do not use system or game-mechanic language."
            ),
            "elapsed_minutes": 0,
            "attitude_deltas": [],
            "internal_state_deltas": [],
            "emotional_state_updates": [],
            "location_change": [],
            "item_changes": [],
            "item_transfers": [],
            "new_location_details": [],
            "faction_reputation_changes": [],
            "pending_intent_updates": [],
            "activity_updates": [],
            "npc_initiated_actions": [],
            "new_characters": [],
            "narrative_point_delta": 0,
            "adjudication_notes": f"Move blocked (engine pre-check): {reason}",
        }

        pass3_packet = build_pass3_packet(self.db, self.game_id, synthetic_outcome)
        pass3_prompt = PASS3_PROMPT_TEMPLATE.format(
            context_json=json.dumps(pass3_packet, indent=2)
        )
        logger.debug("Move-blocked Pass 3 prompt:\n%s", pass3_prompt)

        prose = self.llm.call(pass3_prompt)
        logger.debug("Move-blocked prose: %.120s", prose)
        self._check_pass3_length(prose, synthetic_outcome, action_log_id=None)
        return prose

    # -------------------------------------------------------------------------
    # Green Room character creation stage (v11+)
    # -------------------------------------------------------------------------

    def _run_green_room(self) -> None:
        """
        Run the out-of-character character creation stage for green_room modules.

        Called from run() when player_definition_mode == 'green_room' and the
        player has no existing character_aspect records. Presents the module
        author's creation prompt, collects the player's free-text description,
        calls the LLM to extract structured Fate Core data, and writes the
        results to the database before the opening scene begins.

        The module author configures this stage by setting two keys in the
        game record's module_flags JSON:
            character_creation_prompt  — the framing shown to the player.
            character_creation_hint    — optional shorter cue (one paragraph)
                                         explaining Fate Core aspects to players
                                         who may not be familiar with the system.

        If High Concept or Trouble are missing after the first extraction pass,
        a short targeted follow-up question is asked for each missing field.
        The follow-up answer is appended to the original input and a second
        extraction pass is run. Only the still-missing fields are updated;
        everything already extracted is preserved.

        On LLM failure or empty player input the stage is skipped gracefully;
        the opening scene will render with whatever character data already exists
        in the database (which may be the seeded skeleton only).

        DB writes:
            - character_aspect records (high_concept, trouble, up to 3 aspects)
            - character.description (from LLM synthesis)
            - character_skill rows for any skills mentioned (INSERT OR IGNORE —
              does not overwrite skills already seeded)
        """
        flags = self._game.get("module_flags") or {}
        creation_prompt = (flags.get("character_creation_prompt") or "").strip()
        creation_hint   = (flags.get("character_creation_hint")   or "").strip()

        # Print out-of-character header and module prompt.
        print("--- Character Creation ---\n")
        if creation_prompt:
            print(textwrap.fill(creation_prompt, width=80))
            print()
        if creation_hint:
            print(textwrap.fill(f"({creation_hint})", width=80))
            print()

        print(
            "Describe your character below.\n"
            "Press Enter on a blank line when done.\n"
        )

        # Collect multi-line input: accumulate lines until a blank line is
        # entered or the player interrupts. A trailing blank line is the
        # conventional multi-line sentinel in terminal UIs.
        lines: list[str] = []
        while True:
            try:
                line = input("  ")
            except (EOFError, KeyboardInterrupt):
                break
            if not line.strip():
                if lines:
                    break   # at least one non-empty line received — done
                # else: leading blank line; keep waiting
            else:
                lines.append(line)

        if not lines:
            logger.warning("Green Room: no character description provided; skipping.")
            print("\n[No character description received — skipping character creation.]\n")
            return

        player_input = "\n".join(lines)
        self._transcript_write(
            f"\n--- Green Room ---\n> [character description]\n{player_input}"
        )

        # Call LLM to extract structured Fate Core data from the free text.
        module_context = json.dumps({
            "game_name": self._game.get("name"),
            "genre":     self._game.get("genre"),
            "tone":      self._game.get("tone"),
            "era":       self._game.get("era"),
            "creation_prompt": creation_prompt,
        }, indent=2)

        # ------------------------------------------------------------------
        # Extraction and confirmation loop.
        #
        # Runs up to MAX_REFINEMENTS + 1 times. After each extraction the
        # player sees the LLM's interpretation and is asked whether it looks
        # right. If not, they provide a correction which is appended to the
        # running input and the extraction re-runs from scratch. On the final
        # attempt (or when the player accepts), the loop exits.
        #
        # DB writes happen inside the loop; clear_character_aspects() at the
        # top of each iteration keeps the table consistent with the latest
        # extraction result regardless of how many passes were needed.
        # ------------------------------------------------------------------
        MAX_REFINEMENTS = 2     # player may correct up to twice (3 passes total)

        # These are declared here so the transcript write after the loop has
        # access to the final values even if the loop exits early.
        high_concept: str = ""
        trouble:      str = ""
        aspects:      list[str] = []
        skills:       list[str] = []

        for attempt in range(MAX_REFINEMENTS + 1):

            print("\n[Interpreting your character...]\n")

            try:
                prompt = GREEN_ROOM_EXTRACTION_PROMPT.format(
                    module_context=module_context,
                    player_input=player_input,
                )
                logger.debug("Green Room extraction prompt (attempt %d):\n%s",
                             attempt + 1, prompt)
                extracted = self.llm.call_json(prompt)
            except (LLMError, LLMJSONError) as exc:
                logger.error("Green Room extraction failed: %s", exc)
                print("[Character extraction failed. Proceeding without character aspects.]\n")
                return

            # Parse and validate extracted fields.
            high_concept = (extracted.get("high_concept") or "").strip()
            trouble      = (extracted.get("trouble")      or "").strip()
            aspects_raw  = extracted.get("aspects") or []
            aspects      = [a.strip() for a in aspects_raw
                            if isinstance(a, str) and a.strip()][:3]
            description  = (extracted.get("description")  or "").strip()
            skills_raw   = extracted.get("skills") or []
            skills       = [s.strip() for s in skills_raw
                            if isinstance(s, str) and s.strip()]
            confirmation = (extracted.get("confirmation_text") or "").strip()

            # ------------------------------------------------------------------
            # Follow-up prompts for missing required Fate Core fields.
            # High Concept and Trouble are required; additional aspects (0-3)
            # are always optional. If either is missing after the main
            # extraction pass, ask a short targeted follow-up question and
            # re-run against the combined input. Only the missing fields are
            # updated from the second pass; everything else is preserved.
            # ------------------------------------------------------------------
            followup_parts: list[str] = []

            if not high_concept:
                print("What are a few words that describe your character?")
                hc_answer = input("> ").strip()
                if hc_answer:
                    followup_parts.append(
                        "Q: How would you describe your character in a short phrase?\n"
                        f"A: {hc_answer}"
                    )

            if not trouble:
                print("What is one thing your character struggles against or tries to avoid?")
                tr_answer = input("> ").strip()
                if tr_answer:
                    followup_parts.append(
                        "Q: What is one thing your character struggles against or avoids?\n"
                        f"A: {tr_answer}"
                    )

            if followup_parts:
                combined_input = (
                    player_input
                    + "\n\nAdditional details provided by the player:\n"
                    + "\n".join(followup_parts)
                )
                try:
                    prompt2 = GREEN_ROOM_EXTRACTION_PROMPT.format(
                        module_context=module_context,
                        player_input=combined_input,
                    )
                    extracted2 = self.llm.call_json(prompt2)
                except (LLMError, LLMJSONError) as exc:
                    logger.warning("Green Room follow-up extraction failed: %s", exc)
                    extracted2 = {}

                # Fill in only what was missing; preserve all first-pass results.
                if not high_concept:
                    high_concept = (extracted2.get("high_concept") or "").strip()
                if not trouble:
                    trouble = (extracted2.get("trouble") or "").strip()
                # Merge additional aspects (deduplicate, cap at 3).
                new_aspects = [
                    a.strip() for a in (extracted2.get("aspects") or [])
                    if isinstance(a, str) and a.strip()
                ]
                seen = set(aspects)
                for a in new_aspects:
                    if a not in seen and len(aspects) < 3:
                        aspects.append(a)
                        seen.add(a)
                # Use follow-up description if first pass produced nothing.
                if not description:
                    description = (extracted2.get("description") or "").strip()
                # Merge skills (preserve order, deduplicate).
                new_skills = [
                    s.strip() for s in (extracted2.get("skills") or [])
                    if isinstance(s, str) and s.strip()
                ]
                skills = list(dict.fromkeys(skills + new_skills))
                # Use follow-up confirmation text if the first pass had none.
                if not confirmation and extracted2.get("confirmation_text"):
                    confirmation = extracted2["confirmation_text"].strip()

            logger.info(
                "Green Room extracted (attempt %d): char=%d high_concept=%r "
                "trouble=%r aspects=%d skills=%d",
                attempt + 1, self._player["id"],
                high_concept, trouble, len(aspects), len(skills),
            )

            # Write to DB. clear_character_aspects() first so each iteration
            # is a clean slate — the confirmed result is always what's stored.
            player_id = self._player["id"]
            self.db.clear_character_aspects(player_id)

            if high_concept:
                self.db.create_character_aspect(player_id, high_concept, "high_concept")
            if trouble:
                self.db.create_character_aspect(player_id, trouble, "trouble")
            for i, aspect_text in enumerate(aspects):
                self.db.create_character_aspect(player_id, aspect_text, "aspect",
                                                sort_order=i)

            if description:
                self.db.update_player_character(
                    character_id=player_id,
                    description=description,
                )

            # Write skills as character_skill rows (INSERT OR IGNORE preserves
            # any skill levels seeded by the module author).
            for skill_name in skills:
                self.db._execute(  # noqa: SLF001 — direct access justified here
                    """INSERT OR IGNORE INTO character_skill
                           (character_id, skill_name, skill_level)
                       VALUES (?, ?, 0.5)""",
                    (player_id, skill_name),
                )

            # Display LLM confirmation text and structured summary.
            if confirmation:
                print(textwrap.fill(confirmation, width=80))
                print()

            if high_concept:
                print(f"  High Concept: {high_concept}")
            if trouble:
                print(f"  Trouble:      {trouble}")
            for aspect_text in aspects:
                print(f"  Aspect:       {aspect_text}")
            if skills:
                print(f"  Skills noted: {', '.join(skills)}")
            print()

            # ------------------------------------------------------------------
            # Confirmation gate.
            # Ask whether the interpretation looks right. "n" collects a
            # correction that is appended to player_input before the next pass.
            # On the final attempt we skip the question and proceed regardless.
            # ------------------------------------------------------------------
            if attempt < MAX_REFINEMENTS:
                try:
                    answer = input("Does this look right? (y/n) ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    break   # treat interruption as acceptance
                if answer.startswith("n"):
                    try:
                        correction = input("What would you like to change? ").strip()
                    except (EOFError, KeyboardInterrupt):
                        break
                    if correction:
                        player_input = (
                            player_input
                            + "\n\nPlayer correction: "
                            + correction
                        )
                        self._transcript_write(f"> [correction]\n{correction}")
                    continue   # re-run extraction with updated input
            break   # accepted (or final attempt exhausted)

        print("\n--- Beginning the game ---\n")

        # Write structured summary to transcript.
        self._transcript_write(
            f"High Concept: {high_concept}\n"
            f"Trouble: {trouble}\n"
            + "".join(f"Aspect: {a}\n" for a in aspects)
            + (f"Skills: {', '.join(skills)}\n" if skills else "")
            + "---"
        )

    # =========================================================================
    # Public web API
    #
    # These methods expose the engine's turn loop and Green Room flow as a
    # request/response interface suitable for a web frontend. They do not
    # use input() or print() — all I/O is handled by the caller.
    #
    # The existing run() method and all private methods are unchanged; CLI
    # use continues to work exactly as before.
    # =========================================================================

    def needs_green_room(self) -> bool:
        """
        Return True if this session requires the Green Room character creation
        stage and it has not yet been completed.

        The stage is required when:
          - The game's player_definition_mode is 'green_room', AND
          - The player character has no existing character_aspect records.

        The second condition makes this idempotent: resuming a session after
        character creation was completed in a prior run returns False.
        """
        if self._game.get("player_definition_mode") != "green_room":
            return False
        existing = self.db.get_character_aspects(self._player["id"])
        return not existing

    def get_green_room_config(self) -> dict:
        """
        Return the module's character creation configuration for display in
        the web UI registration / session-start form.

        Returns a dict with keys:
            game_name       (str)  — display name of the module
            creation_prompt (str)  — module author's framing shown to the player
            creation_hint   (str)  — optional Fate Core explanation (may be empty)
        """
        flags = self._game.get("module_flags") or {}
        return {
            "game_name":       self._game.get("name", ""),
            "creation_prompt": (flags.get("character_creation_prompt") or "").strip(),
            "creation_hint":   (flags.get("character_creation_hint")   or "").strip(),
        }

    def extract_green_room_character(self, player_input: str) -> dict:
        """
        Extract structured Fate Core character data from the player's
        free-text description and write it to the database.

        This is the engine half of the Green Room stage. The caller is
        responsible for collecting the player's input and displaying the
        returned data for confirmation. If the player wants to correct
        something, the caller collects the correction and calls this method
        again with updated text; the clear-and-rewrite pattern ensures the
        DB always reflects the latest accepted extraction.

        DB writes (cleared and rewritten on each call):
            - character_aspect rows (high_concept, trouble, up to 3 aspects)
            - character.description
            - character_skill rows (INSERT OR IGNORE)

        Args:
            player_input: The player's free-text character description,
                          possibly with appended corrections from prior rounds.

        Returns:
            A dict with keys:
                high_concept      (str)        — extracted High Concept
                trouble           (str)        — extracted Trouble
                aspects           (list[str])  — up to 3 additional Aspects
                skills            (list[str])  — mentioned skills
                confirmation_text (str)        — LLM-written player-facing summary
                missing_fields    (list[str])  — names of required fields that
                                                 could not be extracted; caller
                                                 should prompt the player to
                                                 supply them before confirming

        Raises:
            LLMError:     On non-retryable LLM failure.
            LLMJSONError: If the LLM returns malformed JSON after all retries.
        """
        module_context = json.dumps({
            "game_name": self._game.get("name"),
            "genre":     self._game.get("genre"),
            "tone":      self._game.get("tone"),
            "era":       self._game.get("era"),
            "creation_prompt": self.get_green_room_config()["creation_prompt"],
        }, indent=2)

        prompt = GREEN_ROOM_EXTRACTION_PROMPT.format(
            module_context=module_context,
            player_input=player_input,
        )
        logger.debug("Green Room web extraction prompt:\n%s", prompt)

        extracted = self.llm.call_json(prompt)

        high_concept = (extracted.get("high_concept") or "").strip()
        trouble      = (extracted.get("trouble")      or "").strip()
        aspects_raw  = extracted.get("aspects") or []
        aspects      = [a.strip() for a in aspects_raw
                        if isinstance(a, str) and a.strip()][:3]
        description  = (extracted.get("description")  or "").strip()
        skills_raw   = extracted.get("skills") or []
        skills       = [s.strip() for s in skills_raw
                        if isinstance(s, str) and s.strip()]
        confirmation = (extracted.get("confirmation_text") or "").strip()

        # Identify required fields that are still missing so the web layer
        # can ask the player to supply them before accepting the result.
        missing: list[str] = []
        if not high_concept:
            missing.append("high_concept")
        if not trouble:
            missing.append("trouble")

        # Write to DB (clear first so repeated calls are idempotent).
        player_id = self._player["id"]
        self.db.clear_character_aspects(player_id)

        if high_concept:
            self.db.create_character_aspect(player_id, high_concept, "high_concept")
        if trouble:
            self.db.create_character_aspect(player_id, trouble, "trouble")
        for i, aspect_text in enumerate(aspects):
            self.db.create_character_aspect(player_id, aspect_text, "aspect",
                                            sort_order=i)

        if description:
            self.db.update_player_character(
                character_id=player_id,
                description=description,
            )

        for skill_name in skills:
            self.db._execute(  # noqa: SLF001 — direct access justified here
                """INSERT OR IGNORE INTO character_skill
                       (character_id, skill_name, skill_level)
                   VALUES (?, ?, 0.5)""",
                (player_id, skill_name),
            )

        logger.info(
            "Green Room web extraction: char=%d high_concept=%r trouble=%r "
            "aspects=%d skills=%d missing=%r",
            player_id, high_concept, trouble, len(aspects), len(skills), missing,
        )

        return {
            "high_concept":      high_concept,
            "trouble":           trouble,
            "aspects":           aspects,
            "skills":            skills,
            "confirmation_text": confirmation,
            "missing_fields":    missing,
        }

    def confirm_green_room(self) -> None:
        """
        Finalise the Green Room stage.

        Call this once the player has confirmed their character data. It
        refreshes the cached player record so that get_opening_scene() and
        subsequent step() calls see the description and aspects just written
        by extract_green_room_character().
        """
        self._player = self.db.get_player_character(self.game_id)
        logger.info(
            "Green Room confirmed: char=%d description_set=%s",
            self._player["id"],
            bool(self._player.get("description")),
        )

    def get_opening_scene(self) -> str:
        """
        Render and return the opening scene prose.

        Call this once per session, after Green Room (if required) has been
        completed. No state is changed. Returns a fallback string if the LLM
        call fails rather than raising.

        Returns:
            Opening prose string for display to the player.
        """
        try:
            return self._render_opening_scene()
        except (LLMError, LLMJSONError) as exc:
            logger.warning(
                "Opening scene render failed (%s); using fallback.", exc
            )
            return f"You are {self._player['name']}."

    def step(self, player_input: str) -> str | None:
        """
        Process one full turn for the web interface and return the prose output.

        Runs the same per-turn sequence as the CLI run() loop:
            1. Refreshes the player record
            2. Checks involuntary events
            3. Clears expired NPC activities
            4. Moves wandering NPCs (and flags any who arrive in the player's
               own location — see NPC ARRIVAL AWARENESS in
               _check_npc_wandering())
            5. Runs the three-pass pipeline (Pass 1 → Pass 2 → DB write → Pass 3)

        Args:
            player_input: The player's raw text input for this turn.
                          Strip whitespace before passing.

        Returns:
            The rendered prose string to display to the player, or None if
            the player typed an exit command ('quit', 'exit', 'q').

        Raises:
            LLMError:     On non-retryable LLM failure (caller should display
                          an error message and allow the player to retry).
            LLMJSONError: If the LLM returns malformed JSON after all retries.
        """
        # Refresh the player record so location and state are always current.
        self._player = self.db.get_player_character(self.game_id)

        # Per-turn pre-pass checks (same order as CLI run()).
        involuntary_fired = self._check_involuntary_events()
        self._check_activity_expiry()
        newly_arrived_npcs = self._check_npc_wandering()

        # Exit commands signal the caller to end the session.
        if player_input.strip().lower() in ("quit", "exit", "q"):
            logger.info("Player exited via command: %r", player_input.strip())
            return None

        return self._process_turn(player_input.strip(), involuntary_fired, newly_arrived_npcs)

    # -------------------------------------------------------------------------
    # Turn processing
    # -------------------------------------------------------------------------

    def _process_turn(
        self,
        raw_input: str,
        involuntary_fired: list[dict],
        newly_arrived_npcs: list[dict] | None = None,
    ) -> str:
        """
        Run all three LLM passes for one turn and return the prose output.

        Writes all adjudication results to the database before Pass 3 runs,
        so the database always reflects the current world state.

        Args:
            raw_input:          The player's raw text input for this turn.
            involuntary_fired:  Involuntary event state dicts that fired this turn.
            newly_arrived_npcs: NPCs (from _check_npc_wandering()) who wandered
                                 into the player's current location this turn,
                                 before this turn's action was processed. Passed
                                 through to Pass 2 as newly_arrived_npcs_this_turn
                                 so it can react to the arrival. Defaults to None
                                 (treated as empty) for callers that don't track it.

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
                    reason = (
                        route.get("no_path_reason")
                        or "There's no way to get there from here."
                    )
                    logger.info("Move blocked: %s", reason)
                    # Render through Pass 3 so the player gets module-appropriate
                    # prose rather than a raw engine constraint string.
                    return self._render_move_blocked(reason)

        # Pass 2 — Outcome Adjudication
        instance_id = self._instance["id"] if self._instance else None
        pass2_packet = build_pass2_packet(
            self.db, self.game_id, action_record,
            involuntary_events=involuntary_fired,
            newly_arrived_npcs=newly_arrived_npcs,
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

        # Write all adjudication results to the database. Capture the
        # action_log_id so we can write Pass 3 prose back after it is rendered.
        action_log_id = self._apply_outcome(action_record, outcome)

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
        self._check_pass3_length(prose, outcome, action_log_id=action_log_id)

        # Write prose back to the action_log row so future turns can fetch it
        # for anti-repetition context via build_pass3_packet() → get_recent_prose().
        self.db.update_action_log_prose(action_log_id, prose)

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
    # Timed activity expiry (v8+)
    # -------------------------------------------------------------------------

    def _check_activity_expiry(self) -> None:
        """
        Mechanically clear current_activity for any NPC whose timed activity
        has expired and is eligible for auto-clearing.

        Called once per turn, before NPC wandering is checked. Activities are
        cleared mechanically only when all of the following hold:
            - current_activity IS NOT NULL
            - activity_estimated_duration IS NOT NULL (not open-ended)
            - activity_renewable = 0 (not set to persist past expiry)
            - activity_duration_confidence >= ACTIVITY_AUTO_CLEAR_CONFIDENCE
            - activity_started_at + activity_estimated_duration <= current_time

        Activities that do not meet all criteria are left for Pass 2 to clear
        explicitly via activity_updates in the outcome JSON.

        This is intentionally engine-side only — the LLM does not need to
        poll for expiry. Pass 2 can always override a cleared activity by
        setting a new one in activity_updates.
        """
        current_time = self._current_game_time()
        expired = self.db.get_characters_with_expired_activities(
            game_id=self.game_id,
            current_time_minutes=current_time,
            confidence_threshold=config.ACTIVITY_AUTO_CLEAR_CONFIDENCE,
        )
        for npc in expired:
            self.db.clear_character_activity(npc["id"])
            logger.info(
                "Activity auto-expired: char=%d (%s) activity=%r "
                "started_at=%d duration=%d current_time=%d",
                npc["id"],
                npc["name"],
                (npc.get("current_activity") or "")[:60],
                npc.get("activity_started_at", 0),
                npc.get("activity_estimated_duration", 0),
                current_time,
            )

    # -------------------------------------------------------------------------
    # NPC autonomous wandering
    # -------------------------------------------------------------------------

    def _check_npc_wandering(self) -> list[dict]:
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

        This movement is otherwise silent from the player's perspective —
        nothing is written to the action log — unless they observe the NPC in
        its new position. NPC ARRIVAL AWARENESS (v16+) is the one exception:
        any NPC who wanders into the player character's own current location
        this pass is collected and returned so the Pass 2 context packet can
        surface it as newly_arrived_npcs_this_turn, letting Pass 2 decide
        whether the arrival is narratively salient. This addresses the
        "Spook teleporting" playtest observation (2026-07-06): NPCs were
        wandering into the player's room with no way for the player, or
        Pass 2, to ever learn it had just happened.

        Returns:
            A list of {id, name} dicts, one per NPC who wandered into the
            player character's current location this pass. Empty list if
            none did (the common case).
        """
        import random as _random  # module-level import would shadow stdlib elsewhere

        newly_arrived: list[dict] = []
        player_location_id = (
            self._player["current_location_id"] if self._player else None
        )

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

            # Suppression 3: active non-expired current_activity (v8+).
            # An NPC who is mid-activity — dancing, greeting guests, playing
            # cards — does not wander. We suppress the roll when:
            #   - current_activity is set, AND
            #   - the activity has not yet mechanically expired
            #     (i.e. open-ended, OR within its estimated duration, OR
            #      renewable past its estimated end time).
            # This is the fix for the John Lucas incident: activity persists
            # through commitment-fulfillment events, unlike pending_intent.
            if npc.get("current_activity"):
                started    = npc.get("activity_started_at")
                duration   = npc.get("activity_estimated_duration")
                confidence = npc.get("activity_duration_confidence")
                renewable  = npc.get("activity_renewable", 0)
                current_time = self._current_game_time()

                # Determine whether the activity has expired.
                # An activity is NOT expired if any of these hold:
                #   a) duration is None (open-ended — never expires by time)
                #   b) renewable=1 (persists past estimated end)
                #   c) confidence < threshold (low-confidence — only Pass 2 clears)
                #   d) start time + duration > current_time (still within window)
                activity_expired = (
                    duration is not None
                    and not renewable
                    and confidence is not None
                    and confidence >= config.ACTIVITY_AUTO_CLEAR_CONFIDENCE
                    and started is not None
                    and (started + duration) <= current_time
                )
                if not activity_expired:
                    logger.debug(
                        "NPC wander suppressed (current_activity=%r): %s (id=%d)",
                        npc["current_activity"][:40],
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

            # NPC ARRIVAL AWARENESS (v16+): flag arrivals into the player's
            # own location so Pass 2 has a chance to react to them this turn,
            # instead of the player only finding out via a later, unrelated
            # action.
            if player_location_id is not None and destination == player_location_id:
                newly_arrived.append({"id": npc["id"], "name": npc["name"]})
                logger.info(
                    "NPC arrival: %s (id=%d) wandered into player's location (loc %d)",
                    npc["name"], npc["id"], destination,
                )

        return newly_arrived

    # -------------------------------------------------------------------------
    # Outcome application (DB writes)
    # -------------------------------------------------------------------------

    def _apply_outcome(self, action_record: dict, outcome: dict) -> int:
        """
        Write all adjudication results from the outcome dict to the database.

        This method is the only place where the engine writes game state. It
        processes each field of the outcome in a defined order and logs any
        unexpected fields for debugging.

        Returns:
            The action_log id for this turn, so the caller can write the Pass 3
            prose back via update_action_log_prose() once it is available.

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
        # Item changes (field-level updates to existing items)
        # ------------------------------------------------------------------
        # Each entry: {item_id, field, new_value}. Only the fields below are
        # permitted — prevents the LLM from making unintended schema changes.
        # To move an item, use item_instantiations (new item) or item_transfers
        # (move existing item). Do not use item_changes to alter FK columns —
        # the CHECK constraint requires all three to be updated atomically.
        _ALLOWED_ITEM_FIELDS = {"is_confirmed", "description", "is_visible", "quality"}
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
                logger.debug(
                    "item_change applied: item=%d %s=%r",
                    int(change["item_id"]), field, change["new_value"],
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping malformed item_change %r: %s", change, exc)

        # ------------------------------------------------------------------
        # Item instantiations (v9+)
        # ------------------------------------------------------------------
        # Pass 2 emits these when the player claims a new item (mid-play or
        # during self-definition) or when an NPC gives the player something.
        # Each entry creates a new item record and optionally places it in a
        # character's inventory or at a location.
        for entry in outcome.get("item_instantiations") or []:
            try:
                name                 = str(entry["name"])
                description          = entry.get("description")
                properties           = entry.get("properties") or {}
                is_confirmed         = int(entry.get("is_confirmed", 1))
                char_id              = entry.get("character_id")
                loc_id               = entry.get("location_id")
                container_item_id    = entry.get("container_item_id")
                slot                 = entry.get("slot", "carried")
                location_description = entry.get("location_description")

                # Guard: don't create a duplicate if the item is already in
                # the character's inventory by the same name (v10: query char_id directly).
                if char_id is not None:
                    existing = self.db._row(  # noqa: SLF001
                        "SELECT id FROM item WHERE char_id = ? AND name = ?",
                        (int(char_id), name),
                    )
                    if existing:
                        logger.debug(
                            "item_instantiation skipped: %r already in char=%d inventory",
                            name, int(char_id),
                        )
                        continue

                # Determine exactly one location FK for the INSERT.
                # The schema CHECK constraint requires exactly one non-null.
                # Fallback: place at player's current location if nothing specified.
                if char_id is not None:
                    new_item_id = self.db.create_item(
                        game_id=self.game_id,
                        name=name,
                        description=description,
                        properties=properties if isinstance(properties, dict) else {},
                        is_confirmed=is_confirmed,
                        char_id=int(char_id),
                        slot=str(slot),
                        location_description=location_description,
                    )
                    logger.info(
                        "Item instantiated: %r (id=%d) → char=%d slot=%s confirmed=%d",
                        name, new_item_id, int(char_id), slot, is_confirmed,
                    )
                elif container_item_id is not None:
                    new_item_id = self.db.create_item(
                        game_id=self.game_id,
                        name=name,
                        description=description,
                        properties=properties if isinstance(properties, dict) else {},
                        is_confirmed=is_confirmed,
                        item_id=int(container_item_id),
                        location_description=location_description,
                    )
                    logger.info(
                        "Item instantiated: %r (id=%d) → container=%d confirmed=%d",
                        name, new_item_id, int(container_item_id), is_confirmed,
                    )
                elif loc_id is not None:
                    new_item_id = self.db.create_item(
                        game_id=self.game_id,
                        name=name,
                        description=description,
                        properties=properties if isinstance(properties, dict) else {},
                        is_confirmed=is_confirmed,
                        loc_id=int(loc_id),
                        location_description=location_description,
                    )
                    logger.info(
                        "Item instantiated: %r (id=%d) → location=%d confirmed=%d",
                        name, new_item_id, int(loc_id), is_confirmed,
                    )
                else:
                    # No placement specified — default to player's current location.
                    player = self.db.get_player_character(self.game_id)
                    fallback_loc = player["current_location_id"] if player else None
                    if fallback_loc is None:
                        logger.warning(
                            "item_instantiation %r skipped: no placement and player "
                            "has no current_location_id",
                            name,
                        )
                        continue
                    new_item_id = self.db.create_item(
                        game_id=self.game_id,
                        name=name,
                        description=description,
                        properties=properties if isinstance(properties, dict) else {},
                        is_confirmed=is_confirmed,
                        loc_id=fallback_loc,
                        location_description=location_description,
                    )
                    logger.info(
                        "Item instantiated: %r (id=%d) → player location=%d (fallback) confirmed=%d",
                        name, new_item_id, fallback_loc, is_confirmed,
                    )

            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed item_instantiation %r: %s", entry, exc
                )

        # ------------------------------------------------------------------
        # Item transfers (v10+): move an existing item to a new location
        # ------------------------------------------------------------------
        # Pass 2 emits these when the player picks up, drops, or gives an item,
        # or when an NPC moves an item. Each entry must include:
        #   item_id         — id of the item to move
        #   location_description — natural-language description of where it now sits
        # Plus exactly one destination:
        #   to_char_id      — move to a character's inventory (also requires slot)
        #   to_loc_id       — place at a location
        #   to_item_id      — put inside a container item
        # When to_loc_id is set, is_confirmed is set to 1 (player placed deliberately).
        for transfer in outcome.get("item_transfers") or []:
            try:
                t_item_id            = int(transfer["item_id"])
                location_description = transfer.get("location_description")
                to_char_id           = transfer.get("to_char_id")
                to_loc_id            = transfer.get("to_loc_id")
                to_item_id           = transfer.get("to_item_id")
                slot                 = transfer.get("slot", "carried")

                destinations = sum(
                    1 for x in (to_char_id, to_loc_id, to_item_id) if x is not None
                )
                if destinations != 1:
                    logger.warning(
                        "Skipping item_transfer for item=%d: expected exactly one "
                        "destination, got %d (to_char=%s to_loc=%s to_item=%s)",
                        t_item_id, destinations, to_char_id, to_loc_id, to_item_id,
                    )
                    continue

                if to_char_id is not None:
                    self.db.transfer_item_to_character(
                        item_id=t_item_id,
                        character_id=int(to_char_id),
                        slot=str(slot),
                        location_description=location_description,
                    )
                    logger.info(
                        "Item %d transferred to char=%d slot=%s",
                        t_item_id, int(to_char_id), slot,
                    )
                elif to_loc_id is not None:
                    self.db.transfer_item_to_location(
                        item_id=t_item_id,
                        location_id=int(to_loc_id),
                        location_description=location_description,
                        is_confirmed=1,  # player placed deliberately
                    )
                    logger.info(
                        "Item %d transferred to location=%d (confirmed)",
                        t_item_id, int(to_loc_id),
                    )
                elif to_item_id is not None:
                    self.db.transfer_item_to_container(
                        item_id=t_item_id,
                        container_item_id=int(to_item_id),
                        location_description=location_description,
                    )
                    logger.info(
                        "Item %d transferred into container item=%d",
                        t_item_id, int(to_item_id),
                    )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed item_transfer %r: %s", transfer, exc
                )

        # ------------------------------------------------------------------
        # Player character update (v9+)
        # ------------------------------------------------------------------
        # Pass 2 emits this when the player describes themselves (self-definition
        # at game start or mid-play appearance correction). Updates description,
        # gender, and/or pronouns on the player character record. The engine
        # applies whatever Pass 2 returns — including the default mirror text
        # when the player gave no self-description.
        pcu = outcome.get("player_character_update")
        if pcu and self._player:
            try:
                self.db.update_player_character(
                    character_id=self._player["id"],
                    description=pcu.get("description"),
                    gender=pcu.get("gender"),
                    pronouns=pcu.get("pronouns"),
                )
                logger.info(
                    "Player character updated: char=%d description=%.60s",
                    self._player["id"],
                    (pcu.get("description") or "")[:60],
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed player_character_update %r: %s", pcu, exc
                )

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
        # Activity updates (v8+)
        # ------------------------------------------------------------------
        # Pass 2 issues these when an NPC begins a new activity, changes what
        # they are doing, or explicitly ends their current activity. Each entry
        # may set or clear a character's current_activity record.
        #
        # When setting an activity, Pass 2 supplies activity text, duration,
        # confidence, and renewable flag. The engine records activity_started_at
        # from the current game clock — Pass 2 does not set the start time.
        #
        # To clear an activity, Pass 2 sets activity to null (or None). This
        # handles explicit narrative endings (dance concludes, card game breaks
        # up) as distinct from mechanical auto-expiry in _check_activity_expiry().
        current_time = self._current_game_time()
        for update in outcome.get("activity_updates") or []:
            try:
                char_id  = int(update["character_id"])
                activity = update.get("activity")  # str or None

                if activity is None:
                    # Explicit clear — the activity has ended narratively.
                    self.db.clear_character_activity(char_id)
                    logger.info("activity cleared (Pass 2): char=%d", char_id)
                else:
                    duration   = update.get("duration_minutes")
                    confidence = update.get("confidence")
                    renewable  = int(update.get("renewable", 0))

                    # Validate confidence range if supplied.
                    if confidence is not None:
                        confidence = max(0.0, min(1.0, float(confidence)))
                    # Validate renewable flag.
                    if renewable not in (0, 1):
                        logger.warning(
                            "activity_update for char=%d: renewable=%r not 0/1, "
                            "defaulting to 0", char_id, renewable,
                        )
                        renewable = 0

                    self.db.set_character_activity(
                        character_id=char_id,
                        activity=str(activity),
                        started_at=current_time,
                        duration_minutes=int(duration) if duration is not None else None,
                        confidence=confidence,
                        renewable=renewable,
                    )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed activity_update %r: %s", update, exc
                )

        # ------------------------------------------------------------------
        # Lazy NPC creation (session 14+)
        # ------------------------------------------------------------------
        # Pass 2 emits new_characters when the player references a plausible
        # character not yet in the cast (e.g. "Maria Lucas" — Charlotte's
        # sister, whose existence is implied by Charlotte's description).
        # The engine inserts the character record so they become canonical
        # from the next turn onward.
        for entry in outcome.get("new_characters") or []:
            try:
                name = str(entry["name"])

                # Guard: don't create duplicates. Check by name + game_id.
                existing = self.db._row(  # noqa: SLF001
                    "SELECT id FROM character WHERE game_id=? AND name=?",
                    (self.game_id, name),
                )
                if existing:
                    logger.debug(
                        "Lazy NPC %r already exists (id=%d); skipping creation",
                        name, existing["id"],
                    )
                    continue

                # Parse optional OCEAN traits if supplied.
                def _ocean(key: str) -> float | None:
                    v = entry.get(key)
                    if v is None:
                        return None
                    return max(0.0, min(1.0, float(v)))

                # Pronouns from Pass 2 may come as a list; store as JSON string.
                import json as _json
                pronouns_raw = entry.get("pronouns")
                pronouns_str = (
                    _json.dumps(pronouns_raw)
                    if isinstance(pronouns_raw, list)
                    else pronouns_raw  # already a string or None
                )

                new_char = self.db.create_character(
                    game_id=self.game_id,
                    name=name,
                    description=entry.get("description"),
                    emotional_state=entry.get("emotional_state", "neutral"),
                    current_location_id=entry.get("current_location_id"),
                    gender=entry.get("gender"),
                    pronouns=pronouns_str,
                    role="npc_background",
                    species=entry.get("species", "human"),
                    ocean_openness=_ocean("ocean_openness"),
                    ocean_conscientiousness=_ocean("ocean_conscientiousness"),
                    ocean_extraversion=_ocean("ocean_extraversion"),
                    ocean_agreeableness=_ocean("ocean_agreeableness"),
                    ocean_neuroticism=_ocean("ocean_neuroticism"),
                )
                logger.info(
                    "Lazy NPC instantiated: %r (id=%d) at location=%s",
                    name, new_char["id"], entry.get("current_location_id"),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning(
                    "Skipping malformed new_character entry %r: %s", entry, exc
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
        action_log_id = self.db.write_action_log(
            game_id=self.game_id,
            character_id=self._player["id"] if self._player else 0,
            action_json=action_record,
            narrative_beat=outcome.get("narrative_beat"),
        )

        # ------------------------------------------------------------------
        # Interaction history (increment for each NPC present at the location)
        #
        # Regression fix (2026-07-07): this block was unreachable — a
        # `return action_log_id` had been added directly above it (session 35,
        # when _apply_outcome() was changed to return the action_log_id for
        # Pass 3's prose-writeback), and nothing after a return executes.
        # npc_player_history has not actually been incremented during play
        # since that session, though it fails silently rather than erroring.
        # Restoring this as-is for now (player-to-NPC-at-location only, still
        # a rolling summary rather than a precise fact ledger); tracked as an
        # interim step toward broader personal-history tracking (NPC-to-NPC
        # pairs, object modifications) via the semantic action-log-retrieval
        # feature already in docs/future_features.md (#23).
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

        return action_log_id

        logger.info(
            "Outcome applied: type=%s attitudes=%d states=%d moves=%d "
            "item_changes=%d item_instantiations=%d item_transfers=%d details=%d "
            "faction_reps=%d pending_intents=%d activities=%d player_update=%s",
            outcome.get("outcome_type"),
            len(outcome.get("attitude_deltas") or []),
            len(outcome.get("internal_state_deltas") or []),
            len(loc_changes),
            len(outcome.get("item_changes") or []),
            len(outcome.get("item_instantiations") or []),
            len(outcome.get("item_transfers") or []),
            len(outcome.get("new_location_details") or []),
            len(outcome.get("faction_reputation_changes") or []),
            len(outcome.get("pending_intent_updates") or []),
            len(outcome.get("activity_updates") or []),
            "yes" if outcome.get("player_character_update") else "no",
        )


# =============================================================================
# Entry point helper
# =============================================================================

def main() -> None:
    """
    Command-line entry point. Reads configuration from environment variables
    and optional CLI arguments, validates it, opens the database, and starts
    the engine.

    Typical invocation:
        DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python -m engine

    With transcript output:
        python -m engine                        # auto-saves to transcripts/<name>_<timestamp>.txt
        python -m engine --transcript           # same (explicit bare flag)
        python -m engine --transcript path.txt  # saves to specified path
        DAVE_TRANSCRIPT_PATH=path.txt python -m engine  # same via env var
        DAVE_NO_TRANSCRIPT=1 python -m engine   # disable transcript entirely

    For debug-level logging (written to log file, not terminal):
        DAVE_LOG_LEVEL=DEBUG DAVE_DB_PATH=... python -m engine
    """
    # ------------------------------------------------------------------
    # CLI argument parsing
    # ------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="DAVE RPG Engine — text-based RPG with LLM adjudication.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--transcript",
        metavar="PATH",
        nargs="?",           # 0 or 1 arguments: bare --transcript uses the auto-path
        const="",            # sentinel: --transcript with no PATH → auto-generate
        default=None,        # --transcript absent → fall through to env var / auto
        help=(
            "Save a transcript of this session (player inputs + prose). "
            "If PATH is omitted, a timestamped file is auto-saved to transcripts/. "
            "Overrides DAVE_TRANSCRIPT_PATH. Use DAVE_NO_TRANSCRIPT=1 to disable."
        ),
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Logging setup
    #
    # Engine logs go to a timestamped file in logs/ at the configured level.
    # The stderr handler is set to WARNING so only genuine problems appear
    # on the terminal during play — no httpx INFO chatter, no turn summaries
    # breaking prose immersion.
    # ------------------------------------------------------------------
    log_level_name = os.environ.get("DAVE_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Root logger accepts everything; handlers filter independently.
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    log_fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

    # File handler: full engine log at configured level.
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_stem = Path(config.DB_PATH).stem  # e.g. "meryton" from "meryton.db"
    log_path = log_dir / f"{db_stem}_{timestamp}.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_fmt)
    root_logger.addHandler(file_handler)

    # Stderr handler: WARNING and above only, so terminal stays clean during play.
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(log_fmt)
    root_logger.addHandler(stderr_handler)

    # Suppress httpx INFO/DEBUG (Anthropic SDK uses httpx internally; its
    # connection and request logs would otherwise appear on every LLM call).
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)

    logger.info("Log file: %s  (level=%s)", log_path, log_level_name)

    # ------------------------------------------------------------------
    # Transcript path resolution
    #
    # Priority: --transcript CLI arg > DAVE_TRANSCRIPT_PATH env var >
    # auto-generated timestamped file in transcripts/ > disabled if
    # DAVE_NO_TRANSCRIPT=1.
    # ------------------------------------------------------------------
    no_transcript = os.environ.get("DAVE_NO_TRANSCRIPT", "").strip() not in ("", "0")
    if no_transcript:
        transcript_path = None
    elif args.transcript:
        # --transcript PATH: explicit path supplied (non-empty string)
        transcript_path = args.transcript
    elif os.environ.get("DAVE_TRANSCRIPT_PATH"):
        transcript_path = os.environ["DAVE_TRANSCRIPT_PATH"]
    else:
        # --transcript (bare flag, no path) or no transcript flag at all:
        # auto-generate a timestamped filename in transcripts/.
        transcript_dir = Path("transcripts")
        transcript_dir.mkdir(exist_ok=True)
        transcript_path = str(transcript_dir / f"{db_stem}_{timestamp}.txt")

    if transcript_path:
        logger.info("Transcript: %s", transcript_path)
    else:
        logger.info("Transcript: disabled (DAVE_NO_TRANSCRIPT=1)")

    # ------------------------------------------------------------------
    # Configuration validation
    # ------------------------------------------------------------------
    try:
        config.validate()
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Default game_id to 1; override with DAVE_GAME_ID for multi-game setups.
    game_id = int(os.environ.get("DAVE_GAME_ID", "1"))

    # ------------------------------------------------------------------
    # Engine startup
    # ------------------------------------------------------------------
    try:
        with Database(config.DB_PATH) as db:
            engine = GameEngine(db, game_id=game_id, transcript_path=transcript_path)
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
