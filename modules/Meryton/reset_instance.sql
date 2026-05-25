-- =============================================================================
-- DAVE RPG Engine — Instance Reset: Meryton Module, Chapter 3
-- "The First Assembly"
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Purpose: restore the canonical starting state for a fresh playthrough
-- without re-running the full seed. Static module data (locations, connections,
-- factions, character definitions, OCEAN values, goals) is left untouched.
--
-- What this resets:
--   - All character current_location_id and emotional_state
--   - All character pending_intent (cleared)
--   - All internal_state values
--   - All character_attitude values (delete + re-insert)
--   - All character_faction_reputation values (delete + re-insert)
--   - character_visited_location (cleared)
--   - game_instance clock and status
--   - action_log (cleared; see note below)
--
-- action_log note: cleared by default so each playtest starts clean.
-- Comment out the action_log DELETE below if you want to preserve history.
--
-- Usage:
--   sqlite3 modules/Meryton/meryton.db < modules/Meryton/reset_instance.sql
-- =============================================================================

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;


-- =============================================================================
-- ACTION LOG (optional — comment out to preserve play history)
-- =============================================================================

DELETE FROM action_log WHERE game_id = 2;


-- =============================================================================
-- CHARACTER VISITED LOCATIONS
-- Elizabeth starts in the vestibule and has not yet been anywhere.
-- =============================================================================

DELETE FROM character_visited_location
WHERE character_id IN (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19);


-- =============================================================================
-- CHARACTER LOCATIONS, EMOTIONAL STATES, PENDING INTENT
-- =============================================================================

-- Elizabeth Bennet: vestibule on arrival; has not yet entered the assembly
UPDATE character SET current_location_id = 1, emotional_state = 'anticipatory',   pending_intent = NULL WHERE id = 1;

-- Mr. Darcy: ballroom; reserved and uncomfortable; disdain has not yet formed
UPDATE character SET current_location_id = 4, emotional_state = 'reserved',        pending_intent = NULL WHERE id = 2;

-- Mr. Bingley: ballroom; delighted; dancing every dance
UPDATE character SET current_location_id = 4, emotional_state = 'delighted',       pending_intent = NULL WHERE id = 3;

-- Jane Bennet: ballroom; quietly hopeful
UPDATE character SET current_location_id = 4, emotional_state = 'quietly_hopeful', pending_intent = NULL WHERE id = 4;

-- Charlotte Lucas: ballroom; near Elizabeth's party
UPDATE character SET current_location_id = 4, emotional_state = 'pleasant',        pending_intent = NULL WHERE id = 5;

-- Mrs. Bennet: ballroom wall seating; watching everything
UPDATE character SET current_location_id = 4, emotional_state = 'excited_and_anxious', pending_intent = NULL WHERE id = 6;

-- Lydia Bennet: ballroom; giddy and already dancing
UPDATE character SET current_location_id = 4, emotional_state = 'giddy',           pending_intent = NULL WHERE id = 7;

-- Kitty Bennet: ballroom; following Lydia
UPDATE character SET current_location_id = 4, emotional_state = 'excited',         pending_intent = NULL WHERE id = 8;

-- Mary Bennet: ballroom wall seating; earnest and observing
UPDATE character SET current_location_id = 4, emotional_state = 'earnest',         pending_intent = NULL WHERE id = 9;

-- Miss Bingley: ballroom; poised and watchful
UPDATE character SET current_location_id = 4, emotional_state = 'poised_and_watchful', pending_intent = NULL WHERE id = 10;

-- Mrs. Hurst: ballroom; comfortable; following Miss Bingley's lead
UPDATE character SET current_location_id = 4, emotional_state = 'comfortable',     pending_intent = NULL WHERE id = 11;

-- Mr. Hurst: card room; content; will not move
UPDATE character SET current_location_id = 5, emotional_state = 'content',         pending_intent = NULL WHERE id = 12;

-- Lady Lucas: ballroom wall seating; near Mrs. Bennet
UPDATE character SET current_location_id = 4, emotional_state = 'sociable',        pending_intent = NULL WHERE id = 13;

-- Sir William Lucas: landing at top of stairs; greeting arrivals
UPDATE character SET current_location_id = 3, emotional_state = 'genial',          pending_intent = NULL WHERE id = 14;

-- Mr. Robinson: ballroom
UPDATE character SET current_location_id = 4, emotional_state = 'sociable',        pending_intent = NULL WHERE id = 15;

-- John Lucas: ballroom
UPDATE character SET current_location_id = 4, emotional_state = 'pleasant',        pending_intent = NULL WHERE id = 16;

-- Edward Long: ballroom
UPDATE character SET current_location_id = 4, emotional_state = 'pleasant',        pending_intent = NULL WHERE id = 17;

-- Thomas Philips: ballroom
UPDATE character SET current_location_id = 4, emotional_state = 'dutiful',         pending_intent = NULL WHERE id = 18;

-- William Goulding: ballroom
UPDATE character SET current_location_id = 4, emotional_state = 'comfortable',     pending_intent = NULL WHERE id = 19;


-- =============================================================================
-- INTERNAL STATES
-- =============================================================================

-- Elizabeth
UPDATE internal_state SET value = 0.78 WHERE character_id = 1 AND state_name = 'composure';
UPDATE internal_state SET value = 0.72 WHERE character_id = 1 AND state_name = 'social_ease';
UPDATE internal_state SET value = 0.70 WHERE character_id = 1 AND state_name = 'curiosity';

-- Darcy
UPDATE internal_state SET value = 0.72 WHERE character_id = 2 AND state_name = 'social_discomfort';
UPDATE internal_state SET value = 0.80 WHERE character_id = 2 AND state_name = 'composure';
UPDATE internal_state SET value = 0.78 WHERE character_id = 2 AND state_name = 'pride';

-- Bingley
UPDATE internal_state SET value = 0.82 WHERE character_id = 3 AND state_name = 'enjoyment';
UPDATE internal_state SET value = 0.90 WHERE character_id = 3 AND state_name = 'social_ease';

-- Mrs. Bennet
UPDATE internal_state SET value = 0.65 WHERE character_id = 6 AND state_name = 'anxiety';
UPDATE internal_state SET value = 0.80 WHERE character_id = 6 AND state_name = 'excitement';
UPDATE internal_state SET value = 0.22 WHERE character_id = 6 AND state_name = 'composure';

-- Lydia
UPDATE internal_state SET value = 0.90 WHERE character_id = 7 AND state_name = 'excitement';
UPDATE internal_state SET value = 0.15 WHERE character_id = 7 AND state_name = 'composure';

-- Miss Bingley
UPDATE internal_state SET value = 0.85 WHERE character_id = 10 AND state_name = 'composure';
UPDATE internal_state SET value = 0.72 WHERE character_id = 10 AND state_name = 'self_satisfaction';
UPDATE internal_state SET value = 0.52 WHERE character_id = 10 AND state_name = 'social_vigilance';

-- Mrs. Hurst
UPDATE internal_state SET value = 0.78 WHERE character_id = 11 AND state_name = 'comfort';
UPDATE internal_state SET value = 0.68 WHERE character_id = 11 AND state_name = 'social_ease';

-- Sir William Lucas
UPDATE internal_state SET value = 0.88 WHERE character_id = 14 AND state_name = 'social_ease';
UPDATE internal_state SET value = 0.80 WHERE character_id = 14 AND state_name = 'enjoyment';


-- =============================================================================
-- CHARACTER ATTITUDES
-- Delete all and re-insert from canonical starting values.
-- This catches any drift without requiring per-row UPDATE logic.
-- =============================================================================

DELETE FROM character_attitude
WHERE character_id IN (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19);

-- Elizabeth → Darcy: strangers on arrival; both surface and hidden at zero
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (1, 2, 0.0,   'surface');
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (1, 2, 0.0,   'hidden');
-- Elizabeth → Bingley: favorable first impression
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (1, 3, 0.35,  'surface');
-- Elizabeth → Jane: warm sisterly love
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (1, 4, 0.92,  'surface');
-- Elizabeth → Charlotte: genuine close friendship
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (1, 5, 0.80,  'surface');
-- Elizabeth → Sir William: fond; mildly amused by his knighthood pride
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (1, 14, 0.38, 'surface');
-- Elizabeth → John Lucas: Charlotte's brother; old acquaintance
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (1, 16, 0.35, 'surface');
-- Elizabeth → Robinson: familiar neighbor
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (1, 15, 0.12, 'surface');
-- Elizabeth → Edward Long: neighborhood acquaintance
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (1, 17, 0.10, 'surface');
-- Elizabeth → Thomas Philips: familiar; slightly obligatory dynamic
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (1, 18, 0.18, 'surface');
-- Elizabeth → William Goulding: neighborhood acquaintance
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (1, 19, 0.12, 'surface');

-- Darcy → Elizabeth: strangers on arrival
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (2, 1, 0.0,   'surface');
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (2, 1, 0.0,   'hidden');
-- Darcy → Bingley: genuine warmth and protectiveness
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (2, 3, 0.78,  'surface');

-- Bingley → Jane: immediate genuine attraction
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (3, 4, 0.55,  'surface');

-- Jane → Bingley: pleasantly interested; more reserved on surface than she feels
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (4, 3, 0.30,  'surface');
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (4, 3, 0.50,  'hidden');

-- Miss Bingley → Darcy: pursuing; surface warmth and hidden depth
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (10, 2, 0.50, 'surface');
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (10, 2, 0.65, 'hidden');
-- Miss Bingley → Jane: surface politeness masking indifference
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (10, 4, 0.05, 'surface');
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (10, 4, -0.12,'hidden');

-- Mrs. Hurst → Mr. Hurst: comfortable marriage; not warm
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (11, 12, 0.22,'surface');
-- Mrs. Hurst → Bingley: genuine sibling affection
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (11, 3, 0.58, 'surface');

-- Sir William → Elizabeth: Charlotte's friend; fond
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (14, 1, 0.38, 'surface');
-- Sir William → Charlotte: his daughter; warm paternal affection
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (14, 5, 0.82, 'surface');
-- Sir William → Bingley: warmly welcoming new neighbor
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (14, 3, 0.45, 'surface');
-- Sir William → Darcy: respectful; not intimidated
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (14, 2, 0.22, 'surface');

-- Mr. Robinson → Elizabeth
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (15, 1, 0.18, 'surface');
-- John Lucas → Elizabeth
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (16, 1, 0.42, 'surface');
-- John Lucas → Charlotte: close siblings
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (16, 5, 0.75, 'surface');
-- John Lucas → Sir William: his father
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (16, 14, 0.72,'surface');
-- Edward Long → Elizabeth
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (17, 1, 0.15, 'surface');
-- Thomas Philips → Elizabeth
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (18, 1, 0.22, 'surface');
-- William Goulding → Elizabeth
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type) VALUES (19, 1, 0.15, 'surface');


-- =============================================================================
-- CHARACTER FACTION REPUTATIONS
-- Delete and re-insert for the same reason as attitudes.
-- =============================================================================

DELETE FROM character_faction_reputation
WHERE character_id IN (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19);

-- Elizabeth
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (1, 1, 0.65, 'Respected and trusted daughter; no conflicts yet this evening.');
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (1, 2, 0.68, 'Well-regarded locally; clever and personable. The family is eccentric but Elizabeth is not.');
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (1, 3, 0.05, 'Unknown to Bingley''s party on arrival; no judgments formed yet.');

-- Sir William Lucas
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (14, 2, 0.80, 'Former mayor, knight, and natural host of the neighborhood. Highly regarded.');
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (14, 3, 0.30, 'Welcomed Bingley''s party on arrival. Politely regarded; his origins in trade are noted.');

-- Mr. Robinson
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (15, 2, 0.58, 'Ordinary neighborhood standing; well enough liked.');

-- John Lucas
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (16, 2, 0.62, 'Well-regarded; son of the most prominent local family.');

-- Edward Long
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (17, 2, 0.52, 'Ordinary neighborhood standing; known through Mrs. Long.');

-- Thomas Philips
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (18, 2, 0.55, 'Unremarkable neighborhood standing; known through the Philips connection.');

-- William Goulding
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (19, 2, 0.62, 'Solid neighborhood standing; the Gouldings are a well-regarded local family.');


-- =============================================================================
-- GAME INSTANCE: reset clock to 8:00 PM start; status back to ready
-- =============================================================================

UPDATE game_instance SET
    current_time_minutes = 1200,
    status = 'ready'
WHERE game_id = 2;


COMMIT;
