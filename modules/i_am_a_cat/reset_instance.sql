-- =============================================================================
-- DAVE RPG Engine — Module: I Am a Cat
-- Instance reset script
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- PURPOSE: Reset all per-playthrough state to the canonical 3:00 AM starting
-- values, discarding any accumulated test or play session state. Run this
-- before starting a fresh play session.
--
-- This script does NOT touch module-definition data (game params, location
-- descriptions, location_connection, static character definitions). It resets
-- mutable playthrough state: character positions, emotional states, internal
-- state values, item state, the game instance clock, and the action log.
--
-- ITEM RESET (added 2026-07-07): items were originally left untouched here on
-- the assumption that they were static furniture. That assumption no longer
-- holds — item_transfers/item_changes make items mutable during play (moved,
-- consumed, or their description rewritten, e.g. the hallway runner getting
-- pounced into a "destroyed" state), so a reset that skips them silently
-- carries play-session damage into the next "fresh" session. Section 6 below
-- follows the DELETE-then-re-INSERT convention already documented in
-- docs/module_authoring.md (reset_instance.sql conventions) and already used
-- by Hidden Hostel's reset script.
--
-- When the module/instance architectural split is implemented (v7), this will
-- become seed_instance.sql and re-running it will create a new game_instance
-- row rather than mutating the existing one.
--
-- Usage:
--   python3 -c "
--   import sqlite3
--   db = sqlite3.connect('modules/i_am_a_cat/i_am_a_cat.db')
--   db.executescript(open('modules/i_am_a_cat/reset_instance.sql').read())
--   db.commit(); db.close(); print('Reset complete.')
--   "
-- =============================================================================

PRAGMA foreign_keys = ON;

-- =============================================================================
-- 1. Game instance — reset clock to 3:00 AM (180 min); status back to ready
-- =============================================================================

UPDATE game_instance
SET current_time_minutes = 180,
    status               = 'ready'
WHERE game_id = 1;

-- =============================================================================
-- 2. Character locations and emotional states
-- =============================================================================

-- Toulouse (id=1): Living Room; restless at 3am
UPDATE character
SET current_location_id = 1,
    emotional_state     = 'restless'
WHERE id = 1;

-- Spook (id=2): Study (loc 11); playful — probably batting something at 3am
UPDATE character
SET current_location_id = 11,
    emotional_state     = 'playful'
WHERE id = 2;

-- Mama (id=3): Bedroom (loc 10); lightly asleep
UPDATE character
SET current_location_id = 10,
    emotional_state     = 'lightly_asleep'
WHERE id = 3;

-- Guy (id=4): Bedroom (loc 10); deeply asleep
UPDATE character
SET current_location_id = 10,
    emotional_state     = 'deeply_asleep'
WHERE id = 4;

-- Lillis (id=5): Basement Main Room (loc 6); asleep
UPDATE character
SET current_location_id = 6,
    emotional_state     = 'asleep'
WHERE id = 5;

-- =============================================================================
-- 3. Internal state values — reset to starting calibration values
-- =============================================================================

-- Toulouse's states
UPDATE internal_state SET value = 0.00 WHERE character_id = 1 AND state_name = 'boredom';
UPDATE internal_state SET value = 0.05 WHERE character_id = 1 AND state_name = 'hairball_pressure';
UPDATE internal_state SET value = 0.45 WHERE character_id = 1 AND state_name = 'hunger';

-- Guy's sleepiness (0.88 = deeply asleep; passive rate -0.006/min → wakes ~5:27 AM)
UPDATE internal_state SET value = 0.88 WHERE character_id = 4 AND state_name = 'sleepiness';

-- Mama's sleepiness (0.22 = lightly asleep; passive rate -0.004/min → wakes ~3:55 AM)
UPDATE internal_state SET value = 0.22 WHERE character_id = 3 AND state_name = 'sleepiness';

-- Spook's states
UPDATE internal_state SET value = 0.03 WHERE character_id = 2 AND state_name = 'boredom';
UPDATE internal_state SET value = 0.31 WHERE character_id = 2 AND state_name = 'hairball_pressure';
UPDATE internal_state SET value = 0.38 WHERE character_id = 2 AND state_name = 'hunger';

-- Clear any transient states that may have been set during play
-- (mildly_frustrated, etc.) — set to 0 if they exist; no-op if they don't
UPDATE internal_state SET value = 0.00
WHERE character_id = 1
  AND state_name NOT IN ('boredom', 'hairball_pressure', 'hunger');

-- =============================================================================
-- 4. Clear the action log
-- Removes all turn history so the LLM context starts clean.
-- Comment this out if you want to preserve history for debugging.
-- =============================================================================

DELETE FROM action_log WHERE game_id = 1;

-- =============================================================================
-- 5. Reset visited locations for Toulouse
-- Clears pathfinding history so the engine doesn't remember prior routes.
-- =============================================================================

DELETE FROM character_visited_location WHERE character_id = 1;

-- Toulouse knows every room in the house — it is his territory.
-- Re-seed all 13 locations as visited so the player can quick-move
-- to any room from turn 1, matching the design intent in seed.sql.
INSERT OR IGNORE INTO character_visited_location (character_id, location_id)
VALUES
    (1, 1),   -- Living Room
    (1, 2),   -- Dining Room
    (1, 3),   -- Kitchen
    (1, 4),   -- Utility Room
    (1, 5),   -- Main Stairs
    (1, 6),   -- Basement Main Room
    (1, 7),   -- Basement Storage Room
    (1, 8),   -- Tiled Overlook
    (1, 9),   -- Bathroom
    (1, 10),  -- Bedroom
    (1, 11),  -- Study
    (1, 12),  -- Upper Hallway
    (1, 13);  -- Main Floor Hallway

-- =============================================================================
-- 6. Items — restore all items to their seeded state
--
-- v10 schema: no character_item join table (removed; item FK lives directly
-- on the item row as char_id), so a single DELETE on item is sufficient —
-- no FK-dependent child table to clear first. All 37 seeded items use loc_id
-- (none are seeded into a character's inventory), copied verbatim from
-- seed.sql so reset state always matches the true seed rather than a
-- hand-maintained duplicate that could drift from it.
-- =============================================================================

DELETE FROM item WHERE game_id = 1;

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (1, 1, 'couch',
    'A large soft thing with cushions, good for sleeping on, nesting in, and jumping off. The arm is especially desirable: flat, slightly elevated, and positioned directly beside the living room window. Sharpening claws on the sides is not permitted, which is an ongoing disagreement.',
    1, 0.80, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (2, 1, 'armchair',
    'A good sitting chair. Not as prime as the couch arm, but a solid secondary position with a decent view of the room.',
    1, 0.75, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (3, 1, 'short cat tree (living room)',
    'A short cat tree with a flat top platform, a lower perch, and a post wrapped in something satisfying to scratch. Positioned well in the living room. Identical to the one upstairs.',
    1, 0.85, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (4, 1, 'TV (living room)',
    'A large dark rectangle mounted on the wall that sometimes shows things that move and make sounds. The humans call it the TV. It is currently off and dark, which makes it boring. When on, it occasionally shows birds or small animals that require close investigation.',
    1, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (5, 1, 'coffee table (large)',
    'A flat hard surface at a good height. Good for sitting on and observing the room, or for placing objects that then fall off.',
    1, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (6, 1, 'coffee table (small)',
    'A smaller flat surface. Good for sitting on. Things can be knocked off it.',
    1, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (7, 1, 'plant (tasty)',
    'A plant the humans have placed in the living room. They do not seem to understand that it is food. It is quite good. Probably a cat grass or something similarly reasonable.',
    1, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (8, 1, 'plant (not tasty)',
    'Another plant the humans have placed here. Unlike the other one, this one does not taste good. The experience of finding this out was disappointing.',
    1, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (9, 1, 'dining table',
    'A large flat hard surface the humans don''t want cats on. This is a rule that has been noted and considered.',
    2, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (10, 1, 'dining chairs',
    'Shorter flat surfaces with soft cushions that are apparently acceptable to sit on. The humans'' position on cats on chairs vs. cats on the table is difficult to fully understand.',
    2, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (11, 1, 'pantry cupboard',
    'A tall cabinet in the dining room. Contains treats. The sound of its opening is distinctive and requires immediate investigation regardless of current location or activity. Other food items may also be inside.',
    2, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (12, 1, 'automatic food dispenser',
    'A machine that dispenses dry food approximately every four hours (2am, 6am, 10am, 2pm, 6pm, 10pm). It does this without being asked and without any warmth or ceremony. The food is perfectly acceptable but lacks the meaning of food distributed by a human. The 2am feeding has recently run.',
    4, 0.70, 1);  -- 0.70: recently dispensed, still has food available

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (13, 1, 'washer',
    'A large boxy appliance. Excellent for hiding behind. Sometimes vibrates, which is startling but also interesting.',
    4, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (14, 1, 'dryer',
    'Another large boxy appliance. Also good for hiding behind. Sometimes warm on top after a cycle, which is a premium sleeping spot if one can get up there.',
    4, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (15, 1, 'litter box',
    'The litter box. Cats have strong opinions about its condition. A full or dirty litter box is an affront and will be treated as such. Currently at acceptable-but-not-ideal cleanliness; has not been scooped since yesterday evening.',
    7, 0.60, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (16, 1, 'bird cage',
    'A metal cage containing the bird. The bars present an engineering challenge the cats have not yet solved. The humans have been explicit about the reaching-in policy. The bird is currently asleep inside and therefore boring, but the cage itself is interesting to sniff and sit near.',
    6, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (17, 1, 'computer (basement)',
    'A glowing rectangle the female human likes to look at while sitting in her chair in the basement. Currently off and dark. When on, it sometimes shows interesting things. The chair in front of it is a good sitting spot.',
    6, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (18, 1, 'craft supplies',
    'A collection of fabric, yarn, containers, and various crafting materials stored in the basement. Most of it is in bins and bags. Whether any string or ribbon has been left accessible depends on how carefully the female human put things away before bed. Worth investigating.',
    6, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (19, 1, 'storage boxes (basement)',
    'Many boxes of various sizes. Most are sealed and too heavy to move. Good for hiding behind. Not much else.',
    7, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (20, 1, 'short cat tree (study)',
    'A short cat tree identical to the one in the living room. Has a post wrapped in sisal rope that is excellent for claw maintenance. Located in the study, where claw-sharpening is explicitly sanctioned.',
    11, 0.85, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (21, 1, 'cardboard scratch pad',
    'A flat corrugated cardboard surface on the floor of the study. Good for scratching. Has that satisfying texture.',
    11, 0.75, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (22, 1, 'TV (study)',
    'A large dark rectangle in the study that the male human likes to look at a lot. Currently off.',
    11, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (23, 1, 'bed',
    'The large soft flat sleeping surface in the bedroom. The humans are currently on it. Cats are welcome on or under it. It is warm and good for sleeping. It is also a viable play location if one is persistent, though this tends to produce a reaction.',
    10, 0.95, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (24, 1, 'nightstand (mama)',
    'The female human''s nightstand. Has things on it. Some of these things are at a good height for interaction. A glass of water may be present.',
    10, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (25, 1, 'nightstand (guy)',
    'The male human''s nightstand. Also has things on it.',
    10, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (26, 1, 'water container (bathroom)',
    'A cup or container left in the bathroom that holds water. This water is somehow better than the water in the bowl. It can be played with: scooped, scattered, and generally enjoyed. The humans do not seem to understand why this is the preferred water source.',
    9, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (27, 1, 'treats',
    'The treats. Located inside the pantry cupboard. The best food item in the house by a significant margin. Humans will sometimes throw them across the room, which is excellent. The sound of the pantry opening is the primary signal of their potential availability.',
    2, 1.0, 0);  -- hidden inside pantry (is_visible=0)

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (28, 1, 'canned cat food',
    'Soft food in cans, stored in the kitchen. Significantly better than the dry food from the machine. The male human puts it out approximately twice per day, including in the morning. Whether it is morning yet is always worth investigating.',
    3, 0.90, 0);  -- stored in cabinet (is_visible=0)

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (29, 1, 'soft mouse toy',
    'A small soft toy shaped approximately like a mouse. Light enough to carry in the mouth. Can be brought upstairs, dropped from elevated positions, or batted across smooth floors. A reliable toy.',
    1, 0.72, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (30, 1, 'jingle ball',
    'A small ball with a bell inside. Makes a jingling sound when moved. The sound is interesting at 3am. The humans may disagree.',
    1, 0.80, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (31, 1, 'chirping electronic toy',
    'A toy that emits chirping sounds when activated. Sounds plausibly like a small bird or insect. The battery may be getting low, which affects the sound quality in interesting ways.',
    1, 0.55, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (32, 1, 'spring bounce toy',
    'A coiled spring toy that bounces unpredictably. Excellent fun until it goes down the stairs, at which point retrieving it is effortful. Currently on the main floor.',
    1, 0.78, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (33, 1, 'crinkle toy',
    'A soft toy made of crinkly material. Makes a satisfying sound when bitten or kneaded. Portable.',
    1, 0.68, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (34, 1, 'reading glasses',
    'A pair of human optical devices belonging to the female human. Left on her nightstand. They slide satisfyingly on smooth surfaces and have interesting components. The humans do not seem to understand that these are toys.',
    10, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (35, 1, 'keys',
    'A bunch of metal keys on a ring. Left in the dining room. Make a good noise when batted. Can be moved to inconvenient locations. The humans do not seem to understand that these are also toys.',
    2, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (36, 1, 'hair tie',
    'A small elastic hair tie left on the bathroom counter. Stretchy, flingable, and small enough to bat under the gap at the bottom of the door. A very good accidental toy.',
    9, NULL, 1);

INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (37, 1, 'hallway runner',
    'A long thin rug running the length of the main floor hallway. The smooth floor beneath it means it can and does shift if a cat crosses it at speed. When it bunches or skews, it becomes a different kind of surface and also an interesting obstacle. The humans straighten it periodically.',
    13, 0.85, 1);
