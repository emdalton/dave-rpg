-- =============================================================================
-- DAVE RPG Engine — Instance Reset: The Hidden Hostel
-- modules/hidden_hostel/reset_instance.sql
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Resets all mutable instance state to the canonical starting values from
-- seed.sql WITHOUT rebuilding from scratch. Run this between play sessions
-- to start fresh without dropping and recreating the database.
--
-- What this resets:
--   - game_instance: clock and status
--   - character: location, emotional_state, maslow_tier, pending_intent,
--                current_activity and all activity fields
--   - internal_state: value (rates are stable; not reset)
--   - character_attitude: all attitude values
--   - character_faction_reputation: all reputation values and notes
--   - character_visited_location: trimmed to seeded set
--   - location_detail: lazily generated details removed; seeded detail restored
--   - action_log: cleared entirely
--
-- What this does NOT touch (stable world data):
--   - game record
--   - location records and location_connection records
--   - character OCEAN traits, goals, skills, pronouns, descriptions,
--     voice parameters, wander_range, wander_probability
--   - faction records
--
-- Usage:
--   sqlite3 modules/hidden_hostel/hidden_hostel.db < modules/hidden_hostel/reset_instance.sql
-- =============================================================================

PRAGMA foreign_keys = ON;


-- =============================================================================
-- GAME INSTANCE: reset clock and status
-- =============================================================================

UPDATE game_instance
SET status               = 'ready',
    current_time_minutes = 1200,   -- 8:00 PM
    updated_at           = datetime('now')
WHERE id = 1 AND game_id = 1;


-- =============================================================================
-- CHARACTERS: reset mutable fields to starting values
-- =============================================================================

-- The Traveller (id=1)
UPDATE character
SET current_location_id          = 1,      -- Common Room
    emotional_state              = 'curious',
    maslow_tier                  = 'belonging',
    pending_intent               = NULL,
    current_activity             = NULL,
    activity_started_at          = NULL,
    activity_estimated_duration  = NULL,
    activity_duration_confidence = NULL,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 1;

-- Marta (id=2)
UPDATE character
SET current_location_id          = 2,      -- Kitchen
    emotional_state              = 'focused',
    maslow_tier                  = 'esteem',
    pending_intent               = NULL,
    current_activity             = 'preparing the evening meal',
    activity_started_at          = 1140,   -- 7:00 PM
    activity_estimated_duration  = 90,
    activity_duration_confidence = 0.72,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 2;

-- The Wanderer (id=3)
UPDATE character
SET current_location_id          = 1,      -- Common Room
    emotional_state              = 'content',
    maslow_tier                  = 'self_actualization',
    pending_intent               = NULL,
    current_activity             = NULL,
    activity_started_at          = NULL,
    activity_estimated_duration  = NULL,
    activity_duration_confidence = NULL,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 3;

-- The Scholar (id=4)
UPDATE character
SET current_location_id          = 4,      -- Room A
    emotional_state              = 'guarded',
    maslow_tier                  = 'safety',
    pending_intent               = 'seeking a specific text rumored to exist somewhere in the hostel; will approach any guest who seems knowledgeable',
    current_activity             = NULL,
    activity_started_at          = NULL,
    activity_estimated_duration  = NULL,
    activity_duration_confidence = NULL,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 4;

-- The Old Soldier (id=5)
UPDATE character
SET current_location_id          = 3,      -- Upper Corridor
    emotional_state              = 'vigilant',
    maslow_tier                  = 'safety',
    pending_intent               = NULL,
    current_activity             = 'sharpening a blade, seated against the corridor wall with sight lines to both doors',
    activity_started_at          = 1170,   -- 7:30 PM
    activity_estimated_duration  = 60,
    activity_duration_confidence = 0.80,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 5;

-- Gin-chan (id=6)
UPDATE character
SET current_location_id          = 1,      -- Common Room
    emotional_state              = 'drowsy',
    maslow_tier                  = 'self_actualization',
    pending_intent               = NULL,
    current_activity             = NULL,
    activity_started_at          = NULL,
    activity_estimated_duration  = NULL,
    activity_duration_confidence = NULL,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 6;


-- =============================================================================
-- INTERNAL STATES: reset values to starting levels
-- passive_rate_per_minute is stable configuration; not reset here.
-- =============================================================================

UPDATE internal_state SET value = 0.40, updated_at = datetime('now')
WHERE character_id = 1 AND state_name = 'curiosity';

UPDATE internal_state SET value = 0.55, updated_at = datetime('now')
WHERE character_id = 2 AND state_name = 'fatigue';

UPDATE internal_state SET value = 0.72, updated_at = datetime('now')
WHERE character_id = 6 AND state_name = 'sleepiness';


-- =============================================================================
-- CHARACTER ATTITUDES: reset all to seeded values
-- =============================================================================

DELETE FROM character_attitude
WHERE character_id IN (1, 2, 3, 4, 5, 6)
   OR target_id    IN (1, 2, 3, 4, 5, 6);

-- Attitudes toward The Traveller
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    (3, 1,  0.65, 'surface'),
    (4, 1,  0.60, 'surface'),
    (2, 1,  0.35, 'surface'),
    (5, 1, -0.30, 'surface'),
    (6, 1,  0.50, 'surface');

-- Traveller's attitudes
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    (1, 2,  0.40, 'surface');

-- NPC-to-NPC attitudes
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    (5, 3, -0.40, 'surface');


-- =============================================================================
-- FACTION REPUTATIONS: reset to seeded values
-- =============================================================================

DELETE FROM character_faction_reputation
WHERE character_id IN (1, 2, 3, 4, 5, 6);

INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES
    (2, 1, 0.90,
     'Founding keeper of the Hidden Hostel. Marta''s standing with hosts_of_the_hostel is unquestioned.'),
    (1, 1, 0.40,
     'Newly arrived traveller. Guest status acknowledged; no significant actions taken yet.');


-- =============================================================================
-- CHARACTER VISITED LOCATIONS: reset to seeded set
-- =============================================================================

DELETE FROM character_visited_location
WHERE character_id IN (1, 2, 3, 4, 5, 6);

INSERT INTO character_visited_location (character_id, location_id)
VALUES
    (1, 1),
    (2, 1), (2, 2),
    (3, 1), (3, 2), (3, 3),
    (4, 3), (4, 4),
    (5, 3),
    (6, 1);


-- =============================================================================
-- LOCATION DETAILS: remove lazily generated details; restore seeded detail
-- =============================================================================

-- Remove any details generated during play for locations 2-5
DELETE FROM location_detail WHERE location_id IN (2, 3, 4, 5);

-- Restore the pre-seeded Common Room detail if it was invalidated or removed
DELETE FROM location_detail WHERE location_id = 1;

INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (
    1,
    'The central hearth is surrounded by mismatched chairs — carved oak, cushioned velvet, and what appears to be a throne reduced by time and use to something merely comfortable. The fire burns steadily, as it always does.',
    1,
    'fire goes out or is significantly altered'
);


-- =============================================================================
-- ACTION LOG: clear all entries for this game
-- =============================================================================

DELETE FROM action_log WHERE game_id = 1;
