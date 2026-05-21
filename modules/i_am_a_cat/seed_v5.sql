-- =============================================================================
-- DAVE RPG Engine — Module: I Am a Cat
-- Seed data for schema v5 additions
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Applies to: modules/i_am_a_cat/i_am_a_cat.db
--   (after migrate_v4_to_v5.sql has been applied)
--
-- Contents:
--   1. game_instance record for a fresh playthrough.
--      start_time_minutes = 180  (3:00 AM)
--      status set to 'ready' as the final step.
--
--   2. passive_rate_per_minute values on existing internal_state rows.
--      Sets background drift rates for time-varying physiological states.
--      All rates are starting estimates; tune during play.
--
-- To reset the game to its opening state, re-run this file:
--   sqlite3 modules/i_am_a_cat/i_am_a_cat.db < modules/i_am_a_cat/seed_v5.sql
-- This deletes the existing instance and creates a fresh one. Other state
-- tables (character locations, internal state values) must be reset separately
-- until the full module/instance split (v6) is implemented.
--
-- Character ID reference:
--   1 = Toulouse (player cat)
--   2 = Spook (NPC cat)
--   3 = The mama (human)
--   4 = Guy (human)
--   5 = Lillis (cockatiel)
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- 1. Game instance
-- -----------------------------------------------------------------------------

-- Remove any existing instance for game 1 so this file is idempotent.
DELETE FROM game_instance WHERE game_id = 1;

INSERT INTO game_instance (
    game_id,
    status,
    start_time_minutes,
    current_time_minutes,
    premise_modifier
) VALUES (
    1,
    'pending',       -- will be set to 'ready' at the end of this file
    180,             -- 3:00 AM: the scenario's canonical start time
    180,             -- current time = start time for a fresh instance
    NULL             -- no "What if..." modifier
);

-- -----------------------------------------------------------------------------
-- 2. Passive drift rates on internal_state
-- -----------------------------------------------------------------------------

-- Toulouse — boredom
-- Accumulates slowly when the player is inactive. Pass 2 reduces it when
-- interesting things happen. If the player does nothing engaging, boredom
-- drifts upward at ~0.12 per hour. Starting value: 0.0; failure at 1.0.
UPDATE internal_state
SET passive_rate_per_minute = 0.002
WHERE character_id = 1 AND state_name = 'boredom';

-- Toulouse — hunger
-- Slow background accumulation. Current value ~0.45; reaches ~0.70 after
-- roughly 2 hours of play. Guy feeding the cats (morning routine) would
-- reset this via Pass 2 internal_state_deltas.
UPDATE internal_state
SET passive_rate_per_minute = 0.002
WHERE character_id = 1 AND state_name = 'hunger';

-- Toulouse — hairball_pressure
-- Very slow background drift; most accumulation comes from grooming events
-- (+0.04 to +0.10 each via Pass 2). Passive rate represents residual
-- pressure that builds even without explicit grooming actions.
UPDATE internal_state
SET passive_rate_per_minute = 0.0003
WHERE character_id = 1 AND state_name = 'hairball_pressure';

-- Guy — sleepiness (sleep depth)
-- For sleeping characters, sleepiness represents depth of sleep: high = deep,
-- low = light/waking. Guy starts deeply asleep (0.88) and lightens naturally
-- toward morning. Rate of -0.006/min means:
--   0.88 → ~0.35 (light sleep threshold) around 88 min in (~4:28 AM)
--   0.88 → 0.00 (fully awake) around 147 min in (~5:27 AM)
-- These thresholds are starting estimates. Pass 2 can accelerate decay via
-- disturbance events (persistent meowing, loud noises, etc.).
UPDATE internal_state
SET passive_rate_per_minute = -0.006
WHERE character_id = 4 AND state_name = 'sleepiness';

-- The mama — sleepiness (sleep depth)
-- Lighter sleeper than Guy; started the session already at 0.22 (recently
-- fell asleep after reading late). Rate of -0.004/min means:
--   0.22 → 0.00 (could wake) around 55 min in (~3:55 AM)
-- In practice she may cycle — Pass 2 might raise her sleepiness again if
-- she rolls over and settles back. The passive rate handles the baseline
-- drift; Pass 2 handles context-sensitive adjustments.
UPDATE internal_state
SET passive_rate_per_minute = -0.004
WHERE character_id = 3 AND state_name = 'sleepiness';

-- -----------------------------------------------------------------------------
-- Confirm instance is fully initialised — set status to 'ready'.
-- This must be the last statement. The engine will not start a session
-- unless status is 'ready' or 'active'.
-- -----------------------------------------------------------------------------

UPDATE game_instance SET status = 'ready' WHERE game_id = 1;
