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
-- This script populates a fresh database (schema v1) with all seed records
-- for the I Am a Cat module. Run after applying schema.sql.
--
-- Usage:
--   sqlite3 i_am_a_cat.db < ../../schema/schema.sql
--   sqlite3 i_am_a_cat.db < seed.sql
--   sqlite3 i_am_a_cat.db .tables   -- verify
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
        "pantry_rule": "Any human opening the pantry cupboard must be investigated immediately, without exception."
    }')
);


-- =============================================================================
-- LOCATIONS (11 total)
-- IDs 1-11. Connections between locations are managed by the engine at
-- adjudication time based on location type and description; no explicit
-- connection table is needed for this module.
-- =============================================================================

-- Main floor -------------------------------------------------------------------

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (1, 1, 'Living Room', 'living_room',
    'A comfortable room with a couch, an armchair, two coffee tables, and several plants the humans have inexplicably placed at cat level. A row of windows faces the street; an outside light means there is always something to observe if one is patient enough. The arm of the couch is a premium resting location: soft, flat, and positioned directly at the window. A short cat tree stands near the wall. A large dark rectangle (the TV) hangs on one wall and sometimes shows things that move. The female human occasionally leaves objects on the couch that are in the way and could theoretically be moved.',
    'private', 0,
    json('["night", "quiet", "humans_asleep", "outside_light_on"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (2, 1, 'Dining Room', 'dining_room',
    'A room containing a large flat hard surface the humans do not want cats on (the table) and several shorter flat soft surfaces that are apparently acceptable (the chairs). The pantry cupboard is here — a tall cabinet whose contents include TREATS. Any sound of this cupboard opening requires immediate investigation. There is a large window and an outside light. The porch is accessible through a door here. It is rare to see humans outside this window at night, but other animals occasionally appear on the porch.',
    'private', 0,
    json('["night", "quiet", "pantry_nearby"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (3, 1, 'Kitchen', 'kitchen',
    'The room where human food activities happen. The canned cat food is stored here. If the male human enters this room at any hour, it is worth investigating whether he considers it to be morning yet. The female human has been known to share pieces of spinach or cucumber, which are unexpectedly delicious. There is a flat counter area with a water source (sink). A large window overlooks the back.',
    'private', 0,
    json('["night", "quiet", "canned_food_nearby"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (4, 1, 'Laundry Room', 'utility_room',
    'A utilitarian room containing the automatic food dispenser, a water source (sink), and two large boxy appliances (the washer and dryer) that provide excellent hiding places behind them and sometimes harbor escaped toys. The food dispenser operates on a schedule regardless of whether anyone deserves it.',
    'private', 0,
    json('["night", "quiet", "auto_feeder_present"]')
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (5, 1, 'Main Stairs', 'stairwell',
    'The staircase connecting all three floors. A good vantage point. Toys placed at the top have interesting trajectories downward. The stairs to the basement are at one end; the stairs to the upper floor at the other.',
    'private', 0,
    json('["night", "quiet"]')
);

-- Basement --------------------------------------------------------------------

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (6, 1, 'Basement Main Room', 'basement_room',
    'A large cluttered room with many places to hide. The bird cage is here — the bird is asleep and boring, but the cage itself is interesting to investigate. The female human has a chair here facing a strange window (a computer). There are many craft supplies stored here: fabric, yarn, and various containers. Whether any string has been left accessible depends on how carefully the female human put things away. There are boxes and furniture and excellent hiding spots behind most of it.',
    'private', 0,
    json('["night", "quiet", "bird_asleep", "cluttered", "good_hiding_spots"]')
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
    'An adult woman who is genuinely fond of the cats, shares food items that are surprisingly good (spinach, cucumber), and reads in bed late. She is asleep right now but not as deeply as guy. She has craft supplies in the basement that may or may not be put away properly.',
    'Primary food-sharer; opener of the pantry; source of midnight snacks.',
    10,  -- bedroom, asleep

    -- OCEAN: Open and flexible (O high), reasonably organized but sometimes careless
    -- with craft supplies (C moderate), warm and social (E moderate-high), very
    -- agreeable — shares food, responds to cats (A high), not particularly anxious (N low).
    0.75, 0.62, 0.60, 0.85, 0.32,

    'safety',     -- asleep; physiological need for rest is dominant right now
    'deeply_asleep',

    'Wants to sleep. Will occasionally get up for a snack or to use the bathroom.',
    NULL,
    0,

    -- Voice when woken: warm but groggy. Short responses. May address the cat
    -- directly and with more affection than the hour warrants.
    'groggy_warm', 0.88, 0.30,
    0,

    json('{
        "ignoring_persistent_cat": 0.40,
        "falling_back_asleep":     0.75,
        "finding_midnight_snack":  0.85
    }'),

    json('{
        "cat_will_let_me_sleep": 0.50,
        "something_is_wrong_if_cat_is_insistent": 0.60
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
    'An adult man who likes the cats and puts out canned food reliably. Gets up earlier than the mama. Harder to wake in the middle of the night. His presence in the kitchen is a meaningful signal that morning may have arrived.',
    'Primary canned food provider; reliable morning anchor.',
    10,  -- bedroom, deeply asleep

    -- OCEAN: Moderate openness, high conscientiousness (reliable routines, gets up
    -- early), moderate extraversion, agreeable toward cats, low neuroticism.
    0.55, 0.75, 0.45, 0.75, 0.28,

    'physiological',  -- asleep; deeper sleep state than the mama
    'deeply_asleep',

    'Wants to sleep until morning. Will then make coffee and feed the cats.',
    NULL,
    0,

    -- Voice when woken: gruff, minimal, mostly unintelligible. Hard to get
    -- more than a syllable before he falls back asleep.
    'gruff_sleepy', 0.70, 0.18,
    0,

    json('{
        "sleeping_through_disturbance": 0.80,
        "getting_up_for_morning_routine": 0.95
    }'),

    json('{
        "it_is_not_morning_yet": 0.85,
        "cat_has_a_real_problem": 0.25
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

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (1, 1, 'couch',
    'A large soft thing with cushions, good for sleeping on, nesting in, and jumping off. The arm is especially desirable: flat, slightly elevated, and positioned directly beside the living room window. Sharpening claws on the sides is not permitted, which is an ongoing disagreement.',
    1, 0.80, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (2, 1, 'armchair',
    'A good sitting chair. Not as prime as the couch arm, but a solid secondary position with a decent view of the room.',
    1, 0.75, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (3, 1, 'short cat tree (living room)',
    'A short cat tree with a flat top platform, a lower perch, and a post wrapped in something satisfying to scratch. Positioned well in the living room. Identical to the one upstairs.',
    1, 0.85, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (4, 1, 'TV (living room)',
    'A large dark rectangle mounted on the wall that sometimes shows things that move and make sounds. The humans call it the TV. It is currently off and dark, which makes it boring. When on, it occasionally shows birds or small animals that require close investigation.',
    1, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (5, 1, 'coffee table (large)',
    'A flat hard surface at a good height. Good for sitting on and observing the room, or for placing objects that then fall off.',
    1, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (6, 1, 'coffee table (small)',
    'A smaller flat surface. Good for sitting on. Things can be knocked off it.',
    1, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (7, 1, 'plant (tasty)',
    'A plant the humans have placed in the living room. They do not seem to understand that it is food. It is quite good. Probably a cat grass or something similarly reasonable.',
    1, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (8, 1, 'plant (not tasty)',
    'Another plant the humans have placed here. Unlike the other one, this one does not taste good. The experience of finding this out was disappointing.',
    1, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (9, 1, 'dining table',
    'A large flat hard surface the humans don''t want cats on. This is a rule that has been noted and considered.',
    2, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (10, 1, 'dining chairs',
    'Shorter flat surfaces with soft cushions that are apparently acceptable to sit on. The humans'' position on cats on chairs vs. cats on the table is difficult to fully understand.',
    2, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (11, 1, 'pantry cupboard',
    'A tall cabinet in the dining room. Contains treats. The sound of its opening is distinctive and requires immediate investigation regardless of current location or activity. Other food items may also be inside.',
    2, NULL, 1);

-- Auto feeder: the food machine. Distributes dry food on a schedule.
-- Quality represents how recently it has dispensed (1.0 = just dispensed, decays).
-- Current value: the 2am feeding has just run; quality is moderate.
INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (12, 1, 'automatic food dispenser',
    'A machine that dispenses dry food approximately every four hours (2am, 6am, 10am, 2pm, 6pm, 10pm). It does this without being asked and without any warmth or ceremony. The food is perfectly acceptable but lacks the meaning of food distributed by a human. The 2am feeding has recently run.',
    4, 0.70, 1);  -- 0.70: recently dispensed, still has food available

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (13, 1, 'washer',
    'A large boxy appliance. Excellent for hiding behind. Sometimes vibrates, which is startling but also interesting.',
    4, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (14, 1, 'dryer',
    'Another large boxy appliance. Also good for hiding behind. Sometimes warm on top after a cycle, which is a premium sleeping spot if one can get up there.',
    4, NULL, 1);

-- Litter box: quality float represents cleanliness.
-- 1.0 = freshly scooped, pristine. 0.0 = full, overflowing, unacceptable.
-- Starting value: 0.60 — acceptable but not ideal. It is the middle of the night
-- and it has not been scooped since yesterday evening.
INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (15, 1, 'litter box',
    'The litter box. Cats have strong opinions about its condition. A full or dirty litter box is an affront and will be treated as such. Currently at acceptable-but-not-ideal cleanliness; has not been scooped since yesterday evening.',
    7, 0.60, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (16, 1, 'bird cage',
    'A metal cage containing the bird. The bars present an engineering challenge the cats have not yet solved. The humans have been explicit about the reaching-in policy. The bird is currently asleep inside and therefore boring, but the cage itself is interesting to sniff and sit near.',
    6, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (17, 1, 'computer (basement)',
    'A glowing rectangle the female human likes to look at while sitting in her chair in the basement. Currently off and dark. When on, it sometimes shows interesting things. The chair in front of it is a good sitting spot.',
    6, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (18, 1, 'craft supplies',
    'A collection of fabric, yarn, containers, and various crafting materials stored in the basement. Most of it is in bins and bags. Whether any string or ribbon has been left accessible depends on how carefully the female human put things away before bed. Worth investigating.',
    6, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (19, 1, 'storage boxes (basement)',
    'Many boxes of various sizes. Most are sealed and too heavy to move. Good for hiding behind. Not much else.',
    7, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (20, 1, 'short cat tree (study)',
    'A short cat tree identical to the one in the living room. Has a post wrapped in sisal rope that is excellent for claw maintenance. Located in the study, where claw-sharpening is explicitly sanctioned.',
    11, 0.85, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (21, 1, 'cardboard scratch pad',
    'A flat corrugated cardboard surface on the floor of the study. Good for scratching. Has that satisfying texture.',
    11, 0.75, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (22, 1, 'TV (study)',
    'A large dark rectangle in the study that the male human likes to look at a lot. Currently off.',
    11, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (23, 1, 'bed',
    'The large soft flat sleeping surface in the bedroom. The humans are currently on it. Cats are welcome on or under it. It is warm and good for sleeping. It is also a viable play location if one is persistent, though this tends to produce a reaction.',
    10, 0.95, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (24, 1, 'nightstand (mama)',
    'The female human''s nightstand. Has things on it. Some of these things are at a good height for interaction. A glass of water may be present.',
    10, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (25, 1, 'nightstand (guy)',
    'The male human''s nightstand. Also has things on it.',
    10, NULL, 1);

INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (26, 1, 'water container (bathroom)',
    'A cup or container left in the bathroom that holds water. This water is somehow better than the water in the bowl. It can be played with: scooped, scattered, and generally enjoyed. The humans do not seem to understand why this is the preferred water source.',
    9, NULL, 1);

-- Food items ------------------------------------------------------------------

-- Treats: inside the pantry cupboard, not directly visible.
-- is_visible = 0 because they are inside a closed cabinet.
INSERT INTO item (id, game_id, name, description, location_id, held_by_character_id, quality, is_visible)
VALUES (27, 1, 'treats',
    'The treats. Located inside the pantry cupboard. The best food item in the house by a significant margin. Humans will sometimes throw them across the room, which is excellent. The sound of the pantry opening is the primary signal of their potential availability.',
    2, NULL, 1.0, 0);  -- hidden inside pantry (is_visible=0)

-- Canned food: stored in the kitchen.
INSERT INTO item (id, game_id, name, description, location_id, held_by_character_id, quality, is_visible)
VALUES (28, 1, 'canned cat food',
    'Soft food in cans, stored in the kitchen. Significantly better than the dry food from the machine. The male human puts it out approximately twice per day, including in the morning. Whether it is morning yet is always worth investigating.',
    3, NULL, 0.90, 0);  -- stored in cabinet (is_visible=0)

-- Toys -----------------------------------------------------------------------

-- Soft mouse: portable, can be carried upstairs and dropped places.
INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (29, 1, 'soft mouse toy',
    'A small soft toy shaped approximately like a mouse. Light enough to carry in the mouth. Can be brought upstairs, dropped from elevated positions, or batted across smooth floors. A reliable toy.',
    1, 0.72, 1);

-- Jingle ball: makes a satisfying noise.
INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (30, 1, 'jingle ball',
    'A small ball with a bell inside. Makes a jingling sound when moved. The sound is interesting at 3am. The humans may disagree.',
    1, 0.80, 1);

-- Chirping toy: electronic, sounds like something alive.
INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (31, 1, 'chirping electronic toy',
    'A toy that emits chirping sounds when activated. Sounds plausibly like a small bird or insect. The battery may be getting low, which affects the sound quality in interesting ways.',
    1, 0.55, 1);

-- Bouncy spring toy: tends to go downstairs; hard to retrieve.
INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (32, 1, 'spring bounce toy',
    'A coiled spring toy that bounces unpredictably. Excellent fun until it goes down the stairs, at which point retrieving it is effortful. Currently on the main floor.',
    1, 0.78, 1);

-- Crinkle toy: soft and portable.
INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (33, 1, 'crinkle toy',
    'A soft toy made of crinkly material. Makes a satisfying sound when bitten or kneaded. Portable.',
    1, 0.68, 1);

-- Accidental toys (human objects) ---------------------------------------------

-- Mama's reading glasses: on her nightstand, probably.
INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (34, 1, 'reading glasses',
    'A pair of human optical devices belonging to the female human. Left on her nightstand. They slide satisfyingly on smooth surfaces and have interesting components. The humans do not seem to understand that these are toys.',
    10, NULL, 1);

-- Keys: probably in the dining room.
INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (35, 1, 'keys',
    'A bunch of metal keys on a ring. Left in the dining room. Make a good noise when batted. Can be moved to inconvenient locations. The humans do not seem to understand that these are also toys.',
    2, NULL, 1);

-- A hair tie: in the bathroom. Small, stretchy, satisfying.
INSERT INTO item (id, game_id, name, description, location_id, quality, is_visible)
VALUES (36, 1, 'hair tie',
    'A small elastic hair tie left on the bathroom counter. Stretchy, flingable, and small enough to bat under the gap at the bottom of the door. A very good accidental toy.',
    9, NULL, 1);


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
