-- =============================================================================
-- DAVE RPG Engine — Core Database Schema
-- Current version: 7
--
-- Digitally Adjudicated Virtual Environment
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- The database is the canonical source of truth. The LLM holds nothing
-- permanently. All adjudication results are written here before prose
-- rendering runs.
--
-- This file is the canonical schema for fresh installs. It incorporates all
-- changes through the current schema version. For fresh install, run this
-- file followed by the module seed file — no migration scripts needed.
-- Migration scripts in schema/migrations/ are only needed when upgrading an
-- existing database from an older version.
--
-- Foreign key enforcement must be enabled per connection:
--   PRAGMA foreign_keys = ON;
-- =============================================================================


-- =============================================================================
-- SCHEMA VERSION
-- A single-row table that records the current schema version. Every migration
-- script increments this value and appends a row to preserve the history.
-- =============================================================================

CREATE TABLE schema_version (
    -- Monotonically increasing integer; the current schema version is MAX(version).
    version     INTEGER NOT NULL,
    applied_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    description TEXT    NOT NULL
);

-- Seed the version history with the initial schema.
INSERT INTO schema_version (version, description)
VALUES (1, 'Initial schema: game, location, character, item, action_log');


-- =============================================================================
-- GAME
-- One row per game instance (i.e. per module/playthrough). Stable world
-- parameters that color every LLM call. Loaded once per session.
-- =============================================================================

CREATE TABLE game (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,   -- human-readable name, e.g. 'I Am a Cat'

    -- Genre and tone are passed verbatim to the LLM in every context packet.
    -- They establish the adjudication register for the entire module.
    -- Examples: genre='domestic_comedy', tone='comedic_absurdist'
    genre       TEXT    NOT NULL,
    tone        TEXT    NOT NULL,

    -- Era and technology level provide period-appropriate inference context.
    -- Null is acceptable for contemporary or genre-undefined settings.
    era         TEXT,
    technology_level TEXT,

    -- Magic system description. Null means no magic exists in this world.
    magic_system TEXT,

    -- Default narrative register for prose rendering.
    -- Controls grammatical person: 'first_person', 'second_person',
    -- 'third_person_close', 'third_person_distant', 'atmospheric'
    narrative_register TEXT NOT NULL DEFAULT 'third_person_close',

    -- Speech filter configuration as JSON. Specifies constraints on how
    -- player output and NPC speech are rendered. Used by Pass 3 (prose
    -- rendering) to apply permanent speech rendering rules.
    -- Example for I Am a Cat:
    --   {"player_output": "meow_variants", "npc_input_filter": "feline_comprehension",
    --    "vocabulary_breakthrough": ["treats", "no", "bad", "food"]}
    speech_filter TEXT NOT NULL DEFAULT '{}',

    -- Internal state display configuration as JSON.
    -- Maps state_name -> 'prose' | 'numeric' for each tracked internal state.
    -- 'prose' = rendered as character-voice commentary by the LLM (default for play)
    -- 'numeric' = displayed as a float value (for dev/testing contexts)
    -- Example: {"boredom": "prose", "hunger": "prose"}
    internal_state_display TEXT NOT NULL DEFAULT '{}',

    -- Cultural norms relevant to common action types, passed to Pass 2 when
    -- the action warrants it. JSON object of norm_name -> description.
    cultural_norms TEXT NOT NULL DEFAULT '{}',

    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- =============================================================================
-- LOCATION
-- Rooms, areas, or places in the world. Seeded with skeleton data; details
-- are generated lazily and stored in location_detail.
-- =============================================================================

CREATE TABLE location (
    id          INTEGER PRIMARY KEY,
    game_id     INTEGER NOT NULL REFERENCES game(id),
    name        TEXT    NOT NULL,   -- e.g. 'Master Bedroom', 'Kitchen'

    -- Location type drives plausibility checks during lazy world generation.
    -- The LLM uses this to evaluate whether a queried detail is plausible
    -- before generating and storing it.
    -- Examples: 'bedroom', 'kitchen', 'living_room', 'hallway', 'bathroom'
    location_type TEXT NOT NULL,

    -- Skeleton description: enough to establish the space without committing
    -- to details that have not yet been generated. Details are in location_detail.
    description_skeleton TEXT,

    -- Social setting affects NPC behavior and witness effects during adjudication.
    -- 'private'      = unobserved or nearly so
    -- 'semi_private' = small number of known witnesses
    -- 'public'       = observed by many, reputation consequences apply
    social_setting TEXT NOT NULL DEFAULT 'private'
        CHECK(social_setting IN ('private', 'semi_private', 'public')),

    -- Approximate witness count at a given moment, used in Pass 2 context packets.
    -- Updated dynamically as characters move between locations.
    witness_count INTEGER NOT NULL DEFAULT 0,

    -- Active situation flags as a JSON array of natural language strings.
    -- Transient conditions that affect adjudication.
    -- Example: ["dark", "quiet", "humans_asleep", "3am"]
    situation_flags TEXT NOT NULL DEFAULT '[]',

    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- =============================================================================
-- LOCATION_DETAIL
-- Lazily generated facts about a location. Generated on first query and stored
-- canonically; subsequent queries retrieve rather than regenerate. Details can
-- be invalidated by world events without being deleted, preserving history.
-- =============================================================================

CREATE TABLE location_detail (
    id          INTEGER PRIMARY KEY,
    location_id INTEGER NOT NULL REFERENCES location(id),

    -- The generated detail as a natural language statement.
    -- Example: 'A half-full glass of water sits on the nightstand.'
    detail      TEXT    NOT NULL,

    -- Whether this detail is currently valid.
    -- Set to 0 when a world event satisfies the invalidation_condition.
    is_valid    INTEGER NOT NULL DEFAULT 1 CHECK(is_valid IN (0, 1)),

    -- Natural language description of the event type that would invalidate
    -- this detail. Null means the detail is considered permanent unless
    -- explicitly invalidated by the engine.
    -- Example: 'cat knocks glass off nightstand', 'human wakes and moves around'
    invalidation_condition TEXT,

    -- Timestamp when this detail was marked invalid. Null if still valid.
    invalidated_at TEXT,

    generated_at TEXT NOT NULL DEFAULT (datetime('now'))
);


-- =============================================================================
-- CHARACTER
-- Unified table for all characters: player characters and NPCs alike.
-- Every character carries the same psychological depth. The role field
-- determines whether a character is currently being played by the human player.
--
-- This design makes it trivial to switch which character the player embodies —
-- a configuration change, not a schema change. It also ensures NPCs are
-- modeled with equal richness to player characters, which is a deliberate
-- design commitment of this engine.
-- =============================================================================

CREATE TABLE character (
    id          INTEGER PRIMARY KEY,
    game_id     INTEGER NOT NULL REFERENCES game(id),
    name        TEXT    NOT NULL,

    -- Role in the current game session.
    -- 'player'         = the character the human is currently playing
    -- 'npc_active'     = named NPC with a full psychological record
    -- 'npc_background' = minor or unnamed character; minimal record
    role        TEXT    NOT NULL
        CHECK(role IN ('player', 'npc_active', 'npc_background')),

    -- Species matters for adjudication (feline vs. human comprehension,
    -- physical capability, etc.) and for the speech filter in Pass 3.
    species     TEXT    NOT NULL DEFAULT 'human',

    -- Gender label: 'male', 'female', 'nonbinary', 'neuter', or any
    -- author-defined value. NULL = LLM infers from name/species/context.
    -- Used as a hint to Pass 3 prose rendering; does not affect adjudication.
    gender      TEXT    NULL,

    -- Pronouns as a JSON array of {"case": <case_name>, "form": <pronoun>}
    -- pairs in the module's target language. Case labels are English keywords
    -- regardless of module language (language-neutral schema key). NULL = LLM
    -- infers from gender field or name/species context.
    --
    -- English she/her: [{"case":"nominative","form":"she"},
    --                    {"case":"accusative","form":"her"},
    --                    {"case":"genitive","form":"her"}]
    --
    -- German masculine: [{"case":"nominative","form":"er"},
    --                     {"case":"accusative","form":"ihn"},
    --                     {"case":"dative","form":"ihm"},
    --                     {"case":"genitive","form":"seiner"}]
    --
    -- Future multi-language extension: wrap in a locale-keyed dict without
    -- breaking existing single-language data.
    pronouns    TEXT    NULL,

    -- Visible description: what other characters can observe directly.
    description TEXT,

    -- Apparent social role as perceived by others. May differ from actual
    -- role when hidden motivation is in play.
    apparent_status TEXT,

    -- Current location. Updated each time the character moves.
    current_location_id INTEGER REFERENCES location(id),

    -- -------------------------------------------------------------------------
    -- Big Five personality traits (OCEAN)
    -- Floats 0.0 (low) to 1.0 (high). Stable and slow-changing.
    -- These traits determine how a character pursues goals and responds to
    -- social pressure. Two characters with identical goals but different OCEAN
    -- profiles will respond very differently to the same action.
    -- The LLM receives these directly and applies them without further translation.
    -- -------------------------------------------------------------------------
    ocean_openness          REAL CHECK(ocean_openness          BETWEEN 0.0 AND 1.0),
    ocean_conscientiousness REAL CHECK(ocean_conscientiousness BETWEEN 0.0 AND 1.0),
    ocean_extraversion      REAL CHECK(ocean_extraversion      BETWEEN 0.0 AND 1.0),
    ocean_agreeableness     REAL CHECK(ocean_agreeableness     BETWEEN 0.0 AND 1.0),
    ocean_neuroticism       REAL CHECK(ocean_neuroticism       BETWEEN 0.0 AND 1.0),

    -- -------------------------------------------------------------------------
    -- Maslow tier (priority-override mechanism)
    -- The character's current dominant need level. When lower-tier needs are
    -- threatened, higher-tier goal pursuit is temporarily suppressed. Used as
    -- a principled behavioral override, not as a strict psychological theory.
    -- Updated dynamically by world events.
    -- -------------------------------------------------------------------------
    maslow_tier TEXT NOT NULL DEFAULT 'belonging'
        CHECK(maslow_tier IN (
            'physiological', 'safety', 'belonging', 'esteem', 'self_actualization'
        )),

    -- -------------------------------------------------------------------------
    -- Emotional state (short-term modifier)
    -- Qualitative description of the character's current emotional condition.
    -- Separate from stable OCEAN traits. Updated by adjudication outcomes.
    -- Natural language string passed directly to the LLM.
    -- Examples: 'groggy', 'annoyed', 'content', 'curious', 'anxious', 'elated'
    -- -------------------------------------------------------------------------
    emotional_state TEXT NOT NULL DEFAULT 'neutral',

    -- -------------------------------------------------------------------------
    -- MST capability and context beliefs (Ford-Nichols)
    -- Per MST, motivation depends on four components: goals, capability beliefs
    -- (self-efficacy), context beliefs (perceived environmental support/threat),
    -- and emotional arousal. Goals are in character_goal; emotional arousal is
    -- in internal_state. Beliefs are stored here as JSON objects.
    --
    -- capability_beliefs: self-efficacy per relevant domain.
    --   Example: {"hunting": 0.8, "opening_doors": 0.1, "meowing_persuasively": 0.9}
    -- context_beliefs: perceived environmental support or threat per domain.
    --   Example: {"waking_humans": 0.4, "finding_toys": 0.6}
    -- -------------------------------------------------------------------------
    capability_beliefs  TEXT NOT NULL DEFAULT '{}',
    context_beliefs     TEXT NOT NULL DEFAULT '{}',

    -- -------------------------------------------------------------------------
    -- Surface and hidden motivation
    -- Surface motivation: goals and attitudes the character presents to the world.
    --   Used by low-insight interactions; observable by the player.
    -- Hidden motivation: actual goals, fears, and attitudes the character conceals.
    --   Used by the adjudication pass for truthful outcome computation.
    --   Only surfaced when access_hidden_motivation = 1 or via high-insight actions.
    --
    -- Both are stored as prose summaries here; detailed goals are in character_goal.
    -- -------------------------------------------------------------------------
    surface_motivation      TEXT,
    hidden_motivation       TEXT,

    -- Access control flag for hidden motivation.
    -- 0 = concealed (default); 1 = revealed to the adjudication layer and/or player
    access_hidden_motivation INTEGER NOT NULL DEFAULT 0
        CHECK(access_hidden_motivation IN (0, 1)),

    -- -------------------------------------------------------------------------
    -- Voice parameters (NPC prose rendering)
    -- Passed to Pass 3 to calibrate how this character speaks.
    -- register:  e.g. 'formal', 'casual', 'sleepy', 'gruff', 'imperious'
    -- warmth:    0.0 = cold/hostile, 1.0 = warm/affectionate
    -- verbosity: 0.0 = terse/monosyllabic, 1.0 = expansive/voluble
    -- -------------------------------------------------------------------------
    voice_register  TEXT,
    voice_warmth    REAL CHECK(voice_warmth    BETWEEN 0.0 AND 1.0),
    voice_verbosity REAL CHECK(voice_verbosity BETWEEN 0.0 AND 1.0),

    -- -------------------------------------------------------------------------
    -- Narrative points
    -- Accumulate when the character acts consistently with their established
    -- personality record; spent when they act against type. Displayed to the
    -- player for the player character; tracked silently for NPCs.
    -- -------------------------------------------------------------------------
    narrative_points INTEGER NOT NULL DEFAULT 0,

    -- Teaching capability: distinct from domain skill level. Expert practitioners
    -- are not always effective teachers. Used when this character instructs another.
    -- Float 0.0 (cannot teach effectively) to 1.0 (exceptional teacher).
    teaching_capability REAL CHECK(teaching_capability BETWEEN 0.0 AND 1.0),

    -- -------------------------------------------------------------------------
    -- NPC wandering parameters (added v3)
    -- Engine-driven autonomous background movement, separate from LLM-driven
    -- reactive movement in Pass 2 outcomes.
    -- -------------------------------------------------------------------------

    -- JSON array of location_ids this character may inhabit during autonomous
    -- wandering. The engine will only move an NPC to a location within this
    -- range AND adjacent to their current location. NULL = no autonomous movement.
    -- Example: [1, 2, 3, 5] for a character who circulates among four rooms.
    wander_range TEXT DEFAULT NULL,

    -- Per-turn probability that this character moves autonomously to an adjacent
    -- location within their wander_range. Checked once per turn before player input.
    -- 0.0 = never moves autonomously (default; includes all player characters).
    -- NOTE: the wander roll is skipped for any character with a non-null
    -- pending_intent — social engagements are commitments, and wandering off
    -- mid-conversation is not done.
    wander_probability REAL NOT NULL DEFAULT 0.0,

    -- -------------------------------------------------------------------------
    -- Pending intent (added v7)
    -- A working-memory slot for deferred social obligations and queued
    -- intentions. Natural language string describing what this character
    -- intends to do, or is socially obligated to do, as a result of a prior
    -- interaction. Set and cleared by Pass 2 via 'pending_intent_updates' in
    -- outcome JSON. Included in the NPC profile block of the Pass 2 context
    -- packet so commitments persist across turn boundaries without relying on
    -- action log recall.
    --
    -- Distinct from emotional_state (mood), internal_state (physiology), and
    -- character_goal (stable MST weights). This is a short-term behavioral
    -- commitment slot, not a stable trait.
    --
    -- Examples: 'owes reciprocal grooming to Toulouse (ears)'
    --           'has agreed to open the next set with Elizabeth'
    --           'intends to maneuver toward Wickham before supper'
    -- -------------------------------------------------------------------------
    pending_intent TEXT DEFAULT NULL,

    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- =============================================================================
-- CHARACTER_GOAL
-- Ford-Nichols Motivational Systems Theory goals per character.
-- Each character carries a weighted set drawn from the 24-goal taxonomy.
-- Separate table because characters have multiple goals with varying priorities.
-- =============================================================================

CREATE TABLE character_goal (
    id              INTEGER PRIMARY KEY,
    character_id    INTEGER NOT NULL REFERENCES character(id),

    -- Goal name from the Ford-Nichols 24-goal taxonomy, stored as a natural
    -- language string. Examples: 'belonging', 'self_determination', 'mastery',
    -- 'safety', 'understanding', 'equity', 'social_responsibility', 'resource_acquisition'
    goal_name       TEXT    NOT NULL,

    -- Whether this is a surface (visible) or hidden goal.
    -- 'surface' = the character openly pursues or acknowledges this goal
    -- 'hidden'  = the character conceals this goal; subject to access_hidden_motivation
    goal_type       TEXT    NOT NULL DEFAULT 'surface'
        CHECK(goal_type IN ('surface', 'hidden')),

    -- Priority weight: 0.0 (negligible) to 1.0 (dominant).
    -- Determines how strongly this goal drives behavior relative to others.
    priority        REAL    NOT NULL CHECK(priority BETWEEN 0.0 AND 1.0),

    -- Approach/avoidance orientation from the Ford-Nichols taxonomy.
    -- 'approach' = character is motivated toward this goal
    -- 'avoidance' = character is motivated away from its negation/threat
    orientation     TEXT    NOT NULL DEFAULT 'approach'
        CHECK(orientation IN ('approach', 'avoidance')),

    -- Within-person vs. person-environment scope from the Ford-Nichols taxonomy.
    -- 'within_person'      = aimed at changes in oneself (growth, self-regulation)
    -- 'person_environment' = aimed at changes in the external world
    scope           TEXT    NOT NULL DEFAULT 'person_environment'
        CHECK(scope IN ('within_person', 'person_environment')),

    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- =============================================================================
-- CHARACTER_ATTITUDE
-- Attitude of one character toward another, stored as a relation.
-- Separate from goals because attitudes are dyadic and numerous.
-- Updated by adjudication outcomes after each interaction.
-- =============================================================================

CREATE TABLE character_attitude (
    id              INTEGER PRIMARY KEY,
    -- The character holding this attitude.
    character_id    INTEGER NOT NULL REFERENCES character(id),
    -- The character this attitude is directed toward.
    target_id       INTEGER NOT NULL REFERENCES character(id),

    -- Attitude value: -1.0 (hostile/contemptuous) to 1.0 (warm/trusting).
    -- 0.0 = neutral/unknown. Updated by Pass 2 adjudication outcomes.
    attitude        REAL    NOT NULL DEFAULT 0.0
        CHECK(attitude BETWEEN -1.0 AND 1.0),

    -- Surface attitudes are expressed and observable.
    -- Hidden attitudes are concealed; subject to access_hidden_motivation on the holder.
    attitude_type   TEXT    NOT NULL DEFAULT 'surface'
        CHECK(attitude_type IN ('surface', 'hidden')),

    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),

    UNIQUE(character_id, target_id, attitude_type)
);


-- =============================================================================
-- CHARACTER_SKILL
-- Skill floats per character using an open, natural-language taxonomy.
-- Skill names are natural language strings — the LLM evaluates semantic
-- relevance at adjudication time without a lookup table.
-- 'Cat hunting technique' is narrow and applies fully in its specific context.
-- 'Stealth' is broad and applies at moderate strength across many contexts.
-- The string stored here IS the skill definition.
-- =============================================================================

CREATE TABLE character_skill (
    id              INTEGER PRIMARY KEY,
    character_id    INTEGER NOT NULL REFERENCES character(id),

    -- Natural language skill name. No canonical list; specificity is encoded
    -- in the term itself. The LLM reads semantic breadth at adjudication time.
    skill_name      TEXT    NOT NULL,

    -- Skill level: 0.0 (none) to 1.0 (virtuoso). Continuous float.
    -- Drives adjudication. Threshold labels (novice, apprentice, journeyman,
    -- master, virtuoso) are defined per domain for prose rendering only —
    -- they do not constrain the underlying float.
    skill_level     REAL    NOT NULL DEFAULT 0.0
        CHECK(skill_level BETWEEN 0.0 AND 1.0),

    -- Timestamp of last practice or exercise. Used to compute skill decay:
    -- a domain not exercised recently loses ground at a rate modulated by
    -- how deeply established the skill is (i.e. by skill_level itself).
    last_practiced_at TEXT,

    -- How much this character enjoys exercising this skill for its own sake,
    -- independent of any external goal it serves. (Added v2.)
    -- NULL  = no intrinsic motivation recorded (skill is purely instrumental)
    -- 0.0   = the character actively dislikes this skill but may still use it
    -- 0.5   = mild preference for using this skill when it is relevant
    -- 1.0   = deep hobby; the character will seek opportunities to exercise this
    --          skill spontaneously, without external prompting
    intrinsic_motivation REAL DEFAULT NULL,

    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),

    UNIQUE(character_id, skill_name)
);


-- =============================================================================
-- CHARACTER_GROWTH_EVENT
-- Milestone log of personality record updates.
-- Created when a character acts against established type in a dramatically
-- significant and contextually appropriate way. At these milestones the OCEAN
-- scores or goal weights are updated to reflect who the character is becoming,
-- rather than simply debiting narrative points.
-- Applies to both player characters and NPCs.
-- =============================================================================

CREATE TABLE character_growth_event (
    id              INTEGER PRIMARY KEY,
    character_id    INTEGER NOT NULL REFERENCES character(id),

    -- Prose description of what happened and why it qualified as a growth event.
    description     TEXT    NOT NULL,

    -- JSON snapshot of what changed: field names and old/new values.
    -- Example: {"ocean_openness": {"old": 0.3, "new": 0.38},
    --           "goal_belonging_priority": {"old": 0.9, "new": 0.7}}
    changes_json    TEXT    NOT NULL,

    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- =============================================================================
-- INTERNAL_STATE
-- Named float values representing quantitative internal states that change
-- during play and affect behavior. Distinct from OCEAN (stable traits) and
-- emotional_state (qualitative label). These are time-varying states with
-- direct behavioral and narrative consequences.
--
-- In I Am a Cat, boredom is the primary internal state and serves as the
-- time-pressure mechanic: boredom approaching 1.0 is the failure condition.
-- This is a reusable design pattern — internal state degradation as narrative
-- stakes, replacing hit points.
-- =============================================================================

CREATE TABLE internal_state (
    id              INTEGER PRIMARY KEY,
    character_id    INTEGER NOT NULL REFERENCES character(id),

    -- State name in natural language.
    -- Examples: 'boredom', 'hunger', 'sleepiness', 'curiosity', 'annoyance',
    --           'language_confidence', 'bank_account_balance'
    state_name      TEXT    NOT NULL,

    -- State value: 0.0 (absent/minimum) to 1.0 (maximum/overwhelming).
    -- Behavioral thresholds are specified in the game record's
    -- internal_state_display config, not hard-coded in this schema.
    value           REAL    NOT NULL DEFAULT 0.0
        CHECK(value BETWEEN 0.0 AND 1.0),

    -- How to surface this state to the player.
    -- 'prose'   = rendered as character-voice commentary by the LLM.
    --             Preferred for immersive play. Example: "Oh, this is SOOOO boring."
    -- 'numeric' = displayed as a raw float. Useful for dev/testing contexts.
    display_mode    TEXT    NOT NULL DEFAULT 'prose'
        CHECK(display_mode IN ('prose', 'numeric')),

    -- Involuntary event support (added v2).
    -- Some internal states can trigger events the character does not control —
    -- hairballs being the canonical example. The engine rolls each turn against a
    -- probability computed from the state value; if it fires, the event is injected
    -- into Pass 2 as an additional constraint on the outcome.
    --
    -- is_involuntary: 1 = can fire an involuntary event; 0 = adjudication-only (default).
    is_involuntary          INTEGER NOT NULL DEFAULT 0,

    -- How the trigger fires.
    -- 'threshold'     = event fires when value >= involuntary_trigger_param
    -- 'probabilistic' = per-turn probability = value * involuntary_trigger_param,
    --                   capped at INVOLUNTARY_MAX_PROB in config.py
    -- NULL when is_involuntary = 0
    involuntary_trigger_type TEXT DEFAULT NULL,

    -- Trigger parameter. Interpretation depends on involuntary_trigger_type:
    --   threshold:    the value at which the event fires (e.g. 0.85)
    --   probabilistic: scale factor → per-turn probability (e.g. 0.15 means
    --                  at value=1.0 there is a 15% chance per turn)
    involuntary_trigger_param REAL DEFAULT NULL,

    -- Instruction to the adjudication layer when the event fires. Describes
    -- what happens, its consequences, and what actions affect this state.
    involuntary_event_description TEXT DEFAULT NULL,

    -- Rate of passive change per elapsed in-game minute.
    -- Positive = accumulates toward 1.0; negative = decays toward 0.0.
    -- Applied by the engine after each turn's clock advance (before Pass 3):
    --   new_value = clamp(value + passive_rate_per_minute * elapsed_minutes,
    --                     0.0, 1.0)
    -- NULL = no passive drift; this state changes only via Pass 2 outcome JSON.
    --
    -- Use this field for physiological states with true background drift:
    -- sleepiness, hunger, thirst, thermal discomfort, air depletion, etc.
    -- Do NOT use for activity-dependent states (restlessness, impatience) —
    -- those should be NULL here and managed entirely by Pass 2.
    --
    -- Example rates for I Am a Cat:
    --   boredom (Toulouse):           +0.002  per minute
    --   hunger (Toulouse):            +0.002  per minute
    --   hairball_pressure (Toulouse): +0.0003 per minute
    --   sleepiness (Guy):             -0.006  per minute (lightens toward dawn)
    --   sleepiness (Mama):            -0.004  per minute (lighter sleeper)
    passive_rate_per_minute REAL DEFAULT NULL,

    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),

    UNIQUE(character_id, state_name)
);


-- =============================================================================
-- GAME_INSTANCE
-- One row per playthrough of a module. Holds per-session dynamic state that
-- is distinct from the module definition. This is the beginning of a
-- module/instance architectural split; full support (instance_id on all state
-- tables) is deferred to a future migration.
--
-- Current behaviour: other state tables (character, internal_state, etc.)
-- implicitly belong to the one active instance. The engine identifies the
-- active instance as the most recent game_instance row for a given game_id
-- with status IN ('ready', 'active').
--
-- Future (v6): instance_id will be threaded through character, internal_state,
-- item_location, action_log, and character_visited_location, enabling multiple
-- concurrent instances, save slots, and the "What if..." premise modifier.
-- =============================================================================

CREATE TABLE game_instance (
    id      INTEGER PRIMARY KEY,

    -- The module this instance belongs to.
    game_id INTEGER NOT NULL REFERENCES game(id),

    -- Lifecycle state. Checked by the engine before starting a session.
    -- 'pending'  = instance not yet fully initialised; engine will not start.
    -- 'ready'    = all required values set; ready to begin play.
    -- 'active'   = session currently in progress.
    -- 'complete' = session ended via an end condition (boredom limit, sunrise,
    --              etc.). A new instance must be created to play again.
    -- The seed process must set status to 'ready' as its final statement.
    status  TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'ready', 'active', 'complete')),

    -- The module's canonical opening time in minutes past midnight.
    -- Set by the seed; never updated during play. Used to reset the clock
    -- when starting a new playthrough:
    --   UPDATE game_instance SET current_time_minutes = start_time_minutes
    -- Sentinel -1 means unseeded; the engine refuses to start with this value.
    start_time_minutes   INTEGER NOT NULL DEFAULT -1,

    -- Live in-game clock: minutes elapsed since midnight at the start of the
    -- game day. Incremented each turn by Pass 2's elapsed_minutes output.
    -- Starts equal to start_time_minutes on a fresh instance.
    -- Human-readable label computed at runtime (never stored):
    --   hour   = (current_time_minutes // 60) % 24
    --   minute = current_time_minutes % 60
    -- Sentinel -1 means unseeded; the engine refuses to start with this value.
    current_time_minutes INTEGER NOT NULL DEFAULT -1,

    -- Optional "What if..." player-entered premise modifier. NULL when not in
    -- use. When present, carried in every context packet as an addendum to the
    -- module premise. Set once at session start via a dedicated LLM call
    -- (Sonnet or better); not modified during play.
    -- See docs/future_features.md §6 for full design.
    premise_modifier TEXT DEFAULT NULL,

    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_game_instance_game ON game_instance(game_id);


-- =============================================================================
-- ITEM
-- Objects in the world that characters can interact with.
-- Items carry natural language names and descriptions; the LLM infers relevant
-- properties (container, toy, food, improvised weapon, percussion instrument)
-- from context at adjudication time. No boolean taxonomy flags are stored —
-- this is one of the fundamental architectural shifts LLM adjudication enables.
-- =============================================================================

CREATE TABLE item (
    id                      INTEGER PRIMARY KEY,
    game_id                 INTEGER NOT NULL REFERENCES game(id),

    -- Natural language name and description. The description IS the item's
    -- property definition. The LLM determines what role the item plays based
    -- on what the player is attempting and the item's described properties.
    name                    TEXT    NOT NULL,
    description             TEXT    NOT NULL,

    -- Current location. Null if the item is being held by a character.
    location_id             INTEGER REFERENCES location(id),

    -- Character currently holding this item. Null if the item is in a location.
    held_by_character_id    INTEGER REFERENCES character(id),

    -- Tool/material quality: 0.0 (poor) to 1.0 (exceptional).
    -- Raises the execution ceiling for creative actions without raising the
    -- underlying skill float. Poor tools constrain even high skill.
    -- Null means quality is not applicable or not yet determined.
    quality                 REAL    CHECK(quality IS NULL OR quality BETWEEN 0.0 AND 1.0),

    -- Whether this item is currently visible and accessible in its location.
    -- Hidden items exist in the world but require discovery before interaction.
    is_visible              INTEGER NOT NULL DEFAULT 1
        CHECK(is_visible IN (0, 1)),

    created_at              TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- =============================================================================
-- NPC_PLAYER_HISTORY
-- Rolling summary of the interaction history between any two characters.
-- Not a full event log — regenerated and compressed periodically to stay
-- token-efficient. Captures relationship trajectory, notable events, and
-- any private knowledge one character has about another.
--
-- Stored symmetrically: character_a_id < character_b_id by convention,
-- so each pair has exactly one row regardless of interaction direction.
-- =============================================================================

CREATE TABLE npc_player_history (
    id                          INTEGER PRIMARY KEY,

    -- The two characters this history describes.
    -- Convention: character_a_id < character_b_id (enforced by application layer).
    character_a_id              INTEGER NOT NULL REFERENCES character(id),
    character_b_id              INTEGER NOT NULL REFERENCES character(id),

    -- Rolling prose summary of the relationship, notable events, and any
    -- private knowledge either character holds about the other.
    -- Passed to Pass 2 as 'history_summary' in the context packet.
    summary                     TEXT    NOT NULL DEFAULT '',

    -- Number of interactions recorded since the last summary regeneration.
    -- When this crosses a threshold, the engine regenerates and compresses the summary.
    interactions_since_summary  INTEGER NOT NULL DEFAULT 0,

    updated_at                  TEXT    NOT NULL DEFAULT (datetime('now')),

    UNIQUE(character_a_id, character_b_id)
);


-- =============================================================================
-- ACTION_LOG
-- Recent player actions for Pass 1 (intent parsing) context assembly.
-- Provides the 'recent_actions' field in the Pass 1 context packet.
-- Not intended as a permanent audit log — older entries can be pruned
-- once they fall outside the context window needed for intent parsing.
-- =============================================================================

CREATE TABLE action_log (
    id              INTEGER PRIMARY KEY,
    game_id         INTEGER NOT NULL REFERENCES game(id),

    -- The character who performed the action (usually the player character).
    character_id    INTEGER NOT NULL REFERENCES character(id),

    -- Structured action record produced by Pass 1 (intent parsing).
    -- JSON with fields: type, target_character_id, target_item_id,
    --                   inferred_goal, raw_input
    action_json     TEXT    NOT NULL,

    -- Narrative beat produced by Pass 2 adjudication.
    -- Stored here so future context packets can include recent outcomes
    -- without re-querying the full adjudication history.
    narrative_beat  TEXT,

    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- =============================================================================
-- INDEXES
-- Covering the most frequent access patterns: character lookup by game,
-- location detail validity checks, action log recency queries.
-- =============================================================================

CREATE INDEX idx_character_game     ON character(game_id);
CREATE INDEX idx_character_location ON character(current_location_id);
CREATE INDEX idx_location_game      ON location(game_id);
CREATE INDEX idx_location_detail_valid ON location_detail(location_id, is_valid);
CREATE INDEX idx_item_location      ON item(location_id);
CREATE INDEX idx_item_holder        ON item(held_by_character_id);
CREATE INDEX idx_action_log_recent  ON action_log(game_id, created_at DESC);
CREATE INDEX idx_character_goal     ON character_goal(character_id);
CREATE INDEX idx_character_attitude ON character_attitude(character_id, target_id);
CREATE INDEX idx_internal_state     ON internal_state(character_id, state_name);


-- =============================================================================
-- CHARACTER_VISITED_LOCATION  (added v4)
-- Record of locations a character has previously entered. Used to validate
-- quick-move pathfinding (BFS, Option C): the player may name any previously
-- visited location as a destination; the engine computes the path. NPCs are
-- not subject to this restriction.
--
-- Each (character, location) pair is unique; subsequent visits do not create
-- new rows. Pre-populate in seed for characters who know the whole map at
-- the start of play (e.g. a cat who lives in the house).
-- =============================================================================

CREATE TABLE character_visited_location (
    id              INTEGER PRIMARY KEY,
    character_id    INTEGER NOT NULL REFERENCES character(id),
    location_id     INTEGER NOT NULL REFERENCES location(id),

    -- Timestamp of first visit. Used for ordering and future analytics;
    -- not used for gameplay logic.
    first_visited_at DATETIME NOT NULL DEFAULT (datetime('now')),

    UNIQUE(character_id, location_id)
);

CREATE INDEX idx_visited_character ON character_visited_location(character_id);


-- =============================================================================
-- LOCATION_CONNECTION  (added v3)
-- Explicit adjacency graph between locations. Each row is a bidirectional
-- connection; by convention location_a_id < location_b_id. Queries must
-- check both directions: WHERE location_a_id = ? OR location_b_id = ?
--
-- Added because the engine had no explicit model of adjacency in v1–v2: the
-- LLM could move characters to unreachable locations via prose-context drift
-- (observed in first play session). This table validates all movement and
-- informs Pass 2 of what is reachable from the current location.
-- =============================================================================

CREATE TABLE location_connection (
    id              INTEGER PRIMARY KEY,

    -- The two locations this connection links. Canonical order: a_id < b_id.
    location_a_id   INTEGER NOT NULL REFERENCES location(id),
    location_b_id   INTEGER NOT NULL REFERENCES location(id),

    -- How the connection is traversed.
    -- 'open'    = no barrier; characters move freely (open-plan rooms, archways)
    -- 'door'    = a door that may be open or closed; cats may be blocked
    -- 'stairs'  = a staircase; passable by all but noted for context
    -- 'squeeze' = requires physical effort (e.g. cat squeezing through railing)
    connection_type TEXT NOT NULL DEFAULT 'door'
        CHECK(connection_type IN ('open', 'door', 'stairs', 'squeeze')),

    -- Whether this connection is currently passable. Doors can be closed by
    -- world events; this flag tracks current state.
    -- 1 = passable (default), 0 = blocked
    is_passable     INTEGER NOT NULL DEFAULT 1
        CHECK(is_passable IN (0, 1)),

    -- Natural language description of the barrier type, for Pass 2 context.
    -- (Added v7.) is_passable is the engine's binary movement gate; this field
    -- gives the LLM semantic context to adjudicate what kind of barrier applies
    -- and what it costs to attempt passage.
    --
    -- Key distinction:
    --   'locked' — physically impassable; requires a key or forced entry.
    --   'closed by convention' — unlocked but socially impassable; entry is
    --       possible at reputational cost. Pass 2 adjudicates the consequence.
    -- NULL = no special note needed; connection_type and is_passable suffice.
    passage_note    TEXT DEFAULT NULL,

    -- Bidirectional uniqueness enforced by convention (a < b) + constraint.
    UNIQUE(location_a_id, location_b_id),
    CHECK(location_a_id < location_b_id)
);

CREATE INDEX idx_location_connection_a ON location_connection(location_a_id);
CREATE INDEX idx_location_connection_b ON location_connection(location_b_id);


-- =============================================================================
-- FACTION  (added v7)
-- Named social groups whose opinion of a character has mechanical weight.
-- Scoped to a game module via game_id; a module with no factions (e.g.
-- I Am a Cat) has no rows for its game_id. game_id is the isolation boundary
-- when multiple modules share a database.
--
-- Factions may be created dynamically during play: a new family unit formed
-- by marriage, a political alliance that coalesces during events, etc. Pass 2
-- issues a create_faction entry in outcome JSON; the engine inserts the row
-- before applying reputation changes. The schema requires no modification for
-- this use case.
--
-- A character's allegiance to a faction (how they identify with or feel driven
-- toward a group) is modeled via MST goals in character_goal — e.g. a
-- 'belonging' goal whose description names the faction. Reputation (this table
-- and character_faction_reputation) is how the faction views the character.
-- The two are distinct and complementary, not redundant.
-- =============================================================================

CREATE TABLE faction (
    id          INTEGER PRIMARY KEY,
    game_id     INTEGER NOT NULL REFERENCES game(id),

    -- Short snake_case slug used as a key in context packets and Pass 2
    -- outcome JSON. Examples: 'bennet_family', 'meryton_neighborhood',
    -- 'bingley_circle'. Must be unique within a game_id (see constraint).
    name        TEXT    NOT NULL,

    -- LLM-facing description of this faction's values and judgment criteria.
    -- Explains what the faction values, how it judges characters, and what
    -- kinds of actions raise or lower standing. Passed verbatim to Pass 2
    -- in the faction_reputations block of the context packet.
    description TEXT    NOT NULL,

    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),

    -- Faction slugs must be unique within a module. Used as keys in outcome
    -- JSON; collisions within a game_id would be ambiguous.
    UNIQUE(game_id, name)
);

CREATE INDEX idx_faction_game ON faction(game_id);


-- =============================================================================
-- CHARACTER_FACTION_REPUTATION  (added v7)
-- A character's standing with a faction as a float in [0.0, 1.0].
--   0.0 = complete disgrace or ostracism
--   0.5 = neutral or unknown (default starting value)
--   1.0 = exceptional standing, full acceptance
--
-- Tracked primarily for the player character. May also be seeded for NPCs
-- whose faction standing affects adjudication (e.g. Wickham's standing with
-- the militia affects what other characters say about him in Pass 2 context).
--
-- Pass 2 updates these via 'faction_reputation_changes' in outcome JSON:
--   [{"character_id": N, "faction_id": M, "delta": -0.08,
--     "reason": "Elizabeth refused to manage Mrs. Bennet's outburst"}]
-- The engine applies delta and clamps to [0.0, 1.0] in _apply_outcome().
-- The reason string is written to the notes field on update.
--
-- Rows may be added mid-play when new factions form or when a character
-- first becomes relevant to a faction that was previously out of scope.
-- =============================================================================

CREATE TABLE character_faction_reputation (
    character_id    INTEGER NOT NULL REFERENCES character(id),
    faction_id      INTEGER NOT NULL REFERENCES faction(id),

    -- Standing: 0.0 (ostracised) to 1.0 (full acceptance). 0.5 = neutral.
    reputation      REAL    NOT NULL DEFAULT 0.5
        CHECK(reputation BETWEEN 0.0 AND 1.0),

    -- Human-readable note on why standing is at its current value.
    -- Set by seed; updated by Pass 2 alongside each delta. Included in the
    -- faction_reputations block of the Pass 2 context packet so the LLM has
    -- narrative context for reputation decisions, not just a raw float.
    -- Example: "Bennet family pleased with her conduct; no embarrassments yet"
    notes           TEXT,

    updated_at      TEXT    NOT NULL DEFAULT (datetime('now')),

    PRIMARY KEY (character_id, faction_id)
);

CREATE INDEX idx_faction_rep_character ON character_faction_reputation(character_id);


-- =============================================================================
-- SCHEMA VERSION — CURRENT
-- This INSERT records the version of this file. Migration scripts each append
-- their own row; this entry represents the version at which schema.sql was last
-- updated and is what fresh-install databases will report as their version.
-- The engine reads MAX(version) from schema_version to determine the schema version.
-- =============================================================================

INSERT INTO schema_version (version, description)
VALUES (7, 'Fresh install at v7: faction, character_faction_reputation, passage_note on location_connection, pending_intent on character, wander_range/wander_probability on character, character_visited_location');
