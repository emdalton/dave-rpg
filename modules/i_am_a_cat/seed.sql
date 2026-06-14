-- =============================================================================
-- DAVE RPG Engine — Module: I Am a Cat
-- Seed Data
--
-- Digitally Adjudicated Virtual Environment
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Setting: a townhouse condo unit, approximately 3am.
-- Player character: Toulouse, a large older male cat with long black fur.
-- Goal: avoid boredom until morning.
--
-- This script is the complete standalone seed for the I Am a Cat module,
-- compatible with schema v10. Run after applying schema.sql — no versioned
-- seed files (seed_v3 through seed_v7) are needed; their content has been
-- consolidated here.
--
-- Usage:
--   sqlite3 i_am_a_cat.db < ../../schema/schema.sql
--   sqlite3 i_am_a_cat.db < seed.sql
--   sqlite3 i_am_a_cat.db .tables   -- verify
--
-- Contents (in order):
--   GAME RECORD — module parameters (tone, speech filter, cultural norms)
--   LOCATIONS — 13 locations, IDs 1–13
--   CHARACTERS — 5 characters (Toulouse, Spook, Mama, Guy, Lillis)
--   CHARACTER GOALS — MST goal weights per character
--   CHARACTER ATTITUDES — dyadic attitude floats at session start
--   INTERNAL STATES — starting values for boredom, hunger, hairball_pressure, sleepiness
--   ITEMS — 37 items (furniture, food, toys, accidental toys)
--   CHARACTER SKILLS — Toulouse: fetch, burrowing under blankets
--   PRE-SEEDED LOCATION DETAILS — established facts and lazy discovery mechanics
--   NPC-PLAYER HISTORY — relationship summaries at session start
--   GAME INSTANCE — clock set to 3:00 AM; status = 'ready'
--   PASSIVE DRIFT RATES — background rate per minute on time-varying states
--   GENDER AND PRONOUNS — third-person pronoun sets for all characters
--   NPC WANDER PARAMETERS — range and per-turn probability for each NPC
--   LOCATION CONNECTIONS — full adjacency graph (13 connections)
--   TOULOUSE VISITED LOCATIONS — all 13 rooms pre-marked (he knows the house)
-- =============================================================================

PRAGMA foreign_keys = ON;

-- =============================================================================
-- GAME RECORD
-- =============================================================================

INSERT INTO game (
    id, name, genre, tone, era, technology_level, magic_system,
    narrative_register, speech_filter, internal_state_display, cultural_norms
) VALUES (
    1,
    'I Am a Cat',
    'domestic_comedy',
    'comedic_absurdist',
    'contemporary',
    'contemporary',
    NULL,  -- no magic; the supernatural mystery of why humans sleep so much is sufficient
    'third_person_close',

    -- Speech filter: player output renders as meow variants calibrated to
    -- emotional state and urgency. Human speech is filtered through feline
    -- comprehension — mostly acoustic impression, with a small vocabulary
    -- of semantically salient words breaking through clearly.
    json('{
        "player_output": "meow_variants",
        "player_output_note": "All cat vocalizations render as meow variants. Emotional state and urgency calibrate pitch, duration, and repetition. The cat knows exactly what it means; the human hears a cat.",
        "npc_human_input_filter": "feline_comprehension",
        "feline_comprehension_note": "Human speech renders as tonal impression and acoustic texture. Semantically salient words break through at varying clarity.",
        "vocabulary_breakthrough": {
            "treats":     "penetrates clearly and immediately",
            "no":         "penetrates partially and inconsistently",
            "bad":        "penetrates partially",
            "food":       "penetrates partially",
            "hungry":     "penetrates partially",
            "morning":    "does not penetrate",
            "sleeping":   "does not penetrate",
            "three_am":   "does not penetrate"
        }
    }'),

    -- Internal state display: all states rendered as in-character prose for
    -- immersion. Numeric display available via meta-channel override.
    json('{
        "boredom":  "prose",
        "hunger":   "prose",
        "sleepiness": "prose"
    }'),

    -- Cultural norms: feline behavioral conventions passed to adjudication
    -- when relevant. These replace the social/political norms of other modules.
    json('{
        "toy_qualification": "An object qualifies as a toy if it moves, makes noise, has an interesting texture, or can be knocked off something. Human taxonomy is irrelevant.",
        "food_hierarchy": "Human-dispensed food outranks machine-dispensed food, even if the food is identical. Treats outrank everything.",
        "litter_box_standards": "A full or dirty litter box is an affront. Cats have opinions and will express them.",
        "territory": "High places confer status. The arm of the couch and the tiled overlook are premium locations.",
        "humans_asleep": "Sleeping humans are a challenge, not a barrier. Sufficient persistence overcomes rest goals.",
        "pantry_rule": "Any human opening the pantry cupboard must be investigated immediately, without exception.",
        "clutter_character": "The house is cluttered but clean. No food waste, no dirty dishes. Clutter is books, craft supplies, electronics, bags, and similar objects. Most items are not fragile; breakage should not be the default outcome of cat exploration. Some items are too heavy to move.",
        "stray_treats": "Crunchy treats thrown during play sessions accumulate under and behind main-floor furniture. Finding one is plausible (~40%) when a cat investigates a furniture hiding spot for the first time."
    }')
);


-- =============================================================================
-- LOCATIONS (13 total, IDs 1-13)
--
-- Flooring note: the house has smooth hard floors throughout (no wall-to-wall
-- carpet). A cat moving at speed can slide on them. Exceptions:
--   - Living Room (1): large area rug, fixed
--   - Main Floor Hallway (13): long thin runner rug, can shift at speed
--   - Basement Main Room (6): large area rug, fixed
-- The Upper Hallway (12) has smooth floors like the rest of the upper floor.
--
-- Connections between locations are defined in seed_v3.sql via the
-- location_connection table (schema v3+).
-- =============================================================================

-- Main floor -------------------------------------------------------------------

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (1, 1, 'Living Room', 'living_room',
    'A comfortable room with a couch, an armchair, two coffee tables, and several plants the humans have inexplicably placed at cat level. The floor is smooth and good for sliding runs if approached correctly; a large area rug in the middle of the room provides traction and an excellent surface for kneading. A row of windows faces the street; an outside light means there is always something to observe if one is patient enough. The arm of the couch is a premium resting location: soft, flat, and positioned directly at the window. A short cat tree stands near the wall. A large dark rectangle (the TV) hangs on one wall and sometimes shows things that move. An open stairwell in the corner leads up to the upper floor. The female human occasionally leaves objects on the couch that are in the way and could theoretically be moved.',
    'private', 0,
    json('["night", "quiet", "humans_asleep", "outside_light_on", "rug_present", "open_stairwell"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (2, 1, 'Dining Room', 'dining_room',
    'A room containing a large flat hard surface the humans do not want cats on (the table) and several shorter flat soft surfaces that are apparently acceptable (the chairs). The floor is smooth. A half wall of cabinets separates the dining room from the living room — cats can go over or under it. The pantry cupboard is here — a tall cabinet whose contents include TREATS. Any sound of this cupboard opening requires immediate investigation. There is a large window and an outside light. The porch is accessible through a door here. At the far end, an opening leads into the main floor hallway.',
    'private', 0,
    json('["night", "quiet", "pantry_nearby", "porch_door_present"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (3, 1, 'Kitchen', 'kitchen',
    'The room where human food activities happen. The floor is smooth. The kitchen opens directly onto the main floor hallway with no door. The canned cat food is stored here. If the male human enters this room at any hour, it is worth investigating whether he considers it to be morning yet. The female human has been known to share pieces of spinach or cucumber, which are unexpectedly delicious. There is a flat counter area with a water source (sink). A large window overlooks the back.',
    'private', 0,
    json('["night", "quiet", "canned_food_nearby"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (4, 1, 'Utility Room', 'utility_room',
    'A utilitarian room off the main floor hallway serving as laundry room, half bath, and cat feeding station. The floor is smooth. Contains the automatic food dispenser (operates on a schedule regardless of whether anyone deserves it), a water source (sink), a toilet, and two large boxy appliances (the washer and dryer) that provide excellent hiding places behind them and sometimes harbor escaped toys.',
    'private', 0,
    json('["night", "quiet", "auto_feeder_present"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (5, 1, 'Main Stairs', 'stairwell',
    'The open stairwell in the corner of the living room, connecting the main floor to the upper hallway. Smooth wooden treads. A good vantage point from the landing halfway up. Toys placed at the top have interesting trajectories downward into the living room. The basement is accessed separately via a door off the main floor hallway.',
    'private', 0,
    json('["night", "quiet", "smooth_treads"]')
);

-- Basement --------------------------------------------------------------------

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (6, 1, 'Basement Main Room', 'basement_room',
    'A large cluttered room with many places to hide. The floor is smooth concrete under a large area rug that covers most of the room — the rug is fixed and does not move. The bird cage is here — the bird is asleep and boring, but the cage itself is interesting to investigate. The female human has a chair here facing a strange window (a computer). There are many craft supplies stored here: fabric, yarn, and various containers. Whether any string has been left accessible depends on how carefully the female human put things away. There are boxes and furniture and excellent hiding spots behind most of it.',
    'private', 0,
    json('["night", "quiet", "bird_asleep", "cluttered", "good_hiding_spots", "rug_present"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (7, 1, 'Basement Storage Room', 'storage_room',
    'A small cluttered room lined with boxes, most of which are sealed and too heavy to move. The litter box is here. The door to this room once closed with cats inside — it has not happened again, but the memory lingers. There is enough space to use the litter box in peace, if the litter box merits use.',
    'private', 0,
    json('["night", "quiet", "litter_box_present"]')
);

-- Upper floor -----------------------------------------------------------------

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (8, 1, 'Tiled Overlook', 'overlook',
    'A tiled platform accessible by squeezing through the railing at the top of the stairs. Technically the top of a closet on the main floor below. Offers an excellent elevated view of the living room. Objects placed at the edge fall to the living room below, which is interesting. The small cat does not like to come up here, but will engage in combat through the iron bars of the railing, which is also interesting.',
    'private', 0,
    json('["night", "elevated", "good_view", "railing_access"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (9, 1, 'Bathroom', 'bathroom',
    'A room with a large wet area (the shower/tub) that usually contains some residual water worth investigating. The humans leave a container here and the water in it is particularly good to play with — it can be scooped and scattered. There is a counter with a sink and many small objects of varying sizes and knockability.',
    'private', 0,
    json('["night", "quiet", "water_present"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (10, 1, 'Bedroom', 'bedroom',
    'The large soft flat room where the humans sleep. There is an enormous soft sleeping surface (the bed) that cats are welcome on or under. Two smaller flat surfaces (nightstands) at different heights hold various objects. The female human sleeps here and may be reading. The male human sleeps here and is unlikely to wake before morning. A large window is very sunny in the daytime; at night it shows sky.',
    'semi_private', 2,  -- two humans present
    json('["night", "humans_asleep", "quiet", "bed_available"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (11, 1, 'Study', 'study',
    'A room with a sunny window (in the daytime). A large dark rectangle (the TV) that the male human likes to look at a lot is mounted here. There are soft things to sit on. Most importantly, there are excellent scratching surfaces: several cardboard scratching pads on the floor and a short cat tree with sisal rope wrapping on the post. Sharpening claws here is encouraged; on the furniture downstairs, it is not.',
    'private', 0,
    json('["night", "quiet", "scratching_available"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (12, 1, 'Upper Hallway', 'hallway',
    'The corridor of the upper floor. Smooth floor — good for a running start if the objective warrants it. A small cat tree stands near the wall, its top platform surveying the hallway with commanding detachment. A charging cable dangles near the stairwell end of the hallway, a matter for later. Doors lead off the hallway to the bathroom, bedroom, and study. At the far end, a thin stripe of light sometimes leaks under the bedroom door. The tiled overlook is accessible by squeezing through the railing near the stairwell end.',
    'private', 0,
    json('["night", "quiet", "small_cat_tree_present", "charging_cable_present"]')
);

-- Main Floor Hallway: the corridor running along the side of the main floor,
-- connecting the Living Room, Dining Room, Kitchen, Utility Room, and the
-- basement stairs. The hallway runner can shift if crossed at speed — the only
-- rug in the house that moves. Good for a fast approach to any main-floor room.
INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (13, 1, 'Main Floor Hallway', 'hallway',
    'A corridor running along the side of the main floor, open at both ends into the living room and dining room, and connecting the kitchen, utility room, and the door to the basement stairs. The floor is smooth — good for speed if the destination matters. A long thin runner rug covers most of the length; unlike the rugs in the living room and basement, this one can and does shift at speed. Moving at a full run, a cat can slide it into a satisfying pile at one end. The pantry cupboard is accessible from here via the dining room. At 3am the hallway is quiet and mostly dark.',
    'private', 0,
    json('["night", "quiet", "runner_rug_present", "moveable_rug"]')
);


-- =============================================================================
-- CHARACTERS (5 total)
-- =============================================================================

-- Toulouse: the player character. Large, older, long black fur. Knows the name
-- Toulouse. Getting mellower with age. Motivated primarily by food and the
-- avoidance of boredom. Knows how to play fetch, which is unusual and delightful.
INSERT INTO character (
    id, game_id, name, role, species, description, apparent_status,
    current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    narrative_points,
    capability_beliefs, context_beliefs
) VALUES (
    1, 1, 'Toulouse', 'player', 'cat',
    'A large male domestic cat with long black fur, going a bit grey around the muzzle. Getting older and less frantically energetic, but still fully committed to the pursuit of interesting things. Knows the name Toulouse and occasionally responds to it. Knows how to play fetch, which he considers a reasonable exchange of effort for entertainment.',
    'Senior resident; has been here longest and knows every inch of the place.',
    1,  -- starts in the living room

    -- OCEAN: Curious but mellowing (O moderate), low discipline (C low, he is a cat),
    -- sociable but not needy (E moderate), genuinely fond of his humans (A high),
    -- some reactivity to sudden stimuli like late-arriving neighbors (N moderate-low).
    0.60, 0.30, 0.50, 0.72, 0.40,

    'belonging',   -- well-cared-for cat; basic needs met; operating at belonging/esteem level
    'restless',    -- it is 3am and things are insufficiently interesting

    'Wants to find something interesting to do. Would also accept food.',
    'Fundamentally convinced that the humans exist to serve him and are not currently doing their jobs.',
    0,  -- hidden motivation not yet revealed to player (it is the tutorial framing)

    -- Voice: Toulouse communicates with an air of entitled expectation.
    -- All output renders as meow variants per the speech filter; these parameters
    -- calibrate tone and persistence rather than vocabulary.
    'imperious', 0.65, 0.72,

    0,  -- narrative points start at zero

    -- Capability beliefs: what Toulouse believes he can do (self-efficacy per MST)
    json('{
        "meowing_persuasively":   0.85,
        "carrying_toys_in_mouth": 0.90,
        "jumping_to_high_places": 0.65,
        "going_up_and_down_stairs": 0.90,
        "waking_sleeping_humans": 0.70,
        "opening_closed_doors":   0.05,
        "hunting_small_things":   0.45,
        "playing_fetch":          0.85,
        "squeezing_through_railing": 0.75
    }'),

    -- Context beliefs: Toulouse's read on how supportive the environment is right now
    json('{
        "humans_will_respond_to_meowing":   0.55,
        "food_available_from_humans":       0.35,
        "interesting_things_to_discover":   0.50,
        "spook_available_to_interact_with": 0.50,
        "treats_accessible":                0.10
    }')
);


-- Spook: younger cat, black and white shorthair. Very energetic. Often needs a
-- bath whether or not he agrees. Will sometimes clean another cat's ears.
-- Entertaining to observe but occasionally annoying when he demands play.
INSERT INTO character (
    id, game_id, name, role, species, description, apparent_status,
    current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    narrative_points,
    capability_beliefs, context_beliefs
) VALUES (
    2, 1, 'Spook', 'npc_active', 'cat',
    'A black and white shorthaired cat, younger and considerably more energetic than his housemate. Often in need of a bath, a fact he contests. Will occasionally groom another cat''s ears with no warning. Entertaining to watch when he is doing something ridiculous, which is most of the time.',
    'Junior resident; enthusiastic; frequently in the way.',
    11,  -- starts in the study, probably playing with something at 3am

    -- OCEAN: Very high openness (into everything), very low conscientiousness (zero
    -- self-regulation), very high extraversion (always wants interaction), moderately
    -- agreeable, low neuroticism (young and fearless about most things).
    0.88, 0.18, 0.90, 0.62, 0.25,

    'belonging',
    'playful',

    'Wants to play. Right now. Possibly with Toulouse, possibly with a toy, possibly with something that is not technically a toy.',
    NULL,
    0,

    'energetic', 0.80, 0.85,
    0,

    json('{
        "running_fast":               0.95,
        "jumping_high":               0.92,
        "getting_toulouse_to_play":   0.50,
        "cleaning_ears":              0.82,
        "going_through_railing":      0.30,
        "knocking_things_over":       0.95
    }'),

    json('{
        "toulouse_will_play_with_me":  0.45,
        "humans_will_play_with_me":    0.30,
        "interesting_things_here":     0.80
    }')
);


-- The mama: female human. Likes cats and also likes sleep, in roughly that order.
-- Reads late in bed; may get up for a midnight snack. More likely to share food
-- (spinach, cucumber). More likely to be awake at odd hours than guy.
INSERT INTO character (
    id, game_id, name, role, species, description, apparent_status,
    current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    narrative_points,
    capability_beliefs, context_beliefs
) VALUES (
    3, 1, 'the mama', 'npc_active', 'human',
    'An adult woman who is genuinely fond of the cats and reads in bed late — she may have only recently fallen asleep at 3am, or may still be awake. Lighter sleeper than guy. Gets up occasionally for a midnight snack or bathroom trip. Shares interesting food items (spinach, cucumber) during waking hours. Has a firm and conscious policy of not feeding the cats in the middle of the night, specifically because she does not want to train them to pester her at 3am. The cats have not fully internalized this policy. Has craft supplies in the basement that may or may not be put away properly.',
    'Primary food-sharer during waking hours; source of midnight snacks for herself; will not feed cats overnight by policy.',
    10,  -- bedroom, asleep (possibly just recently)

    -- OCEAN: Open and flexible (O high), reasonably organized but sometimes careless
    -- with craft supplies (C moderate), warm and social (E moderate-high), very
    -- agreeable — shares food, responds to cats (A high), not particularly anxious (N low).
    0.75, 0.62, 0.60, 0.85, 0.32,

    'safety',     -- asleep; physiological need for rest is dominant right now
    'lightly_asleep',  -- lighter sleep than guy; may have been reading until recently

    'Wants to sleep. Will get up for a bathroom trip or midnight snack if needed. Will not feed the cats overnight regardless of how persuasively they ask — this is a deliberate policy she maintains consistently.',
    NULL,
    0,

    -- Voice when woken: warm but groggy. Short responses. Addresses cats by name
    -- with affection, then firmly declines food requests and attempts to return to sleep.
    'groggy_warm', 0.88, 0.30,
    0,

    json('{
        "ignoring_persistent_cat":          0.55,
        "falling_back_asleep":              0.70,
        "finding_midnight_snack":           0.85,
        "refusing_cat_food_request":        0.95,
        "getting_up_for_bathroom":          0.90
    }'),

    json('{
        "cat_will_let_me_sleep":                        0.45,
        "feeding_cats_now_trains_bad_behavior":         0.95,
        "something_is_wrong_if_cat_is_truly_insistent": 0.60,
        "guy_will_feed_cats_in_the_morning":            0.99
    }')
);


-- Guy: male human. Also likes cats and sleep. Harder to wake than the mama.
-- More likely to get up early in the morning. Puts out canned food, typically
-- including a morning feeding. If he enters the kitchen, it may be morning.
INSERT INTO character (
    id, game_id, name, role, species, description, apparent_status,
    current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    narrative_points,
    capability_beliefs, context_beliefs
) VALUES (
    4, 1, 'guy', 'npc_active', 'human',
    'An adult man and a morning person. Goes to bed at a reasonable hour and wakes naturally well before sunrise — usually sometime between 4am and 6am. The first things he does when he wakes are make coffee and feed the cats. He is a softie about cat food requests and has been thoroughly trained by the cats to respond to persistent meowing with canned food, often earlier than strictly necessary. He is harder to rouse in the early part of the night (before 2am or so) but his sleep lightens naturally as morning approaches. His presence in the kitchen at any hour is a meaningful signal that he considers it morning. He is reliable, routine-driven, and the cats have correctly identified him as the more negotiable of the two humans.',
    'Primary canned food provider; morning anchor; thoroughly trained by cats; most likely to get up and feed them before sunrise.',
    10,  -- bedroom, asleep

    -- OCEAN: Moderate openness, high conscientiousness (reliable routines, early riser),
    -- moderate extraversion, high agreeableness toward cats (they have trained him well),
    -- low neuroticism (calm, not easily rattled by 3am cat activity).
    0.55, 0.78, 0.45, 0.82, 0.28,

    'physiological',  -- asleep; sleep lightens naturally as morning approaches
    'deeply_asleep',  -- deeply asleep now; will lighten over the course of the session

    'Wants to sleep until his internal clock wakes him, then feed the cats and make coffee. Can be roused by persistent cat activity, especially as morning approaches, though he will resist being woken before he is ready.',
    NULL,
    0,

    -- Voice when woken mid-night: gruff, minimal, mostly unintelligible; falls back
    -- asleep readily. Voice when waking naturally for morning: warm, mumbling, functional;
    -- orients immediately toward coffee and cats.
    'gruff_sleepy', 0.78, 0.22,
    0,

    json('{
        "sleeping_through_disturbance_early_night": 0.82,
        "sleeping_through_disturbance_near_morning": 0.35,
        "getting_up_for_morning_routine":            0.97,
        "feeding_cats_when_awake":                   0.98,
        "resisting_cat_food_request_when_asleep":    0.75,
        "getting_up_for_bathroom":                   0.70
    }'),

    json('{
        "it_is_not_morning_yet":                0.80,
        "cats_will_be_fed_when_i_get_up":       0.99,
        "persistent_meowing_means_feed_me":     0.85,
        "mama_will_not_feed_cats_overnight":    0.99
    }')
);


-- Lillis: the cockatiel. Asleep in the cage in the basement. The cats do not
-- know or use her name; they know her as the bird in the cage. Boring when
-- asleep. Spectacular when woken. The humans scold cats for reaching into the cage.
INSERT INTO character (
    id, game_id, name, role, species, description, apparent_status,
    current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    narrative_points,
    capability_beliefs, context_beliefs
) VALUES (
    5, 1, 'Lillis', 'npc_active', 'bird',
    'A cockatiel living in a cage in the basement. The cats know her as the bird in the cage and have opinions about the cage bars. She is asleep at this hour, which makes her boring. If woken, she produces impressive noise: loud flapping, banging against the cage, and vocalizations that carry through the whole house. The humans have been clear about the cage-reaching policy.',
    'Prey-adjacent; protected by cage and human disapproval; currently asleep.',
    6,  -- basement main room, in her cage

    -- OCEAN: Low openness to cat interaction, very high conscientiousness about
    -- her own safety routines, low extraversion (asleep), very low agreeableness
    -- toward cats, very high neuroticism (extremely reactive when startled).
    0.20, 0.80, 0.25, 0.10, 0.92,

    'safety',     -- a caged bird in a house with two cats has safety as a permanent concern
    'asleep',

    'Wants to sleep undisturbed until morning.',
    NULL,
    0,

    -- Voice when woken: loud, panicked, percussive. High verbosity, zero warmth.
    'panicked_loud', 0.05, 0.95,
    0,

    json('{
        "staying_in_cage": 1.0,
        "making_loud_noise_when_startled": 0.98
    }'),

    json('{
        "cats_will_leave_me_alone": 0.40,
        "cage_will_protect_me": 0.85
    }')
);


-- =============================================================================
-- CHARACTER GOALS
-- =============================================================================

-- Toulouse's goals ------------------------------------------------------------
-- Primary goal: avoid boredom. This is modeled as avoidance of a within-person
-- state, not approach toward an external target.
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (1, 'avoid_boredom', 'surface', 0.95, 'avoidance', 'within_person');

-- Eating is a consistent high-priority goal, moderated by actual hunger.
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (1, 'resource_acquisition_food', 'surface', 0.72, 'approach', 'person_environment');

-- Belonging: Toulouse likes his humans and finds their company genuinely
-- satisfying, not merely instrumentally useful.
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (1, 'belonging_human_connection', 'surface', 0.60, 'approach', 'person_environment');

-- Understanding: Toulouse is curious about the world and investigates things.
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (1, 'understanding_exploration', 'surface', 0.55, 'approach', 'person_environment');

-- Sleep is a low-priority goal at 3am; it will become dominant toward morning.
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (1, 'sleep', 'surface', 0.20, 'approach', 'within_person');

-- Spook's goals ---------------------------------------------------------------
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (2, 'mastery_play', 'surface', 0.90, 'approach', 'within_person');

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (2, 'belonging_interaction', 'surface', 0.75, 'approach', 'person_environment');

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (2, 'social_responsibility_grooming', 'surface', 0.42, 'approach', 'person_environment');

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (2, 'resource_acquisition_food', 'surface', 0.55, 'approach', 'person_environment');

-- The mama's goals ------------------------------------------------------------
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (3, 'sleep', 'surface', 0.85, 'approach', 'within_person');

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (3, 'safety_comfort', 'surface', 0.70, 'approach', 'within_person');

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (3, 'social_responsibility_cat_care', 'surface', 0.62, 'approach', 'person_environment');

-- Reading: lower priority at 3am but may activate if she wakes.
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (3, 'understanding_reading', 'surface', 0.35, 'approach', 'within_person');

-- Guy's goals -----------------------------------------------------------------
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (4, 'sleep', 'surface', 0.90, 'approach', 'within_person');

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (4, 'social_responsibility_cat_care', 'surface', 0.65, 'approach', 'person_environment');

-- Morning routine: low priority now, will dominate when it is actually morning.
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (4, 'morning_routine', 'surface', 0.20, 'approach', 'within_person');

-- Lillis's goals --------------------------------------------------------------
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (5, 'sleep', 'surface', 0.95, 'approach', 'within_person');

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (5, 'safety_avoid_cats', 'surface', 0.88, 'avoidance', 'person_environment');


-- =============================================================================
-- CHARACTER ATTITUDES
-- All surface attitudes. No hidden attitudes needed for this module.
-- =============================================================================

-- Toulouse's attitudes --------------------------------------------------------
-- Toulouse genuinely likes his humans; he finds them useful, warm, and sometimes
-- surprising with their treats and vegetables.
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 3, 0.80, 'surface');  -- Toulouse → the mama

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 4, 0.75, 'surface');  -- Toulouse → guy

-- Spook is tolerated, occasionally entertaining, sometimes annoying.
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 2, 0.48, 'surface');  -- Toulouse → Spook

-- The bird is interesting in a way that is not exactly friendly.
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 5, 0.15, 'surface');  -- Toulouse → Lillis (predatory interest, not warmth)

-- Spook's attitudes -----------------------------------------------------------
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (2, 1, 0.68, 'surface');  -- Spook → Toulouse (admiring; wants to play)

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (2, 3, 0.85, 'surface');  -- Spook → the mama

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (2, 4, 0.78, 'surface');  -- Spook → guy

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (2, 5, 0.20, 'surface');  -- Spook → Lillis (excited interest)

-- The mama's attitudes --------------------------------------------------------
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (3, 1, 0.90, 'surface');  -- the mama → Toulouse

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (3, 2, 0.85, 'surface');  -- the mama → Spook

-- Guy's attitudes -------------------------------------------------------------
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (4, 1, 0.85, 'surface');  -- guy → Toulouse

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (4, 2, 0.80, 'surface');  -- guy → Spook

-- Lillis's attitudes ----------------------------------------------------------
-- Lillis is afraid of both cats. Spook's energy makes him the more alarming one.
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (5, 1, -0.58, 'surface');  -- Lillis → Toulouse (fearful)

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (5, 2, -0.72, 'surface');  -- Lillis → Spook (more fearful)


-- =============================================================================
-- INTERNAL STATES
-- Starting values at approximately 3am.
-- =============================================================================

-- Toulouse: boredom is the primary time-pressure mechanic. Starting at 0.50 —
-- restless and motivated, but not yet desperate. Hunger at 0.40 — the 10pm
-- auto-feeder has run but dry food is not exciting.
INSERT INTO internal_state (character_id, state_name, value, display_mode)
VALUES (1, 'boredom', 0.50, 'prose');

INSERT INTO internal_state (character_id, state_name, value, display_mode)
VALUES (1, 'hunger', 0.40, 'prose');

-- Spook: less bored (younger, more easily entertained by everything), also hungry.
INSERT INTO internal_state (character_id, state_name, value, display_mode)
VALUES (2, 'boredom', 0.28, 'prose');

INSERT INTO internal_state (character_id, state_name, value, display_mode)
VALUES (2, 'hunger', 0.38, 'prose');

-- Humans: high sleepiness at 3am. Displayed numerically since humans don't
-- narrate their own sleepiness in this module.
INSERT INTO internal_state (character_id, state_name, value, display_mode)
VALUES (3, 'sleepiness', 0.78, 'numeric');

-- Guy sleeps more deeply; harder to wake.
INSERT INTO internal_state (character_id, state_name, value, display_mode)
VALUES (4, 'sleepiness', 0.88, 'numeric');

-- Hairball pressure: an involuntary state for both cats. Builds gradually and
-- through grooming. The engine computes per-turn probability as
-- (value * involuntary_trigger_param) and rolls against it each turn.
-- Grooming actions (self-grooming or grooming another cat) raise this value
-- by the amount specified in involuntary_event_description.
--
-- Toulouse: moderate baseline. Less frantic groomer than Spook.
INSERT INTO internal_state (
    character_id, state_name, value, display_mode,
    is_involuntary, involuntary_trigger_type, involuntary_trigger_param,
    involuntary_event_description
) VALUES (
    1, 'hairball_pressure', 0.22, 'prose',
    1, 'probabilistic', 0.15,
    'Toulouse produces a hairball. This is involuntary and unpleasant — he does not enjoy it. Any human in earshot will wake and come to investigate. They will not be pleased. Their annoyance is genuine, not affectionate, regardless of their usual attitude toward the cat. ENGINE: raise hairball_pressure by 0.12 after each self-grooming session; raise by 0.10 after grooming another cat. Reset to 0.05 after a hairball event. Decay hairball_pressure by 0.02 per hour without grooming.'
);

-- Spook: higher baseline. He grooms himself frequently and also grooms Toulouse,
-- making his hairball pressure accumulate faster.
INSERT INTO internal_state (
    character_id, state_name, value, display_mode,
    is_involuntary, involuntary_trigger_type, involuntary_trigger_param,
    involuntary_event_description
) VALUES (
    2, 'hairball_pressure', 0.31, 'prose',
    1, 'probabilistic', 0.18,
    'Spook produces a hairball. Involuntary. Humans in earshot wake and investigate; they are not pleased. ENGINE: raise hairball_pressure by 0.15 after self-grooming; raise by 0.12 after grooming another cat. Reset to 0.05 after a hairball event. Decay by 0.02 per hour without grooming.'
);


-- =============================================================================
-- ITEMS
-- =============================================================================

-- Furniture and fixtures -------------------------------------------------------

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

-- Auto feeder: the food machine. Distributes dry food on a schedule.
-- Quality represents how recently it has dispensed (1.0 = just dispensed, decays).
-- Current value: the 2am feeding has just run; quality is moderate.
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

-- Litter box: quality float represents cleanliness.
-- 1.0 = freshly scooped, pristine. 0.0 = full, overflowing, unacceptable.
-- Starting value: 0.60 — acceptable but not ideal. It is the middle of the night
-- and it has not been scooped since yesterday evening.
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

-- Food items ------------------------------------------------------------------

-- Treats: inside the pantry cupboard, not directly visible.
-- is_visible = 0 because they are inside a closed cabinet.
INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (27, 1, 'treats',
    'The treats. Located inside the pantry cupboard. The best food item in the house by a significant margin. Humans will sometimes throw them across the room, which is excellent. The sound of the pantry opening is the primary signal of their potential availability.',
    2, 1.0, 0);  -- hidden inside pantry (is_visible=0)

-- Canned food: stored in the kitchen.
INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (28, 1, 'canned cat food',
    'Soft food in cans, stored in the kitchen. Significantly better than the dry food from the machine. The male human puts it out approximately twice per day, including in the morning. Whether it is morning yet is always worth investigating.',
    3, 0.90, 0);  -- stored in cabinet (is_visible=0)

-- Toys -----------------------------------------------------------------------

-- Soft mouse: portable, can be carried upstairs and dropped places.
INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (29, 1, 'soft mouse toy',
    'A small soft toy shaped approximately like a mouse. Light enough to carry in the mouth. Can be brought upstairs, dropped from elevated positions, or batted across smooth floors. A reliable toy.',
    1, 0.72, 1);

-- Jingle ball: makes a satisfying noise.
INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (30, 1, 'jingle ball',
    'A small ball with a bell inside. Makes a jingling sound when moved. The sound is interesting at 3am. The humans may disagree.',
    1, 0.80, 1);

-- Chirping toy: electronic, sounds like something alive.
INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (31, 1, 'chirping electronic toy',
    'A toy that emits chirping sounds when activated. Sounds plausibly like a small bird or insect. The battery may be getting low, which affects the sound quality in interesting ways.',
    1, 0.55, 1);

-- Bouncy spring toy: tends to go downstairs; hard to retrieve.
INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (32, 1, 'spring bounce toy',
    'A coiled spring toy that bounces unpredictably. Excellent fun until it goes down the stairs, at which point retrieving it is effortful. Currently on the main floor.',
    1, 0.78, 1);

-- Crinkle toy: soft and portable.
INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (33, 1, 'crinkle toy',
    'A soft toy made of crinkly material. Makes a satisfying sound when bitten or kneaded. Portable.',
    1, 0.68, 1);

-- Accidental toys (human objects) ---------------------------------------------

-- Mama's reading glasses: on her nightstand, probably.
INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (34, 1, 'reading glasses',
    'A pair of human optical devices belonging to the female human. Left on her nightstand. They slide satisfyingly on smooth surfaces and have interesting components. The humans do not seem to understand that these are toys.',
    10, NULL, 1);

-- Keys: probably in the dining room.
INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (35, 1, 'keys',
    'A bunch of metal keys on a ring. Left in the dining room. Make a good noise when batted. Can be moved to inconvenient locations. The humans do not seem to understand that these are also toys.',
    2, NULL, 1);

-- A hair tie: in the bathroom. Small, stretchy, satisfying.
INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (36, 1, 'hair tie',
    'A small elastic hair tie left on the bathroom counter. Stretchy, flingable, and small enough to bat under the gap at the bottom of the door. A very good accidental toy.',
    9, NULL, 1);

-- Hallway runner rug: in the main floor hallway. Can and does move.
-- This is a moveable item; its location_id tracks its current position.
-- quality encodes how displaced it currently is (1.0 = flat and centred,
-- lower = bunched or skewed from prior traffic). Starting value: 0.85.
INSERT INTO item (id, game_id, name, description, loc_id, quality, is_visible)
VALUES (37, 1, 'hallway runner',
    'A long thin rug running the length of the main floor hallway. The smooth floor beneath it means it can and does shift if a cat crosses it at speed. When it bunches or skews, it becomes a different kind of surface and also an interesting obstacle. The humans straighten it periodically.',
    13, 0.85, 1);


-- =============================================================================
-- CHARACTER SKILLS
-- =============================================================================

-- Toulouse: fetch.
-- He knows how to play fetch and genuinely enjoys it. His initiation method is
-- specific: he picks up a toy and drops it in front of or directly on a human,
-- then waits. This is not a random act — it is a deliberate play invitation with
-- an established protocol. A human who does not respond will receive a second
-- delivery. The intrinsic motivation is high: Toulouse will seek opportunities
-- to play fetch spontaneously, especially when bored.
INSERT INTO character_skill (character_id, skill_name, skill_level, intrinsic_motivation)
VALUES (1, 'fetch', 0.85, 0.90);

-- Toulouse: burrowing under blankets.
-- Toulouse is skilled at locating and entering the warm space beneath the covers
-- on the bed, particularly when a human is present. The combination of warmth
-- and proximity to a human is the point. He will work at the edge of the covers
-- until he has made an opening. High intrinsic motivation: he seeks this out.
INSERT INTO character_skill (character_id, skill_name, skill_level, intrinsic_motivation)
VALUES (1, 'burrowing under blankets', 0.90, 0.88);

-- Update Toulouse's surface_motivation and context_beliefs to reflect the food
-- preference nuance: dry food is actually preferred on its own merits, but
-- canned food is worth pursuing because it means a human is present and
-- engaged, which is independently valuable.
UPDATE character
SET
    surface_motivation = 'Wants to find something interesting to do. Would also accept food — preferably dry food, which he actually likes, though canned food has the advantage of indicating a human is present and doing something, which is interesting in its own right.',
    context_beliefs = json('{
        "humans_will_respond_to_meowing":   0.55,
        "food_available_from_humans":       0.35,
        "canned_food_signals_human_activity": 0.80,
        "interesting_things_to_discover":   0.50,
        "spook_available_to_interact_with": 0.50,
        "treats_accessible":                0.10,
        "human_will_play_fetch_if_asked":   0.45
    }')
WHERE id = 1;

-- =============================================================================
-- PRE-SEEDED LOCATION DETAILS
-- Established facts about the world at game start. Lazily generated details
-- are added by the engine at query time; these are known starting conditions.
-- =============================================================================

-- The couch arm is the premium window seat. This is an established fact.
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (1,
    'The arm of the couch, positioned directly at the window, is warm from the day and offers a clear view of the street below and the outside light.',
    1, 'significant physical rearrangement of living room furniture');

-- The outside light is on.
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (1,
    'An outside light illuminates the front of the building, making it possible to observe the street and entrance from the window.',
    1, 'outside light is turned off or dawn arrives and makes it irrelevant');

-- The auto feeder has recently dispensed. Food is in the bowl.
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (4,
    'The automatic feeder dispensed dry food at 2am. There is food in the bowl.',
    1, 'food is fully consumed');

-- The bird is asleep.
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (6,
    'The bird is asleep on her perch in the cage, feathers fluffed, eyes closed. She is boring.',
    1, 'bird is disturbed or woken');

-- The humans are asleep in the bedroom.
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (10,
    'Both humans are asleep in the bed. The female human may be a lighter sleeper.',
    1, 'either human wakes up');

-- The litter box has not been scooped since yesterday evening.
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (7,
    'The litter box was last scooped yesterday evening. It is acceptable but not pristine.',
    1, 'litter box is scooped');

-- The craft supplies are out, but whether string is accessible is lazy.
-- This detail will be generated on first investigation.
-- (No pre-seed for string: it is intentionally a lazy detail.)

-- Clutter character: established world facts for adjudication.
-- These details inform how the engine handles exploration and object interaction
-- throughout the house. Pre-seeded on the game's primary location (living room)
-- as world-level context; the engine should treat them as global.
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (1,
    'WORLD NOTE — applies house-wide: The house is cluttered but kept clean. There are no dirty dishes left out, no spoiling food, and no food debris other than scattered treat crumbs. Clutter consists of books, craft projects, electronics, bags, clothing, and miscellaneous objects. Most clutter items are not fragile; knocking them over or moving them produces noise and minor disorder but is unlikely to cause damage. Some objects are too heavy for a cat to move easily. The engine should not generate fragile-object-breaking outcomes for ordinary cat exploration behavior.',
    1, NULL  -- permanent world fact; no invalidation condition
);

-- Stray treats: because the humans throw crunchy treats across the room during
-- play sessions, stray treats accumulate under and behind furniture on the main
-- floor. When a cat investigates the space under or behind a piece of furniture
-- on the main floor, there is a plausible chance of finding one.
-- This is a lazy discovery mechanic: the engine generates the find on first
-- investigation of a specific hiding spot, then stores it as a location_detail.
-- The probability is moderate — treats are thrown often enough that finding one
-- is genuinely plausible, but not guaranteed.
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (1,
    'LAZY DISCOVERY MECHANIC — main floor: Crunchy treats are thrown across the room during play sessions. Stray treats accumulate under and behind furniture over time. When a cat investigates the space beneath or behind a main-floor furniture item for the first time, the engine should run a plausibility check (moderate probability: ~40%) and generate a treat discovery if it passes. Store the result as a new location_detail on that item''s location. A found treat is consumed immediately and its location_detail marked invalid.',
    1, NULL  -- mechanic description; does not expire
);


-- =============================================================================
-- NPC-PLAYER HISTORY
-- Initial relationship summaries at game start.
-- character_a_id < character_b_id by convention.
-- =============================================================================

-- Toulouse (1) ↔ Spook (2): established housemates. Toulouse tolerates Spook;
-- Spook admires Toulouse and wants to play with him more than Toulouse wants.
INSERT INTO npc_player_history (character_a_id, character_b_id, summary, interactions_since_summary)
VALUES (1, 2,
    'Toulouse and Spook have been housemates long enough for Toulouse to have formed clear opinions. Spook is entertaining to watch and occasionally useful as a source of activity, but his energy is a lot. Spook clearly looks up to Toulouse and tries to initiate play regularly, with mixed success. Toulouse has learned that Spook will clean his ears if he stays still long enough, which is acceptable. Spook''s cleanliness standards are another matter.',
    0);

-- Toulouse (1) ↔ the mama (3): warm and well-established. She gives good food.
INSERT INTO npc_player_history (character_a_id, character_b_id, summary, interactions_since_summary)
VALUES (1, 3,
    'The mama and Toulouse have a long and warm relationship. She gives him vegetables sometimes, which are surprisingly good. She responds to meowing more reliably than guy does in the middle of the night. She sometimes leaves things on the couch that need to be moved. She is asleep right now, which is technically her problem.',
    0);

-- Toulouse (1) ↔ guy (4): warm but guy is reliable rather than exciting.
INSERT INTO npc_player_history (character_a_id, character_b_id, summary, interactions_since_summary)
VALUES (1, 4,
    'Guy is reliable. He puts out canned food in the morning. When he enters the kitchen, it is always worth investigating whether morning has officially arrived. He is much harder to wake in the middle of the night than the mama and generally less yielding. He likes Toulouse, which is correct of him.',
    0);

-- Toulouse (1) ↔ Lillis (5): one-sided interest. Lillis does not appreciate Toulouse.
INSERT INTO npc_player_history (character_a_id, character_b_id, summary, interactions_since_summary)
VALUES (1, 5,
    'The bird in the cage is interesting. The cage is an ongoing engineering problem. The humans have opinions about reaching into it. The bird''s opinions are expressed loudly and physically when disturbed.',
    0);

-- Spook (2) ↔ the mama (3)
INSERT INTO npc_player_history (character_a_id, character_b_id, summary, interactions_since_summary)
VALUES (2, 3,
    'The mama is fond of Spook and tolerates his energy with good humor. She tells him he needs a bath, which he ignores.',
    0);

-- Spook (2) ↔ guy (4)
INSERT INTO npc_player_history (character_a_id, character_b_id, summary, interactions_since_summary)
VALUES (2, 4,
    'Guy likes Spook and plays with him occasionally. He is harder to engage late at night.',
    0);


-- =============================================================================
-- GAME INSTANCE
-- One row per playthrough. Sets the starting clock to 3:00 AM (180 minutes
-- past midnight) and marks the instance as ready for play.
--
-- Consolidated from seed_v5.sql (schema v5). The game_instance table was
-- added in v5; this record was previously seeded separately.
-- =============================================================================

INSERT INTO game_instance (
    game_id,
    status,
    start_time_minutes,
    current_time_minutes,
    premise_modifier
) VALUES (
    1,
    'ready',    -- fully initialised; engine may start immediately
    180,        -- 3:00 AM: canonical starting time for this module
    180,        -- current time = start time on a fresh instance
    NULL        -- no "What if..." premise modifier
);


-- =============================================================================
-- PASSIVE DRIFT RATES
-- Background drift rates on time-varying internal states. Applied by the engine
-- each turn after the clock advances, before Pass 3 runs.
-- Formula: new_value = clamp(value + rate * elapsed_minutes, 0.0, 1.0)
--
-- Consolidated from seed_v5.sql (schema v5).
-- =============================================================================

-- Toulouse — boredom: accumulates when nothing interesting happens.
-- Rate +0.002/min ≈ +0.12/hour. Starting at 0.00; failure condition at 1.0.
UPDATE internal_state
SET passive_rate_per_minute = 0.002
WHERE character_id = 1 AND state_name = 'boredom';

-- Toulouse — hunger: slow background accumulation.
-- Starting ~0.40; reaches ~0.70 after roughly 2.5 hours without eating.
UPDATE internal_state
SET passive_rate_per_minute = 0.002
WHERE character_id = 1 AND state_name = 'hunger';

-- Toulouse — hairball_pressure: very slow passive accumulation.
-- Most pressure comes from grooming events via Pass 2 outcome deltas;
-- this rate captures residual drift between grooming sessions.
UPDATE internal_state
SET passive_rate_per_minute = 0.0003
WHERE character_id = 1 AND state_name = 'hairball_pressure';

-- Guy — sleepiness (represents depth of sleep; high = deep, low = waking).
-- Negative rate: sleep lightens naturally as morning approaches.
-- At -0.006/min: starts at 0.88 (deeply asleep); reaches ~0.00 around 5:27 AM.
-- Disturbances may accelerate decay via Pass 2 internal_state_deltas.
UPDATE internal_state
SET passive_rate_per_minute = -0.006
WHERE character_id = 4 AND state_name = 'sleepiness';

-- The mama — sleepiness: lighter sleeper than Guy.
-- At -0.004/min: starts at 0.22; reaches ~0.00 (potentially waking) around 3:55 AM.
UPDATE internal_state
SET passive_rate_per_minute = -0.004
WHERE character_id = 3 AND state_name = 'sleepiness';


-- =============================================================================
-- GENDER AND PRONOUNS
-- Third-person pronoun sets for all characters. Passed to Pass 3 for consistent
-- prose rendering. Case labels are English-language keys regardless of module
-- language; form values are the actual pronouns.
--
-- Consolidated from seed_v6.sql (schema v6).
-- =============================================================================

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

-- The mama: female human, she/her/her
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

-- Lillis: female cockatiel, she/her/her
-- Named companion animals with a known sex are conventionally referred to
-- with personal pronouns in English.
UPDATE character
SET gender   = 'female',
    pronouns = '[{"case":"nominative","form":"she"},
                 {"case":"accusative","form":"her"},
                 {"case":"genitive","form":"her"}]'
WHERE id = 5;


-- =============================================================================
-- NPC WANDER PARAMETERS
-- Per-character autonomous movement configuration. The engine rolls against
-- wander_probability each turn; if it fires, the NPC moves to a random
-- adjacent location within their wander_range. The roll is skipped when
-- the character has a non-null pending_intent, an active current_activity,
-- or (for sleep-depth states) sleepiness >= WANDER_SLEEPINESS_THRESHOLD (0.60).
--
-- Consolidated from seed_v3.sql (initial values) and seed_v7.sql (corrections
-- for Guy and Mama after the sleepiness suppression mechanic was confirmed).
-- =============================================================================

-- Spook: uses the whole house freely; energetic and curious.
-- All 13 locations in range. Probability 0.08 ≈ one move per 12-13 turns,
-- enough for restless feel without disrupting sustained interaction.
UPDATE character
SET wander_range       = '[1,2,3,4,5,6,7,8,9,10,11,12,13]',
    wander_probability = 0.08
WHERE id = 2;

-- The mama: sleeping human; whole house except Tiled Overlook (8), which
-- requires squeezing through the railing. Low probability because she is
-- asleep; her sleepiness starts at 0.22 (below threshold), so the roll
-- is live from turn 1 — she may get up for the bathroom or a snack.
UPDATE character
SET wander_range       = '[1,2,3,4,5,6,7,9,10,11,12,13]',
    wander_probability = 0.10
WHERE id = 3;

-- Guy: sleeping human; same physical access as the mama. Starts deeply asleep
-- (sleepiness 0.88, above threshold), so the wander roll is suppressed until
-- his sleep lightens naturally (~5:27 AM). Probability 0.20 reflects
-- restlessness as morning approaches — roughly one move per 5 turns once
-- suppression lifts.
UPDATE character
SET wander_range       = '[1,2,3,4,5,6,7,9,10,11,12,13]',
    wander_probability = 0.20
WHERE id = 4;

-- Lillis: caged bird; cannot move autonomously.
-- wander_range records her fixed location; probability 0.0 ensures the engine
-- never attempts to move her.
UPDATE character
SET wander_range       = '[6]',
    wander_probability = 0.0
WHERE id = 5;


-- =============================================================================
-- LOCATION CONNECTIONS
-- Physical adjacency graph for all 13 locations. Each row is bidirectional;
-- by convention location_a_id < location_b_id. The engine validates all
-- movement against this table and uses it for BFS pathfinding.
--
-- Consolidated from seed_v3.sql (schema v3). The location_connection table
-- was added in v3 after the first play session revealed the LLM could move
-- characters to unreachable locations without an explicit adjacency model.
-- =============================================================================

-- Main floor loop: Living Room ↔ Dining Room ↔ Main Floor Hallway ↔ Living Room
-- The main floor can be traversed in a loop; all three rooms connect to the hallway.

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

-- Main Stairs ↔ Upper Hallway: staircase connecting main floor to upper floor
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (5, 12, 'stairs', 1);

-- Main Floor Hallway ↔ Basement Main Room: door off hallway leads to basement stairs
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (6, 13, 'stairs', 1);

-- Basement Main Room ↔ Basement Storage Room: interior door
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (6, 7, 'door', 1);

-- Upper Hallway ↔ Tiled Overlook: accessible by squeezing through the railing.
-- 'squeeze' reflects the physical effort; Toulouse can do it (capability 0.75).
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (8, 12, 'squeeze', 1);

-- Upper Hallway ↔ Bathroom: door off the hallway
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (9, 12, 'door', 1);

-- Upper Hallway ↔ Bedroom: door off the hallway; closed at 3am but passable.
-- A closed door is not an impassable barrier — Toulouse can scratch or push.
-- is_passable=1: the LLM adjudicates the interaction cost; the engine does not block.
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (10, 12, 'door', 1);

-- Upper Hallway ↔ Study: door off the hallway
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable)
VALUES (11, 12, 'door', 1);


-- =============================================================================
-- TOULOUSE VISITED LOCATIONS
-- Toulouse knows every room in the house — it is his territory and he has
-- explored every corner of it. All 13 locations are pre-marked as visited
-- so the player can quick-move to any room from the first turn.
--
-- Human NPCs and Lillis do not receive visited records; their movement is
-- engine-driven (wander) or LLM-driven (reactive), not player quick-move.
--
-- Consolidated from seed_v4.sql (schema v4).
-- =============================================================================

INSERT OR IGNORE INTO character_visited_location (character_id, location_id)
VALUES
    (1, 1),   -- Toulouse: Living Room
    (1, 2),   -- Toulouse: Dining Room
    (1, 3),   -- Toulouse: Kitchen
    (1, 4),   -- Toulouse: Utility Room
    (1, 5),   -- Toulouse: Main Stairs
    (1, 6),   -- Toulouse: Basement Main Room
    (1, 7),   -- Toulouse: Basement Storage Room
    (1, 8),   -- Toulouse: Tiled Overlook
    (1, 9),   -- Toulouse: Bathroom
    (1, 10),  -- Toulouse: Bedroom
    (1, 11),  -- Toulouse: Study
    (1, 12),  -- Toulouse: Upper Hallway
    (1, 13);  -- Toulouse: Main Floor Hallway
