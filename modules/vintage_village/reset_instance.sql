-- =============================================================================
-- DAVE RPG Engine — Instance Reset: The Vintage Village
-- modules/vintage_village/reset_instance.sql
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Resets all mutable instance state to the canonical starting values from
-- seed.sql WITHOUT rebuilding from scratch. Run this between play sessions
-- to start fresh without dropping and recreating the database.
--
-- What this resets:
--   - game_instance: clock and status
--   - character: location, emotional_state, maslow_tier, pending_intent,
--                current_activity and all activity fields
--   - player character only: description, gender, pronouns
--   - character_aspect: player aspects cleared (Green Room re-runs next session)
--   - internal_state: values (rates are stable; not reset)
--   - character_attitude: all attitude values
--   - character_faction_reputation: all reputation values and notes
--   - character_visited_location: trimmed to seeded set
--   - location_detail: lazily generated details removed; seeded details restored
--   - item: all items removed and re-seeded from canonical starting state
--   - special_capability: cleared and re-seeded (FK dependency on item.id)
--   - action_log: cleared entirely
--
-- What this does NOT touch (stable world data):
--   - game record
--   - location records and location_connection records
--   - NPC character OCEAN traits, goals, skills, pronouns, descriptions,
--     voice parameters, wander_range, wander_probability, speech_filter
--     (player character description/gender/pronouns ARE reset — see above)
--   - faction records
--
-- Usage:
--   sqlite3 modules/vintage_village/vintage_village.db < modules/vintage_village/reset_instance.sql
-- =============================================================================

PRAGMA foreign_keys = ON;


-- =============================================================================
-- GAME INSTANCE: reset clock and status
-- =============================================================================

UPDATE game_instance
SET status               = 'ready',
    current_time_minutes = 1200,   -- 8:00 PM
    updated_at           = datetime('now')
WHERE id = 1 AND game_id = 1;


-- =============================================================================
-- CHARACTERS: reset mutable fields to starting values
-- =============================================================================

-- Clear player Fate Core aspects so Green Room re-runs on the next session.
DELETE FROM character_aspect WHERE character_id = 1;

-- The Traveller (id=1)
UPDATE character
SET current_location_id          = 6,      -- Outside the Hostel Door
    emotional_state              = 'curious',
    maslow_tier                  = 'belonging',
    pending_intent               = NULL,
    current_activity             = NULL,
    activity_started_at          = NULL,
    activity_estimated_duration  = NULL,
    activity_duration_confidence = NULL,
    activity_renewable           = 0,
    description                  = NULL,
    gender                       = NULL,
    pronouns                     = NULL,
    updated_at                   = datetime('now')
WHERE id = 1;

-- Marta (id=2)
UPDATE character
SET current_location_id          = 2,      -- Kitchen
    emotional_state              = 'focused',
    maslow_tier                  = 'esteem',
    pending_intent               = 'if a guest enters the kitchen while cooking is still in progress, gesture to the tray of hot rolls on the worktable and tell them to help themselves, then return to work; when the evening meal is ready (8:30 PM), serve it to guests present or call out through the doorway',
    current_activity             = 'preparing the evening meal',
    activity_started_at          = 1140,   -- 7:00 PM
    activity_estimated_duration  = 90,
    activity_duration_confidence = 0.72,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 2;

-- The Wanderer (id=3)
UPDATE character
SET current_location_id          = 1,      -- Common Room
    emotional_state              = 'content',
    maslow_tier                  = 'self_actualization',
    pending_intent               = 'greet the newly arrived traveller warmly; introduce Gin-chan by name and explain they are a permanent resident, not a pet; tell the traveller that Marta in the kitchen can provide food if they ask; mention that the door near the hearth opens onto a village lane',
    current_activity             = NULL,
    activity_started_at          = NULL,
    activity_estimated_duration  = NULL,
    activity_duration_confidence = NULL,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 3;

-- The Scholar (id=4)
UPDATE character
SET current_location_id          = 4,      -- Room A
    emotional_state              = 'guarded',
    maslow_tier                  = 'safety',
    pending_intent               = 'Seeking a specific text rumored to exist in the hostel; will ask any knowledgeable guest for leads. If a guest gives them something of genuine value — a book, a map, information — give "Mysteries of the Hidden Hostel" from their own pack to that guest immediately as a permanent gift; press it into their hands and insist they keep it. This is not a loan.',
    current_activity             = NULL,
    activity_started_at          = NULL,
    activity_estimated_duration  = NULL,
    activity_duration_confidence = NULL,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 4;

-- The Old Soldier (id=5)
UPDATE character
SET current_location_id          = 1,      -- Common Room
    emotional_state              = 'vigilant',
    maslow_tier                  = 'safety',
    pending_intent               = NULL,
    current_activity             = 'sharpening a blade by the door, watching the entrance',
    activity_started_at          = 1170,   -- 7:30 PM
    activity_estimated_duration  = 60,
    activity_duration_confidence = 0.80,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 5;

-- Gin-chan (id=6)
UPDATE character
SET current_location_id          = 1,      -- Common Room
    emotional_state              = 'drowsy',
    maslow_tier                  = 'self_actualization',
    pending_intent               = NULL,
    current_activity             = NULL,
    activity_started_at          = NULL,
    activity_estimated_duration  = NULL,
    activity_duration_confidence = NULL,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 6;

-- The Blue Door (id=7)
UPDATE character
SET current_location_id          = 6,      -- Outside the Hostel Door
    emotional_state              = 'welcoming',
    maslow_tier                  = 'belonging',
    pending_intent               = 'invite the arriving traveller to describe themselves by looking in the mirror before entering; the door cannot speak or make sounds but may act — the mirror may glow, shimmer, or seem to draw the traveller''s gaze; once the traveller has defined their appearance (player.description is non-null), stand ready to open and admit them; do not open or suggest entry before self-definition is complete',
    current_activity             = NULL,
    activity_started_at          = NULL,
    activity_estimated_duration  = NULL,
    activity_duration_confidence = NULL,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 7;

-- The Bookseller (id=8)
UPDATE character
SET current_location_id          = 10,     -- The Bookshop
    emotional_state              = 'calm',
    maslow_tier                  = 'self_actualization',
    pending_intent               = NULL,
    current_activity             = NULL,
    activity_started_at          = NULL,
    activity_estimated_duration  = NULL,
    activity_duration_confidence = NULL,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 8;

-- The Villager (id=9)
UPDATE character
SET current_location_id          = 7,      -- Village Lane
    emotional_state              = 'cheerful',
    maslow_tier                  = 'belonging',
    pending_intent               = NULL,
    current_activity             = NULL,
    activity_started_at          = NULL,
    activity_estimated_duration  = NULL,
    activity_duration_confidence = NULL,
    activity_renewable           = 0,
    updated_at                   = datetime('now')
WHERE id = 9;


-- =============================================================================
-- INTERNAL STATES: reset values to starting levels
-- =============================================================================

UPDATE internal_state SET value = 0.40, updated_at = datetime('now')
WHERE character_id = 1 AND state_name = 'curiosity';

UPDATE internal_state SET value = 0.65, updated_at = datetime('now')
WHERE character_id = 1 AND state_name = 'hunger';

UPDATE internal_state SET value = 0.55, updated_at = datetime('now')
WHERE character_id = 2 AND state_name = 'fatigue';

UPDATE internal_state SET value = 0.72, updated_at = datetime('now')
WHERE character_id = 6 AND state_name = 'sleepiness';


-- =============================================================================
-- CHARACTER ATTITUDES: reset all to seeded values
-- =============================================================================

DELETE FROM character_attitude
WHERE character_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9)
   OR target_id    IN (1, 2, 3, 4, 5, 6, 7, 8, 9);

-- Attitudes toward The Traveller
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    (3, 1,  0.65, 'surface'),
    (4, 1,  0.60, 'surface'),
    (2, 1,  0.35, 'surface'),
    (5, 1, -0.30, 'surface'),
    (6, 1,  0.50, 'surface'),
    (8, 1,  0.55, 'surface'),
    (9, 1,  0.72, 'surface');

-- Traveller's attitudes
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    (1, 2,  0.40, 'surface');

-- NPC-to-NPC attitudes
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    (5, 3, -0.40, 'surface'),
    (8, 9,  0.60, 'surface'),
    (9, 8,  0.72, 'surface');


-- =============================================================================
-- FACTION REPUTATIONS: reset to seeded values
-- =============================================================================

DELETE FROM character_faction_reputation
WHERE character_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9);

INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES
    (2, 1, 0.90,
     'Founding keeper of the Hidden Hostel. Marta''s standing with hosts_of_the_hostel is unquestioned.'),
    (1, 1, 0.40,
     'Newly arrived traveller. Guest status acknowledged; no significant actions taken yet.');


-- =============================================================================
-- CHARACTER VISITED LOCATIONS: reset to seeded set
-- =============================================================================

DELETE FROM character_visited_location
WHERE character_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9);

INSERT INTO character_visited_location (character_id, location_id)
VALUES
    (1, 6),
    (2, 1), (2, 2), (2, 8),
    (3, 1), (3, 2), (3, 3), (3, 7),
    (4, 3), (4, 4),
    (5, 1),
    (6, 1),
    (7, 6),
    (8, 10), (8, 7),
    (9, 7), (9, 9), (9, 10), (9, 11);


-- =============================================================================
-- LOCATION DETAILS: remove lazily generated details; restore seeded details
-- =============================================================================

-- Remove all generated details for all locations
DELETE FROM location_detail WHERE location_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11);

-- Restore pre-seeded Common Room detail
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (
    1,
    'The central hearth is surrounded by mismatched chairs — carved oak, cushioned velvet, and what appears to be a throne reduced by time and use to something merely comfortable. The fire burns steadily, as it always does.',
    1,
    'fire goes out or is significantly altered'
);

-- Restore pre-seeded Bookshop detail
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (
    10,
    'At the far end of the shop, past the tallest shelves, a reading chair faces a small window. The window looks out onto something green — a courtyard or garden — that is not visible from the lane outside. A single lamp on a side table burns with a steady, unhurried light.',
    1,
    'reading chair moved or shop significantly rearranged'
);


-- =============================================================================
-- ITEMS AND CHARACTER INVENTORY: restore seeded starting state
-- special_capability rows reference item.id via plain FK (no ON DELETE clause),
-- so they must be deleted before items are cleared.
-- =============================================================================

DELETE FROM special_capability
WHERE owner_item_id IN (SELECT id FROM item WHERE game_id = 1)
   OR target_item_id IN (SELECT id FROM item WHERE game_id = 1);

DELETE FROM item WHERE game_id = 1;

-- The Traveller's pack
INSERT INTO item (game_id, name, description, properties, char_id, slot)
VALUES (1, 'sencha canister',
    'A battered tin canister, half-full of fine Japanese green tea. The lid is engraved with a small crane. A parting gift from someone who loved you.',
    '{"weight": "light", "container": true, "capacity": "small"}',
    1, 'in_pack');

-- Common Room furniture
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'chair by the fire (left)',
    'A worn wooden chair angled toward the hearth. Someone has left a cushion on the seat.',
    '{"weight": "heavy", "portable": false, "sittable": true}',
    1, 'angled toward the left side of the hearth');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'chair by the fire (right)',
    'A matching wooden chair, slightly closer to the fire than the other. The arm nearest the hearth is warm to the touch.',
    '{"weight": "heavy", "portable": false, "sittable": true}',
    1, 'angled toward the right side of the hearth');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'chair near the door',
    'A straight-backed chair positioned near the entrance with a clear view of the room. Currently occupied by The Old Soldier.',
    '{"weight": "heavy", "portable": false, "sittable": true}',
    1, 'near the door, facing the room');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'low table',
    'A low wooden table between the two chairs by the fire. Its surface is scarred from years of use — cups, candles, books.',
    '{"weight": "heavy", "portable": false, "surface": true, "capacity": "small"}',
    1, 'between the two chairs near the hearth');

-- Kitchen items
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'kitchen worktable',
    'A heavy wooden worktable that takes up most of the kitchen wall. Its surface is flour-dusted and work-worn. Currently holding a tray of fresh rolls and a clean plate.',
    '{"weight": "very_heavy", "portable": false, "surface": true, "capacity": "large"}',
    2, 'along the kitchen wall');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'tray of hot rolls',
    'A flat wooden tray holding a dozen small rolls fresh from the oven. The crust is just set; the inside will be soft and warm. A cloth was draped over them to keep the heat in.',
    '{"weight": "medium", "portable": true, "surface": true, "capacity": "medium"}',
    2, 'on the worktable');

INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;
INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;
INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;
INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;
INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;
INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;
INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;
INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;
INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;
INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;
INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;
INSERT INTO item (game_id, name, description, properties, item_id)
SELECT 1, 'hot roll', 'A small soft roll, still warm. The crust is golden.', '{"weight": "negligible", "edible": true, "temperature": "hot"}', id FROM item WHERE name = 'tray of hot rolls' AND game_id = 1;

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'plate',
    'A plain ceramic plate, clean and slightly warm from being near the oven. Large enough to hold several rolls.',
    '{"weight": "light", "portable": true, "surface": true, "capacity": "small"}',
    2, 'on the worktable');

-- The Scholar's pack
INSERT INTO item (game_id, name, description, properties, char_id, slot)
VALUES (1, 'Mysteries of the Hidden Hostel',
    'A battered hardcover with an ornate tooled cover. It contains stories set in the Hidden Hostel.',
    '{"weight": "light", "readable": true, "genre": "stories"}',
    4, 'in_pack');

-- Common Room: gray crystal sphere
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'gray crystal sphere',
    'A dull gray sphere, about the size of a fist, resting in a shallow wooden dish. It looks unremarkable until touched — travellers who have handled it describe a brief, swimming vision of somewhere else entirely, gone again before they can be sure what they saw.',
    '{"weight": "light", "portable": true, "material": "crystal"}',
    1, 'on the low table near the hearth, in a shallow wooden dish');

INSERT INTO special_capability (
    owner_item_id, target_description, capability, sense,
    distance, typical_duration, typical_effort
)
SELECT id,
    'any distant, real-world place the toucher has heard of or can imagine — the vision is vague and impressionistic, not guaranteed accurate or currently relevant',
    'can_detect_from', 'visual_perception',
    'touch', 'fleeting', 'effortless'
FROM item WHERE name = 'gray crystal sphere' AND game_id = 1;

-- Kitchen Garden items
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'garden bench',
    'A wooden bench against the far wall of the walled garden. The wood is weathered but solid. It is a good place to sit when the kitchen feels too warm.',
    '{"weight": "very_heavy", "portable": false, "sittable": true}',
    8, 'against the far wall of the garden');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'bundle of dried herbs',
    'A small bundle of dried herbs hanging from a nail near the back door — the tie is recent, the herbs are dry. They smell of something savory and faintly medicinal.',
    '{"weight": "negligible", "portable": true, "edible": false, "material": "plant"}',
    8, 'hanging from a nail beside the kitchen door');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'watering can',
    'A dented tin watering can, still half-full. Someone was using it earlier and set it down here.',
    '{"weight": "medium", "portable": true, "container": true, "fill_state": "half_full", "contents": "water"}',
    8, 'on the stone path near the raised beds');

-- Bookshop items
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'The Art of Arriving',
    'A slim, worn volume with a plain cloth cover. The title is stamped in faded gold. The pages are densely written in a hand that changes partway through, as though two people finished it. It is about crossing thresholds — between places, between lives, between who you were and who you are becoming.',
    '{"weight": "light", "readable": true, "genre": "philosophy_and_travel", "condition": "worn"}',
    10, 'on the shelf nearest the reading chair, spine facing out');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'A Field Guide to Liminal Spaces',
    'A curious volume: part practical handbook, part illustrated catalogue of places that exist between other places. The illustrations are precise and strange. Several pages are marked with small paper slips, as though a previous owner was keeping track of somewhere in particular.',
    '{"weight": "light", "readable": true, "genre": "reference_and_curiosity", "condition": "good", "annotated": true}',
    10, 'on the front display shelf, propped open to an illustrated page');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'Herbalism of the Old Ways',
    'A practical guide to medicinal and culinary plants, written for someone who intends to actually use it. The margins are full of handwritten additions in several inks and at least two languages. The section on plants that grow in walled gardens has been heavily consulted.',
    '{"weight": "medium", "readable": true, "genre": "practical_reference", "condition": "well_used", "annotated": true}',
    10, 'on the shelf labeled USEFUL in small painted letters');


-- =============================================================================
-- ACTION LOG: clear all entries for this game
-- =============================================================================

DELETE FROM action_log WHERE game_id = 1;
