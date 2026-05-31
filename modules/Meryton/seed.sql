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
-- Locations: 14 (7 navigable public, 3 non-passable, 4 service)
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
    'The local social community of Meryton and its surrounds: the Lucas family, the Phillips family, and the general neighborhood. This is the primary public reputation metric for the Chapter 3 assembly. The neighborhood values social grace, appropriate behavior, management of one''s family''s excesses, and good dancing. Elizabeth is well-regarded here — she is clever and personable, and her family''s eccentricities are familiar enough to be forgiven. Behavior that draws favorable comment raises standing; public embarrassments (especially caused by Mrs. Bennet or the younger Bennet sisters) lower it, as the family is seen as a unit.'
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


-- =============================================================================
-- SESSION 10 ADDITIONS
--
-- New characters: Sir William Lucas (14), Mr. Robinson (15), John Lucas (16),
--   Edward Long (17), Thomas Phillips (18), William Goulding (19).
-- Pre-snub start: scene opens as the Bennet family arrives at the vestibule.
--   Elizabeth and Darcy are strangers; attitudes reset accordingly.
-- Miss Bingley and Mrs. Hurst: internal states added.
-- Game: cultural_norms updated with assembly scale context.
-- =============================================================================


-- =============================================================================
-- PRE-SNUB START: adjustments to existing character records
-- These UPDATEs run after the INSERTs above and override values that
-- assumed a mid-assembly starting point. The snub scene now plays out
-- during gameplay rather than being baked into the starting state.
-- =============================================================================

-- Elizabeth starts in the vestibule; scene opens as the family arrives.
UPDATE character SET
    current_location_id = 1,
    description = 'A young woman of middling height with fine eyes and an expressive, intelligent face. She is not considered a conventional beauty but her animation makes her striking. She has just arrived at the assembly with her family.'
WHERE id = 1;

-- Elizabeth has not yet visited any location (arriving now).
DELETE FROM character_visited_location WHERE character_id = 1;

-- Elizabeth and Darcy are strangers on arrival; no attitudes yet formed.
-- Both the surface and hidden rows are reset.
UPDATE character_attitude SET attitude = 0.0
WHERE character_id = 1 AND target_id = 2;

-- Elizabeth's standing with Bingley's party: unknown on arrival.
-- The post-snub value (0.30, with Darcy's dismissal noted) is premature.
UPDATE character_faction_reputation SET
    reputation = 0.05,
    notes = 'Unknown to Bingley''s party on arrival; no judgments formed yet.'
WHERE character_id = 1 AND faction_id = 3;

-- Darcy: pre-snub emotional state. Disdain and hidden interest both develop
-- during the evening. He arrives reserved and uncomfortable, not yet dismissive.
UPDATE character SET
    emotional_state = 'reserved',
    hidden_motivation = NULL,
    description = 'A tall, handsome man of aristocratic bearing, richly dressed and composed. He has arrived with Bingley''s party and immediately draws attention by his height, his dress, and the report of his fortune. His manner is reserved; he has not yet engaged with anyone outside his own party.'
WHERE id = 2;

-- Darcy and Elizabeth: strangers; both direction rows reset.
UPDATE character_attitude SET attitude = 0.0
WHERE character_id = 2 AND target_id = 1;


-- =============================================================================
-- GAME: cultural_norms updated with assembly scale and local family context.
-- Full JSON rewritten to add two new keys; all existing entries preserved.
-- =============================================================================

UPDATE game SET cultural_norms = '{
    "dancing": "A lady who refuses a set must sit it out entirely for that set. Refusing a partner is a significant social statement and will be observed.",
    "introductions": "A gentleman must be formally introduced before addressing a lady he does not know. Bingley''s party arrived as strangers; Sir William Lucas is the appropriate introducer.",
    "conversation": "A person engaged in conversation does not simply walk away. To do so is considered rude under any circumstances. Characters with pending social engagements remain in place.",
    "service_areas": "A lady or gentleman of quality does not enter service passages, back stairs, or staging areas. To do so would be considered eccentric at best, scandalous at worst.",
    "card_room": "The card room is predominantly occupied by older guests and those disinclined to dance. A young lady entering unescorted would be unusual but not impossible.",
    "supper_room": "The supper room is closed for this assembly — no supper is served. The door is unlocked but convention prohibits entry. A well-bred guest would not attempt it without compelling reason.",
    "gentlemen_scarcity": "There are notably more ladies than gentlemen willing to dance at this assembly. This reflects the ongoing depletion of young men from country society by the European wars. Ladies sitting out a set carry no stigma; it is simply the circumstance of the evening.",
    "local_families": "Known local families and residences: Bennet of Longbourn; Lucas of Lucas Lodge; Goulding of Haye-Park; Long (Mrs. Long and her nephews); Phillips (attorney in Meryton, related to the Bennets by marriage); Bingley of Netherfield Park (recently arrived). Other nearby properties whose resident family names may be generated as needed: Purvis Lodge, Ashworth, Oakham Mount, Stoke. The militia is not yet quartered in the area."
}'
WHERE id = 2;


-- =============================================================================
-- MISS BINGLEY (id = 10): internal states and surface attitude toward Darcy
-- =============================================================================

INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (10, 'composure', 0.85, 'prose', NULL);
-- High: she performs social ease with discipline; it costs her little tonight —
-- the neighborhood has not yet presented a threat worth managing.

INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (10, 'self_satisfaction', 0.72, 'prose', NULL);
-- Moderate-high: she is with Darcy, elegantly dressed, and the assembly room
-- has not yet produced anyone she needs to take seriously.

INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (10, 'social_vigilance', 0.52, 'prose', NULL);
-- Moderate: she watches the room habitually for social threats and opportunities,
-- but has not yet identified a target. Will rise if Elizabeth registers.

-- Miss Bingley performs visible warmth toward Darcy in addition to feeling it.
-- Her existing hidden attitude (0.65) reflects the depth; this surface row
-- reflects the attentiveness she allows herself to show.
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (10, 2, 0.50, 'surface');


-- =============================================================================
-- MRS. HURST (id = 11): internal states and key attitudes
-- =============================================================================

INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (11, 'comfort', 0.78, 'prose', NULL);
-- High: seated with her party; nothing is required of her this evening.

INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (11, 'social_ease', 0.68, 'prose', NULL);
-- Moderate: she follows Caroline's lead; independent social navigation
-- is not required and she is content to leave it to her sister.

-- Mrs. Hurst → Mr. Hurst: the marriage is comfortable rather than affectionate.
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (11, 12, 0.22, 'surface');

-- Mrs. Hurst → Bingley: genuine sibling warmth; she is fond of her brother.
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (11, 3, 0.58, 'surface');


-- =============================================================================
-- SIR WILLIAM LUCAS (id = 14)
-- Former mayor of Meryton; received a knighthood by presenting an address
-- to the King. Retired from trade to Lucas Lodge. Warm, sociable, pleasantly
-- pompous. The closest thing to a master of ceremonies at this public assembly.
-- Circulates freely; makes introductions; encourages participation.
-- =============================================================================

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
    14, 2, 'Sir William Lucas', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'A stout, cheerful man of middling age with the comfortable manner of someone who has long been the most prominent person in a room. He moves through the assembly with proprietorial ease, greeting arrivals and nudging the conversation along.',
    'Sir William Lucas of Lucas Lodge; formerly mayor of Meryton; Knight.',
    3,  -- Landing; positioned at the top of the stairs to greet arrivals
    0.48, 0.55, 0.80, 0.75, 0.22,
    'belonging', 'genial',
    'Enjoying the assembly in his customary role as social center of gravity; pleased to welcome the new arrivals from Netherfield.',
    'Quietly proud of his knighthood and the deference it earns; enjoys being the man who makes introductions and smooths awkward moments.',
    0,
    'warm_jovial', 0.80, 0.78,
    '[3, 4, 5]',
    0.22  -- circulates actively through public rooms; never stays long in one place
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (14, 'belonging — social connection; he is energized by a full room and a lively evening', 'surface', 0.80, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (14, 'status — appreciation of his knighthood and his position as the leading local gentleman', 'surface', 0.72, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (14, 'entertainment — a well-run, lively assembly is its own reward', 'surface', 0.58, 'approach', 'person_environment');

INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (14, 'social_ease', 0.88, 'prose', NULL);
INSERT INTO internal_state (character_id, state_name, value, display_mode, passive_rate_per_minute)
VALUES (14, 'enjoyment', 0.80, 'prose', NULL);

INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (14, 2, 0.80, 'Former mayor, knight, and natural host of the neighborhood. Highly regarded.');
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (14, 3, 0.30, 'Welcomed Bingley''s party and made himself known on their arrival. Politely regarded; his origins in trade are noted by the Bingley circle.');

-- Sir William → Elizabeth: Charlotte's closest friend; he has known her for years
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (14, 1, 0.38, 'surface');
-- Sir William → Charlotte: his daughter; warm paternal affection
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (14, 5, 0.82, 'surface');
-- Sir William → Bingley: warmly welcoming the new neighbor
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (14, 3, 0.45, 'surface');
-- Sir William → Darcy: respectful of rank but not intimidated (he too has a title)
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (14, 2, 0.22, 'surface');

-- Elizabeth → Sir William: fond; slightly amused by his knighthood pride
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 14, 0.38, 'surface');


-- =============================================================================
-- MR. ROBINSON (id = 15)
-- Named in Chapter 3; asked Bingley directly about the ladies of the assembly.
-- Sociable neighborhood gentleman; the sort who talks to strangers.
-- =============================================================================

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
    15, 2, 'Mr. Robinson', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'A cheerful neighborhood gentleman of no particular distinction; the sort of man who talks to strangers at assemblies and means well by it. He has already introduced himself to Mr. Bingley.',
    'A neighbor; address unspecified.',
    4,  -- Ballroom
    0.55, 0.52, 0.72, 0.65, 0.25,
    'belonging', 'sociable',
    'Enjoying the company; interested in the new arrivals; happy to dance.',
    NULL, 0,
    'warm_direct', 0.65, 0.65,
    '[3, 4, 5]',
    0.12
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (15, 'belonging — enjoys company and a lively assembly', 'surface', 0.72, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (15, 'entertainment — dancing and good conversation', 'surface', 0.65, 'approach', 'person_environment');

INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (15, 2, 0.58, 'Ordinary neighborhood standing; well enough liked.');

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (15, 1, 0.18, 'surface');  -- Elizabeth: pleasant neighborhood acquaintance
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 15, 0.12, 'surface');  -- Elizabeth → Robinson: familiar neighbor


-- =============================================================================
-- JOHN LUCAS (id = 16)
-- Charlotte's eldest brother. Knows Elizabeth well through his sister.
-- Sensible and pleasant; will stand up with her as a matter of course.
-- =============================================================================

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
    16, 2, 'John Lucas', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'Charlotte''s eldest brother; a sensible, pleasant young man with something of his sister''s directness and his father''s sociable manner. He and Elizabeth are old acquaintances.',
    'Son of Sir William and Lady Lucas of Lucas Lodge.',
    4,  -- Ballroom
    0.55, 0.65, 0.60, 0.70, 0.22,
    'belonging', 'pleasant',
    'Enjoying the assembly; happy to dance; attentive to his family''s friends.',
    NULL, 0,
    'pleasant_direct', 0.70, 0.60,
    '[3, 4, 5]',
    0.12
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (16, 'belonging — enjoys the company of friends and neighbors', 'surface', 0.75, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (16, 'affiliation — attentive to family connections and his father''s social duties', 'surface', 0.65, 'approach', 'person_environment');

INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (16, 2, 0.62, 'Well-regarded; son of the most prominent local family.');

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (16, 1, 0.42, 'surface');  -- Elizabeth: old acquaintance through Charlotte
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 16, 0.35, 'surface');  -- Elizabeth → John Lucas: Charlotte's brother; familiar
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (16, 5, 0.75, 'surface');  -- John → Charlotte: close siblings
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (16, 14, 0.72, 'surface'); -- John → Sir William: his father; respect and affection


-- =============================================================================
-- EDWARD LONG (id = 17)
-- Nephew of Mrs. Long; present as part of his aunt's party.
-- Pleasant and unremarkable; no particular agenda.
-- =============================================================================

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
    17, 2, 'Edward Long', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'Mrs. Long''s nephew; a pleasant young man of no particular distinction, present as part of his aunt''s party.',
    'Nephew of Mrs. Long.',
    4,  -- Ballroom
    0.50, 0.52, 0.60, 0.62, 0.30,
    'belonging', 'pleasant',
    'Dancing and enjoying the company.',
    NULL, 0,
    'pleasant_unremarkable', 0.62, 0.55,
    '[3, 4, 5]',
    0.10
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (17, 'entertainment — dancing and agreeable company', 'surface', 0.68, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (17, 'belonging — a pleasant evening in familiar company', 'surface', 0.62, 'approach', 'person_environment');

INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (17, 2, 0.52, 'Ordinary neighborhood standing; known through Mrs. Long.');

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (17, 1, 0.15, 'surface');  -- Elizabeth: known neighborhood girl
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 17, 0.10, 'surface');  -- Elizabeth → Edward Long: familiar acquaintance


-- =============================================================================
-- THOMAS PHILIPS (id = 18)
-- Nephew of Mr. Phillips the attorney (Mrs. Bennet's brother-in-law).
-- Present partly from family obligation; decent but lacking initiative.
-- The family connection makes him a semi-obligatory dance partner for the
-- Bennet girls, which Elizabeth is aware of.
-- =============================================================================

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
    18, 2, 'Thomas Phillips', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'Nephew of Mr. Phillips the attorney; a decent young man who attends assemblies partly from family duty. He is perfectly pleasant but lacks initiative.',
    'Nephew of Mr. Phillips, attorney of Meryton.',
    4,  -- Ballroom
    0.45, 0.68, 0.48, 0.68, 0.32,
    'belonging', 'dutiful',
    'Fulfilling family social obligations; will dance when expected to.',
    NULL, 0,
    'polite_correct', 0.62, 0.52,
    '[3, 4, 5]',
    0.08
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (18, 'equity — meeting family social obligations without embarrassment', 'surface', 0.72, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (18, 'belonging — a pleasant enough evening in familiar company', 'surface', 0.58, 'approach', 'person_environment');

INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (18, 2, 0.55, 'Unremarkable neighborhood standing; known through the Phillips connection.');

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (18, 1, 0.22, 'surface');  -- Elizabeth: cousin-by-connection; mild obligation
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 18, 0.18, 'surface');  -- Elizabeth → Thomas Phillips: familiar; slightly obligatory


-- =============================================================================
-- WILLIAM GOULDING (id = 19)
-- Son of the Goulding family of Haye-Park; minor gentry.
-- Easy-mannered and unpretentious; one of the better local families.
-- =============================================================================

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
    19, 2, 'William Goulding', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'Eldest son of the Goulding family of Haye-Park; a decent, easy-mannered young man from one of the better-established local families. There is nothing remarkable about him.',
    'Son of the Goulding family of Haye-Park.',
    4,  -- Ballroom
    0.52, 0.58, 0.62, 0.65, 0.22,
    'belonging', 'comfortable',
    'Dancing and agreeable company; no particular agenda.',
    NULL, 0,
    'easy_unremarkable', 0.65, 0.55,
    '[3, 4, 5]',
    0.10
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (19, 'entertainment — a good evening of dancing and company', 'surface', 0.70, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (19, 'belonging — comfortable in his neighborhood circle', 'surface', 0.65, 'approach', 'person_environment');

INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (19, 2, 0.62, 'Solid neighborhood standing; the Gouldings are a well-regarded local family.');

INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (19, 1, 0.15, 'surface');  -- Elizabeth: known neighborhood girl
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 19, 0.12, 'surface');  -- Elizabeth → William Goulding: neighborhood acquaintance


-- =============================================================================
-- SESSION 11 ADDITIONS
--
-- Dance-seeking pending_intent for all characters with a credible motivation
-- to dance or engage socially. These seed the state that the NPC initiative
-- mechanism (§5b design) will eventually act on; in the meantime they give
-- Pass 2 accurate material when it describes NPC behavior.
--
-- Design notes:
-- - Young women: passive intent — they want to dance but wait to be asked
-- - Young men: active intent — they will seek partners when a set forms
-- - Bingley: strong active intent; danced every set (canonical)
-- - Darcy: explicitly refuses strangers; canonical non-participant
-- - Mary: will dance if asked but does not seek it
-- - Miss Bingley: conditional intent — only if Darcy asks
-- - Older/married guests and spectators: NULL (no dance intent)
-- =============================================================================

-- Elizabeth: wants to dance; will accept a partner if asked
UPDATE character SET pending_intent = 'wants to dance this evening; will accept a partner if asked'
WHERE id = 1;

-- Darcy: not intending to dance with strangers; his refusal is canonical
UPDATE character SET pending_intent = 'not intending to dance with strangers; will decline all introductions for dancing'
WHERE id = 2;

-- Bingley: eager and active; danced every set
UPDATE character SET pending_intent = 'eager to dance; will seek a partner for every set'
WHERE id = 3;

-- Jane: wants to dance; will accept a partner if asked
UPDATE character SET pending_intent = 'wants to dance; will accept a partner if asked'
WHERE id = 4;

-- Charlotte: wants to dance; will accept a partner if asked
UPDATE character SET pending_intent = 'wants to dance; will accept a partner if asked'
WHERE id = 5;

-- Mary: passive; will dance if asked but will not seek it
UPDATE character SET pending_intent = 'content to observe; will dance if asked but will not seek a partner'
WHERE id = 9;

-- Miss Bingley: will only dance if Darcy asks; otherwise observing
UPDATE character SET pending_intent = 'will dance only if Mr. Darcy asks; otherwise content to observe and be seen'
WHERE id = 10;

-- Young men: all actively seeking partners when a set forms
UPDATE character SET pending_intent = 'wants to dance; will seek a partner when a new set forms'
WHERE id IN (15, 16, 17, 18, 19);  -- Robinson, John Lucas, Edward Long, Thomas Phillips, William Goulding

-- Lydia: will dance with anyone immediately; no patience for waiting
UPDATE character SET pending_intent = 'desperate to dance; will accept any partner without hesitation'
WHERE id = 7;

-- Kitty: follows Lydia; will dance if a partner presents himself
UPDATE character SET pending_intent = 'wants to dance; will follow Lydia''s lead and accept any willing partner'
WHERE id = 8;


-- =============================================================================
-- SESSION 12 ADDITIONS (2026-05-26)
--
-- Cloakroom added as location 14 (ground floor, adjacent to vestibule).
-- Omission identified in design review; standard provision at a Regency
-- civic assembly and a natural first stop for arriving parties.
--
-- Starting locations corrected: Jane, Mary, and Mrs. Bennet now arrive at
-- the vestibule (location 1) with Elizabeth, not the ballroom. Lydia and
-- Kitty are already in the ballroom — they ran ahead.
--
-- Mrs. Bennet description updated to arrival state.
-- Mrs. Bennet pending_intent added: she has a clear immediate goal on entry.
-- =============================================================================


-- Location 14: Cloakroom / Anteroom
-- NOTE: not mentioned in Chapter 3 text; present by architectural and social
-- inference. Standard provision at a civic assembly of this type.
INSERT INTO location (id, game_id, name, location_type, description_skeleton, social_setting, witness_count, situation_flags)
VALUES (
    14, 2, 'Cloakroom', 'anteroom',
    'A small, low-ceilinged room with coat pegs along one wall and a wooden bench. A servant stands near the door. The noise of the assembly is faint but audible through the entrance hall. The smells of damp wool and cold night air linger from earlier arrivals.',
    'semi_private', 3,
    '["evening", "arrival_area", "cloaks_and_coats", "servant_present"]'
);

-- Vestibule ↔ Cloakroom connection (door, freely passable)
-- Convention: location_a_id < location_b_id
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (1, 14, 'door', 1, NULL);


-- Jane, Mary, and Mrs. Bennet: arriving at vestibule with Elizabeth,
-- not already seated in the ballroom. Lydia and Kitty ran ahead (id 7, 8)
-- and remain at their seeded location (4 — Ballroom).
UPDATE character SET current_location_id = 1
WHERE id IN (4, 6, 9);  -- Jane, Mrs. Bennet, Mary

-- Mrs. Bennet: description updated to arrival state (she is not yet seated).
UPDATE character SET
    description = 'A woman of middling age with an expressive face and a loud voice. She has arrived at the assembly with her daughters and is already scanning the room above for intelligence on Bingley''s party.'
WHERE id = 6;

-- Mrs. Bennet: pending_intent. Her MST goal (securing advantageous marriages)
-- is permanent and lives in character_goal. This pending_intent is its
-- tactical expression on arrival: get to the ballroom and establish a
-- position with line-of-sight to the dancing floor.
UPDATE character SET pending_intent = 'escort daughters to the ballroom and secure wall seating with a clear view of the dancing floor'
WHERE id = 6;

-- Header update: seed now covers 14 locations. Update the header comment.
-- (Comment-only; no SQL change needed.)


-- =============================================================================
-- SESSION 13 ADDITIONS (2026-05-26): v8 timed activity system — initial seeds
--
-- Two characters are seeded with current_activity at scene open, reflecting
-- their canonical starting positions and intentions for the evening.
--
-- Sir William Lucas (id=14): greeting guests on the landing at the top of
--   the stairs. His welcome is a social performance as much as a courtesy;
--   he will do it until the flow of arrivals slows or he is drawn away
--   by something more interesting. High renewable=1 because there is no
--   natural endpoint — he will keep greeting until Pass 2 decides otherwise.
--   Low confidence (0.15) because his duration is genuinely unpredictable.
--
-- Mr. Hurst (id=12): settled in the card room for the evening. There is no
--   supper at this assembly and no other compelling reason for him to move.
--   High confidence (0.70) reflecting that he will almost certainly stay put
--   for at least three hours. renewable=1 because 'all evening' is the plan —
--   he should not be auto-cleared; only Pass 2 can move him.
--
-- activity_started_at = 1200 = 8:00 PM (scene open, game clock start).
-- =============================================================================

-- Sir William Lucas: greeting arrivals on the landing at the top of the stairs.
UPDATE character
SET current_activity             = 'greeting guests as they arrive at the top of the stairs',
    activity_started_at          = 1200,
    activity_estimated_duration  = 45,
    activity_duration_confidence = 0.15,
    activity_renewable           = 1
WHERE id = 14;  -- Sir William Lucas

-- Mr. Hurst: ensconced in the card room for the evening.
UPDATE character
SET current_activity             = 'playing cards in the card room',
    activity_started_at          = 1200,
    activity_estimated_duration  = 180,
    activity_duration_confidence = 0.70,
    activity_renewable           = 1
WHERE id = 12;  -- Mr. Hurst


-- =============================================================================
-- SESSION 14 ADDITIONS (2026-05-26): character description corrections
--
-- Playtest revealed that Pass 2 could not resolve relational terms ("my cousin",
-- "Charlotte's brother") because family relationships were absent from character
-- descriptions. character_attitude has no notes column, so descriptions are the
-- only place Pass 2 can see these connections.
--
-- Thomas Phillips was also incorrectly described as Mr. Phillips's nephew rather
-- than his son, making the stated cousin relationship to Elizabeth impossible.
-- =============================================================================

-- Thomas Phillips: correct error (was "nephew", should be "son") and add cousin
-- relationship to Elizabeth. Mrs. Phillips is Mrs. Bennet's sister, making
-- Thomas Elizabeth's first cousin on the Phillips side.
UPDATE character SET description =
    'Son of Mr. Phillips the attorney and Mrs. Phillips, who is Mrs. Bennet''s sister; Elizabeth Bennet''s first cousin. A decent young man who attends assemblies partly from family duty. He is perfectly pleasant but lacks initiative.'
WHERE id = 18;  -- Thomas Phillips

-- Charlotte Lucas: add family context so Pass 2 can resolve "Charlotte's brother"
-- and similar relational references.
UPDATE character SET description =
    'A sensible, plain young woman a few years older than Elizabeth. She is pleasant and sociable without being showy. She and Elizabeth are close friends. Eldest daughter of Sir William and Lady Lucas; sister of John Lucas and Maria Lucas.'
WHERE id = 5;  -- Charlotte Lucas

-- Lady Lucas: add family context.
UPDATE character SET description =
    'A pleasant, sociable woman of the neighborhood, seated beside Mrs. Bennet. She knows who everyone is, what everyone''s prospects are, and is happy to discuss both. Wife of Sir William Lucas; mother of Charlotte, John, and Maria Lucas.'
WHERE id = 13;  -- Lady Lucas

-- Sir William Lucas: add family context.
UPDATE character SET description =
    'A stout, cheerful man of middling age with the comfortable manner of someone who has long been the most prominent person in a room. He moves through the assembly with proprietorial ease, greeting arrivals and nudging the conversation along. Husband of Lady Lucas; father of Charlotte, John, and Maria Lucas.'
WHERE id = 14;  -- Sir William Lucas


-- =============================================================================
-- SESSION 16 ADDITIONS (2026-05-29)
--
-- 1. Maria Lucas (id=20): Charlotte's younger sister, ~16. Referenced by name
--    in the updated family descriptions (Charlotte, Lady Lucas, Sir William)
--    but not previously seeded as a character. She is present at the assembly.
--
-- 2. Jane→Elizabeth and Charlotte→Elizabeth attitudes: these were added to
--    reset_instance.sql in session 14 but never backfilled into seed.sql,
--    meaning a fresh database install would be missing them. Added here.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Maria Lucas (id = 20)
-- Charlotte's younger sister; ~16. Lively, warm, easily excited. She looks up
-- to Charlotte and is delighted to be included in the evening. Not yet out in
-- the full sense — this is one of her first real assemblies — which gives her
-- manner a slightly unguarded quality that Charlotte has long since smoothed
-- away. She knows Elizabeth through Charlotte and likes her.
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
    20, 2, 'Maria Lucas', 'npc_active', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'Charlotte Lucas''s younger sister; about sixteen, lively and warm, with a manner that is not yet fully polished. She is clearly delighted to be here and makes little effort to conceal it. She and Elizabeth are easy acquaintances through Charlotte.',
    'Youngest daughter of Sir William and Lady Lucas of Lucas Lodge attending the assembly.',
    4,  -- Ballroom; near Charlotte initially
    0.62, 0.38, 0.80, 0.75, 0.45,
    'belonging', 'excited',
    'Enjoying her first real assembly; eager to dance and be noticed favorably.',
    NULL, 0,
    'warm_expressive', 0.78, 0.72,
    '[3, 4, 5]',
    0.18
);

INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (20, 'belonging — enjoying her first assembly among the neighborhood', 'surface', 0.75, 'approach', 'person_environment');
INSERT INTO character_goal (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES (20, 'entertainment — dancing and the pleasure of being out in society', 'surface', 0.68, 'approach', 'person_environment');

INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (20, 2, 0.52, 'Lucas family; younger daughter; well regarded as a pleasant girl.');

-- Maria → Elizabeth: warm acquaintance through Charlotte; looks up to her slightly
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (20, 1, 0.52, 'surface');
-- Maria → Charlotte: devoted younger sister
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (20, 5, 0.85, 'surface');
-- Maria → Sir William: her father; fond and a little in awe
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (20, 14, 0.72, 'surface');

-- Elizabeth → Maria: fond; slightly amused by her enthusiasm
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 20, 0.42, 'surface');

UPDATE character SET pending_intent = 'wants to dance; will accept any suitable partner when a set forms'
WHERE id = 20;  -- Maria Lucas

-- -----------------------------------------------------------------------------
-- Jane→Elizabeth and Charlotte→Elizabeth attitudes (backfill from session 14)
-- These were added to reset_instance.sql in session 14 but omitted from
-- seed.sql. A fresh database install would seed these at 0 without this block.
-- -----------------------------------------------------------------------------

-- Jane → Elizabeth: deep sisterly warmth; surface reserved (Jane conceals feeling)
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (4, 1, 0.72, 'surface');
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (4, 1, 0.90, 'hidden');

-- Charlotte → Elizabeth: genuine close friendship
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (5, 1, 0.75, 'surface');
