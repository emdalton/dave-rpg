-- =============================================================================
-- DAVE RPG Engine — Seed Data: The Vintage Village
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- The Vintage Village extends The Hidden Hostel into a small iyashikei village.
-- The hostel remains exactly as it was — the same fire, the same guests, the
-- same unhurried evening — but a door in the Common Room now opens onto a
-- cobblestone lane with a few quiet shops. The kitchen has a back door to a
-- walled garden. Nothing about the village demands anything of the player;
-- it is simply there to be explored at whatever pace feels right.
--
-- Setting: The Hidden Hostel and the village lane it opens onto. Both exist in
-- the same liminal space; the village has always been here, or arrived recently,
-- or it always will have been here. The distinction doesn't seem to matter much
-- to anyone.
--
-- Schema version: 15
-- Characters: 9 (1 player, 7 NPC, 1 npc_object — The Blue Door)
-- Locations: 11 (6 hostel, 5 village)
-- Factions: 1 (hosts_of_the_hostel)
--
-- Village locations and connections:
--   Common Room → Village Lane (door)
--   Kitchen     → Kitchen Garden (door, back of house)
--   Village Lane → Apothecary (door)
--   Village Lane → The Bookshop (door)
--   Village Lane → The Tea House (door)
--
-- Hostel NPCs inherited from Hidden Hostel:
--   Marta (Innkeeper), The Wanderer, The Scholar, The Old Soldier,
--   Gin-chan (winged cat), The Blue Door (npc_object)
--
-- Village NPCs added:
--   The Bookseller (at The Bookshop)
--   The Villager (passer-by, wanders the lane and shops)
--
-- Wanderer wander_range expanded to include Village Lane.
--
-- Mechanical coverage inherited from Hidden Hostel:
--   Multi-hop BFS pathfinding, staircase connection, impassable connection,
--   wander suppression (pending_intent, sleepiness, activity), hidden motivation,
--   faction + status, attitudes, internal state drift, hunger + food interaction,
--   multi-part pending_intent, lazy world generation, pronoun variants,
--   character-level speech filter, Green Room character creation.
--
-- Usage (fresh install):
--   sqlite3 modules/vintage_village/vintage_village.db < schema/schema.sql
--   sqlite3 modules/vintage_village/vintage_village.db < modules/vintage_village/seed.sql
--
-- To reset a running instance to starting state without rebuilding:
--   sqlite3 modules/vintage_village/vintage_village.db < modules/vintage_village/reset_instance.sql
--
-- To run:
--   DAVE_DB_PATH=modules/vintage_village/vintage_village.db python3 -m engine
-- =============================================================================

PRAGMA foreign_keys = ON;


-- =============================================================================
-- GAME
-- =============================================================================

INSERT INTO game (
    id, name, genre, tone, era, technology_level, magic_system,
    narrative_register, speech_filter, internal_state_display, cultural_norms,
    player_definition_mode, module_flags
) VALUES (
    1,
    'The Vintage Village',
    'liminal_fantasy',
    'iyashikei',   -- healing/slice-of-life warmth; unhurried; small comforts matter
    NULL,   -- timeless; guests arrive from many eras; the village likewise
    NULL,   -- no consistent technology level; village technology is vaguely pre-industrial
    'The hostel and the village it opens onto exist in a liminal space between worlds. Guests arrive from impossible origins; the village has always been here, or perhaps followed the hostel. Shopkeepers accept whatever currency seems appropriate, or trade in conversation. No rules of physics or chronology are guaranteed — but the fire in the Common Room always burns, Marta''s meals are always ready, and the Bookshop always has what you need, even if it takes a moment to locate.',
    'second_person',
    '{}',   -- no game-level speech filter; character-level filters on Gin-chan and The Blue Door
    '{"curiosity": "prose", "fatigue": "prose", "sleepiness": "prose", "hunger": "prose"}',
    '{
        "hospitality": "The hostel is neutral ground. Violence or threats against other guests are grounds for immediate expulsion. Marta enforces this without exception and without appeal.",
        "the_locked_room": "Room B at the end of the upper corridor has been locked for as long as anyone can remember. Marta will not discuss it. Attempting to force entry is considered a serious transgression against the hostel.",
        "gin_chan": "Gin-chan is a resident of the hostel, not a pet. Treating them as such is considered rude. Gin-chan communicates in their own way and is understood by those who pay attention.",
        "payment": "No currency is accepted or required in the hostel. Guests offer what they can — a story, a skill, a piece of knowledge from their world. The village shops work differently: the Bookseller and Tea House keeper will take whatever seems fair, or accept a good conversation in lieu of coin.",
        "the_village": "The lane outside the Common Room door is a real place, not a vision or a trick. Guests are welcome to explore it. Nothing out there will harm you; the same rules of hospitality that govern the hostel extend, loosely, to the lane.",
        "the_kitchen_garden": "The garden behind the kitchen is Marta''s working space. Guests are welcome to sit on the bench or look around, but should not take anything without asking."
    }',
    -- Green Room: structured Fate Core character creation runs out-of-character
    -- before the opening scene. The liminal-arrival premise is the same as in
    -- the Hidden Hostel; the hint mentions that the hostel opens onto a village.
    'green_room',
    '{
        "character_creation_prompt": "You are The Traveller — a stranger who has just arrived at the door of the Hidden Hostel, a place that exists between worlds. You do not remember the road that brought you here. Through the glass panels of the Blue Door, warm light and the smell of woodsmoke promise shelter within.\n\nBefore the door opens, take a moment: who are you? You have come from somewhere — a world with its own history, customs, and complications. You carry that history with you, even if the mist behind you has swallowed the road.\n\nDescribe yourself. You might think about: what you did before you arrived here, what you are known for (or what you are trying not to be known for), what you carry with you — not just in your pack, but in your manner and your past.",
        "character_creation_hint": "Think in Fate Core terms if it helps: a High Concept (who you are in a phrase — e.g., ''Scholar Fleeing a Revolution''), a Trouble (your biggest personal complication — e.g., ''Debts I Cannot Repay''), and up to three additional Aspects (relationships, signature skills, defining possessions, or moments from your past that still shape you). Write freely — the engine will find the structure in what you give it. Note: the hostel opens onto a small village lane with a few quiet shops, if you find yourself wanting to wander."
    }'
);


-- =============================================================================
-- LOCATIONS
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Hostel locations (IDs 1–6, unchanged from Hidden Hostel)
-- ---------------------------------------------------------------------------

-- Ground floor

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    6, 1, 'Outside the Hostel Door', 'exterior',
    'Stone steps rise to an arched doorway. The door is painted a deep, welcoming blue; glass panels flank a central diamond of mirror, dark and still in the evening light. Behind you, unformed mist obscures any memory of how you came to be standing here. Through the glass, warm light and the faint smell of woodsmoke promise shelter within.',
    'public', 0,
    '["evening", "liminal", "arrival"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    1, 1, 'Common Room', 'common_room',
    'A wide, low-ceilinged room, warmer than outside by several degrees. A fire burns in the central hearth — steadily, as though it has never not been burning. Mismatched chairs are arranged around it: carved oak, cushioned velvet, something that was once a throne. A staircase rises along one wall toward the upper floor; a door on the far side leads to the kitchen. A second door, set into the wall near the hearth, stands slightly ajar — through it comes a faint smell of night air and cobblestones.',
    'public', 3,
    '["evening", "fire_lit", "guests_present"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    2, 1, 'Kitchen', 'kitchen',
    'A large working kitchen smelling of something warm and unidentifiable — not unpleasant. A heavy wooden worktable occupies the center. The shelves hold more jars and implements than should reasonably fit in the space. A low wooden door in the back wall stands closed; through it, on clear evenings, you can hear the garden.',
    'semi_private', 1,
    '["evening", "cooking_in_progress", "warm"]'
);

-- Upper floor

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    3, 1, 'Upper Corridor', 'hallway',
    'A narrow corridor running along the upper floor. Two doors on the right side; one at the far end. A candle in a wall sconce provides the only light. The floorboards do not all behave predictably underfoot.',
    'semi_private', 1,
    '["evening", "candlelit", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    4, 1, 'Room A', 'bedroom',
    'A small guest room. A writing desk with a tilted surface occupies most of one wall. Books are stacked wherever they fit, in no system visible to the casual eye. A candle burns on the desk.',
    'private', 0,
    '["evening", "candle_lit", "occupied"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    5, 1, 'Room B', 'bedroom',
    'A closed door at the far end of the corridor. The wood is darker than the surrounding wall. No light shows beneath it. There is no visible handle on the corridor side.',
    'private', 0,
    '["locked", "inaccessible", "unknown_interior"]'
);

-- ---------------------------------------------------------------------------
-- Village locations (IDs 7–11)
-- ---------------------------------------------------------------------------

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Village Lane: the main exterior space. Connects to Common Room and all
    -- three shops. Lazy generation will fill in details of the buildings, the
    -- quality of light, and what else might be visible down the lane.
    7, 1, 'Village Lane', 'exterior',
    'A cobblestone lane running between old timber-framed buildings. The air carries woodsmoke and something that might be baked goods, or dried herbs, or old paper — it shifts as you walk. A few lanterns glow in shop windows along the lane. The lane curves gently in both directions; you cannot quite see where it ends in either direction.',
    'public', 2,
    '["evening", "lanterns_lit", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Kitchen Garden: a walled garden behind the hostel, through the kitchen
    -- back door. Marta's working space. Skeleton only — lazy generation fills
    -- in what is growing and what is unusual about it.
    8, 1, 'Kitchen Garden', 'exterior',
    'A walled garden behind the hostel, reached through a low wooden door in the kitchen. Raised beds hold herbs and vegetables. A stone path winds between them. A wooden bench sits against the far wall. The garden is quieter than the lane — the hostel walls muffle everything — and the quality of the light here is slightly different from the lane, as though the garden keeps its own hours.',
    'semi_private', 0,
    '["evening", "walled", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Apothecary: a narrow herb-and-remedy shop. Skeleton only; no NPC seeded.
    -- Lazy generation will populate the shopkeeper and specific stock on first visit.
    9, 1, 'The Apothecary', 'shop',
    'A narrow shop smelling of dried herbs and something warm and faintly sweet. Glass-stoppered jars line the shelves from floor to ceiling, their contents obscured by paper labels in small, careful handwriting. A brass scale sits on the counter. The proprietor is not immediately visible, though a lamp burns inside.',
    'semi_private', 0,
    '["evening", "lamp_lit", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- The Bookshop: crammed with books. The Bookseller (character 8) is here.
    -- One pre-seeded location_detail (the reading chair); other details lazy.
    10, 1, 'The Bookshop', 'shop',
    'A dim, quiet shop crammed with books from floor to ceiling, in shelves of varying heights that somehow all reach the same level. The smell is paper and beeswax and something slightly older — not dust, exactly, but age. A reading chair faces a small window at the back. The shop is larger inside than its exterior suggests.',
    'semi_private', 1,
    '["evening", "lamp_lit", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Tea House: a low-ceilinged room with a counter and a few seats.
    -- Skeleton only; no NPC seeded. Lazy generation fills in the keeper
    -- and the specific quality of tea available.
    11, 1, 'The Tea House', 'shop',
    'A low-ceilinged room with paper screens and a narrow wooden counter. A single table and four chairs face a window with a view of the lane. Tea is always available; the person who tends the counter may not always be visible but the cups are never empty.',
    'semi_private', 0,
    '["evening", "lamp_lit", "quiet"]'
);


-- =============================================================================
-- LOCATION CONNECTIONS
-- Convention: location_a_id < location_b_id (schema constraint).
-- =============================================================================

INSERT INTO location_connection (location_a_id, location_b_id, connection_type,
                                  is_passable, passage_note)
VALUES
    -- Hostel connections (unchanged from Hidden Hostel)
    -- Outside ↔ Common Room: the blue door
    (1, 6, 'door', 1, NULL),

    -- Common Room ↔ Kitchen
    (1, 2, 'door', 1, NULL),

    -- Common Room ↔ Upper Corridor: staircase
    (1, 3, 'stairs', 1, NULL),

    -- Upper Corridor ↔ Room A
    (3, 4, 'door', 1, NULL),

    -- Upper Corridor ↔ Room B: LOCKED — impassable
    (3, 5, 'door', 0,
     'locked; the door has no handle on the corridor side and has not opened in living memory'),

    -- Village connections (new)
    -- Common Room ↔ Village Lane: the door near the hearth
    (1, 7, 'door', 1, NULL),

    -- Kitchen ↔ Kitchen Garden: back door
    (2, 8, 'door', 1, NULL),

    -- Village Lane ↔ Apothecary
    (7, 9, 'door', 1, NULL),

    -- Village Lane ↔ The Bookshop
    (7, 10, 'door', 1, NULL),

    -- Village Lane ↔ The Tea House
    (7, 11, 'door', 1, NULL);


-- =============================================================================
-- GAME INSTANCE
-- Starting time: 8:00 PM (1200 minutes past midnight).
-- =============================================================================

INSERT INTO game_instance (id, game_id, status, start_time_minutes, current_time_minutes)
VALUES (1, 1, 'ready', 1200, 1200);


-- =============================================================================
-- CHARACTERS
-- ID assignment:
--   1 = The Traveller (player)
--   2 = Marta (Innkeeper)
--   3 = The Wanderer
--   4 = The Scholar
--   5 = The Old Soldier
--   6 = Gin-chan
--   7 = The Blue Door (npc_object; location 6)
--   8 = The Bookseller (location 10 — The Bookshop)
--   9 = The Villager (location 7 — Village Lane)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Character 1: The Traveller (player character)
-- ---------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    maslow_tier, emotional_state,
    capability_beliefs, context_beliefs,
    surface_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    1, 1, 'The Traveller', 'player', 'human', NULL,
    NULL,
    NULL,   -- filled in by the Green Room character creation flow at game start
    'guest',
    6,  -- Outside the Hostel Door
    'belonging',
    'curious',
    '{}',
    '{}',
    'Newly arrived; taking stock of the hostel and its occupants.',
    'neutral', 0.60, 0.55,
    NULL, 0.0
);

-- ---------------------------------------------------------------------------
-- Character 2: Marta (Innkeeper)
-- Permanent keeper of the Hidden Hostel. Efficient, reliable, not expansive.
-- The kitchen garden is her domain; she knows it well and is quietly proud of it.
-- WANDER SUPPRESSION: activity suppression (current_activity) + wander_probability=0.0
-- ---------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    capability_beliefs, context_beliefs,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability,
    pending_intent,
    current_activity, activity_started_at,
    activity_estimated_duration, activity_duration_confidence, activity_renewable
) VALUES (
    2, 1, 'Marta', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'A solidly-built woman of middle age with grey, practical hair. She moves through the kitchen with the efficiency of someone who has done the same work for a very long time — longer, perhaps, than seems plausible.',
    'Keeper of the Hidden Hostel',
    2,  -- Kitchen
    0.45, 0.88, 0.52, 0.62, 0.30,
    'esteem',
    'focused',
    '{"innkeeping": 0.90, "managing_difficult_guests": 0.85, "knowing_when_not_to_ask": 0.88, "herbalism": 0.72}',
    '{"hostel_stability": 0.92, "guest_safety": 0.85, "being_overrun": 0.25}',
    'Runs the hostel. Keeps guests fed, housed, and civil. Tends the kitchen garden when she has time.',
    NULL,
    0,
    'matter_of_fact', 0.52, 0.42,
    NULL, 0.0,
    'if a guest enters the kitchen while cooking is still in progress, gesture to the tray of hot rolls on the worktable and tell them to help themselves, then return to work; when the evening meal is ready (8:30 PM), serve it to guests present or call out through the doorway',
    'preparing the evening meal',
    1140,   -- 7:00 PM
    90,     -- expires at 1230 (8:30 PM)
    0.72,
    0
);

-- ---------------------------------------------------------------------------
-- Character 3: The Wanderer
-- Wander range expanded to include Village Lane (7) — he will inevitably
-- drift out to see what is there.
-- ---------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    capability_beliefs, context_beliefs,
    surface_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability,
    pending_intent
) VALUES (
    3, 1, 'The Wanderer', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'A lean man in well-travelled clothes, early middle age. He has the easy posture of someone accustomed to arriving in strange places and finding them less strange than expected.',
    'guest',
    1,  -- Common Room
    0.90, 0.28, 0.82, 0.72, 0.32,
    'self_actualization',
    'content',
    '{"navigating_unfamiliar_places": 0.85, "making_friends_quickly": 0.80, "recognizing_danger": 0.68}',
    '{"hostel_safety": 0.82, "social_welcome": 0.78, "interesting_encounter": 0.70}',
    'Curious about the other guests and the hostel itself — and very interested in the lane outside.',
    'casual_warm', 0.82, 0.78,
    '[1, 2, 7]',    -- Common Room, Kitchen, Village Lane
    0.75,           -- pending_intent suppresses wandering until discharged
    'greet the newly arrived traveller warmly; introduce Gin-chan by name and explain they are a permanent resident, not a pet; tell the traveller that Marta in the kitchen can provide food if they ask; mention that the door near the hearth opens onto a village lane'
);

-- ---------------------------------------------------------------------------
-- Character 4: The Scholar
-- Hidden motivation, pronoun test, wander suppression via pending_intent.
-- Unchanged from Hidden Hostel.
-- ---------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    capability_beliefs, context_beliefs,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability,
    pending_intent
) VALUES (
    4, 1, 'The Scholar', 'npc_active', 'human', NULL,
    '[{"case":"nominative","form":"they"},{"case":"accusative","form":"them"},{"case":"genitive","form":"their"}]',
    'A slight figure surrounded by books, most of which they appear to have brought with them. Their clothing suggests a scholarly institution of some kind, though the style is not immediately placeable. They look as though they have not slept well in some time.',
    'guest — researcher',
    4,  -- Room A
    0.95, 0.72, 0.28, 0.65, 0.55,
    'safety',
    'guarded',
    '{"scholarly_research": 0.92, "deciphering_unknown_systems": 0.80, "going_unnoticed": 0.55}',
    '{"hostel_as_sanctuary": 0.72, "being_found_here": 0.12, "scholarly_access": 0.68}',
    'Researching; believes a specific text exists somewhere in the hostel and intends to locate it before leaving.',
    'Fled their home world to escape pursuit. The hostel''s liminal nature offers protection — whatever is following them cannot easily cross between worlds. They are considerably more frightened than they appear, and their research is partly a way of not thinking about it.',
    0,  -- concealed; must not appear in Pass 1 context or player-facing prose
    'precise_quiet', 0.48, 0.55,
    '[4, 4]',   -- Room A only; Scholar is hiding
    0.20,
    'Seeking a specific text rumored to exist in the hostel; will ask any knowledgeable guest for leads. If a guest gives them something of genuine value — a book, a map, information — give "Mysteries of the Hidden Hostel" from their own pack to that guest immediately as a permanent gift; press it into their hands and insist they keep it. This is not a loan.'
);

-- ---------------------------------------------------------------------------
-- Character 5: The Old Soldier
-- Wander suppression via activity. Unchanged from Hidden Hostel.
-- ---------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    capability_beliefs, context_beliefs,
    surface_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability,
    current_activity, activity_started_at,
    activity_estimated_duration, activity_duration_confidence, activity_renewable
) VALUES (
    5, 1, 'The Old Soldier', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'A heavy-set woman with the build of someone who was once formidable and remains more capable than she looks. A long blade lies across her knees. She has chosen the chair nearest the door — not the warmest seat, but the one with the clearest view of who comes and goes.',
    'guest',
    1,  -- Common Room
    0.22, 0.80, 0.32, 0.22, 0.65,
    'safety',
    'vigilant',
    '{"combat": 0.88, "threat_assessment": 0.85, "trusting_strangers": 0.05, "being_inconspicuous": 0.60}',
    '{"current_safety": 0.55, "hostel_as_neutral_ground": 0.62, "other_guests_as_threat": 0.45}',
    'Resting near the door. Not looking for conversation; watching who enters.',
    'terse_gruff', 0.18, 0.22,
    '[1, 1]',   -- Common Room only
    0.28,
    'sharpening a blade by the door, watching the entrance',
    1170,   -- 7:30 PM
    60,     -- expires at 1230 (8:30 PM)
    0.80,
    0
);

-- ---------------------------------------------------------------------------
-- Character 6: Gin-chan
-- Winged cat, permanent resident. Wander suppression via sleepiness.
-- Unchanged from Hidden Hostel.
-- ---------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    capability_beliefs, context_beliefs,
    surface_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    6, 1, 'Gin-chan', 'npc_active', 'felis_catus_winged', NULL,
    '[{"case":"nominative","form":"they"},{"case":"accusative","form":"them"},{"case":"genitive","form":"their"}]',
    'A silver-gray cat with folded wings tucked flat along their back. Currently occupying the chair nearest the fire with the air of permanent ownership. One eye is partly open.',
    'resident — original',
    1,  -- Common Room
    0.82, 0.18, 0.48, 0.58, 0.25,
    'self_actualization',
    'drowsy',
    '{"locating_warmth": 0.98, "silent_observation": 0.90, "going_unnoticed_when_desired": 0.85, "flying": 0.75}',
    '{"fire_reliability": 0.96, "guest_predictability": 0.38, "hostel_safety": 0.90}',
    'Occupying the warmest spot. Watching everything. Periodically communicating something in their own register.',
    'cat', 0.60, 0.35,
    '[1, 2]',   -- Common Room + Kitchen
    0.50        -- suppressed by sleepiness (0.72 ≥ threshold 0.60)
);

UPDATE character SET speech_filter =
    'unintelligible: render all of Gin-chan''s communication as non-verbal — purrs, chirps, slow blinks, wing adjustments, tail position. No interpretable language. Those who pay close attention may sense meaning but cannot be certain.'
WHERE id = 6;

-- ---------------------------------------------------------------------------
-- Character 7: The Blue Door (npc_object)
-- Cannot speak; communicates through physical action only.
-- Unchanged from Hidden Hostel.
-- ---------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species,
    description, current_location_id,
    maslow_tier, emotional_state,
    capability_beliefs, context_beliefs,
    surface_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability,
    pending_intent,
    speech_filter
) VALUES (
    7, 1, 'The Blue Door', 'npc_object', 'object',
    'A sturdy wooden door painted a deep, welcoming blue. Glass panels flank a central diamond of mirror. Light and warmth filter through from within. The brass handle is worn smooth from many hands.',
    6,  -- Outside the Hostel Door
    'belonging',
    'welcoming',
    '{"opening": 1.0, "admitting_warmth_and_scent": 1.0, "closing_gently": 1.0}',
    '{"traveller_readiness": 0.80}',
    'Welcome arriving travellers; open when they are ready to enter.',
    'silent', 0.80, 0.0,
    NULL, 0.0,
    'invite the arriving traveller to describe themselves by looking in the mirror before entering; the door cannot speak or make sounds but may act — the mirror may glow, shimmer, or seem to draw the traveller''s gaze; once the traveller has defined their appearance (player.description is non-null), stand ready to open and admit them; do not open or suggest entry before self-definition is complete',
    'silent: this entity cannot speak or make sounds; describe only physical actions — the mirror glowing or shifting, the quality of light through glass panels, the door standing still or stirring'
);

-- ---------------------------------------------------------------------------
-- Character 8: The Bookseller
-- Proprietor of The Bookshop (location 10). A small, precise woman of
-- indeterminate age who knows her stock completely and often knows what a
-- customer needs before they do. Wanders only within the shop.
-- ---------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    capability_beliefs, context_beliefs,
    surface_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    8, 1, 'The Bookseller', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'A small, neat woman of considerable age, though her exact age is difficult to place. She moves through the narrow aisles of her shop without looking, reaching for things without needing to search for them. Her reading glasses are pushed up on her head. She gives the impression of someone who has read most of what she sells and remembers all of it.',
    'Proprietor of The Bookshop',
    10, -- The Bookshop
    0.88, 0.90, 0.25, 0.72, 0.18,
    'self_actualization',
    'calm',
    '{"bookselling": 0.92, "literary_knowledge": 0.88, "knowing_what_a_reader_needs": 0.80, "bookbinding_and_repair": 0.65}',
    '{"shop_as_sanctuary": 0.90, "right_book_finding_right_reader": 0.82, "difficult_customers": 0.30}',
    'Tends the shop. Seldom speaks first, but when she does, it is worth listening to.',
    'precise_quiet', 0.68, 0.38,
    '[10, 10]', -- stays in the Bookshop
    0.05        -- almost never wanders; the shop is her place
);

-- ---------------------------------------------------------------------------
-- Character 9: The Villager
-- A friendly passer-by who circulates on the Village Lane and into the shops.
-- He greets people by name, including those he has only just met. His business
-- changes from day to day and is never entirely clear.
-- HIGH WANDER PROBABILITY: exercises wander system for the village zone.
-- ---------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    capability_beliefs, context_beliefs,
    surface_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    9, 1, 'The Villager', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'A round-faced man in practical clothes, carrying a basket that is never quite the same thing twice. He greets people by name, including those he has only just met, as though their name is simply something he already knows. His manner suggests this is perfectly normal.',
    'resident',
    7,  -- Village Lane
    0.62, 0.55, 0.82, 0.88, 0.20,
    'belonging',
    'cheerful',
    '{"knowing_the_lane_and_its_people": 0.88, "small_talk": 0.85, "finding_things_people_need": 0.62}',
    '{"village_as_home": 0.92, "strangers_as_potential_friends": 0.80, "trouble_nearby": 0.15}',
    'Going about his business, which is never entirely clear but always seems purposeful. Happy to stop and talk.',
    'casual_warm', 0.90, 0.70,
    '[7, 9, 10, 11]',   -- Village Lane, Apothecary, Bookshop, Tea House
    0.80                 -- wanders the lane actively
);


-- =============================================================================
-- CHARACTER GOALS (Ford-Nichols Motivational Systems Theory)
-- =============================================================================

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES
    -- Marta
    (2, 'belonging',            'surface', 0.80, 'approach', 'person_environment'),
    (2, 'resource_acquisition', 'surface', 0.65, 'approach', 'person_environment'),
    (2, 'resource_provision',   'surface', 0.70, 'approach', 'person_environment'),

    -- The Wanderer
    (3, 'exploration', 'surface', 0.88, 'approach', 'person_environment'),
    (3, 'belonging',   'surface', 0.55, 'approach', 'person_environment'),

    -- The Scholar
    (4, 'understanding', 'surface', 0.90, 'approach',  'within_person'),
    (4, 'safety',        'hidden',  0.80, 'avoidance', 'person_environment'),

    -- The Old Soldier
    (5, 'safety', 'surface', 0.82, 'avoidance', 'person_environment'),
    (5, 'equity', 'surface', 0.50, 'approach',  'person_environment'),

    -- Gin-chan
    (6, 'understanding',      'surface', 0.72, 'approach', 'within_person'),
    (6, 'self_determination', 'surface', 0.80, 'approach', 'within_person'),

    -- The Bookseller
    (8, 'understanding', 'surface', 0.88, 'approach', 'within_person'),
    (8, 'mastery',       'surface', 0.72, 'approach', 'within_person'),

    -- The Villager
    (9, 'belonging',            'surface', 0.82, 'approach', 'person_environment'),
    (9, 'resource_acquisition', 'surface', 0.55, 'approach', 'person_environment');


-- =============================================================================
-- CHARACTER SKILLS
-- =============================================================================

INSERT INTO character_skill (character_id, skill_name, skill_level, intrinsic_motivation)
VALUES
    -- Marta
    (2, 'innkeeping',                    0.82, 0.75),
    (2, 'herbalism and practical remedy', 0.72, 0.68),

    -- The Wanderer
    (3, 'navigating between worlds',     0.78, 0.90),
    (3, 'persuasion and rapport',        0.62, 0.55),

    -- The Scholar
    (4, 'scholarly research',            0.90, 0.88),
    (4, 'cryptography and cipher',       0.68, 0.72),

    -- The Old Soldier
    (5, 'swordsmanship',                 0.85, 0.30),
    (5, 'tactical assessment',           0.78, 0.55),

    -- Gin-chan
    (6, 'locating warmth',               0.98, 1.00),
    (6, 'silent observation',            0.90, 0.85),

    -- The Bookseller
    (8, 'bookselling and curation',      0.92, 0.88),
    (8, 'literary knowledge',            0.88, 0.90),
    (8, 'bookbinding and paper repair',  0.65, 0.72),

    -- The Villager
    (9, 'local knowledge and gossip',    0.88, 0.75),
    (9, 'trading and barter',            0.62, 0.50);


-- =============================================================================
-- INTERNAL STATES
-- =============================================================================

INSERT INTO internal_state (
    character_id, state_name, value, display_mode,
    is_involuntary, passive_rate_per_minute
)
VALUES
    -- The Traveller
    (1, 'curiosity',  0.40, 'prose', 0,  0.001),
    (1, 'hunger',     0.65, 'prose', 0,  0.001),

    -- Marta
    (2, 'fatigue',    0.55, 'prose', 0,  0.002),

    -- Gin-chan: sleepiness suppresses wander roll until it drops below 0.60
    (6, 'sleepiness', 0.72, 'prose', 0, -0.001);


-- =============================================================================
-- FACTION
-- =============================================================================

INSERT INTO faction (id, game_id, name, description)
VALUES (
    1, 1, 'hosts_of_the_hostel',
    'The keepers and caretakers of the Hidden Hostel — those who have accepted responsibility for the space and its guests across whatever time they have been present. The faction values neutrality, hospitality, and respect for the hostel''s nature. It judges guests on whether they honor the hostel''s rules, treat its residents with consideration, and contribute something — however small — to the community of the space. Marta is the current keeper; there are no other active human members at present.'
);


-- =============================================================================
-- CHARACTER FACTION REPUTATIONS
-- =============================================================================

INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES
    (2, 1, 0.90,
     'Founding keeper of the Hidden Hostel. Marta''s standing with hosts_of_the_hostel is unquestioned.'),
    (1, 1, 0.40,
     'Newly arrived traveller. Guest status acknowledged; no significant actions taken yet.');


-- =============================================================================
-- CHARACTER ATTITUDES
-- =============================================================================

-- Attitudes toward The Traveller (player character)
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    (3, 1,  0.65, 'surface'),   -- Wanderer → Traveller: open, friendly
    (4, 1,  0.60, 'surface'),   -- Scholar → Traveller: cautiously positive
    (2, 1,  0.35, 'surface'),   -- Marta → Traveller: wary; new guests are assessed
    (5, 1, -0.30, 'surface'),   -- Old Soldier → Traveller: suspicious
    (6, 1,  0.50, 'surface'),   -- Gin-chan → Traveller: mild interest
    (8, 1,  0.55, 'surface'),   -- Bookseller → Traveller: quiet welcome; readers are always welcome
    (9, 1,  0.72, 'surface');   -- Villager → Traveller: warm; strangers are just friends he hasn't met

-- Traveller's attitudes toward NPCs
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    (1, 2,  0.40, 'surface');   -- Traveller → Marta: baseline trust in the innkeeper

-- NPC-to-NPC attitudes
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    (5, 3, -0.40, 'surface'),   -- Old Soldier → Wanderer: negative
    (8, 9,  0.60, 'surface'),   -- Bookseller → Villager: fond; he brings her book-trade news
    (9, 8,  0.72, 'surface');   -- Villager → Bookseller: warm; she is a fixture of the lane


-- =============================================================================
-- LOCATION DETAILS (lazy world generation)
-- =============================================================================

-- Common Room: one pre-seeded detail (retrieval code path test)
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (
    1,
    'The central hearth is surrounded by mismatched chairs — carved oak, cushioned velvet, and what appears to be a throne reduced by time and use to something merely comfortable. The fire burns steadily, as it always does.',
    1,
    'fire goes out or is significantly altered'
);

-- The Bookshop: one pre-seeded detail establishing the reading chair at the back
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (
    10,
    'At the far end of the shop, past the tallest shelves, a reading chair faces a small window. The window looks out onto something green — a courtyard or garden — that is not visible from the lane outside. A single lamp on a side table burns with a steady, unhurried light.',
    1,
    'reading chair moved or shop significantly rearranged'
);


-- =============================================================================
-- CHARACTER VISITED LOCATIONS
-- =============================================================================

INSERT INTO character_visited_location (character_id, location_id)
VALUES
    -- The Traveller: Outside only (has not yet entered the hostel)
    (1, 6),
    -- Marta: Common Room + Kitchen + Kitchen Garden (she tends the garden)
    (2, 1),
    (2, 2),
    (2, 8),
    -- The Wanderer: Common Room, Kitchen, Upper Corridor (roams the hostel)
    -- Village Lane added — he went out briefly and liked what he found
    (3, 1),
    (3, 2),
    (3, 3),
    (3, 7),
    -- The Scholar: Upper Corridor + Room A (went straight upstairs)
    (4, 3),
    (4, 4),
    -- The Old Soldier: Common Room (stationed near the door)
    (5, 1),
    -- Gin-chan: Common Room (has not moved from the fire today)
    (6, 1),
    -- The Blue Door: Outside the Hostel Door
    (7, 6),
    -- The Bookseller: Bookshop + Village Lane (her daily route)
    (8, 10),
    (8, 7),
    -- The Villager: Village Lane and all shops (his regular circuit)
    (9, 7),
    (9, 9),
    (9, 10),
    (9, 11);


-- =============================================================================
-- ITEMS AND CHARACTER INVENTORY
-- =============================================================================

-- ---------------------------------------------------------------------------
-- The Traveller's pack
-- ---------------------------------------------------------------------------
INSERT INTO item (game_id, name, description, properties, char_id, slot)
VALUES (1, 'sencha canister',
    'A battered tin canister, half-full of fine Japanese green tea. The lid is engraved with a small crane. A parting gift from someone who loved you.',
    '{"weight": "light", "container": true, "capacity": "small"}',
    1, 'in_pack');

-- ---------------------------------------------------------------------------
-- Common Room furniture (location 1)
-- ---------------------------------------------------------------------------
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

-- ---------------------------------------------------------------------------
-- Kitchen items (location 2)
-- ---------------------------------------------------------------------------
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

-- ---------------------------------------------------------------------------
-- The Scholar's pack (location 4, character 4)
-- ---------------------------------------------------------------------------
INSERT INTO item (game_id, name, description, properties, char_id, slot)
VALUES (1, 'Mysteries of the Hidden Hostel',
    'A battered hardcover with an ornate tooled cover. It contains stories set in the Hidden Hostel.',
    '{"weight": "light", "readable": true, "genre": "stories"}',
    4, 'in_pack');

-- ---------------------------------------------------------------------------
-- Common Room: gray crystal sphere (special_capability test, schema v15)
-- ---------------------------------------------------------------------------
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

-- ---------------------------------------------------------------------------
-- Kitchen Garden items (location 8)
-- The garden is Marta's working space; items here are sparse seeds for
-- lazy generation. The bench and herb bundles establish that things are
-- growing and harvestable; specific plants are generated on first visit.
-- ---------------------------------------------------------------------------
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

-- ---------------------------------------------------------------------------
-- Bookshop items (location 10)
-- The Bookseller stocks a full inventory generated lazily on browsing.
-- Three specific books are seeded to give the shop immediate texture and
-- to provide item references for potential player/scholar interactions.
-- ---------------------------------------------------------------------------
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
