-- =============================================================================
-- DAVE RPG Engine — Seed Data: The Hidden Hostel (Test World Module)
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- The Hidden Hostel is a test world module for the DAVE RPG Engine. It exists
-- to provide deliberate, broad coverage of implemented engine features in a
-- single playable module. Unlike the narrative modules (I Am a Cat, Meryton),
-- this module is designed to exercise specific mechanical behaviors and edge
-- cases rather than to tell a particular story — though it is fully playable.
--
-- Setting: The Hidden Hostel — an inn that exists in a liminal space between
-- worlds. Guests arrive from different eras, places, and cosmologies. The
-- hostel is neutral ground; its rules are simple and absolute. The Innkeeper
-- (Marta) has always been here. No one is entirely sure how long.
--
-- Schema version: 8
-- Characters: 6 (1 player, 5 NPC)
-- Locations: 5 (Common Room, Kitchen, Upper Corridor, Room A, Room B)
-- Factions: 1 (hosts_of_the_hostel)
--
-- Feature coverage:
--   Multi-hop BFS pathfinding  — Kitchen → Common Room → Upper Corridor → Room A
--   Staircase connection        — Common Room ↔ Upper Corridor (connection_type='stairs')
--   Impassable connection       — Upper Corridor ↔ Room B (is_passable=0, locked)
--   Wander positive control     — The Wanderer (prob=0.75, no suppression conditions)
--   Wander suppression: pending_intent  — The Scholar
--   Wander suppression: sleepiness      — Gin-chan (sleepiness=0.72 ≥ threshold 0.60)
--   Wander suppression: activity        — The Old Soldier (sharpening blade)
--   Wander suppression: activity        — Marta (preparing evening meal)
--   Hidden motivation + access control  — The Scholar (access_hidden_motivation=0)
--   Faction + status designation        — hosts_of_the_hostel (Marta=keeper, player=guest)
--   Attitudes                           — positive, negative, and NPC-to-NPC pairs
--   Internal state drift                — positive (curiosity), negative (sleepiness)
--   Lazy world generation               — Common Room has pre-seeded detail (retrieval
--                                         path); Rooms A and B have skeleton only
--   Pronouns (they/them)                — The Scholar, Gin-chan
--   Character-level speech filter       — PENDING schema v9. Gin-chan's vocalizations
--                                         are currently unfiltered at schema level.
--                                         voice_register='cat' signals Pass 3 to use
--                                         meow variants in the interim. When v9 adds
--                                         speech_filter to the character table,
--                                         Gin-chan should have speech_filter='cat'.
--   Future mechanic (not yet built)     — A potion grants temporary ability to
--                                         understand Gin-chan. Requires item/inventory
--                                         system + player state modifier. Tracked in
--                                         implementation_status.md pending work.
--
-- Usage (fresh install):
--   sqlite3 modules/hidden_hostel/hidden_hostel.db < schema/schema.sql
--   sqlite3 modules/hidden_hostel/hidden_hostel.db < modules/hidden_hostel/seed.sql
--
-- To reset a running instance to starting state without rebuilding:
--   sqlite3 modules/hidden_hostel/hidden_hostel.db < modules/hidden_hostel/reset_instance.sql
--
-- To run:
--   DAVE_DB_PATH=modules/hidden_hostel/hidden_hostel.db python3 -m engine
-- =============================================================================

PRAGMA foreign_keys = ON;


-- =============================================================================
-- GAME
-- =============================================================================

INSERT INTO game (
    id, name, genre, tone, era, technology_level, magic_system,
    narrative_register, speech_filter, internal_state_display, cultural_norms
) VALUES (
    1,
    'The Hidden Hostel',
    'liminal_fantasy',
    'mysterious_whimsical',
    NULL,   -- timeless; guests arrive from many eras
    NULL,   -- no consistent technology level across worlds
    'The hostel exists in a liminal space between worlds. Guests from impossible origins, minor uncanny events, and the occasional impossible architecture are unremarkable here. No rules of physics or chronology are guaranteed within these walls — but the fire in the Common Room always burns, and Marta''s meals are always ready.',
    'second_person',
    '{}',   -- no game-level speech filter; character-level filter for Gin-chan pending schema v9
    '{"curiosity": "prose", "fatigue": "prose", "sleepiness": "prose"}',
    '{
        "hospitality": "The hostel is neutral ground. Violence or threats against other guests are grounds for immediate expulsion. Marta enforces this without exception and without appeal.",
        "the_locked_room": "Room B at the end of the upper corridor has been locked for as long as anyone can remember. Marta will not discuss it. Attempting to force entry is considered a serious transgression against the hostel.",
        "gin_chan": "Gin-chan is a resident of the hostel, not a pet. Treating them as such is considered rude. Gin-chan communicates in their own way and is understood by those who pay attention.",
        "payment": "No currency is accepted or required. Guests offer what they can — a story, a skill, a piece of knowledge from their world. The manner of contribution is between each guest and the hostel."
    }'
);


-- =============================================================================
-- LOCATIONS
-- =============================================================================

-- Ground floor

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    1, 1, 'Common Room', 'common_room',
    'A wide, low-ceilinged room with mismatched chairs arranged around a central hearth. The fire is lit. A staircase rises along one wall toward the upper floor; a door leads to the kitchen. The furniture suggests many origins: carved oak, cushioned velvet, something that was once a throne.',
    'public', 3,
    '["evening", "fire_lit", "guests_present"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    2, 1, 'Kitchen', 'kitchen',
    'A large working kitchen smelling of something warm and unidentifiable — not unpleasant. A heavy wooden worktable occupies the center. The shelves hold more jars and implements than should reasonably fit in the space.',
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
    -- Room A: accessible to the player. Sparse skeleton with no pre-generated
    -- details — first entry exercises the lazy-generation code path.
    4, 1, 'Room A', 'bedroom',
    'A small guest room. A writing desk with a tilted surface occupies most of one wall. Books are stacked wherever they fit, in no system visible to the casual eye. A candle burns on the desk.',
    'private', 0,
    '["evening", "candle_lit", "occupied"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES (
    -- Room B: impassable from the corridor (locked). The player can observe it
    -- from outside but never enter. Exists in the location graph to test the
    -- adjacency guard in _apply_outcome() and impassable-connection handling
    -- in Pass 2 context assembly. Skeleton describes what can be inferred
    -- from outside the door only.
    5, 1, 'Room B', 'bedroom',
    'A closed door at the far end of the corridor. The wood is darker than the surrounding wall. No light shows beneath it. There is no visible handle on the corridor side.',
    'private', 0,
    '["locked", "inaccessible", "unknown_interior"]'
);


-- =============================================================================
-- LOCATION CONNECTIONS
-- Convention: location_a_id < location_b_id (schema constraint).
-- The engine queries both directions at runtime via OR logic.
-- =============================================================================

INSERT INTO location_connection (location_a_id, location_b_id, connection_type,
                                  is_passable, passage_note)
VALUES
    -- Common Room ↔ Kitchen: standard door, both directions passable.
    (1, 2, 'door', 1, NULL),

    -- Common Room ↔ Upper Corridor: STAIRCASE.
    -- Exercises the 'stairs' connection_type. Movement-phrase parsing tests
    -- target this connection: "go upstairs", "climb to the corridor",
    -- "head up to the upper floor" should all resolve to a move targeting
    -- location 3. See tests/test_pass1_eval.py for regression coverage.
    (1, 3, 'stairs', 1, NULL),

    -- Upper Corridor ↔ Room A: standard door, passable.
    (3, 4, 'door', 1, NULL),

    -- Upper Corridor ↔ Room B: LOCKED — impassable.
    -- is_passable=0 causes the engine to reject any move targeting location 5.
    -- passage_note gives the LLM semantic context for Pass 2 adjudication
    -- if the player attempts to enter or interact with the door.
    (3, 5, 'door', 0,
     'locked; the door has no handle on the corridor side and has not opened in living memory');


-- =============================================================================
-- GAME INSTANCE
-- Starting time: 8:00 PM (1200 minutes past midnight).
-- Status must be ''ready'' for the engine to start.
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
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Character 1: The Traveller (player character)
-- Newly arrived. Female. No OCEAN profile seeded — the player defines
-- their character through play. No wander parameters; players never wander.
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
    1, 1, 'The Traveller', 'player', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'A traveller of uncertain origin, recently arrived. Carries little; observes much.',
    'guest',
    1,  -- Common Room
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
-- WANDER SUPPRESSION TEST: activity suppression (current_activity set below).
-- wander_probability=0.0 additionally — Marta never leaves the hostel.
-- FACTION TEST: member of hosts_of_the_hostel with status designation.
-- ATTITUDE TEST: wary toward the player (0.35 surface) — new guests are assessed.
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
    '{"innkeeping": 0.90, "managing_difficult_guests": 0.85, "knowing_when_not_to_ask": 0.88}',
    '{"hostel_stability": 0.92, "guest_safety": 0.85, "being_overrun": 0.25}',
    'Runs the hostel. Keeps guests fed, housed, and civil. Does not ask too many questions.',
    NULL,   -- no hidden motivation; Marta is exactly what she appears to be
    0,
    'matter_of_fact', 0.52, 0.42,
    NULL, 0.0,
    -- Activity: preparing the evening meal. Started 7:00 PM (1140), duration 90 min.
    -- Expires at 1230 (8:30 PM, 30 minutes into play). Not yet expired at start.
    -- activity_duration_confidence=0.72 > ACTIVITY_AUTO_CLEAR_CONFIDENCE (0.60),
    -- so the engine will auto-clear when started_at + estimated_duration <= current_time.
    'preparing the evening meal',
    1140,   -- 7:00 PM (60 minutes before game start at 1200)
    90,     -- estimated 90-minute activity; expires at game clock 1230
    0.72,   -- above auto-clear threshold; engine will clear mechanically when expired
    0       -- not renewable
);

-- ---------------------------------------------------------------------------
-- Character 3: The Wanderer
-- A frequent traveller between worlds. Friendly, spontaneous, no fixed agenda.
-- WANDER POSITIVE CONTROL: high wander_probability, no suppression conditions.
-- NPC-TO-NPC ATTITUDE: Old Soldier → Wanderer is negative (see attitudes below).
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
    'Curious about the other guests and the hostel itself. Happy to talk, equally happy to roam.',
    'casual_warm', 0.82, 0.78,
    '[1, 2, 3]',    -- Common Room, Kitchen, Upper Corridor
    0.75            -- WANDER POSITIVE CONTROL: no pending_intent, no activity, sleepiness not tracked
);

-- ---------------------------------------------------------------------------
-- Character 4: The Scholar
-- From an unspecified world; their gender does not map cleanly to familiar
-- categories. Uses they/them pronouns.
-- WANDER SUPPRESSION TEST: pending_intent suppression (set below).
-- HIDDEN MOTIVATION TEST: access_hidden_motivation=0; fleeing pursuit.
-- PRONOUN TEST: they/them for a character where gender is genuinely unknown.
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
    'safety',   -- Maslow override: safety-seeking is the dominant need right now
    'guarded',
    '{"scholarly_research": 0.92, "deciphering_unknown_systems": 0.80, "going_unnoticed": 0.55}',
    '{"hostel_as_sanctuary": 0.72, "being_found_here": 0.12, "scholarly_access": 0.68}',
    'Researching; believes a specific text exists somewhere in the hostel and intends to locate it before leaving.',
    -- Hidden motivation (access_hidden_motivation=0 — concealed from Pass 1 and player):
    'Fled their home world to escape pursuit. The hostel''s liminal nature offers protection — whatever is following them cannot easily cross between worlds. They are considerably more frightened than they appear, and their research is partly a way of not thinking about it.',
    0,  -- concealed; must not appear in Pass 1 context or player-facing prose
    'precise_quiet', 0.48, 0.55,
    '[3, 4]',   -- Upper Corridor + Room A
    0.20,       -- low wander probability; suppressed additionally by pending_intent
    -- pending_intent suppresses the wander roll regardless of wander_probability.
    'seeking a specific text rumored to exist somewhere in the hostel; will approach any guest who seems knowledgeable'
);

-- ---------------------------------------------------------------------------
-- Character 5: The Old Soldier
-- Arrived recently; origins unclear. Distrustful by long habit.
-- WANDER SUPPRESSION TEST: activity suppression (current_activity set below).
-- ATTITUDE TEST: negative toward player (-0.30) and Wanderer (-0.40, NPC→NPC).
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
    'A heavy-set woman with the build of someone who was once formidable and remains more capable than she looks. A long blade lies across her knees. She has positioned herself against the corridor wall with sight lines to both doors.',
    'guest',
    3,  -- Upper Corridor
    0.22, 0.80, 0.32, 0.22, 0.65,
    'safety',
    'vigilant',
    '{"combat": 0.88, "threat_assessment": 0.85, "trusting_strangers": 0.05, "being_inconspicuous": 0.60}',
    '{"current_safety": 0.55, "hostel_as_neutral_ground": 0.62, "other_guests_as_threat": 0.45}',
    'Resting. Prefers the corridor to a room — exits visible from both ends. Not looking for conversation.',
    'terse_gruff', 0.18, 0.22,
    '[3, 4]',   -- Upper Corridor + Room A
    0.28,       -- suppressed by current_activity
    -- Activity: sharpening a blade. Started 7:30 PM (1170), duration 60 min.
    -- Expires at 1230 (8:30 PM, 30 minutes into play). Not yet expired at start.
    'sharpening a blade, seated against the corridor wall with sight lines to both doors',
    1170,   -- 7:30 PM (30 minutes before game start at 1200)
    60,     -- estimated 60-minute activity; expires at game clock 1230
    0.80,   -- high confidence; engine will auto-clear when expired
    0       -- not renewable
);

-- ---------------------------------------------------------------------------
-- Character 6: Gin-chan
-- A silver-gray winged cat of indeterminate gender and uncertain origin.
-- Permanent resident of the hostel; not a guest.
-- WANDER SUPPRESSION TEST: sleepiness suppression (0.72 ≥ threshold 0.60).
-- PRONOUN TEST: they/them for a nonhuman whose gender is genuinely unknown.
-- SPEECH FILTER TEST: pending schema v9. voice_register='cat' signals Pass 3
--   to use meow variants in the interim. When v9 adds speech_filter to the
--   character table, Gin-chan should have speech_filter='cat'.
-- FUTURE MECHANIC: a potion (pending item/inventory system) grants the player
--   temporary ability to understand Gin-chan. Tracked in pending work.
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
    -- voice_register='cat' is the interim signal to Pass 3 to render Gin-chan''s
    -- speech as meow variants until character-level speech_filter is implemented.
    'cat', 0.60, 0.35,
    '[1, 2]',   -- Common Room + Kitchen
    0.50        -- suppressed by sleepiness (0.72 ≥ WANDER_SLEEPINESS_THRESHOLD 0.60)
);


-- =============================================================================
-- CHARACTER GOALS (Ford-Nichols Motivational Systems Theory)
-- Drawn from the 24-goal taxonomy. Hidden goals (goal_type='hidden') are
-- subject to access_hidden_motivation on the character record.
-- =============================================================================

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES
    -- Marta: belonging to the hostel (identity-level) + resource acquisition (operational)
    (2, 'belonging',            'surface', 0.80, 'approach', 'person_environment'),
    (2, 'resource_acquisition', 'surface', 0.65, 'approach', 'person_environment'),

    -- The Wanderer: driven primarily by exploration; belongs to moving between worlds
    (3, 'exploration', 'surface', 0.88, 'approach', 'person_environment'),
    (3, 'belonging',   'surface', 0.55, 'approach', 'person_environment'),

    -- The Scholar: primary surface goal is understanding; hidden goal is safety (avoidance)
    (4, 'understanding', 'surface', 0.90, 'approach',  'within_person'),
    (4, 'safety',        'hidden',  0.80, 'avoidance', 'person_environment'),

    -- The Old Soldier: safety-as-vigilance dominant; equity reflects a residual code
    (5, 'safety', 'surface', 0.82, 'avoidance', 'person_environment'),
    (5, 'equity', 'surface', 0.50, 'approach',  'person_environment'),

    -- Gin-chan: intrinsic drives; self-determination above all
    (6, 'understanding',      'surface', 0.72, 'approach', 'within_person'),
    (6, 'self_determination', 'surface', 0.80, 'approach', 'within_person');


-- =============================================================================
-- CHARACTER SKILLS
-- Open natural-language taxonomy. The LLM evaluates semantic relevance at
-- adjudication time without a lookup table.
-- =============================================================================

INSERT INTO character_skill (character_id, skill_name, skill_level, intrinsic_motivation)
VALUES
    -- Marta
    (2, 'innkeeping',                    0.82, 0.75),
    (2, 'herbalism and practical remedy', 0.65, 0.60),

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
    (6, 'silent observation',            0.90, 0.85);


-- =============================================================================
-- INTERNAL STATES
-- Only characters with tracked passive states are listed here.
-- State value: 0.0 (absent/minimum) to 1.0 (maximum/overwhelming).
-- passive_rate_per_minute: positive = accumulates; negative = decays.
-- =============================================================================

INSERT INTO internal_state (
    character_id, state_name, value, display_mode,
    is_involuntary, passive_rate_per_minute
)
VALUES
    -- The Traveller: curiosity increases as she explores the hostel
    (1, 'curiosity',  0.40, 'prose', 0,  0.001),

    -- Marta: fatigue builds over a long evening of preparation
    (2, 'fatigue',    0.55, 'prose', 0,  0.002),

    -- Gin-chan: sleepiness drifts negative (slowly waking from afternoon nap).
    -- Value 0.72 exceeds WANDER_SLEEPINESS_THRESHOLD (config default: 0.60),
    -- so the engine skips Gin-chan''s wander roll until this drops below 0.60.
    -- At rate -0.001/min, suppression lifts after ~120 game minutes (10:00 PM).
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
    -- Marta: the founding keeper; unquestioned standing with the faction she embodies
    (2, 1, 0.90,
     'Founding keeper of the Hidden Hostel. Marta''s standing with hosts_of_the_hostel is unquestioned.'),

    -- The Traveller: newly arrived; guest status acknowledged but untested
    (1, 1, 0.40,
     'Newly arrived traveller. Guest status acknowledged; no significant actions taken yet.');


-- =============================================================================
-- CHARACTER ATTITUDES
-- attitude: -1.0 (hostile) to 1.0 (warm/trusting); 0.0 = neutral/unknown.
-- =============================================================================

-- Attitudes toward The Traveller (player character)
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    (3, 1,  0.65, 'surface'),   -- Wanderer → Traveller: open, friendly
    (4, 1,  0.60, 'surface'),   -- Scholar → Traveller: cautiously positive
    (2, 1,  0.35, 'surface'),   -- Marta → Traveller: wary; new guests are assessed
    (5, 1, -0.30, 'surface'),   -- Old Soldier → Traveller: suspicious; default for strangers
    (6, 1,  0.50, 'surface');   -- Gin-chan → Traveller: mild interest; fire-adjacent

-- Traveller's attitudes toward NPCs
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    (1, 2,  0.40, 'surface');   -- Traveller → Marta: baseline trust in the innkeeper

-- NPC-to-NPC attitudes (exercises non-player attitude pair in context assembly)
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES
    -- Old Soldier → Wanderer: negative; the Wanderer's ease makes the Soldier uneasy
    (5, 3, -0.40, 'surface');


-- =============================================================================
-- LOCATION DETAILS (lazy world generation)
-- The Common Room has one pre-seeded detail to exercise the detail retrieval
-- code path. All other locations have no details; first entry triggers
-- lazy generation, which is then stored canonically in location_detail.
-- =============================================================================

INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES (
    1,
    'The central hearth is surrounded by mismatched chairs — carved oak, cushioned velvet, and what appears to be a throne reduced by time and use to something merely comfortable. The fire burns steadily, as it always does.',
    1,
    'fire goes out or is significantly altered'
);


-- =============================================================================
-- CHARACTER VISITED LOCATIONS
-- Pre-populated for characters who know the space at game start.
-- The Traveller knows only the Common Room (just arrived).
-- Marta knows both ground-floor rooms. The Wanderer has roamed all accessible
-- ground-floor and upper-corridor locations. The Scholar went straight upstairs.
-- The Old Soldier holds the upper corridor. Gin-chan has not left the fire today.
-- =============================================================================

INSERT INTO character_visited_location (character_id, location_id)
VALUES
    -- The Traveller: Common Room only
    (1, 1),
    -- Marta: Common Room + Kitchen
    (2, 1),
    (2, 2),
    -- The Wanderer: Common Room, Kitchen, Upper Corridor (roams freely)
    (3, 1),
    (3, 2),
    (3, 3),
    -- The Scholar: Upper Corridor + Room A (went straight upstairs)
    (4, 3),
    (4, 4),
    -- The Old Soldier: Upper Corridor only
    (5, 3),
    -- Gin-chan: Common Room (has not moved from the fire today)
    (6, 1);
