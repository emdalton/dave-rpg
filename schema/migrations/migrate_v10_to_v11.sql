-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v10 → v11
-- schema/migrations/migrate_v10_to_v11.sql
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Green Room Mode: character creation stage and Fate Core Aspects
-- -----------------------------------------------------------------------
--
-- Two additions:
--
-- 1. player_definition_mode on game gains a new valid value: 'green_room'.
--    'green_room' triggers the pre-game Fate Core character creation stage
--    (issue #59) before _render_opening_scene(). The module author supplies
--    character_creation_prompt and character_creation_hint in module_flags
--    (JSON, no schema change needed). 'fixed', 'define', and 'choose' are
--    unchanged.
--
--    SQLite does not support ALTER TABLE ... MODIFY CONSTRAINT, so we
--    recreate the game table with the expanded CHECK constraint.
--    PRAGMA foreign_keys = OFF is required while the table is being
--    reconstructed; tables referencing game(id) continue to work after
--    the rename because their FK references are by column name, not by
--    table OID.
--
-- 2. character_aspect table: stores Fate Core Aspects generated during the
--    Green Room stage. Aspects are persistent engine data — not just character
--    description — because they are the currency of the Fate Point Economy
--    (issue #11): an Aspect can be invoked (spend a Fate Point for a bonus)
--    or compelled (accept a Fate Point when the Aspect complicates the
--    situation). Pass 2 needs to see a character's Aspects to adjudicate
--    invocations and compels correctly.
--
--    aspect_type maps to Fate Core's three structural roles:
--      'high_concept' — one phrase that sums up who the character is
--      'trouble'      — a personal complication or vulnerability; the most
--                       natural target for compels
--      'aspect'       — additional defining phrase (skills, background,
--                       relationships, signature items, etc.)
--
-- Usage:
--   sqlite3 <module>.db < schema/migrations/migrate_v10_to_v11.sql
-- =============================================================================

PRAGMA foreign_keys = OFF;   -- required while recreating game table


-- =============================================================================
-- Step 1: Recreate game table with 'green_room' added to CHECK constraint
-- =============================================================================

CREATE TABLE game_new (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,   -- human-readable name, e.g. 'I Am a Cat'

    -- Genre and tone are passed verbatim to the LLM in every context packet.
    genre       TEXT    NOT NULL,
    tone        TEXT    NOT NULL,

    -- Era and technology level provide period-appropriate inference context.
    era         TEXT,
    technology_level TEXT,

    -- Magic system description. Null means no magic exists in this world.
    magic_system TEXT,

    -- Default narrative register for prose rendering.
    -- 'first_person', 'second_person', 'third_person_close',
    -- 'third_person_distant', 'atmospheric'
    narrative_register TEXT NOT NULL DEFAULT 'third_person_close',

    -- Speech filter configuration as JSON.
    speech_filter TEXT NOT NULL DEFAULT '{}',

    -- Internal state display configuration as JSON.
    -- Maps state_name -> 'prose' | 'numeric'.
    internal_state_display TEXT NOT NULL DEFAULT '{}',

    -- Cultural norms relevant to common action types, passed to Pass 2.
    cultural_norms TEXT NOT NULL DEFAULT '{}',

    -- How the player character is established at the start of a session.
    -- 'fixed'      = player character is fully seeded; no startup definition step.
    --                Default. Use for modules with a fixed protagonist.
    -- 'define'     = engine prompts the player to describe themselves at a
    --                designated starting location. Declared items are instantiated.
    -- 'green_room' = pre-game Fate Core character creation stage. Module author
    --                provides character_creation_prompt and character_creation_hint
    --                in module_flags. Player defines High Concept, Trouble, Aspects,
    --                and skills before the opening scene begins. Use when the module
    --                has a fixed identity frame but leaves expression open
    --                (e.g. "you are Alice — who have you become?").
    -- 'choose'     = player selects from pre-defined player_option characters
    --                (future; not yet implemented).
    player_definition_mode TEXT NOT NULL DEFAULT 'fixed'
        CHECK(player_definition_mode IN ('fixed', 'define', 'green_room', 'choose')),

    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);


-- =============================================================================
-- Step 2: Copy all existing game records
--
-- Explicit column list required: ALTER TABLE ADD COLUMN appends to the end of
-- the physical column order, so a DB that received player_definition_mode via
-- migration has it after created_at, while game_new declares it before
-- created_at. SELECT * maps by position, not name, and would insert the
-- created_at timestamp into the player_definition_mode CHECK column — causing a
-- constraint failure. Named columns are always safe across schema versions.
-- =============================================================================

INSERT INTO game_new (
    id, name, genre, tone, era, technology_level, magic_system,
    narrative_register, speech_filter, internal_state_display,
    cultural_norms, player_definition_mode, created_at
)
SELECT
    id, name, genre, tone, era, technology_level, magic_system,
    narrative_register, speech_filter, internal_state_display,
    cultural_norms, player_definition_mode, created_at
FROM game;


-- =============================================================================
-- Step 3: Drop old table, rename new table
-- =============================================================================

DROP TABLE game;
ALTER TABLE game_new RENAME TO game;


-- =============================================================================
-- Step 4: Add character_aspect table
-- =============================================================================

CREATE TABLE character_aspect (
    id              INTEGER PRIMARY KEY,

    -- The character who holds this Aspect.
    character_id    INTEGER NOT NULL REFERENCES character(id),

    -- The Aspect text itself — a short, evocative natural-language phrase.
    -- Examples: "Disgraced surgeon seeking redemption" (high_concept),
    --           "Can't say no to a friend in need" (trouble),
    --           "Educated at the best schools money could buy" (aspect)
    aspect_text     TEXT    NOT NULL,

    -- Fate Core structural role of this Aspect.
    -- 'high_concept' — sums up who the character is; most commonly invoked
    -- 'trouble'      — personal complication; most commonly compelled
    -- 'aspect'       — additional defining phrase (max 3 in standard Fate Core)
    aspect_type     TEXT    NOT NULL
        CHECK(aspect_type IN ('high_concept', 'trouble', 'aspect')),

    -- Display order within aspect_type. Lower numbers appear first.
    -- Not enforced for uniqueness — ordering is advisory for context packet
    -- assembly and display purposes only.
    sort_order      INTEGER NOT NULL DEFAULT 0,

    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Index for fast lookup of all Aspects for a given character.
CREATE INDEX idx_character_aspect ON character_aspect(character_id);


-- =============================================================================
-- Step 5: Re-enable foreign keys and record schema version
-- =============================================================================

PRAGMA foreign_keys = ON;

INSERT INTO schema_version (version, description)
VALUES (11, 'v11: player_definition_mode adds green_room; add character_aspect table for Fate Core character creation and Fate Point Economy');
