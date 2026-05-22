-- =============================================================================
-- DAVE RPG Engine — Schema Migration: v5 → v6
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Reason: Add gender and pronoun fields to the character table to support
-- consistent pronoun use in Pass 3 prose rendering. Without explicit pronouns,
-- the LLM infers from names and species, which produces inconsistent results
-- (e.g. alternating he/she for the same NPC across turns).
--
-- The pronoun field is designed with localization in mind. Case labels use
-- English names as a language-neutral key (nominative, accusative, dative,
-- genitive, etc.); form values are in the module's target language. This
-- supports the three-case English system, the four-case German system,
-- and the six-to-seven case systems of Slavic languages without schema changes.
--
-- Both fields are nullable. NULL means no explicit value is set; the LLM
-- falls back to inference from name, species, and context (same as current
-- behavior). Authors only need to populate these when the default inference
-- would be wrong or inconsistent.
-- =============================================================================

PRAGMA foreign_keys = ON;

-- Add gender to character.
-- Stores a natural-language gender label: 'male', 'female', 'nonbinary',
-- 'neuter', or any author-defined value. Used as a hint to Pass 3; does
-- not affect adjudication logic.
ALTER TABLE character ADD COLUMN gender TEXT NULL;

-- Add pronouns to character.
-- Stores a JSON array of {"case": <case_name>, "form": <pronoun>} pairs
-- in the module's target language. The case label is always an English
-- keyword regardless of module language (language-neutral schema).
-- NULL = LLM infers from gender field or name/species context.
--
-- English she/her example:
--   [{"case":"nominative","form":"she"},
--    {"case":"accusative","form":"her"},
--    {"case":"genitive","form":"her"}]
--
-- German masculine example:
--   [{"case":"nominative","form":"er"},
--    {"case":"accusative","form":"ihn"},
--    {"case":"dative","form":"ihm"},
--    {"case":"genitive","form":"seiner"}]
--
-- Russian feminine example:
--   [{"case":"nominative","form":"она"},
--    {"case":"accusative","form":"её"},
--    {"case":"dative","form":"ей"},
--    {"case":"instrumental","form":"ею"},
--    {"case":"prepositional","form":"ней"},
--    {"case":"genitive","form":"её"}]
--
-- Future multi-language extension: the array can be wrapped in a dict keyed
-- by locale code without breaking existing single-language data.
ALTER TABLE character ADD COLUMN pronouns TEXT NULL;

-- Record this migration in the schema version history.
INSERT INTO schema_version (version, description)
VALUES (6, 'Add gender and pronouns fields to character table for consistent Pass 3 prose rendering');
