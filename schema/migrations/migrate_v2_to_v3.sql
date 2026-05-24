-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v2 → v3
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Reason: Two additions motivated by observed play session behavior.
--
-- 1. Location connectivity table.
--    The engine had no explicit model of which locations are adjacent to one
--    another. Without it, the LLM could move characters to unreachable locations
--    (observed in first play session: Toulouse teleported to the basement via
--    prose-context drift). This table defines the physical connections between
--    locations and is used to validate all movement and to inform Pass 2 of
--    what is reachable from the current location.
--
-- 2. NPC wandering parameters on character.
--    NPCs were frozen at their seed locations indefinitely. Two new fields on
--    character support autonomous background movement: wander_range constrains
--    which locations an NPC may inhabit, and wander_probability is the per-turn
--    chance the engine moves them to an adjacent location within that range.
--    This is separate from LLM-driven NPC movement in Pass 2 outcomes, which
--    handles reactive movement (e.g. a human waking and entering the kitchen).
--
-- Usage (existing database at v2):
--   sqlite3 your_game.db < schema/migrations/migrate_v2_to_v3.sql
--
-- For a fresh install, run schema.sql then all migrations then seed.sql.
-- After applying this migration, also run the module-specific seed_v3.sql
-- to populate location connections and wander parameters for each module.
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- location_connection: physical adjacency between locations
-- -----------------------------------------------------------------------------

-- Each row represents a bidirectional connection between two locations.
-- By convention location_a_id < location_b_id; the application layer
-- normalises before insert. Queries must check both directions:
--   WHERE location_a_id = ? OR location_b_id = ?
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

    -- Note: bidirectional uniqueness enforced by convention (a < b) + constraint.
    UNIQUE(location_a_id, location_b_id),
    CHECK(location_a_id < location_b_id)
);

CREATE INDEX idx_location_connection_a ON location_connection(location_a_id);
CREATE INDEX idx_location_connection_b ON location_connection(location_b_id);

-- -----------------------------------------------------------------------------
-- character: NPC wandering parameters
-- -----------------------------------------------------------------------------

-- JSON array of location_ids this character may inhabit during autonomous
-- wandering. The engine will only move an NPC to a location within this range
-- AND adjacent to their current location. NULL means no autonomous movement.
-- Example: [1, 2, 3, 5, 8, 9, 10] for a human who uses the main and upper floors.
ALTER TABLE character ADD COLUMN wander_range TEXT DEFAULT NULL;

-- Per-turn probability that this character moves autonomously to an adjacent
-- location within their wander_range. Checked once per turn before player input.
-- 0.0 = character never moves on their own (default, includes player character).
-- Typical NPC values: 0.03–0.05 for sleeping humans, 0.15–0.25 for active cats.
ALTER TABLE character ADD COLUMN wander_probability REAL NOT NULL DEFAULT 0.0;

-- -----------------------------------------------------------------------------
-- Schema version
-- -----------------------------------------------------------------------------

INSERT INTO schema_version (version, description)
VALUES (3, 'Add location_connection table; add wander_range and wander_probability to character');
