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
-- Tonal references:
--   Aria (anime series, 2005–2008): a terraformed, flooded Mars whose inhabitants
--   have reconstructed Venice. A young gondolier apprentice explores the city in
--   episodes that are almost entirely minor tasks and quiet discoveries. The voice
--   actresses described the show as "nothing ever happens, but in a really nice way."
--   This is the intended feel of the Vintage Village quest system.
--
--   Studio Ghibli (general): the warmth, the found-family households, the sense
--   that ordinary domestic life is worth lingering over, the way magic is matter-of-fact
--   rather than dramatic. My Neighbor Totoro, Kiki's Delivery Service, and
--   Spirited Away are the closest tonal relatives.
--
-- Setting: The Hidden Hostel and the village lane it opens onto. Both exist in
-- the same liminal space; the village has always been here, or arrived recently,
-- or it always will have been here. The distinction doesn't seem to matter much
-- to anyone.
--
-- Schema version: 15
-- Characters: 10 (1 player, 8 NPC, 1 npc_object — The Blue Door)
-- Locations: 27 (6 hostel, 21 village — civic core, trade district, river zone, 2 farms)
-- Connections: 26
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
    -- Tea House: a small room tucked into the shrine garden. Not on the lane;
    -- reached only through the shrine gate. Paper screens, a narrow counter,
    -- a window facing the garden rather than the lane. Skeleton only; no NPC
    -- seeded. Lazy generation fills in the keeper and the quality of tea.
    11, 1, 'The Tea House', 'tea_house',
    'A small, low-ceilinged room tucked into the corner of the shrine garden, reachable only through the shrine gate. Paper screens diffuse the lamplight into something softer than light usually is. A narrow counter, a single table, four chairs. The window faces the garden and the old tree, not the lane. Tea is always available; whoever tends the counter is not always immediately visible, but the cups are never empty and the water is always hot.',
    'semi_private', 0,
    '["evening", "lamp_lit", "quiet", "garden"]'
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
    (7, 10, 'door', 1, NULL);
    -- Note: Tea House (loc 11) is no longer on Village Lane.
    -- It is in the shrine garden; connection (11, 20) is in village_expansion_proposal.sql.


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
    '[7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19, 20, 21, 27]',
    -- Village Lane, Apothecary, Bookshop, Tea House (via Shrine),
    -- Village Green, Community Hall, Weaver's, Tearoom, Smithy,
    -- Chandler's, Chapel, Shrine, Dock, Butcher's
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

-- =============================================================================
-- DAVE RPG Engine — Village Expansion (PROPOSAL FOR REVIEW)
-- Additions to The Vintage Village module
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- This file contains proposed additions to modules/vintage_village/seed.sql.
-- Once reviewed and approved, its contents will be integrated into seed.sql
-- and the database rebuilt from scratch.
--
-- What this adds:
--   Locations 12–26: full village layout (civic core, trade district, river
--   zone, and two nearby farms)
--   15 new location_connections
--   Audio crystal items in The Bookshop (location 10)
--   Minimal anchor items per new location (skeleton for lazy generation)
--
-- What is NOT in this pass (next pass):
--   - New NPCs (The Weaver, The Baker, The Wright, The Chandler, etc.)
--   - character_visited_location updates for existing characters
--   - wander_range updates for The Villager (character 9)
--   - Bookshop description update in main seed (to mention crystal alcove)
--   - reset_instance.sql updates
--   - Module header counts update
--
-- Location map (full village):
--   Civic core:
--     Village Lane (7) → Village Green (12) → Community Hall (13)
--   Trade district (all from Village Lane):
--     Village Lane (7) → Weaver's Workshop (14)
--     Village Lane (7) → Tearoom/Bakery (15)  [cousin of weaver]
--     Village Lane (7) → Smithy (16)
--     Village Lane (7) → Chandler's Shop (17)
--     Village Lane (7) → Stable (18)
--     Village Lane (7) → Chapel (19)
--     Village Lane (7) → Shrine (20)
--   River and harbor zone:
--     Village Lane (7) → Dock (21)
--     Dock (21) → Portmaster's Office (22)
--     Dock (21) → Wright's Workshop (23)
--     Dock (21) → Mill (24)  [downstream, along riverbank]
--   Nearby farms:
--     Village Lane (7) → Dairy Farm (25)
--     Village Lane (7) → Orchard (26)
--
-- Note on existing locations:
--   The Bookshop (10): audio crystal items added below; description update
--     to mention the crystal alcove is needed in seed.sql (next pass)
--   The Tea House (11): unchanged — it has a different aesthetic (paper screens,
--     Japanese-adjacent) from the new Tearoom/Bakery; they coexist
-- =============================================================================

PRAGMA foreign_keys = ON;


-- =============================================================================
-- NEW LOCATIONS (IDs 12–26)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Civic core
-- ---------------------------------------------------------------------------

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Village Green: the civic center. Theatre troupe performs here in good
    -- weather; Community Hall used in bad. Connects to Village Lane and Hall.
    12, 1, 'Village Green', 'exterior',
    'A small open green in front of the Community Hall, bounded by a low stone wall and a few old trees whose roots have lifted the paving in places without anyone having got round to relaying it. There is a broad flat stone at one end — old enough that no one quite remembers what it was originally for — that now serves as an informal stage when the troupe performs. On mild evenings the village seems to drift this way without quite meaning to.',
    'public', 1,
    '["evening", "lanterns_lit", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Community Hall: multipurpose interior. Meetings, indoor performances in
    -- bad weather, market overflow. Plain and functional; good acoustics.
    13, 1, 'Community Hall', 'community_hall',
    'A plain, high-ceilinged hall that smells of old timber and candle wax. Long tables are folded flat against one wall; chairs stacked to the rafters on the other. A raised platform at the far end serves as a stage when needed. The acoustics are better than they look — voices carry cleanly without effort — and the building is several degrees warmer inside than you expect from outside.',
    'semi_private', 0,
    '["evening", "unlit", "empty"]'
);

-- ---------------------------------------------------------------------------
-- Trade district (shops along Village Lane)
-- ---------------------------------------------------------------------------

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Weaver's Workshop: the village textile hub. Raw fiber, spun yarn, finished
    -- cloth, tailoring and mending. A family operation working both wool and linen.
    -- Flax and wool follow different seasonal peaks. Lazy generation populates
    -- family members, current work in progress, and specific stock.
    14, 1, "The Weaver's Workshop", 'shop',
    'A wide shop with a working loom visible through the open door, its shuttle resting mid-thread in dark wool as if the weaver stepped away moments ago. The smell is wool and lanolin and something damp that is probably linen. Bolts of cloth are arranged along one wall — plain weaves, a few finer things — and baskets of spun yarn along another. A work table near the back holds half-finished garments and a pair of shears. The shop is busier in spring when the wool comes in and again in autumn when the flax harvest arrives.',
    'semi_private', 0,
    '["evening", "lamp_lit", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Tearoom/Bakery: owned by the weaver's cousin, who correctly identified that
    -- people waiting for fittings next door would appreciate somewhere to sit and
    -- have tea. Also a working bakery; the bread is exceptional.
    15, 1, 'The Tearoom', 'shop',
    'A warm, bright room next door to the Weaver — the proximity is not accidental; the owner is the weaver''s cousin and will tell you so. A counter runs along one wall with a glass case of pastries and a row of mismatched teapots. Four small tables, each with a candle. The smell of fresh bread has thoroughly colonized the space. Most people who come in for a quick cup end up staying considerably longer than they intended, which the owner finds gratifying.',
    'semi_private', 0,
    '["evening", "lamp_lit", "warm", "bread_smell"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Smithy: open-fronted forge, visible from the lane. The Smith family handles
    -- ironwork, farriery, and general metalwork. Forge banked for the evening.
    16, 1, 'The Smithy', 'smithy',
    'An open-fronted workshop where the forge dominates the back wall, banked for the evening but still radiating heat that spills onto the lane. Horseshoes hang in bundles from the ceiling joists. Iron tools of varying purposes are ranked on the walls in an order that probably makes sense to someone. The anvil is enormous and ancient, its face worn smooth. The smell is hot metal, coal, and the leather of the bellows.',
    'public', 0,
    '["evening", "forge_banked", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Chandler's General Store: candles, rope, salt, preserved goods, and the
    -- famous back corner. The Chandler has been here long enough to have become
    -- a fixture. The corner of odd things is real and unpredictable.
    17, 1, "The Chandler's Shop", 'shop',
    'A shop crammed from floor to ceiling with practical things and their impractical cousins. Rope in sizes from thread to cable. Candles in every length and color. Salt in paper cones. Preserved goods in ceramic jars with handwritten labels. And behind a half-height door in the back corner, a collection of crates, boxes, and wrapped parcels of indeterminate age and origin. The chandler has been here long enough that the shop has accreted around them like a reef. It would be inaccurate to say they know what is in every crate. But they know roughly.',
    'semi_private', 0,
    '["evening", "lamp_lit", "crowded"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Stable: serves arriving travelers and visiting farmers. A few stalls, tack
    -- storage, water trough. Clean and functional.
    18, 1, 'The Stable', 'stable',
    'A low building of stone and heavy timber, smelling of hay and horse and old leather. Three stalls run along one wall; a fourth has had its partition removed to make a tack room. The water trough outside is full and clean. Someone has hung lantern hooks at every point where light is actually needed, which suggests they thought about it.',
    'semi_private', 0,
    '["evening", "lantern_lit", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Chapel: a small, unpretentious building associated with the more recently
    -- arrived tradition. Door never locked. Coexists with the Shrine cheerfully.
    19, 1, 'The Chapel', 'chapel',
    'A small plain building with two rows of wooden pews and a window of clear glass looking onto the lane. No pretension to grandeur; someone painted a border of flowers around the window frame in spring and no one has suggested removing them. A candle burns on the altar. The door is never locked. People from the village who don''t come regularly will still stop in occasionally — for quiet, mainly.',
    'semi_private', 0,
    '["evening", "candle_lit", "quiet", "open"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Shrine: older than the chapel, probably older than most of the village.
    -- Outdoor, near the river; a place to leave offerings. The coexistence of
    -- chapel and shrine is genuinely friendly and unremarkable to the villagers.
    -- The Tea House (loc 11) is tucked into the corner of the shrine garden.
    20, 1, 'The Shrine', 'exterior',
    'A small wooden gate in a stone wall, leading into a space that feels quieter than the lane despite having no roof. The space is organized around a boulder the size of a small house — gray granite, glacier-dropped, here before the shrine and probably before the village. The altar stone and its offering bowl sit at the boulder''s base. An old tree grows against the far wall, a lantern hanging from its branch and kept lit. In one corner, almost unobtrusive, a small room with paper screens: the Tea House. People tend to speak quietly here, if at all, and leave feeling approximately better than they arrived.',
    'public', 0,
    '["evening", "lantern_lit", "quiet", "still"]'
);

-- ---------------------------------------------------------------------------
-- River and harbor zone
-- ---------------------------------------------------------------------------

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Dock: the main public area at the river. Boats stop; goods are loaded and
    -- unloaded; children are the informal historians. A good place to fish.
    21, 1, 'The Dock', 'exterior',
    'A wooden dock extending into the river, solid and well-maintained, with rope bollards at intervals and a lantern at the far end. The water here is dark and slow and smells of somewhere further downstream. A few children can usually be found at the end keeping a serious record of the boats that have passed; they take this work earnestly. Most evenings someone is fishing from the near end, not necessarily successfully.',
    'public', 1,
    '["evening", "lantern_lit", "river_sound", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Portmaster's Office: a small, warm shed at the shore end of the dock.
    -- Everything that passes through this village on the river passes through
    -- this room in written form. Letters and parcels left for the boats
    -- accumulated; the habit of leaving things for village neighbors followed
    -- naturally. On good days the portmaster puts on a blue hat of uncertain
    -- origin and delivers the uncollected ones by hand — to the village, and
    -- in good weather, to the farms beyond. No one appointed them to this role.
    22, 1, "The Portmaster's Office", 'building',
    'A small, warm shed at the shore end of the dock, smelling of coal smoke and damp wool and tea. A potbellied stove in the corner; a battered desk under ledgers, sealed letters, and parcels in various stages of waiting — some bound for the next boat, some for a house on the lane, some apparently for no one in particular. The kettle is always on. A blue hat hangs on a peg by the door; when the portmaster wears it, the village understands this to mean the post is going out.',
    'semi_private', 0,
    '["evening", "stove_lit", "warm", "paperwork"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Boatwright / Carpenter / Cartwright: one family, one workshop. The skills
    -- overlap substantially and the village couldn't support three separate shops.
    -- Near the dock; riverbank access at the back for larger boat work.
    23, 1, "The Wright's Workshop", 'workshop',
    'A large, high-roofed workshop smelling of sawdust and linseed oil and fresh shavings. A half-finished rowboat occupies most of the floor. Wagon wheels are stacked against one wall; a chair waits on the workbench for its fourth leg. The tools are old and kept in excellent condition. A wide door at the back opens onto the riverbank where larger repairs get done when the weather permits.',
    'semi_private', 0,
    '["evening", "lamp_lit", "quiet", "sawdust"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Mill: downstream of the dock on the river. Grinds grain year-round; flax
    -- processing is a natural extension of seed threshing — the retting vat and
    -- breaking work happen here because the equipment and the river are already
    -- present. Wool is not handled here; it goes from farm directly to the weaver.
    24, 1, 'The Mill', 'watermill',
    'A stone building where the river narrows and the current quickens. The wheel is still for the evening — the day''s work is done — but the millstone is never quite clean, and flour dust has settled into every surface over the years. Grain sacks are ranked along one wall, ready for collection. Near the back door a retting vat holds flax at some stage of processing, smelling of the river and something green and damp. The mill cat has a bed on top of the grain sacks and is not moved by visitors.',
    'semi_private', 0,
    '["evening", "wheel_still", "dusty", "quiet"]'
);

-- ---------------------------------------------------------------------------
-- Nearby farms
-- ---------------------------------------------------------------------------

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Dairy Farm: the nearest farm, a short walk from the village. Supplies milk,
    -- butter, and cheese to the village and the hostel.
    25, 1, 'The Dairy Farm', 'exterior',
    'A working farm close enough to the village that you can hear the cows on still mornings. A stone farmhouse; a dairy kept cool and clean; a small stand of apple trees along the fence. The lane to the farm is worn smooth from years of twice-daily use. The family grows grain for winter fodder and brews a serviceable ale from the surplus — not their primary trade, but available if you ask. They sell milk, butter, and a firm yellow cheese at market, and will sell direct if you knock at the dairy door.',
    'semi_private', 0,
    '["evening", "cows_settled", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Butcher's Shop: standard village shop on the lane. Skeleton only; no NPC
    -- seeded. Lazy generation populates the butcher and current stock.
    27, 1, "The Butcher's Shop", 'shop',
    'A narrow shop with a scrubbed wooden counter and hooks on the wall, most of them occupied. The smell is cold and iron and sawdust. A chalkboard beside the door lists what is available today in handwriting that has not changed in years.',
    'semi_private', 0,
    '["evening", "lamp_lit", "quiet"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Orchard: a little further than the dairy. Fruit and cider. The cider press
    -- is one of the reliable seasonal markers. Also: one enormous quince tree.
    26, 1, 'The Orchard', 'exterior',
    'A farm whose primary crop is fruit — apple, pear, and a single enormous quince tree whose output has never quite found its purpose. In late summer the smell of ripening fruit carries to the lane. The cider press runs from harvest through to the first frost, and the sound of it is one of the dependable markers of the season. The farmer is difficult to find in summer, being always somewhere in the trees.',
    'semi_private', 0,
    '["evening", "fruit_trees", "quiet"]'
);


-- =============================================================================
-- NEW LOCATION CONNECTIONS
-- Convention: location_a_id < location_b_id (schema constraint).
-- All new; no changes to existing connections.
-- =============================================================================

INSERT INTO location_connection (location_a_id, location_b_id, connection_type,
                                  is_passable, passage_note)
VALUES
    -- Civic core
    (7,  12, 'open', 1, NULL),   -- Village Lane ↔ Village Green (open space)
    (12, 13, 'door', 1, NULL),   -- Village Green ↔ Community Hall

    -- Trade district (all off Village Lane)
    (7,  14, 'door', 1, NULL),   -- Village Lane ↔ Weaver's Workshop
    (7,  15, 'door', 1, NULL),   -- Village Lane ↔ Tearoom (next door to Weaver's)
    (7,  16, 'open', 1, NULL),   -- Village Lane ↔ Smithy (open-fronted forge)
    (7,  17, 'door', 1, NULL),   -- Village Lane ↔ Chandler's Shop
    (7,  18, 'open', 1, NULL),   -- Village Lane ↔ Stable
    (7,  19, 'door', 1, NULL),   -- Village Lane ↔ Chapel
    (7,  20, 'open', 1, NULL),   -- Village Lane ↔ Shrine (outdoor, gated wall)

    -- River and harbor zone
    (7,  21, 'open', 1, NULL),   -- Village Lane ↔ Dock
    (21, 22, 'door', 1, NULL),   -- Dock ↔ Portmaster's Office
    (21, 23, 'open', 1, NULL),   -- Dock ↔ Wright's Workshop (near the water)
    (21, 24, 'open', 1, NULL),   -- Dock ↔ Mill (path along riverbank, downstream)

    -- Farms (paths from Village Lane)
    (7,  25, 'open', 1, NULL),   -- Village Lane ↔ Dairy Farm
    (7,  26, 'open', 1, NULL),   -- Village Lane ↔ Orchard

    -- Shrine garden: Tea House is tucked into the shrine garden, not on the lane.
    -- Replaces the (7, 11) Village Lane ↔ Tea House connection removed from seed.sql.
    (11, 20, 'open', 1, NULL),   -- Tea House ↔ Shrine (same garden)

    -- Butcher's Shop
    (7,  27, 'door', 1, NULL);   -- Village Lane ↔ Butcher's Shop


-- =============================================================================
-- NEW CHARACTER: THE FISH SELLER (character 10)
-- npc_background — minimal record. She is at the end of the dock most evenings
-- with a bucket of whatever she caught. No table, no shop. Coins for fish;
-- a few more coins if you want it gutted. She does not wander.
-- =============================================================================

INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    maslow_tier, emotional_state,
    capability_beliefs, context_beliefs,
    surface_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    10, 1, 'The Fish Seller', 'npc_background', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'A weathered woman of indeterminate middle age, sitting on an upturned crate at the end of the dock with a bucket beside her and a gutting knife on her knee. She is there most evenings when the catch has been good. She does not have a table or a sign. If you walk to the end of the dock she will tell you what she has. If you want it gutted she will do that too, for a bit more.',
    'vendor',
    21,  -- The Dock
    'physiological',
    'patient',
    '{}',
    '{}',
    'Selling the day''s catch. Not in a hurry; the fish will keep until morning if they have to.',
    'terse_gruff', 0.55, 0.30,
    NULL, 0.0
);


-- =============================================================================
-- CHARACTER VISITED LOCATIONS — updates for existing and new characters
-- The Villager (char 9) knows the whole village; add all new locations.
-- The Fish Seller (char 10) does not wander; no visited locations needed.
-- =============================================================================

INSERT INTO character_visited_location (character_id, location_id)
VALUES
    -- The Villager: new village locations (existing [7,9,10,11] already in seed.sql)
    (9, 12),   -- Village Green
    (9, 13),   -- Community Hall
    (9, 14),   -- Weaver's Workshop
    (9, 15),   -- Tearoom
    (9, 16),   -- Smithy
    (9, 17),   -- Chandler's Shop
    (9, 18),   -- Stable
    (9, 19),   -- Chapel
    (9, 20),   -- Shrine
    (9, 21),   -- Dock
    (9, 22),   -- Portmaster's Office
    (9, 23),   -- Wright's Workshop
    (9, 24),   -- Mill
    (9, 25),   -- Dairy Farm
    (9, 26),   -- Orchard
    (9, 27);   -- Butcher's Shop


-- =============================================================================
-- AUDIO CRYSTAL ITEMS — THE BOOKSHOP (location 10)
-- The existing Bookshop description in seed.sql should be updated to mention
-- the crystal alcove (next pass). These items establish the stock.
-- The backstory (personal book collection → mage arrived → theatre troupe
-- got involved → now a going concern) lives in NPC and location_detail records
-- to be seeded next pass.
-- =============================================================================

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'listening crystal: "The Song of the Loom"',
    'A faceted crystal the size of a large egg, faintly warm when held. It releases a slow, complex piece of music — plucked strings and a sustained low note — with what sounds like a working loom audible in the background, as though the recording was made in the workshop itself. The label in small careful handwriting reads: "The Song of the Loom. Local composition. First pressing."',
    '{"weight": "light", "crystal": true, "audio_type": "music", "local_recording": true}',
    10, 'in the crystal alcove, on a padded cloth stand');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'listening crystal: "Three Voices Reading"',
    'A smoky gray crystal with a faint audible hum when held. Three distinct voices read the same passage in rotation — the same text, three different readings, then silence, then continuing. Whether this is artistic intention or an editorial accident is unclear. The label reads: "Three Voices Reading. A work in progress."',
    '{"weight": "light", "crystal": true, "audio_type": "reading", "local_recording": true}',
    10, 'in the crystal alcove, beside the first pressing');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'crystal alcove sign',
    'A small handwritten card in a wooden frame: "Audio crystals — local recordings by the village troupe and visiting practitioners. Imports available on request. Handle with care. Please ask before purchasing if you are uncertain what you are purchasing."',
    '{"weight": "negligible", "portable": false, "readable": true}',
    10, 'on a small shelf above the crystal display, facing the shop floor');


-- =============================================================================
-- ANCHOR ITEMS — NEW LOCATIONS
-- Minimal seed per location to establish the space for lazy generation.
-- Detailed inventory and furnishings generated on first visit.
-- =============================================================================

-- Weaver's Workshop (14)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'floor loom',
    'A large working loom, shuttle resting mid-thread in a length of dark wool. The frame is old and has been repaired and adjusted many times; none of the repairs are ugly. The current work is a plain twill, but the tension is even throughout.',
    '{"weight": "immovable", "portable": false}',
    14, 'taking up most of the workshop floor, facing the window');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'basket of undyed wool',
    'A large wicker basket of washed natural wool — white, cream, and occasional gray — clean and dry. The smell is faint lanolin.',
    '{"weight": "medium", "portable": true, "container": true, "material": "wool"}',
    14, 'beside the loom, on the floor');

-- Tearoom/Bakery (15)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'tearoom table (window)',
    'A small round table beside the front window. Two mismatched chairs. The window is lightly fogged from the warmth inside. It is the best table for watching the lane.',
    '{"weight": "heavy", "portable": false, "surface": true}',
    15, 'beside the front window, facing the lane');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'bread loaf',
    'A round loaf on the counter, its crust dark and cracked from the oven. Baked today; the smell is still present. A small card beside it gives the price in whatever denomination seems current.',
    '{"weight": "medium", "portable": true, "edible": true, "surface": false}',
    15, 'on the counter, in a cloth-lined basket');

-- Smithy (16)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'anvil',
    'A massive iron anvil, its working face worn to a near-polish from years of use. It sits on a section of elm trunk bolted to the floor. The anvil does not move. It has not moved in a long time.',
    '{"weight": "immovable", "portable": false}',
    16, 'at the center of the smithy, on its elm-trunk base');

-- Chandler's Shop (17)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'mystery crate',
    'A wooden crate in the back corner behind a half-height door, its slats slightly sprung, muffled inside with straw packing. The chandler will tell you it came in some years ago and they have not gotten around to opening it properly. This is either true or a very good story.',
    '{"weight": "unknown", "portable": false, "container": true, "contents": "unknown"}',
    17, 'in the back corner, behind the half-height door');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'rope coil (heavy)',
    'A coil of thick hemp rope, perhaps fifteen feet, neatly wound and hanging from a ceiling hook. There are several more behind it in descending sizes.',
    '{"weight": "medium", "portable": true, "material": "hemp"}',
    17, 'hanging from a ceiling hook, front of the shop');

-- Stable (18)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'hay bale',
    'A tightly bound bale of dry summer hay stacked against the stable wall. The smell is good — dry grass and a little dust. It would make an adequate seat in the absence of anything better.',
    '{"weight": "heavy", "portable": false, "sittable": true}',
    18, 'stacked against the stable wall, beside the tack room');

-- Community Hall (13)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'trestle table (folded)',
    'A long trestle table folded flat and leaning against the wall with several others. When open it seats eight. The wood is clean; this is a well-maintained piece of community property.',
    '{"weight": "heavy", "portable": false, "surface": false, "foldable": true}',
    13, 'folded against the left wall with the other tables');

-- Village Green (12)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'flat stage stone',
    'A broad flat stone set into the ground at one end of the green, large enough for four people to stand on without crowding. Old enough that its original purpose has been forgotten. It now serves as a stage for the troupe''s outdoor performances, which it does without complaint.',
    '{"weight": "immovable", "portable": false, "surface": true}',
    12, 'at the far end of the green, slightly raised from the surrounding ground');

-- Portmaster's Office (22)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'blue hat (portmaster)',
    'A broad-brimmed hat of deep blue wool, hanging on a peg by the door. Its origin is unclear — it arrived on a boat some years ago and was never claimed. When the portmaster wears it, everyone in the village understands that the post is going out. No one decided this; it simply became true.',
    '{"weight": "negligible", "portable": true, "wearable": true, "worn_by": "portmaster on delivery days"}',
    22, 'on a peg by the door');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'portmaster ledger',
    'A heavy bound ledger, current year, open to today''s page. Entries in a careful hand: boat names, cargo, origin, destination, duties paid or deferred. The handwriting is very small and very legible. A quill and ink pot beside it.',
    '{"weight": "medium", "portable": false, "readable": true, "surface": false}',
    22, 'on the desk, open to the current day''s entries');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'potbellied stove',
    'A small cast-iron stove in the corner, doing more work than its size suggests. A kettle on top is just beginning to steam. The stove has a small door with a mica window and you can see the fire through it.',
    '{"weight": "immovable", "portable": false, "heat_source": true}',
    22, 'in the corner near the door, with a kettle on top');

-- Wright's Workshop (23)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'rowboat (in progress)',
    'A rowboat about two-thirds complete, its planks clamped to the frame and the interior ribbing visible. The wood is good-quality ash, steam-bent and fitted carefully. It will be a sound boat when finished.',
    '{"weight": "immovable", "portable": false}',
    23, 'occupying most of the workshop floor, hull up on sawhorses');

-- Mill (24)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'grain sack (full)',
    'A heavy linen sack of milled flour, neatly tied at the neck and ready for collection. Flour dust has left a faint white ring on the floor around the ranked sacks.',
    '{"weight": "heavy", "portable": true, "container": true, "contents": "flour"}',
    24, 'ranked against the millhouse wall, near the door');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'mill cat bed',
    'A folded blanket on top of the grain sacks, shaped by long use into a permanent nest. The mill cat is not currently in it. The mill cat is somewhere in the building, however.',
    '{"weight": "negligible", "portable": false, "sittable": true}',
    24, 'on top of the grain sacks, near the window');

-- Dock — fish seller's bucket (21)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'fish bucket',
    'A wooden bucket at the fish seller''s feet, holding today''s catch in a little water. The contents vary. She will tell you what is in it if you ask; she will not volunteer the information.',
    '{"weight": "medium", "portable": false, "container": true, "contents": "fish, variable", "for_sale": true}',
    21, 'beside the fish seller''s crate, at the end of the dock');

-- Shrine (20)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'glacier rock',
    'A boulder the size of a small house, gray and rounded, dropped here by a glacier so long ago that the shrine was built around it rather than the other way around. It sits at the bend where the river turns, half in the shrine garden and half beyond the wall. The stone is always slightly cool to the touch regardless of the season. People lean against it, sit on its lower ledges, leave offerings on a flat spot near the base. It does not seem to mind.',
    '{"weight": "immovable", "portable": false, "sittable": true, "climbable": true, "climb_difficulty": "steep; requires effort and good handholds; the top is worth it", "material": "granite"}',
    20, 'at the river bend, half inside the shrine wall and half beyond it');

INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'offering bowl',
    'A shallow ceramic bowl on the altar stone, holding clean water and three small flowers from this morning. Someone tends this regularly. The bowl itself is old — the glaze is finely crazed — but unbroken.',
    '{"weight": "light", "portable": false, "container": true, "fill_state": "full", "contents": "water and flowers"}',
    20, 'on the flat altar stone, centered');

-- Chapel (19)
INSERT INTO item (game_id, name, description, properties, loc_id, location_description)
VALUES (1, 'altar candle',
    'A single candle burning on the altar, the only light in the chapel at this hour. It is a good thick candle — the kind that burns slowly — and whoever tended it last left a fresh one beside it in case.',
    '{"weight": "negligible", "portable": true, "light_source": true}',
    19, 'on the altar, burning');
