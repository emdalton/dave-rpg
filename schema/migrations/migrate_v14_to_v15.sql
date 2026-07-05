-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v14 → v15
-- schema/migrations/migrate_v14_to_v15.sql
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Rename remote_capability -> special_capability; broaden owner/target
-- polymorphism; add can_affect; add typical_duration and typical_effort
-- -----------------------------------------------------------------------
--
-- v14 shipped remote_capability scoped narrowly to "communication/detection
-- across distance," with owner as character-or-item and target as a plain
-- character reference. Design discussion (E) surfaced that the real concept
-- is broader than distance: it's about overriding what a character would
-- normally be able to know or affect, of which cross-location communication
-- is only one instance. Concealment (a rock's hidden history, a person's
-- hidden emotion) is a separate axis from distance, and both need the same
-- owner/target machinery. Hence the rename.
--
-- Five changes:
--
-- 1. Table renamed remote_capability -> special_capability.
--
-- 2. Owner gains a third option: owner_location_id. A location can itself
--    have agency (a warded room that detects anyone entering), not just a
--    character or an item.
--
-- 3. Target changes from a single NOT NULL character FK to four mutually
--    exclusive options: target_character_id, target_item_id,
--    target_location_id (scrying/clairvoyance targets a place, not a
--    character or object), and target_description (free-text filter, e.g.
--    "any distant, real-world place" — adjudicated fresh by Pass 2 each
--    time rather than resolved to one fixed row; for capabilities meant to
--    range over a changing or unenumerable set of targets).
--
-- 4. capability gains a third value: 'can_affect' (owner changes a property
--    of the target — an enchanted glow, a temporarily animated carpet).
--    Distinguished from can_send_to/can_detect_from by being a write, not a
--    read. Scoped by design intent to temporary/environmental effects, not
--    permanent transformation or character-imposed curses — those route
--    through the existing character_aspect + Fate compel mechanism instead.
--    Reuses the `sense` column to name the property being affected (e.g.
--    'luminosity') rather than adding a redundant column.
--
-- 5. Two new nullable, free-text (NOT numeric) columns:
--      distance        — already existed in spirit but is now a real column:
--                         the required spatial relationship between owner
--                         and target. Not just a max range — 'touch' is a
--                         STRICTER requirement than ordinary co-location,
--                         not a looser one. Examples: 'touch', 'unlimited'.
--      typical_duration — qualitative, e.g. 'fleeting', 'a few minutes',
--                         'all day'. Deliberately not a numeric minutes
--                         field — this project is modeling Fate-weight
--                         narrative capability, not a Hero-System-style
--                         crunchy resource system.
--      typical_effort   — qualitative, e.g. 'effortless', 'requires
--                         focused attention and exhausts character'.
--    Actual per-use runtime tracking (is this active right now, for how
--    much longer) is NOT modeled here — it rides on the existing
--    character.current_activity / activity_estimated_duration /
--    activity_duration_confidence / activity_renewable system already used
--    for things like a Regency dance commitment. typical_duration and
--    typical_effort are calibration hints for Pass 2 when it sets that
--    activity, not a new tracked resource.
--
-- Migration notes:
--   SQLite cannot ALTER a CHECK constraint or add/remove columns from an
--   XOR-style polymorphic set in place, so this recreates the table (same
--   approach as the v10->v11 game table migration). Per migration rule #1,
--   explicit column lists are used throughout — no SELECT *. Per migration
--   rule #3, only columns that existed in the v14 remote_capability table
--   are read from the old table; every new column gets an explicit NULL.
--
--   This table has no real-world data yet as of v14 (schema-only, shipped
--   one session ago, no seed file references it) — the copy step below is
--   included anyway for correctness and so this migration is a template for
--   what a populated-table recreation looks like, not because any existing
--   database is expected to have rows to preserve.
--
-- Usage:
--   sqlite3 <module>.db < schema/migrations/migrate_v14_to_v15.sql
-- =============================================================================

PRAGMA foreign_keys = OFF;   -- required while recreating the table


-- =============================================================================
-- Step 1: Create special_capability with the expanded shape
-- =============================================================================

CREATE TABLE special_capability (
    id                   INTEGER PRIMARY KEY,

    -- Owner: exactly one of these three (CHECK below).
    owner_character_id   INTEGER REFERENCES character(id),
    owner_item_id        INTEGER REFERENCES item(id),
    owner_location_id    INTEGER REFERENCES location(id),

    -- Target: exactly one of these four (CHECK below). target_description is
    -- a free-text filter rather than a fixed row — use when the target is a
    -- changing or unenumerable set ("any distant, real-world place") that
    -- Pass 2 should adjudicate fresh each time, not resolve to one row.
    target_character_id  INTEGER REFERENCES character(id),
    target_item_id       INTEGER REFERENCES item(id),
    target_location_id   INTEGER REFERENCES location(id),
    target_description   TEXT,

    -- 'can_send_to'     — owner actively transmits to target (consensual/agentive)
    -- 'can_detect_from' — owner passively reads target regardless of consent
    -- 'can_affect'      — owner changes a property of the target (temporary
    --                     environmental effects; not permanent transformation
    --                     or character-imposed curses — use character_aspect
    --                     + Fate compels for those instead)
    capability           TEXT    NOT NULL
        CHECK(capability IN ('can_send_to', 'can_detect_from', 'can_affect')),

    -- Open natural-language string, no fixed taxonomy — same convention as
    -- character_skill.skill_name and the capability_beliefs JSON domains.
    -- For can_send_to/can_detect_from: the sense/channel ('words',
    -- 'visual_perception', 'telepathic_impression'). For can_affect: the
    -- property being changed ('luminosity', 'buoyancy').
    sense                TEXT    NOT NULL,

    -- Required spatial relationship between owner and target. Open string;
    -- not purely a maximum range — 'touch' is a STRICTER requirement than
    -- ordinary co-location, not a looser one. NULL if not meaningful for
    -- this row. Examples: 'touch', 'same_location', 'unlimited'.
    distance             TEXT,

    -- Qualitative, free text — deliberately NOT a numeric minutes value.
    -- Examples: 'fleeting', 'a few minutes', 'all day', 'permanent'. NULL =
    -- instantaneous or not applicable. Runtime tracking of an active use
    -- rides on character.current_activity, not this field — this is a
    -- calibration hint for Pass 2, the same role duration-calibration notes
    -- play in the Pass 2 prompt for NPC activities.
    typical_duration     TEXT,

    -- Qualitative, free text — deliberately NOT a numeric cost/resource.
    -- Examples: 'effortless', 'requires concentration', 'requires focused
    -- attention and exhausts character'. NULL = not specified (Pass 2 should
    -- assume effortless absent other narrative signal).
    typical_effort       TEXT,

    created_at           TEXT    NOT NULL DEFAULT (datetime('now')),

    -- Exactly one owner reference must be set.
    CHECK (
        (owner_character_id IS NOT NULL) +
        (owner_item_id      IS NOT NULL) +
        (owner_location_id  IS NOT NULL) = 1
    ),

    -- Exactly one target reference must be set.
    CHECK (
        (target_character_id IS NOT NULL) +
        (target_item_id      IS NOT NULL) +
        (target_location_id  IS NOT NULL) +
        (target_description  IS NOT NULL) = 1
    )
);


-- =============================================================================
-- Step 2: Copy any existing rows from remote_capability
--
-- v14 columns were: id, owner_character_id, owner_item_id, target_id
-- (always a character reference), capability, sense, created_at. target_id
-- maps to target_character_id; every other new column gets an explicit NULL
-- (rule #3 — do not assume new columns exist in the source).
-- =============================================================================

INSERT INTO special_capability (
    id, owner_character_id, owner_item_id, owner_location_id,
    target_character_id, target_item_id, target_location_id, target_description,
    capability, sense, distance, typical_duration, typical_effort, created_at
)
SELECT
    id, owner_character_id, owner_item_id, NULL,
    target_id, NULL, NULL, NULL,
    capability, sense, NULL, NULL, NULL, created_at
FROM remote_capability;


-- =============================================================================
-- Step 3: Drop old table, indexes recreated against the new one below
-- =============================================================================

DROP TABLE remote_capability;

CREATE INDEX idx_special_capability_owner_char ON special_capability(owner_character_id);
CREATE INDEX idx_special_capability_owner_item ON special_capability(owner_item_id);
CREATE INDEX idx_special_capability_owner_loc  ON special_capability(owner_location_id);
CREATE INDEX idx_special_capability_target_char ON special_capability(target_character_id);
CREATE INDEX idx_special_capability_target_item ON special_capability(target_item_id);
CREATE INDEX idx_special_capability_target_loc  ON special_capability(target_location_id);


-- =============================================================================
-- Step 4: Re-enable foreign keys and record schema version
-- =============================================================================

PRAGMA foreign_keys = ON;

INSERT INTO schema_version (version, description)
VALUES (15, 'v15: rename remote_capability -> special_capability; owner/target gain location option; target gains free-text description filter; add can_affect capability; add distance, typical_duration, typical_effort (qualitative, not numeric)');
