-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v3 → v4
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Reason: Visited location tracking for multi-step movement.
--
--   Quick-move pathfinding (Option C) restricts destination choices to locations
--   the player character has previously visited. Without a record of visits, the
--   engine cannot enforce this restriction and cannot rule out movement to
--   locations the character has never been. This table records each character's
--   first visit to each location so the engine can validate quick-move targets
--   and inform Pass 2 of which locations are known to the character.
--
--   Note: The I Am a Cat module seed data (seed_v4.sql) pre-populates visited
--   locations for Toulouse, who knows the whole house, while leaving the player's
--   knowledge to accumulate through actual play.
--
-- Usage (existing database at v3):
--   sqlite3 your_game.db < schema/migrations/migrate_v3_to_v4.sql
--
-- For a fresh install, run schema.sql (which incorporates all fields through
-- the current version) then the module seed file. Migrations are only needed
-- when upgrading an existing database.
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- character_visited_location: record of locations a character has entered
-- -----------------------------------------------------------------------------

CREATE TABLE character_visited_location (
    id              INTEGER PRIMARY KEY,

    -- The character who visited this location.
    character_id    INTEGER NOT NULL REFERENCES character(id),

    -- The location that was visited.
    location_id     INTEGER NOT NULL REFERENCES location(id),

    -- When the character first entered this location. Used for ordering and
    -- future analytics; not used for gameplay logic.
    first_visited_at DATETIME NOT NULL DEFAULT (datetime('now')),

    -- Each (character, location) pair is unique; subsequent visits do not
    -- create new rows.
    UNIQUE(character_id, location_id)
);

CREATE INDEX idx_visited_character ON character_visited_location(character_id);

-- -----------------------------------------------------------------------------
-- Schema version
-- -----------------------------------------------------------------------------

INSERT INTO schema_version (version, description)
VALUES (4, 'Add character_visited_location table for quick-move pathfinding');
