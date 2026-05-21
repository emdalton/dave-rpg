-- =============================================================================
-- DAVE RPG Engine — Module: I Am a Cat
-- Seed data for schema v4 additions
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Applies to: modules/i_am_a_cat/i_am_a_cat.db (after migrate_v3_to_v4.sql)
--
-- Contents:
--   Visited location records for Toulouse (character_id=1).
--   Toulouse knows every room in the house — this is her territory and she has
--   explored every corner of it. All 11 locations are pre-marked as visited.
--
--   Human NPCs and Lillis are not given visited records; their movement is
--   engine-driven (wander) or LLM-driven (reactive), not player quick-move,
--   so the visited table is not consulted for them.
--
--   The player's knowledge of the house accumulates through play. When Toulouse
--   (as controlled by the player) enters a location, the engine marks it visited.
--   For this module, since Toulouse already knows the house, all locations are
--   seeded as visited so the player can quick-move from the first turn.
--
-- Location ID reference:
--   Main floor:  1=Living Room, 2=Dining Room, 3=Kitchen,
--                4=Laundry Room, 5=Main Stairs
--   Basement:    6=Basement Main Room, 7=Basement Storage Room
--   Upper floor: 8=Tiled Overlook, 9=Bathroom, 10=Bedroom, 11=Study
-- =============================================================================

INSERT OR IGNORE INTO character_visited_location (character_id, location_id)
VALUES
    (1, 1),   -- Toulouse: Living Room
    (1, 2),   -- Toulouse: Dining Room
    (1, 3),   -- Toulouse: Kitchen
    (1, 4),   -- Toulouse: Laundry Room
    (1, 5),   -- Toulouse: Main Stairs
    (1, 6),   -- Toulouse: Basement Main Room
    (1, 7),   -- Toulouse: Basement Storage Room
    (1, 8),   -- Toulouse: Tiled Overlook
    (1, 9),   -- Toulouse: Bathroom
    (1, 10),  -- Toulouse: Bedroom
    (1, 11),  -- Toulouse: Study
    (1, 12);  -- Toulouse: Upper Hallway
