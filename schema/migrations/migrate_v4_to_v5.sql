-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v4 → v5
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Reason: Per-playthrough instance tracking and generalized passive state drift.
--
-- 1. game_instance table.
--    The current schema has no concept of a playthrough instance — the game
--    table holds module definition and there is only ever one set of live
--    state. This migration introduces a thin instance table that holds
--    per-playthrough metadata, beginning the module/instance architectural
--    split. The game table remains pure module definition; other state tables
--    (character, internal_state, etc.) are unchanged and implicitly belong to
--    the one active instance. Full instance support (instance_id on all state
--    tables) is deferred to v6.
--
--    Fields:
--      game_id              — the module this instance belongs to
--      status               — lifecycle: pending → ready → active → complete
--      start_time_minutes   — module's canonical opening time (minutes past
--                             midnight); copied from module definition at
--                             instance creation; used to reset current_time
--      current_time_minutes — live in-game clock; starts equal to
--                             start_time_minutes; incremented each turn by
--                             Pass 2's elapsed_minutes output
--      premise_modifier     — optional "What if..." player-entered premise
--                             (null when feature is not in use)
--
--    The seed process creates the instance record and sets status to 'ready'
--    as its final step. The engine refuses to start if status is 'pending'.
--
--    Note: start_time_minutes and current_time_minutes have no natural DEFAULT
--    and are NOT NULL. SQLite requires a DEFAULT for NOT NULL ALTER TABLE
--    additions, so a sentinel value of -1 is used here. The seed must set
--    correct values; -1 is detectable as unseeded and the engine rejects it.
--
-- 2. passive_rate_per_minute on internal_state.
--    A signed float per state row controlling background drift per elapsed
--    in-game minute. Positive = accumulates; negative = decays. NULL = no
--    passive drift; state is event-driven only. Covers all physiological
--    states: sleepiness, hunger, thirst, thermal discomfort, air depletion,
--    etc. Adding a new time-varying state requires only seeding the rate —
--    no engine code change. Activity-dependent states (restlessness,
--    impatience) should use NULL and be managed entirely by Pass 2.
--
-- Usage (existing database at v4):
--   sqlite3 your_game.db < schema/migrations/migrate_v4_to_v5.sql
--
-- For a fresh install, run schema.sql then all migrations in order, then the
-- module seed files.
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- game_instance: per-playthrough metadata
-- -----------------------------------------------------------------------------

CREATE TABLE game_instance (
    id      INTEGER PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES game(id),

    -- Lifecycle state. The engine checks this before starting a session.
    -- 'pending'  = instance not yet fully initialised; engine will not start.
    -- 'ready'    = all required values populated; ready to play.
    -- 'active'   = session currently in progress.
    -- 'complete' = session ended (end condition reached).
    -- The seed process must set this to 'ready' as its final statement.
    status  TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'ready', 'active', 'complete')),

    -- The module's canonical opening time in minutes past midnight.
    -- Copied from the module definition at instance creation; never updated
    -- during play. Used to reset the clock on a new game:
    --   UPDATE game_instance SET current_time_minutes = start_time_minutes
    -- Sentinel -1 indicates unseeded; the engine rejects this value.
    start_time_minutes   INTEGER NOT NULL DEFAULT -1,

    -- Live in-game clock in minutes past midnight.
    -- Starts equal to start_time_minutes; incremented each turn by the
    -- elapsed_minutes value returned by Pass 2.
    -- Time label derived at runtime:
    --   hour   = (current_time_minutes // 60) % 24
    --   minute = current_time_minutes % 60
    -- Sentinel -1 indicates unseeded; the engine rejects this value.
    current_time_minutes INTEGER NOT NULL DEFAULT -1,

    -- Optional "What if..." premise modifier entered by the player at session
    -- start. NULL when the feature is not active. When present, included in
    -- every context packet as an addendum to the module premise. See
    -- docs/future_features.md §6 for full design.
    premise_modifier TEXT DEFAULT NULL,

    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_game_instance_game ON game_instance(game_id);

-- -----------------------------------------------------------------------------
-- internal_state: passive drift rate
-- -----------------------------------------------------------------------------

-- Rate of passive change per elapsed in-game minute.
-- Positive = accumulates toward 1.0; negative = decays toward 0.0.
-- Applied by the engine as: clamp(value + rate * elapsed_minutes, 0.0, 1.0)
-- after each turn's clock advance, before Pass 3 runs.
-- NULL = no passive drift; state changes only via Pass 2 outcome JSON.
-- Activity-dependent states (restlessness, impatience) should use NULL and
-- be managed entirely by Pass 2.
ALTER TABLE internal_state ADD COLUMN passive_rate_per_minute REAL DEFAULT NULL;

-- -----------------------------------------------------------------------------
-- Schema version
-- -----------------------------------------------------------------------------

INSERT INTO schema_version (version, description)
VALUES (5, 'Add game_instance table for per-playthrough state; add passive_rate_per_minute to internal_state');
