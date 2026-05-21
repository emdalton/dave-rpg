-- =============================================================================
-- DAVE RPG Engine — Module: I Am a Cat
-- Seed data for schema v3 additions
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Applies to: modules/i_am_a_cat/i_am_a_cat.db (after migrate_v2_to_v3.sql)
--
-- Contents:
--   1. Location connections — physical adjacency between all 11 locations
--   2. NPC wander parameters — range and per-turn movement probability
--
-- Location ID reference:
--   Main floor:  1=Living Room, 2=Dining Room, 3=Kitchen,
--                4=Laundry Room, 5=Main Stairs
--   Basement:    6=Basement Main Room, 7=Basement Storage Room
--   Upper floor: 8=Tiled Overlook, 9=Bathroom, 10=Bedroom, 11=Study
--
-- Convention: location_a_id < location_b_id (enforced by schema CHECK constraint).
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
-- 1. Location connections
-- -----------------------------------------------------------------------------

-- =============================================================================
-- Main floor connections
-- =============================================================================
-- The main floor has a loop path: Living Room → Dining Room →
-- Main Floor Hallway → Living Room (and back the same way).
--
-- Layout:
--   Living Room (1): open stairwell in corner leads up (1↔5); half wall of
--     cabinets separates it from Dining Room (1↔2); hallway opening at the
--     back (1↔13).
--   Dining Room (2): half wall to Living Room (1↔2); opening at far end into
--     Main Floor Hallway (2↔13).
--   Main Floor Hallway (13): runs along the side of the main floor; open to
--     Kitchen (3↔13), door to Utility Room (4↔13), basement stairs (6↔13),
--     and openings back to Living Room (1↔13) and Dining Room (2↔13).
-- =============================================================================

-- Living Room ↔ Dining Room: half wall of cabinets; cats go over or under
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (1, 2, 'open', 1);

-- Living Room ↔ Main Stairs: open stairwell in the corner of the living room
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (1, 5, 'open', 1);

-- Living Room ↔ Main Floor Hallway: opening at the back of the living room
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (1, 13, 'open', 1);

-- Dining Room ↔ Main Floor Hallway: opening at the far end of the dining room
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (2, 13, 'open', 1);

-- Kitchen ↔ Main Floor Hallway: open plan, no door
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (3, 13, 'open', 1);

-- Utility Room ↔ Main Floor Hallway: door
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (4, 13, 'door', 1);

-- Main Stairs ↔ Upper Hallway: stairs up from living room to upper floor
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (5, 12, 'stairs', 1);

-- Main Floor Hallway ↔ Basement Main Room: door off hallway to basement stairs
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (6, 13, 'stairs', 1);

-- Basement connections
-- Basement Main Room ↔ Basement Storage Room: interior door
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (6, 7, 'door', 1);

-- Upper floor connections

-- Upper Hallway ↔ Tiled Overlook: accessible by squeezing through the railing
-- at the landing end of the hallway. The overlook is a tiled platform that
-- extends over the closet below and provides an elevated view of the living room.
-- connection_type 'squeeze' reflects the physical effort required.
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (8, 12, 'squeeze', 1);

-- Upper Hallway ↔ Bathroom: door off the hallway
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (9, 12, 'door', 1);

-- Upper Hallway ↔ Bedroom: door off the hallway; closed at 3am but passable.
-- is_passable=1: a closed door is not an impassable barrier. Toulouse can
-- scratch, yowl, or push through (LLM adjudicates the interaction). The humans
-- have low wander_probability so they rarely traverse this connection autonomously.
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (10, 12, 'door', 1);

-- Upper Hallway ↔ Study: door off the hallway
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (11, 12, 'door', 1);

-- -----------------------------------------------------------------------------
-- 2. NPC wander parameters
-- -----------------------------------------------------------------------------

-- Spook (character_id=2): indoor-outdoor cat, uses the whole house freely.
-- High wander probability: cats are active at 3am and Spook is restless.
-- All 13 locations in range; Spook goes wherever curiosity leads.
UPDATE character
SET wander_range       = '[1,2,3,4,5,6,7,8,9,10,11,12,13]',
    wander_probability = 0.20
WHERE id = 2;

-- Mama (character_id=3): sleeping human; low autonomous movement probability.
-- Range is the whole house except the Tiled Overlook (8), which requires
-- squeezing through the railing — not something humans do. The low
-- wander_probability (not the range) is what keeps her in bed; if she wakes
-- she can go anywhere accessible.
UPDATE character
SET wander_range       = '[1,2,3,4,5,6,7,9,10,11,12,13]',
    wander_probability = 0.03
WHERE id = 3;

-- Guy (character_id=4): sleeping human; slightly more restless than Mama.
-- Same physical access as Mama — everywhere except the Tiled Overlook.
UPDATE character
SET wander_range       = '[1,2,3,4,5,6,7,9,10,11,12,13]',
    wander_probability = 0.05
WHERE id = 4;

-- Lillis (character_id=5): bird in a portable cage. Cannot move autonomously.
-- wander_range=[6] (Basement Main Room only) and wander_probability=0.0
-- ensures the engine never attempts to move Lillis; wander_range records
-- the single location where the cage currently sits.
UPDATE character
SET wander_range       = '[6]',
    wander_probability = 0.0
WHERE id = 5;
