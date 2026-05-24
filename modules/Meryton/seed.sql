-- =============================================================================
-- DAVE RPG Engine — Seed Data: Meryton Module, Chapter 3
-- "The First Assembly"
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- Source: Pride and Prejudice, Jane Austen (1813). Chapter 3.
-- Setting: A public assembly at the Meryton civic rooms, Hertfordshire.
--          Evening. Elizabeth Bennet is sitting out the first two sets.
--
-- Design principle: seed honest psychological values, not scripted outcomes.
-- Characters generate their own behavior from OCEAN traits and MST goals.
-- Minor catastrophes emerge from truthful seeding; nothing is scripted.
--
-- Location model: Regency public assembly hall (Shire Hall, Hertford type).
-- This location graph is designed as a reusable template for any module
-- set in a similar venue. See location_graph_sketch.md for full rationale.
--
-- Schema version: 7
-- Characters: 13 (1 player, 12 NPC)
-- Locations: 13 (6 navigable public, 3 non-passable, 4 service)
-- Factions: 3 (bennet_family, meryton_neighborhood, bingley_circle)
--
-- Usage (fresh install — schema.sql is the canonical current schema):
--   sqlite3 modules/Meryton/meryton.db < schema/schema.sql
--   sqlite3 modules/Meryton/meryton.db < modules/Meryton/seed.sql
--
-- Migration scripts in schema/migrations/ are only needed when upgrading an
-- existing database. A fresh database always uses schema.sql directly.
-- =============================================================================

PRAGMA foreign_keys = ON;


-- =============================================================================
-- GAME
-- =============================================================================

INSERT INTO game (
    id, name, genre, tone, era, technology_level, magic_system,
    narrative_register, speech_filter, internal_state_display, cultural_norms
) VALUES (
    2,
    'Meryton: The First Assembly',
    'social_comedy',
    'ironic_observational',
    'Regency England, approximately 1812',
    'pre-industrial',
    NULL,  -- no magic
    'third_person_close',
    '{}',  -- no speech filter; all characters speak normally
    '{"composure": "prose", "social_ease": "prose", "curiosity": "prose",
      "anxiety": "prose", "excitement": "prose", "social_discomfort": "prose",
      "pride": "prose", "enjoyment": "prose"}',
    '{
        "dancing": "A lady who refuses a set must sit it out entirely for that set. Refusing a partner is a significant social statement and will be observed.",
        "introductions": "A gentleman must be formally introduced before addressing a lady he does not know. Bingley''s party arrived as strangers; Sir William Lucas is the appropriate introducer.",
        "conversation": "A person engaged in conversation does not simply walk away. To do so is considered rude under any circumstances. Characters with pending social engagements remain in place.",
        "service_areas": "A lady or gentleman of quality does not enter service passages, back stairs, or staging areas. To do so would be considered eccentric at best, scandalous at worst.",
        "card_room": "The card room is predominantly occupied by older guests and those disinclined to dance. A young lady entering unescorted would be unusual but not impossible.",
        "supper_room": "The supper room is closed for this assembly — no supper is served. The door is unlocked but convention prohibits entry. A well-bred guest would not attempt it without compelling reason."
    }'
);


-- =============================================================================
-- LOCATIONS
-- =============================================================================

-- Ground floor — public

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    1, 2, 'Street Entrance and Vestibule', 'entrance',
    'The street door opens onto a narrow vestibule of stone flags, lit by a lamp above the entrance. The noise of the assembly reaches down faintly from above. Through the door, the night air and the sounds of horses and carriages waiting.',
    'semi_private', 4,
    '["evening", "carriages_outside", "assembly_in_progress"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    2, 2, 'Staircase', 'hallway',
    'A broad staircase of dark wood, lit by candles in wall sconces. The music from the ballroom above grows with each step. The landing is visible from below; the street door visible from the landing. Being seen on the staircase is being seen.',
    'semi_private', 6,
    '["evening", "candlelit", "assembly_in_progress"]'
);

-- First floor — assembly rooms

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    3, 2, 'Landing', 'hallway',
    'The landing is quieter than the rooms beyond, the music muffled by the closed ballroom door. Tall sash windows face the street, dark now, with candlelight reflected in the glass. A door to the left leads to the ballroom; a door to the right to the card room. At the far end of the landing, two doors stand closed.',
    'semi_private', 8,
    '["evening", "candlelit", "assembly_in_progress", "quieter_than_ballroom"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    4, 2, 'Ballroom', 'ballroom',
    'The ballroom is fully lit — candles in wall sconces and a chandelier overhead, doubled in the dark windows along the far wall. Two lines of couples are forming for the next set. Along the walls, chairs are occupied by those sitting out; small groups stand in conversation near the doors. At the far end, the musicians are tuning. The room smells of candle wax, powder, and the warmth of many people.',
    'public', 60,
    '["evening", "dancing_in_progress", "music_playing", "candlelit",
      "assembly_in_progress", "crowded", "observed"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    5, 2, 'Card Room', 'sitting_room',
    -- NOTE: presence inferred from building type and standard assembly practice;
    -- not directly evidenced in Chapter 3 text.
    'The card room is lit more dimly than the ballroom, the music from next door reduced to a steady rhythm through the wall. Two or three tables are occupied; the conversation is quieter here, the company older on average. A window looks onto the street.',
    'semi_private', 12,
    '["evening", "candlelit", "assembly_in_progress", "quieter_than_ballroom", "cards_in_play"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    6, 2, 'Ladies'' Retiring Room', 'retiring_room',
    -- NOTE: presence inferred from standard assembly provision; not mentioned
    -- in Chapter 3 text.
    'A small room with a dressing table, a mirror, and two chairs. A maid is in attendance. The sounds of the assembly are distant here.',
    'private', 2,
    '["evening", "candlelit", "private", "ladies_only"]'
);

-- First floor — non-passable (convention or lock)

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    7, 2, 'Supper Room', 'dining_room',
    'Dark and smelling of cold wood and linen. Tables folded against the walls, chairs stacked. The noise of the assembly is muffled. Nothing here is meant to be seen tonight.',
    'private', 0,
    '["dark", "unused", "evening", "closed_by_convention"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    8, 2, 'Corn Market Hall', 'hall',
    'Dark. The smell of grain and stone floors. Tall shuttered windows. Trestle tables along the walls. The noise of the assembly is faint and distant. This is not where anyone should be at this hour.',
    'private', 0,
    '["dark", "locked", "closed", "ground_floor"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    9, 2, 'Magistrate''s Room', 'formal_room',
    'A formal room with a raised bench and heavy furniture. Closed during the assembly. The weight of civic authority is present even in the dark.',
    'private', 0,
    '["dark", "locked", "closed", "formal"]'
);

-- Ground floor — service cluster

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    10, 2, 'Service Entrance and Back Yard', 'service_entrance',
    'A flagged yard at the rear of the building, lit by a single lamp above the service door. Stacked crates, a handcart. The sounds of the assembly are faint from here. The street is accessible around the corner of the building, but this is not the entrance anyone came to use.',
    'private', 3,
    '["evening", "service_area", "outside_accessible", "staff_only"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    11, 2, 'Back Stairs', 'staircase',
    'Narrow stairs of bare wood, lit by a single candle in a holder on the wall. Sounds of movement above and below. The smell of food and tallow.',
    'private', 2,
    '["evening", "service_area", "staff_only", "narrow"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    12, 2, 'Service Passage', 'hallway',
    'A narrow corridor, low-ceilinged, smelling of candle wax and the warmth of the rooms on the other side of the thin walls. The music is clearly audible through the ballroom door. A series of plain doors, each leading to one of the assembly rooms.',
    'private', 4,
    '["evening", "service_area", "staff_only", "music_audible"]'
);

INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    13, 2, 'Staging Area', 'service_room',
    'A small, warm room that smells of wine and pastry. A table holds trays set for carrying. Bottles are arranged along one wall. A candle burns on the table. From beyond the door, the muffled beat of the music.',
    'private', 2,
    '["evening", "service_area", "staff_only", "refreshments"]'
);


-- =============================================================================
-- LOCATION CONNECTIONS
-- Convention: location_a_id < location_b_id always.
-- passage_note is included wherever barrier type requires LLM context.
-- =============================================================================

-- Ground floor public → staircase
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (1, 2, 'stairs', 1, NULL);

-- Staircase → landing
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (2, 3, 'stairs', 1, NULL);

-- Landing → ballroom
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (3, 4, 'door', 1, NULL);

-- Landing → card room
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (3, 5, 'door', 1, NULL);

-- Landing → ladies' retiring room
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (3, 6, 'door', 1, NULL);

-- Landing → supper room (convention-closed)
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (3, 7, 'door', 0,
    'Closed by convention — door unlocked, room unlit and unused. Entering would be considered improper for a lady without compelling reason. The social cost is significant; a character with low conscientiousness or high self-determination motivation might attempt it regardless.');

-- Landing → corn market (locked)
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (3, 8, 'door', 0,
    'Locked during the evening assembly. Requires a key or forced entry; no social workaround is available.');

-- Landing → magistrate's room (locked)
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (3, 9, 'door', 0,
    'Locked during the evening assembly. Requires a key or forced entry.');

-- Ballroom ↔ card room (internal, open — modeled as arch; acoustically permeable)
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (4, 5, 'open', 1, NULL);

-- Ballroom → service passage (service door)
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (4, 12, 'door', 1,
    'Service entrance to ballroom — staff only. An upper-class character entering from here would emerge visibly from the wrong side of the room and attract immediate attention from those nearby.');

-- Card room → service passage (service door)
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (5, 12, 'door', 1,
    'Service entrance to card room — staff only. Less visible than the ballroom entrance but still conspicuous to anyone present.');

-- Supper room → service passage (service door; always open for staff)
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (7, 12, 'door', 1,
    'Service access to the supper room — open to staff at all times regardless of the room''s public status.');

-- Supper room → staging area (direct service access)
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (7, 13, 'door', 1,
    'Direct passage between staging and supper room — service use only.');

-- Service entrance → back stairs
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (10, 11, 'stairs', 1,
    'Service stairs — staff only. An upper-class character here would be conspicuously out of place and likely mistaken for lost or attempting to leave discreetly.');

-- Back stairs → service passage
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (11, 12, 'stairs', 1,
    'Service stairs connecting ground floor service entrance to first floor service passage — staff only.');

-- Service passage → staging area
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (12, 13, 'open', 1, NULL);


-- =============================================================================
-- FACTIONS
-- =============================================================================

INSERT INTO faction (id, game_id, name, description) VALUES (
    1, 2, 'bennet_family',
    'The Bennet family unit. Elizabeth''s primary allegiance and the source of her most consequential decisions. The family''s central concern is financial security — the Longbourn estate is entailed away from the female line, and Mr. Bennet''s death will leave his wife and daughters dependent on good marriages or the charity of relatives. Actions that advance the family''s security, reputation, or social harmony raise standing; actions that embarrass them, damage their prospects, or defy clear family interest lower it. Mrs. Bennet is the loudest voice but not the only one; Mr. Bennet''s quiet approval matters, and Jane''s wellbeing is never far from Elizabeth''s mind.'
);

INSERT INTO faction (id, game_id, name, description) VALUES (
    2, 2, 'meryton_neighborhood',
    'The local social community of Meryton and its surrounds: the Lucas family, the Philips family, and the general neighborhood. This is the primary public reputation metric for the Chapter 3 assembly. The neighborhood values social grace, appropriate behavior, management of one''s family''s excesses, and good dancing. Elizabeth is well-regarded here — she is clever and personable, and her family''s eccentricities are familiar enough to be forgiven. Behavior that draws favorable comment raises standing; public embarrassments (especially caused by Mrs. Bennet or the younger Bennet sisters) lower it, as the family is seen as a unit.'
);

INSERT INTO faction (id, game_id, name, description) VALUES (
    3, 2, 'bingley_circle',
    'Charles Bingley, his sisters Caroline and Louisa, and Mr. Darcy. Their social reference points are higher and their standards more exclusive than the Meryton neighborhood. They arrived as strangers; their judgments are forming in real time during this assembly. Elizabeth can have strong neighborhood standing and weak standing with this group simultaneously — this is essentially her situation through most of the novel. Darcy''s stated dismissal of her as "not handsome enough" sets a low initial ceiling, but his actual attention to her is already more complex than his words suggest. Miss Bingley''s condescension is social positioning, not final judgment.'
);


-- =============================================================================
-- CHARACTERS
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Elizabeth Bennet (player character)
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    1, 2, 'Elizabeth Bennet', 'player', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'A young woman of middling height with fine eyes and an expressive, intelligent face. She is not considered a conventional beauty but her animation makes her striking. She is currently seated along the wall, watching the dancing with evident amusement.',
    'Second daughter of Mr. Bennet of Longbourn; well-regarded locally.',
    4,  -- Ballroom
    0.78, 0.62, 0.55, 0.62, 0.28,
    'belonging', 'anticipatory',
    'Enjoying the assembly; curious about Bingley''s party and their manners.',
    NULL, 0,
    'informal_witty', 0.68, 0.65,
    '[4, 3, 5, 6]',  -- ballroom, landing, card room, retiring room
    0.05  -- rarely wanders; she observes more than she moves
);

-- Elizabeth's goals (Ford-Nichols MST)
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (1, 'understanding — making sense of people and their psychology', 'surface', 0.85, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (1, 'individuality — maintaining her own perspective and judgment under social pressure', 'surface', 0.78, 'approach', 'within_person');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (1, 'belonging — genuine connection with Jane, Charlotte, and her family', 'surface', 0.72, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (1, 'equity — resistance to condescension and unfair social judgment', 'surface', 0.65, 'avoidance', 'person_environment');

-- Elizabeth's skills
INSERT INTO character_skill (character_id, skill_name, skill_level)
VALUES (1, 'reading social dynamics and character', 0.82);
INSERT INTO character_skill (character_id, skill_name, skill_level)
VALUES (1, 'witty conversation and verbal sparring', 0.78);
INSERT INTO character_skill (character_id, skill_name, skill_level)
VALUES (1, 'country dancing', 0.70);
INSERT INTO character_skill (character_id, skill_name, skill_level)
VALUES (1, 'maintaining composure under condescension', 0.75);

-- Elizabeth's internal states
INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (1, 'composure', 0.78, 'prose', NULL);
INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (1, 'social_ease', 0.72, 'prose', NULL);
INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (1, 'curiosity', 0.70, 'prose', +0.002);  -- builds as the evening develops

-- Elizabeth's faction reputations
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (1, 1, 0.65, 'Respected and trusted daughter; no conflicts yet this evening.');
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (1, 2, 0.68, 'Well-regarded locally; clever and personable. The family is eccentric but Elizabeth is not.');
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (1, 3, 0.30, 'Unknown to Bingley''s party on arrival. Darcy''s dismissal ("not handsome enough to tempt me") sets a low initial ceiling, though his subsequent attention suggests his judgment is already more complicated than his words.');


-- -----------------------------------------------------------------------------
-- Mr. Darcy
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    2, 2, 'Mr. Darcy', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'A tall, handsome man of aristocratic bearing, well-dressed and composed. He moves through the room without engaging; his expression is difficult to read. He was remarked on as extremely eligible for the first half of the evening, and as proud and disagreeable for the second.',
    'Mr. Fitzwilliam Darcy of Pemberley, Derbyshire; £10,000 a year. Friend to Bingley.',
    4,  -- Ballroom (walking)
    0.35, 0.82, 0.18, 0.22, 0.38,
    'esteem', 'disdainful',
    'Enduring a social occasion he finds beneath him; protecting his sense of propriety and social position.',
    'Has noticed Miss Elizabeth Bennet''s response to his dismissal with unexpected interest — her amusement rather than distress is not what he expected. Will not act on this and is not yet certain what to make of it.',
    0,  -- hidden motivation not accessible to player by default
    'formal_clipped', 0.20, 0.28,
    -- Wander range: ballroom and landing only. He walks the room but does
    -- not retreat to the card room or explore further.
    -- NOTE: wander suppression via pending_intent (engine.py) will prevent
    -- him from walking away mid-conversation. "It just Isn't Done." His
    -- high conscientiousness (0.82) makes this doubly appropriate.
    '[3, 4]',
    0.15  -- walks the room regularly; not stationary
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (2, 'status preservation — protecting the Darcy name and social position', 'surface', 0.82, 'avoidance', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (2, 'affiliation — loyalty to his own circle (Bingley, Georgiana)', 'surface', 0.70, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (2, 'understanding — forming accurate assessments of people and situations', 'hidden', 0.60, 'approach', 'person_environment');

INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (2, 'social_discomfort', 0.72, 'prose', +0.001);
INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (2, 'composure', 0.80, 'prose', NULL);  -- controls discomfort effectively
INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (2, 'pride', 0.78, 'prose', NULL);


-- -----------------------------------------------------------------------------
-- Mr. Bingley
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    3, 2, 'Mr. Bingley', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'A pleasant-looking young man with an open, cheerful face. He danced every dance, talked with animation, and was angry only that the ball ended so early. He is visibly enjoying himself.',
    'Mr. Charles Bingley of Netherfield Park; £4,000–5,000 a year. Recently let Netherfield.',
    4,  -- Ballroom (dancing)
    0.68, 0.42, 0.88, 0.82, 0.22,
    'belonging', 'delighted',
    'Thoroughly enjoying the assembly; eager to dance, meet people, and make a good impression on the neighborhood.',
    NULL, 0,
    'warm_enthusiastic', 0.88, 0.75,
    '[3, 4, 5]',
    0.12
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (3, 'belonging — genuine enjoyment of people and social company', 'surface', 0.85, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (3, 'affiliation — warmth; wanting to like and be liked', 'surface', 0.78, 'approach', 'person_environment');

INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (3, 'enjoyment', 0.82, 'prose', NULL);
INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (3, 'social_ease', 0.90, 'prose', NULL);


-- -----------------------------------------------------------------------------
-- Jane Bennet
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    4, 2, 'Jane Bennet', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'The eldest Miss Bennet; considered the beauty of the family. She has a gentle, open expression and moves gracefully. She danced twice with Bingley and seemed to find him genuinely agreeable.',
    'Eldest daughter of Mr. Bennet of Longbourn.',
    4,  -- Ballroom (dancing / wall)
    0.52, 0.72, 0.55, 0.92, 0.18,
    'belonging', 'quietly_hopeful',
    'Enjoying the evening; hoping to make a good impression; privately pleased by Mr. Bingley''s attention.',
    NULL, 0,
    'warm_gentle', 0.92, 0.55,
    '[3, 4]',
    0.05
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (4, 'affiliation — deep attachment to family and genuine connection', 'surface', 0.88, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (4, 'harmony — avoidance of conflict; she absorbs difficulty rather than create friction', 'surface', 0.80, 'avoidance', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (4, 'romance — present but private; she hopes without declaring', 'hidden', 0.65, 'approach', 'person_environment');


-- -----------------------------------------------------------------------------
-- Charlotte Lucas
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    5, 2, 'Charlotte Lucas', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'A sensible, plain young woman a few years older than Elizabeth. She is pleasant and sociable without being showy. She and Elizabeth are close friends.',
    'Eldest daughter of Sir William and Lady Lucas of Lucas Lodge.',
    4,  -- Ballroom, near Elizabeth initially
    0.58, 0.78, 0.50, 0.68, 0.22,
    'safety', 'pleasant',
    'Enjoying the society; observing the new arrivals with clear-eyed interest; glad to be with Elizabeth.',
    'Aware of her own position as an unmarried woman of modest means; assessing the evening''s matrimonial prospects with pragmatic attention.',
    0,
    'calm_direct', 0.68, 0.58,
    '[3, 4, 5]',
    0.08
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (5, 'security — pragmatic awareness of her position and limited options', 'hidden', 0.82, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (5, 'affiliation — genuine warmth for Elizabeth', 'surface', 0.72, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (5, 'understanding — she reads people accurately', 'surface', 0.68, 'approach', 'person_environment');


-- -----------------------------------------------------------------------------
-- Mrs. Bennet
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    6, 2, 'Mrs. Bennet', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'A woman of middling age, expressive face, and loud voice. She is seated along the wall with Lady Lucas, reporting everything she observes with editorial commentary. She notices everything that happens to her daughters.',
    'Wife of Mr. Bennet of Longbourn; mother of five daughters.',
    4,  -- Ballroom, wall seating; she has observational range over most of the room
    0.32, 0.42, 0.92, 0.45, 0.88,
    'safety', 'excited_and_anxious',
    'Watching Bingley''s every move; calculating which daughter he favors; determined to secure introductions.',
    NULL, 0,
    'loud_effusive', 0.55, 0.92,
    '[4]',  -- stays in ballroom; maximum observation range
    0.02   -- essentially stationary; she watches from the wall
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (6, 'security — financial security for herself and daughters after Mr. Bennet''s death', 'surface', 0.95, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (6, 'status — daughters'' advantageous marriages as social standing', 'surface', 0.82, 'approach', 'person_environment');

INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (6, 'anxiety', 0.65, 'prose', NULL);
INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (6, 'excitement', 0.80, 'prose', NULL);
INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (6, 'composure', 0.22, 'prose', NULL);  -- low; already struggling to contain herself


-- -----------------------------------------------------------------------------
-- Lydia Bennet
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    7, 2, 'Lydia Bennet', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'The youngest Miss Bennet; tall, well-grown, and already developing the assurance of a woman of fashion. She is loud, energetic, and entirely unaware of or untroubled by social consequences.',
    'Youngest daughter of Mr. Bennet of Longbourn.',
    4,  -- Ballroom (dancing)
    0.58, 0.08, 0.95, 0.48, 0.18,
    'belonging', 'giddy',
    'Having as much fun as possible; dancing with everyone available; loudly enjoying herself.',
    NULL, 0,
    'loud_girlish', 0.55, 0.88,
    -- Wide wander range: Lydia goes wherever she pleases. Her C=0.08 means
    -- she will pass through convention-closed locations if she notices them
    -- and nothing immediate stops her. This is a feature, not a bug.
    '[3, 4, 5, 6, 7]',
    0.28  -- moves frequently; one of the highest wander_probabilities in the cast
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (7, 'entertainment — immediate; she wants to have fun right now', 'surface', 0.90, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (7, 'status through male attention — she measures success by admiration', 'surface', 0.72, 'approach', 'person_environment');

INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (7, 'excitement', 0.90, 'prose', NULL);
INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (7, 'composure', 0.15, 'prose', NULL);


-- -----------------------------------------------------------------------------
-- Kitty Bennet (Catherine)
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    8, 2, 'Kitty Bennet', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'The fourth Miss Bennet; follows Lydia''s lead in most things. Less extreme in every respect.',
    'Fourth daughter of Mr. Bennet of Longbourn.',
    4,  -- Ballroom
    0.48, 0.28, 0.75, 0.52, 0.48,
    'belonging', 'excited',
    'Enjoying herself; following Lydia''s lead; dancing when she can.',
    NULL, 0,
    'cheerful_uncertain', 0.58, 0.65,
    '[3, 4, 5, 6]',
    0.18  -- moves frequently but less than Lydia; often in her wake
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (8, 'belonging — wants to be part of the fun; follows Lydia', 'surface', 0.78, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (8, 'entertainment — dancing and admiration', 'surface', 0.68, 'approach', 'person_environment');


-- -----------------------------------------------------------------------------
-- Mary Bennet
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    9, 2, 'Mary Bennet', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'The middle Miss Bennet; bookish and plain, with the serious expression of someone who considers herself more accomplished than she is given credit for.',
    'Third daughter of Mr. Bennet of Longbourn.',
    4,  -- Ballroom, wall seating
    0.62, 0.78, 0.18, 0.42, 0.55,
    'esteem', 'earnest',
    'Observing the assembly with a view to forming considered opinions; hoping to be recognized as accomplished.',
    NULL, 0,
    'formal_pedantic', 0.42, 0.70,
    '[4]',  -- stays in ballroom; unlikely to move
    0.03
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (9, 'recognition — wants acknowledgment of her accomplishments and intelligence', 'surface', 0.80, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (9, 'understanding — forming moral and intellectual judgments', 'surface', 0.65, 'approach', 'within_person');


-- -----------------------------------------------------------------------------
-- Miss Bingley (Caroline)
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    10, 2, 'Miss Bingley', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'A handsome woman, elegantly dressed, with an air of self-possession and superiority. She moves with her brother''s party and addresses the neighborhood with condescension she takes for politeness.',
    'Sister to Mr. Bingley; £20,000 fortune.',
    4,  -- Ballroom, with her party
    0.42, 0.55, 0.68, 0.28, 0.52,
    'esteem', 'poised_and_watchful',
    'Maintaining social superiority; attending to Darcy; observing the neighborhood with assessment that falls short of interest.',
    'Pursuing Darcy; everything she does this evening is subordinate to this. She has not yet registered Elizabeth as relevant.',
    0,
    'formal_condescending', 0.28, 0.65,
    '[3, 4, 5]',
    0.10
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (10, 'status — maintaining and advancing her social position', 'surface', 0.78, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (10, 'romance — securing Darcy; everything is subordinate to this', 'hidden', 0.88, 'approach', 'person_environment');


-- -----------------------------------------------------------------------------
-- Mrs. Hurst (Louisa)
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    11, 2, 'Mrs. Hurst', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'The elder Miss Bingley, now married. She follows her sister''s social lead and is primarily occupied with her own comfort.',
    'Wife of Mr. Hurst; sister to Mr. Bingley.',
    4,  -- Ballroom, with her party
    0.40, 0.48, 0.58, 0.35, 0.38,
    'belonging', 'comfortable',
    'Following Miss Bingley''s social lead; mildly interested in proceedings.',
    NULL, 0,
    'formal_languid', 0.38, 0.45,
    '[3, 4, 5]',
    0.08
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (11, 'comfort — her own ease and contentment', 'surface', 0.72, 'approach', 'within_person');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (11, 'affiliation — alignment with her sister''s judgments', 'surface', 0.58, 'approach', 'person_environment');


-- -----------------------------------------------------------------------------
-- Mr. Hurst
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    12, 2, 'Mr. Hurst', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    '"Merely looked the gentleman." A man of comfortable girth and a preoccupied expression, currently settled at a card table with a glass within reach. He will not move unless strongly prompted.',
    'Husband to Mrs. Hurst; brother-in-law to Mr. Bingley.',
    5,  -- Card Room; he started here and intends to stay
    0.28, 0.35, 0.22, 0.42, 0.32,
    'physiological', 'content',
    'Playing cards; eating and drinking as opportunity allows; being left alone.',
    NULL, 0,
    'terse_indifferent', 0.42, 0.22,
    '[5]',  -- card room only; will not venture further
    0.01   -- essentially immobile
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (12, 'comfort — cards, food, drink, and not being disturbed', 'surface', 0.88, 'approach', 'within_person');


-- -----------------------------------------------------------------------------
-- Lady Lucas
-- -----------------------------------------------------------------------------
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, apparent_status, current_location_id,
    ocean_openness, ocean_conscientiousness, ocean_extraversion,
    ocean_agreeableness, ocean_neuroticism,
    maslow_tier, emotional_state,
    surface_motivation, hidden_motivation, access_hidden_motivation,
    voice_register, voice_warmth, voice_verbosity,
    wander_range, wander_probability
) VALUES (
    13, 2, 'Lady Lucas', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'A pleasant, sociable woman of the neighborhood, seated beside Mrs. Bennet. She knows who everyone is, what everyone''s prospects are, and is happy to discuss both.',
    'Wife of Sir William Lucas of Lucas Lodge.',
    4,  -- Ballroom, wall seating near Mrs. Bennet
    0.45, 0.55, 0.68, 0.62, 0.42,
    'belonging', 'sociable',
    'Enjoying good gossip with Mrs. Bennet; observing all social developments with neighborly interest.',
    NULL, 0,
    'warm_chatty', 0.68, 0.78,
    '[4]',  -- stays in ballroom; wall seating
    0.03
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (13, 'belonging — community and social connection', 'surface', 0.75, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (13, 'understanding — knowing what is happening and who is connected to whom', 'surface', 0.68, 'approach', 'person_environment');


-- =============================================================================
-- CHARACTER ATTITUDES
-- Starting attitudes between key character pairs at the top of the assembly.
-- 0.0 = neutral/unknown; range -1.0 (hostile) to 1.0 (warm/trusting).
-- attitude_type 'surface' = expressed and observable; 'hidden' = concealed.
--
-- Each row is directional: character_id holds the attitude toward target_id.
-- Both directions of a relationship require separate rows.
-- =============================================================================

-- Elizabeth → Darcy: just been snubbed; amused rather than wounded
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 2, -0.15, 'surface');  -- mild public coolness; not wounded
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 2, -0.05, 'hidden');   -- privately more amused than offended

-- Elizabeth → Bingley: favorable first impression
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 3, 0.35, 'surface');

-- Elizabeth → Jane: warm sisterly love
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 4, 0.92, 'surface');

-- Elizabeth → Charlotte: genuine close friendship
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 5, 0.80, 'surface');

-- Darcy → Elizabeth: surface dismissal; hidden interest already stirring
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (2, 1, -0.30, 'surface');  -- openly dismissive ("not handsome enough")
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (2, 1, 0.12, 'hidden');    -- unexpected flicker of interest; not yet conscious

-- Darcy → Bingley: genuine warmth and protectiveness
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (2, 3, 0.78, 'surface');

-- Bingley → Jane: immediate, genuine attraction
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (3, 4, 0.55, 'surface');

-- Jane → Bingley: pleasantly interested; more reserved on surface than she feels
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (4, 3, 0.30, 'surface');
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (4, 3, 0.50, 'hidden');

-- Miss Bingley → Darcy: pursuing; warmest attitude she has for anyone
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (10, 2, 0.65, 'hidden');

-- Miss Bingley → Jane: surface politeness masking indifference
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (10, 4, 0.05, 'surface');
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (10, 4, -0.12, 'hidden');


-- =============================================================================
-- CHARACTER_VISITED_LOCATION
-- Elizabeth begins having visited only the ballroom (she arrived and sat down).
-- =============================================================================

INSERT INTO character_visited_location (character_id, location_id)
VALUES (1, 4);  -- Elizabeth has visited the ballroom


-- =============================================================================
-- GAME INSTANCE
-- Must be the last INSERT; status 'ready' signals the engine can start.
-- The assembly is set at approximately 8:00 PM (1200 minutes past midnight).
-- =============================================================================

INSERT INTO game_instance (
    game_id, status, start_time_minutes, current_time_minutes, premise_modifier
) VALUES (
    2, 'ready', 1200, 1200, NULL
);
