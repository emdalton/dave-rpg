-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v8 → v9
-- schema/migrations/migrate_v8_to_v9.sql
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Three additions in this migration:
--
-- 1. game.player_definition_mode (§9)
--    Controls how the player character is established at the start of a session.
--    'fixed'  = player character is fully seeded; no startup self-definition step.
--              Default for all existing modules (Meryton, I Am a Cat).
--    'define' = engine prompts the player to describe themselves at a designated
--              starting location (e.g. outside the hostel door). The description
--              is parsed into character fields and any declared items are
--              instantiated. Seeded starting items are also present and are
--              revealed via the engine's confirmation pass.
--    'choose' = player selects from a list of pre-defined characters (§11, future).
--              Characters with role='player_option' are presented as choices.
--
-- 2. character.speech_filter (§8)
--    Per-character speech rendering constraint. Passed to Pass 3 to modify how
--    this character's dialogue is rendered. NULL = no filter (default).
--    The game-level speech_filter already exists on the game table for global
--    constraints (e.g. the I Am a Cat meow filter). This field is for character-
--    level overrides — most usefully for NPCs who communicate non-verbally or
--    whose speech is unintelligible to the player until a specific condition is
--    met (e.g. Gin-chan in the Hidden Hostel requires a potion to understand).
--    The value is a natural-language instruction to Pass 3, e.g.:
--      'silent: this entity cannot speak; describe only physical actions'
--      'unintelligible: render dialogue as non-verbal sound and gesture only'
--      'cheshire: speak in elliptical, gnomic fragments; never answer directly'
--
-- 3. item and character_item tables (item system foundation)
--    Items are physical objects that persist in the world across turns. They
--    exist at a location OR are held by a character (via character_item).
--    Introduced in v9 to support:
--      - Seeded starting items (e.g. the sencha canister in the Hidden Hostel)
--      - Player-declared items during self-definition (knapsack, shawl)
--      - Mid-play lazy instantiation: when the player claims to have an item
--        ("I have a book in my pack"), Pass 2 creates the item record and
--        character_item row via 'item_instantiations' in the outcome JSON.
--    The same instantiation mechanism handles all three cases — seeded items
--    are the only ones that exist before the player first mentions them.
--
-- Usage:
--   sqlite3 <module>.db < schema/migrations/migrate_v8_to_v9.sql
-- =============================================================================

PRAGMA foreign_keys = ON;


-- =============================================================================
-- 1. game.player_definition_mode
-- =============================================================================

-- Note: IF NOT EXISTS on ADD COLUMN requires SQLite >= 3.37.0; omitted for
-- compatibility. This migration assumes the DB is at exactly v8.
ALTER TABLE game
ADD COLUMN player_definition_mode TEXT NOT NULL DEFAULT 'fixed'
    CHECK(player_definition_mode IN ('fixed', 'define', 'choose'));

-- Commentary: all existing modules default to 'fixed' — no behaviour change.
-- Set to 'define' in the Hidden Hostel seed (and any future module that wants
-- the self-definition entrance flow).


-- =============================================================================
-- 2. character.speech_filter
-- =============================================================================

ALTER TABLE character
ADD COLUMN speech_filter TEXT DEFAULT NULL;

-- Commentary: NULL = no filter for this character (default everywhere).
-- Game-level game.speech_filter (already exists) applies globally to a module.
-- This character-level field is for per-character overrides. Both are passed
-- to Pass 3; character-level takes precedence when both are set.
--
-- Immediate use cases:
--   - The Blue Door (Hidden Hostel): 'silent: cannot speak; physical actions only'
--   - Gin-chan (Hidden Hostel): 'unintelligible: all sounds are purrs, chirps, and
--     wing-movements; no interpretable language until potion condition is met'
--     (future: change to Cheshire Cat voice once player takes the potion)

-- Also add 'npc_object' to the role CHECK constraint for non-character agents
-- (e.g. the Blue Door). SQLite does not support ALTER COLUMN, so we must
-- recreate the table to change a CHECK constraint. For now, we use a migration
-- note and handle this via the engine treating 'npc_object' as a valid role
-- at the application layer. The CHECK will be updated in schema.sql for fresh
-- installs; existing DBs will accept the value without constraint enforcement.
--
-- New valid role values (update schema.sql CHECK for fresh installs):
--   'npc_object' = a non-character agent that participates in scenes through
--                  physical action only (doors, mechanisms, environmental entities)


-- =============================================================================
-- 3. item table (restructure)
--
-- The item table existed since v1 with a different design: held_by_character_id
-- directly on the item row, location_id (not current_location_id), and no
-- properties or is_confirmed fields. In v9 we:
--   - Rename location_id → current_location_id
--   - Drop held_by_character_id (replaced by character_item join table)
--   - Add properties JSON field
--   - Add is_confirmed flag for lazy instantiation
--   - Add updated_at timestamp
--   - Make description nullable (player-claimed items may not have one yet)
--
-- SQLite does not support DROP COLUMN or RENAME COLUMN (pre-3.35), so we
-- recreate the table. No existing modules seed item rows, so no data migration
-- is needed — the table is always empty at migration time.
-- =============================================================================

DROP TABLE IF EXISTS item;

CREATE TABLE item (
    id          INTEGER PRIMARY KEY,
    game_id     INTEGER NOT NULL REFERENCES game(id),

    -- Canonical name. Short and unambiguous within the module.
    -- Examples: 'sencha canister', 'blue shawl', 'leather-bound journal'
    name        TEXT    NOT NULL,

    -- Full description passed to Pass 2 and Pass 3 when the item is in scope.
    -- Should describe appearance, condition, and any salient properties.
    -- Examples: 'a battered tin canister, half-full of fine Japanese green tea;
    --            the lid is engraved with a small crane'
    description TEXT,

    -- Current location of the item, if it is at a location (not held).
    -- NULL when the item is held by a character (see character_item).
    -- An item should have EITHER a current_location_id OR a character_item row,
    -- not both. The engine enforces this at the application layer.
    current_location_id INTEGER REFERENCES location(id),

    -- Arbitrary item properties as a JSON object. Used for module-specific
    -- attributes that don't warrant a schema column.
    -- Examples: {"weight": "light", "container": true, "capacity": "small"}
    --           {"material": "silk", "condition": "well-mended"}
    --           {"readable": true, "language": "unknown"}
    properties  TEXT NOT NULL DEFAULT '{}',

    -- Whether this item has been concretely instantiated in the world, or is
    -- a placeholder created from a player claim that has not yet been confirmed
    -- by Pass 2. 1 = real item (default); 0 = claimed but not yet adjudicated.
    -- The engine may use this to flag items for Pass 2 confirmation on the
    -- next turn that involves the item.
    is_confirmed INTEGER NOT NULL DEFAULT 1
        CHECK(is_confirmed IN (0, 1)),

    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- =============================================================================
-- 4. character_item table
-- =============================================================================

CREATE TABLE IF NOT EXISTS character_item (
    id              INTEGER PRIMARY KEY,
    character_id    INTEGER NOT NULL REFERENCES character(id),
    item_id         INTEGER NOT NULL REFERENCES item(id),

    -- How the character is carrying or wearing this item.
    -- See schema.sql character_item for full slot vocabulary and rationale.
    slot            TEXT NOT NULL DEFAULT 'carried'
        CHECK(slot IN ('right_hand', 'left_hand', 'both_hands', 'mouth',
                       'worn', 'pocket', 'in_pack', 'carried')),

    -- When the character acquired this item (game clock minutes, or NULL if
    -- seeded at game start).
    acquired_at_minutes INTEGER DEFAULT NULL,

    created_at      TEXT NOT NULL DEFAULT (datetime('now')),

    -- An item can only be held by one character at a time.
    UNIQUE(item_id)
);


-- =============================================================================
-- Schema version
-- =============================================================================

INSERT INTO schema_version (version, description)
VALUES (9, 'v9: player_definition_mode on game; speech_filter on character; item and character_item tables for item system foundation');
