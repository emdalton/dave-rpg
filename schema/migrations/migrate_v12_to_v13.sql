-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v12 → v13
-- schema/migrations/migrate_v12_to_v13.sql
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Add prose column to action_log for Pass 3 anti-repetition context
-- -----------------------------------------------------------------------
--
-- action_log previously stored the Pass 2 narrative_beat alongside the
-- structured action_json, but never persisted the Pass 3 prose output.
-- This meant Pass 3 had no access to recent rendered prose and could not
-- avoid repeating the same imagery, metaphors, or internal-state descriptors
-- across consecutive turns.
--
-- The new `prose` column stores the rendered player-facing prose produced by
-- Pass 3 for each turn. It is NULL at row creation time and filled in after
-- the LLM call completes (via update_action_log_prose() in db.py). The
-- build_pass3_packet() function in context.py fetches the last 2–3 non-null
-- prose values and includes them in the Pass 3 context packet so the renderer
-- can avoid reusing the same language.
--
-- Initial motivation: Mistral Small 3.2 repeatedly used the phrase "curiosity
-- hums/prickles beneath your skin" in every Meryton Assembly turn because the
-- curiosity internal state stayed high throughout and the model had no signal
-- that it had already used that imagery.
--
-- Migration notes:
--   Simple ADD COLUMN — no table recreation needed. The column is nullable
--   so existing rows (which have no prose) are valid at NULL.
--   Per migration rule #2, IF NOT EXISTS is omitted; assumes DB is at v12.
--
-- Usage:
--   sqlite3 <module>.db < schema/migrations/migrate_v12_to_v13.sql
-- =============================================================================

ALTER TABLE action_log
ADD COLUMN prose TEXT;
-- prose: rendered player-facing output from Pass 3. NULL until written after
-- the LLM call. Fetched by get_recent_prose() for anti-repetition context.

INSERT INTO schema_version (version, description)
VALUES (13, 'v13: add prose column to action_log for Pass 3 anti-repetition context');
