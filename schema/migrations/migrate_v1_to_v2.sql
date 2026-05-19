-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v1 → v2
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Reason: Two additions motivated by the I Am a Cat module.
--
-- 1. Involuntary event support on internal_state.
--    Some internal states can trigger events the character does not control —
--    hairballs being the first example. These are probabilistic rather than
--    threshold-based: the engine rolls against a probability computed from the
--    current state value on each relevant turn. Grooming actions (self or
--    other) raise hairball_pressure, increasing the per-turn probability.
--    This mechanic is general and will apply to other involuntary behaviors
--    in future modules.
--
-- 2. Intrinsic motivation on character_skill.
--    Some skills are exercised for their own sake — hobbies, pleasures, things
--    a character does because they enjoy doing them, not merely as a means to
--    an end. This float distinguishes those from purely instrumental skills
--    and allows the adjudication pass to weight a character's likelihood of
--    attempting a skill spontaneously, not just in response to a prompt.
--
-- Usage (existing database at v1):
--   sqlite3 your_game.db < schema/migrations/migrate_v1_to_v2.sql
--
-- For a fresh install, run schema.sql then seed.sql — the seed already
-- includes all v2 fields.
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- internal_state: involuntary event support
-- -----------------------------------------------------------------------------

-- Whether this state can trigger an involuntary event when sufficiently high.
-- 0 = state informs adjudication only (default behavior)
-- 1 = state can fire an event the character does not initiate or control
ALTER TABLE internal_state ADD COLUMN is_involuntary INTEGER NOT NULL DEFAULT 0;

-- How the trigger fires.
-- 'threshold'    = event fires when value crosses involuntary_trigger_param
-- 'probabilistic' = per-turn probability is computed as (value * involuntary_trigger_param),
--                   capped at a reasonable maximum by the engine
-- NULL when is_involuntary = 0
ALTER TABLE internal_state ADD COLUMN involuntary_trigger_type TEXT DEFAULT NULL;

-- Trigger parameter. Interpretation depends on involuntary_trigger_type:
--   threshold:    the value at which the event fires (e.g. 0.85)
--   probabilistic: scale factor applied to current value to get per-turn probability
--                  (e.g. 0.15 means at value=1.0 there is a 15% chance per turn)
ALTER TABLE internal_state ADD COLUMN involuntary_trigger_param REAL DEFAULT NULL;

-- Description of what happens when the event fires, written as an instruction
-- to the adjudication layer. Should specify: the event itself, its consequences,
-- and any actions that raise the state value.
ALTER TABLE internal_state ADD COLUMN involuntary_event_description TEXT DEFAULT NULL;

-- -----------------------------------------------------------------------------
-- character_skill: intrinsic motivation
-- -----------------------------------------------------------------------------

-- How much this character enjoys exercising this skill for its own sake,
-- independent of any external goal it serves.
-- NULL  = no intrinsic motivation recorded (skill is purely instrumental)
-- 0.0   = the character actively dislikes this skill but may still use it
-- 0.5   = mild preference for using this skill when it is relevant
-- 1.0   = deep hobby; the character will seek opportunities to exercise this skill
--          spontaneously, without external prompting
-- The adjudication pass uses this to estimate the likelihood that a character
-- attempts a skill-aligned action on their own initiative.
ALTER TABLE character_skill ADD COLUMN intrinsic_motivation REAL DEFAULT NULL;

-- -----------------------------------------------------------------------------
-- Schema version
-- -----------------------------------------------------------------------------

INSERT INTO schema_version (version, description)
VALUES (2, 'Add involuntary event support to internal_state; add intrinsic_motivation to character_skill');
