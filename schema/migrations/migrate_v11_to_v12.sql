-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v11 → v12
-- schema/migrations/migrate_v11_to_v12.sql
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Add module_flags JSON column to the game table
-- -----------------------------------------------------------------------
--
-- module_flags is a general-purpose JSON object for per-module engine
-- configuration that does not warrant a dedicated schema column. The
-- game table already carries several such JSON columns (speech_filter,
-- cultural_norms, internal_state_display); module_flags is the
-- engine-facing counterpart for feature flags and mode-specific prompts.
--
-- Initial consumers:
--
--   Green Room Mode (player_definition_mode = 'green_room', issue #59):
--     character_creation_prompt  — the out-of-character framing shown to the
--       player before the opening scene begins. Should establish who they are
--       and invite them to describe who they have become.
--       Example (Return to Wonderland):
--         "You are Alice. As a child, you believed you could travel to other
--          worlds, where you had many adventures... Now you are a young woman.
--          What have you been doing in the meantime? Who have you become?"
--     character_creation_hint    — optional, shorter cue shown below the prompt
--       to remind the player what Fate Core aspects are (for players who are
--       not familiar with the system).
--       Example: "Think of a High Concept (who you are in a phrase), a Trouble
--         (your biggest personal complication), and up to three additional
--         Aspects (relationships, notable skills, signature possessions, etc.)."
--
-- Future consumers (not yet implemented):
--   illustrated_mode_style_prompt, tts_voice, debug_flags, etc.
--
-- Migration notes:
--   This is a simple ADD COLUMN — no table recreation is needed because
--   the new column is nullable-equivalent (NOT NULL with DEFAULT '{}').
--   Per migration rule #2, IF NOT EXISTS is omitted; this migration assumes
--   the DB is at exactly v11.
--
-- Usage:
--   sqlite3 <module>.db < schema/migrations/migrate_v11_to_v12.sql
-- =============================================================================

ALTER TABLE game
ADD COLUMN module_flags TEXT NOT NULL DEFAULT '{}';

INSERT INTO schema_version (version, description)
VALUES (12, 'v12: add module_flags JSON column to game table for Green Room prompts and future feature config');
