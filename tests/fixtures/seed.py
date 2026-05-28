"""
tests/fixtures/seed.py — Minimal Test World Seed

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Provides apply_test_seed(conn), called by the tmp_db fixture in conftest.py
after schema.sql has been applied to the fresh database.

Test world inventory
--------------------
game (id=1)         "Test World", genre=adventure, tone=neutral
location (id=1)     "Antechamber" — player start, semi-private
location (id=2)     "Hall"        — adjacent to Antechamber, public
location_connection (1↔2, is_passable=1)
game_instance (id=1)  status=ready, start/current time=180 (3:00 AM)
character (id=1)    "Hero"   — player, at location 1
character (id=2)    "Guard"  — npc_active, at location 1, wander_prob=1.0, range=[1,2]
character (id=3)    "Hermit" — npc_active, at location 2, wander_prob=0.0
faction (id=1)      "town_guard"
internal_state      Hero:boredom=0.10 (+0.002/min), Guard:sleepiness=0.50 (−0.003/min)
character_attitude  Hero → Guard, surface=0.60
character_faction_reputation  Hero in town_guard = 0.70

Design notes
------------
- Guard has wander_probability=1.0 so suppression tests can confirm the NPC
  would have moved without the suppression condition in place.
- The single bidirectional connection (Antechamber ↔ Hall) covers adjacency
  validation tests without creating a maze the tests have to navigate.
- game_instance is seeded at status='ready' so GameEngine.__init__ finds it
  and transitions it to 'active', enabling _current_game_time() to work.
- All IDs are small integers so test assertions remain readable without
  lookup tables.
"""

import sqlite3


def apply_test_seed(conn: sqlite3.Connection) -> None:
    """
    Insert minimal test-world records into conn.

    Must be called after schema.sql has been applied via executescript().
    PRAGMA foreign_keys should already be ON from the conftest fixture.

    Args:
        conn: Open sqlite3.Connection with the DAVE schema applied.
    """
    conn.executescript(_SEED_SQL)
    conn.commit()


# ---------------------------------------------------------------------------
# SQL statements. Each block is a separate logical section.
# ---------------------------------------------------------------------------
_SEED_SQL = """
-- Game record
INSERT INTO game (
    id, name, genre, tone, era, technology_level, magic_system,
    narrative_register, speech_filter, internal_state_display, cultural_norms
) VALUES (
    1, 'Test World', 'adventure', 'neutral', NULL, NULL, NULL,
    'second_person', '{}', '{}', '{}'
);

-- Locations
INSERT INTO location (id, game_id, name, location_type, description_skeleton,
                      social_setting, witness_count, situation_flags)
VALUES
    (1, 1, 'Antechamber', 'hallway', 'A plain stone antechamber.',
     'semi_private', 1, '[]'),
    (2, 1, 'Hall', 'hall', 'A large vaulted hall.',
     'public', 3, '[]');

-- Location connection: Antechamber (1) ↔ Hall (2), bidirectional and passable.
-- Schema constraint: location_a_id < location_b_id; one row encodes both directions.
-- get_location_connections() handles the bidirectional query at runtime.
INSERT INTO location_connection (location_a_id, location_b_id, connection_type, is_passable, passage_note)
VALUES (1, 2, 'door', 1, NULL);

-- Game instance (v5+): a ready instance enables the in-game clock and passive decay.
-- GameEngine.__init__ will transition this to 'active' on construction.
INSERT INTO game_instance (id, game_id, status, start_time_minutes, current_time_minutes)
VALUES (1, 1, 'ready', 180, 180);

-- Player character: Hero, female, at Antechamber
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, current_location_id, emotional_state,
    wander_probability, wander_range,
    capability_beliefs, context_beliefs
) VALUES (
    1, 1, 'Hero', 'player', 'human', 'female',
    '[{"case":"nominative","form":"she"},{"case":"accusative","form":"her"},{"case":"genitive","form":"her"}]',
    'A capable adventurer.', 1, 'calm',
    0.0, NULL,
    '{}', '{}'
);

-- NPC: Guard, male, at Antechamber.
-- wander_probability=1.0 ensures the wander roll always fires when not suppressed,
-- making suppression tests clean binary assertions without random mocking.
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, current_location_id, emotional_state,
    wander_probability, wander_range,
    capability_beliefs, context_beliefs
) VALUES (
    2, 1, 'Guard', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'A vigilant guard.', 1, 'alert',
    1.0, '[1, 2]',
    '{}', '{}'
);

-- NPC: Hermit, male, at Hall. wander_probability=0.0; used as a static bystander.
INSERT INTO character (
    id, game_id, name, role, species, gender, pronouns,
    description, current_location_id, emotional_state,
    wander_probability, wander_range,
    capability_beliefs, context_beliefs
) VALUES (
    3, 1, 'Hermit', 'npc_active', 'human', 'male',
    '[{"case":"nominative","form":"he"},{"case":"accusative","form":"him"},{"case":"genitive","form":"his"}]',
    'A reclusive hermit.', 2, 'withdrawn',
    0.0, '[2]',
    '{}', '{}'
);

-- Faction
INSERT INTO faction (id, game_id, name, description)
VALUES (1, 1, 'town_guard', 'The town guard faction. Values discipline and order.');

-- Internal states
-- Hero boredom: positive drift, starts low
INSERT INTO internal_state (character_id, state_name, value, passive_rate_per_minute)
VALUES (1, 'boredom', 0.10, 0.002);

-- Guard sleepiness: negative drift (waking up over time), starts mid-range.
-- Used in wander-suppression tests: raising to >= 0.60 triggers Suppression 2.
INSERT INTO internal_state (character_id, state_name, value, passive_rate_per_minute)
VALUES (2, 'sleepiness', 0.50, -0.003);

-- Character attitude: Hero's surface attitude toward Guard (range: -1.0 to 1.0)
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES (1, 2, 0.60, 'surface');

-- Faction reputation: Hero's standing with the town_guard faction
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES (1, 1, 0.70, 'Helped patrol the northern gate.');
"""
