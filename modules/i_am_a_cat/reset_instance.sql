-- =============================================================================
-- DAVE RPG Engine — Module: I Am a Cat
-- Instance reset script
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- PURPOSE: Reset all per-playthrough state to the canonical 3:00 AM starting
-- values, discarding any accumulated test or play session state. Run this
-- before starting a fresh play session.
--
-- This script does NOT touch module-definition data (game params, location
-- descriptions, location_connection, static character definitions, items).
-- It resets only mutable playthrough state: character positions, emotional
-- states, internal state values, the game instance clock, and the action log.
--
-- When the module/instance architectural split is implemented (v7), this will
-- become seed_instance.sql and re-running it will create a new game_instance
-- row rather than mutating the existing one.
--
-- Usage:
--   python3 -c "
--   import sqlite3
--   db = sqlite3.connect('modules/i_am_a_cat/i_am_a_cat.db')
--   db.executescript(open('modules/i_am_a_cat/reset_instance.sql').read())
--   db.commit(); db.close(); print('Reset complete.')
--   "
-- =============================================================================

PRAGMA foreign_keys = ON;

-- =============================================================================
-- 1. Game instance — reset clock to 3:00 AM (180 min); status back to ready
-- =============================================================================

UPDATE game_instance
SET current_time_minutes = 180,
    status               = 'ready'
WHERE game_id = 1;

-- =============================================================================
-- 2. Character locations and emotional states
-- =============================================================================

-- Toulouse (id=1): Living Room; restless at 3am
UPDATE character
SET current_location_id = 1,
    emotional_state     = 'restless'
WHERE id = 1;

-- Spook (id=2): Living Room; playful
UPDATE character
SET current_location_id = 1,
    emotional_state     = 'playful'
WHERE id = 2;

-- Mama (id=3): Bedroom (loc 10); lightly asleep
UPDATE character
SET current_location_id = 10,
    emotional_state     = 'lightly_asleep'
WHERE id = 3;

-- Guy (id=4): Bedroom (loc 10); deeply asleep
UPDATE character
SET current_location_id = 10,
    emotional_state     = 'deeply_asleep'
WHERE id = 4;

-- Lillis (id=5): Basement Main Room (loc 6); asleep
UPDATE character
SET current_location_id = 6,
    emotional_state     = 'asleep'
WHERE id = 5;

-- =============================================================================
-- 3. Internal state values — reset to starting calibration values
-- =============================================================================

-- Toulouse's states
UPDATE internal_state SET value = 0.00 WHERE character_id = 1 AND state_name = 'boredom';
UPDATE internal_state SET value = 0.05 WHERE character_id = 1 AND state_name = 'hairball_pressure';
UPDATE internal_state SET value = 0.45 WHERE character_id = 1 AND state_name = 'hunger';

-- Guy's sleepiness (0.88 = deeply asleep; passive rate -0.006/min → wakes ~5:27 AM)
UPDATE internal_state SET value = 0.88 WHERE character_id = 4 AND state_name = 'sleepiness';

-- Mama's sleepiness (0.22 = lightly asleep; passive rate -0.004/min → wakes ~3:55 AM)
UPDATE internal_state SET value = 0.22 WHERE character_id = 3 AND state_name = 'sleepiness';

-- Spook's states
UPDATE internal_state SET value = 0.03 WHERE character_id = 2 AND state_name = 'boredom';
UPDATE internal_state SET value = 0.31 WHERE character_id = 2 AND state_name = 'hairball_pressure';
UPDATE internal_state SET value = 0.38 WHERE character_id = 2 AND state_name = 'hunger';

-- Clear any transient states that may have been set during play
-- (mildly_frustrated, etc.) — set to 0 if they exist; no-op if they don't
UPDATE internal_state SET value = 0.00
WHERE character_id = 1
  AND state_name NOT IN ('boredom', 'hairball_pressure', 'hunger');

-- =============================================================================
-- 4. Clear the action log
-- Removes all turn history so the LLM context starts clean.
-- Comment this out if you want to preserve history for debugging.
-- =============================================================================

DELETE FROM action_log WHERE game_id = 1;

-- =============================================================================
-- 5. Reset visited locations for Toulouse
-- Clears pathfinding history so the engine doesn't remember prior routes.
-- =============================================================================

DELETE FROM character_visited_location WHERE character_id = 1;

-- Insert the starting location as already visited so pathfinding works
-- from turn 1 without needing a dedicated "discover starting room" step.
INSERT OR IGNORE INTO character_visited_location (character_id, location_id)
VALUES (1, 1);  -- Toulouse starts in Living Room
