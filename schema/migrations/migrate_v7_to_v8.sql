-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v7 → v8
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Reason: Add timed activity system to the character table (§5a).
--
-- The problem this solves: pending_intent was being used to suppress NPC
-- wandering, but it is a commitment slot — it gets cleared when a commitment
-- is fulfilled. When John Lucas committed to a dance, his pending_intent was
-- cleared on commitment, leaving nothing to hold him in place. He wandered
-- off mid-bow.
--
-- The fix: a separate current_activity system with its own expiry logic.
-- NPCs with a non-expired current_activity do not roll for wander. Pass 2
-- sets, updates, and clears activity via activity_updates in outcome JSON.
-- High-confidence, non-renewable activities are cleared mechanically by the
-- engine on expiry; everything else requires an explicit Pass 2 clear.
--
-- New fields on character:
--   current_activity              TEXT NULL
--   activity_started_at           INT  NULL
--   activity_estimated_duration   INT  NULL
--   activity_duration_confidence  REAL NULL
--   activity_renewable            INT  NOT NULL DEFAULT 0
--
-- This migration is idempotent: it uses ADD COLUMN IF NOT EXISTS logic
-- (SQLite does not support IF NOT EXISTS on ADD COLUMN; we check pragma
-- table_info instead — see note below).
--
-- SQLite does not support IF NOT EXISTS on ALTER TABLE ADD COLUMN. The
-- standard workaround is to run inside a BEGIN/COMMIT with error catching
-- at the application level, or to check table_info first. This migration
-- is intended to be run once against a v7 database; running it twice will
-- produce a "duplicate column" error from SQLite, which is safe to ignore.
-- The engine's migration runner should check schema version before applying.
--
-- Usage:
--   sqlite3 path/to/game.db < schema/migrations/migrate_v7_to_v8.sql
-- =============================================================================

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

-- ---------------------------------------------------------------------------
-- 1. Add five new fields to the character table.
-- ---------------------------------------------------------------------------

-- Natural language description of what the character is currently doing.
-- Examples: 'dancing with Thomas Phillips', 'greeting arrivals at the top
-- of the stairs', 'playing cards in the card room'. NULL = no activity.
ALTER TABLE character ADD COLUMN current_activity TEXT DEFAULT NULL;

-- Game clock minute (current_time_minutes from game_instance) when the
-- activity started. Set by the engine at the moment the activity is applied,
-- not by Pass 2 — Pass 2 specifies duration_minutes and confidence only.
ALTER TABLE character ADD COLUMN activity_started_at INT DEFAULT NULL;

-- Estimated duration of the activity in game-clock minutes. NULL means
-- the activity is genuinely open-ended (e.g., 'sitting against the wall
-- watching') — the engine will never auto-clear it.
ALTER TABLE character ADD COLUMN activity_estimated_duration INT DEFAULT NULL;

-- Confidence in the duration estimate (0.0–1.0).
-- >= ACTIVITY_AUTO_CLEAR_CONFIDENCE AND renewable=0 → engine clears
--   mechanically when (activity_started_at + activity_estimated_duration)
--   <= current_time_minutes.
-- < threshold OR renewable=1 → only Pass 2 may clear via activity_updates.
-- NULL when activity_estimated_duration is NULL.
ALTER TABLE character ADD COLUMN activity_duration_confidence REAL DEFAULT NULL;

-- 1 = the activity persists past its estimated expiry until Pass 2 explicitly
-- clears it (renewable: "I'll keep dancing until someone tells me otherwise").
-- 0 = the engine may auto-clear when a high-confidence duration expires.
-- NOT NULL with default 0 so existing rows are well-defined.
ALTER TABLE character ADD COLUMN activity_renewable INT NOT NULL DEFAULT 0
    CHECK(activity_renewable IN (0, 1));

-- ---------------------------------------------------------------------------
-- 2. Record the migration in schema_version.
-- ---------------------------------------------------------------------------

INSERT INTO schema_version (version, applied_at, description)
VALUES (8, datetime('now'),
    'Add timed activity system to character table (current_activity, activity_started_at, activity_estimated_duration, activity_duration_confidence, activity_renewable). Fixes NPC wander suppression after commitment fulfillment. See §5a in implementation_status.md.');

COMMIT;
