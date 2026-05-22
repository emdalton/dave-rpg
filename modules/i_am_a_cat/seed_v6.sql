-- =============================================================================
-- DAVE RPG Engine — Module: I Am a Cat
-- Seed data for schema v6 additions
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Applies to: modules/i_am_a_cat/i_am_a_cat.db (after migrate_v5_to_v6.sql)
--
-- Contents:
--   1. Gender and pronouns for all five characters
--
-- Character reference:
--   1 = Toulouse  (player; male cat)
--   2 = Spook     (NPC; female cat)
--   3 = Mama      (NPC; female human)
--   4 = Guy       (NPC; male human)
--   5 = Lillis    (NPC; female bird — Senegal parrot)
--
-- Pronoun format: JSON array of {"case": <english_case_label>, "form": <english_pronoun>}
-- English uses three third-person pronoun cases:
--   nominative  — subject position ("he/she/they went")
--   accusative  — object position ("saw him/her/them")
--   genitive    — possessive ("his/her/their tail")
-- =============================================================================

PRAGMA foreign_keys = ON;

-- Toulouse: male cat, he/him/his
UPDATE character
SET gender   = 'male',
    pronouns = '[{"case":"nominative","form":"he"},
                 {"case":"accusative","form":"him"},
                 {"case":"genitive","form":"his"}]'
WHERE id = 1;

-- Spook: male cat, he/him/his
UPDATE character
SET gender   = 'male',
    pronouns = '[{"case":"nominative","form":"he"},
                 {"case":"accusative","form":"him"},
                 {"case":"genitive","form":"his"}]'
WHERE id = 2;

-- Mama: female human, she/her/her
UPDATE character
SET gender   = 'female',
    pronouns = '[{"case":"nominative","form":"she"},
                 {"case":"accusative","form":"her"},
                 {"case":"genitive","form":"her"}]'
WHERE id = 3;

-- Guy: male human, he/him/his
UPDATE character
SET gender   = 'male',
    pronouns = '[{"case":"nominative","form":"he"},
                 {"case":"accusative","form":"him"},
                 {"case":"genitive","form":"his"}]'
WHERE id = 4;

-- Lillis: female Senegal parrot, she/her/her
-- Note: grammatical gender of birds is not culturally standardized in English;
-- a named companion animal with a known sex is conventionally referred to with
-- personal pronouns. Lillis is female.
UPDATE character
SET gender   = 'female',
    pronouns = '[{"case":"nominative","form":"she"},
                 {"case":"accusative","form":"her"},
                 {"case":"genitive","form":"her"}]'
WHERE id = 5;
