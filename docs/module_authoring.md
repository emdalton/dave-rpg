# DAVE RPG Engine — Module Authoring Reference

*Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)*

*Last updated: 2026-05-31. Authoritative source for schema field semantics is
`schema/schema.sql`. This document captures conventions, ordering, and gotchas
that are not obvious from the schema alone. Read this before writing a seed.*

---

## Module structure

Each module lives in `modules/<module_name>/` and consists of:

```
modules/<module_name>/
├── seed.sql            # canonical starting world state
├── reset_instance.sql  # resets mutable state without rebuilding
└── <module_name>.db    # SQLite database (built from schema + seed; not checked in)
```

Supporting documents (character design notes, location graphs, faction design,
source references) live alongside these files in the same directory. They are
reference material for authoring but are not read by the engine.

To build the database from scratch (always use this for a fresh install):

```bash
sqlite3 modules/<name>/<name>.db < schema/schema.sql
sqlite3 modules/<name>/<name>.db < modules/<name>/seed.sql
```

To reset a running instance to starting state:

```bash
sqlite3 modules/<name>/<name>.db < modules/<name>/reset_instance.sql
```

---

## Seed file conventions

### Header block

Every seed file begins with a standard header comment:

```sql
-- =============================================================================
-- DAVE RPG Engine — Seed Data: <Module Name>
-- <Subtitle if applicable>
--
-- Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)
--
-- <One paragraph on setting, player character, and tone.>
--
-- Schema version: <N>
-- Characters: <N> (1 player, N NPC)
-- Locations: <N>
-- Factions: <N>
--
-- Usage (fresh install):
--   sqlite3 modules/<name>/<name>.db < schema/schema.sql
--   sqlite3 modules/<name>/<name>.db < modules/<name>/seed.sql
--
-- To reset a running instance:
--   sqlite3 modules/<name>/<name>.db < modules/<name>/reset_instance.sql
-- =============================================================================
```

### First line

```sql
PRAGMA foreign_keys = ON;
```

This must appear before any INSERT. Foreign key constraints are disabled by
default in SQLite and must be enabled per-connection. Without this, invalid
references will not be caught at insert time.

### Section ordering

Insert records in dependency order. A row may only reference IDs that already
exist in the database:

1. `game`
2. `location`
3. `location_connection`
4. `game_instance`
5. `character`
6. `character_goal`
7. `character_skill`
8. `internal_state`
9. `faction`
10. `character_faction_reputation`
11. `character_attitude`
12. `location_detail`
13. `character_visited_location`
14. `item`
15. `character_item`

Each section has a `-- === SECTION NAME === --` comment block. Within a section,
insert in ID order so the file is predictable to read and diff.

### game_instance must be last in the game block

The final statement that sets `status = 'ready'` on `game_instance` is the
effective "seal" of the seed. The engine refuses to start with any other status.
This ordering makes it easy to confirm that a seed is complete.

---

## Table-by-table reference

### `game`

One row per module. Stable world parameters passed in every context packet.

```sql
INSERT INTO game (
    id, name, genre, tone, era, technology_level, magic_system,
    narrative_register, speech_filter, internal_state_display, cultural_norms
) VALUES ( ... );
```

**`id`** — use `1` for all single-module databases. Meryton uses `2` because
it shares a database with a stub game record at id=1. Fresh module databases
always start at `1`.

**`genre`** — snake_case string. Examples: `'domestic_comedy'`, `'social_comedy'`,
`'liminal_fantasy'`, `'locked_room_mystery'`. Passed verbatim to the LLM to
establish the adjudication register.

**`tone`** — snake_case string. Examples: `'comedic_absurdist'`,
`'ironic_observational'`, `'mysterious_whimsical'`, `'tense_investigative'`.

**`era`** and **`technology_level`** — NULL is acceptable for timeless or
genre-undefined settings. When set, these strings are passed directly to the LLM:
`'contemporary'`, `'Regency England, approximately 1812'`, `'pre-industrial'`.

**`magic_system`** — NULL means no magic. When set, describe it in plain prose:
the LLM uses this to calibrate plausibility judgments in adjudication.

**`narrative_register`** — controls grammatical person in Pass 3 prose.
Must be one of: `'first_person'`, `'second_person'`, `'third_person_close'`,
`'third_person_distant'`, `'atmospheric'`. Most modules use
`'second_person'` or `'third_person_close'`.

**`player_definition_mode`** — controls how the player character is established
at the start of a session. Must be one of:
- `'fixed'` (default) — player character is fully seeded; no startup self-definition step. Use for modules with a fixed protagonist (Meryton, I Am a Cat).
- `'define'` — engine prompts the player to describe themselves at a designated starting location. The description is parsed into character fields and any declared items are instantiated. Seeded starting items are also revealed via the engine's confirmation pass.
- `'choose'` — player selects from a list of pre-defined characters (future; not yet implemented in the engine).

**`speech_filter`** — JSON object (or `'{}'` for no filter). The game-level
filter applies to all characters. For per-character filtering, use the
`speech_filter` field on the `character` table (schema v9). The I Am a Cat
filter is the canonical example of a game-level filter:

```json
{
    "player_output": "meow_variants",
    "npc_human_input_filter": "feline_comprehension",
    "vocabulary_breakthrough": {"treats": "penetrates clearly", ...}
}
```

Most modules set this to `'{}'`.

**`internal_state_display`** — JSON object mapping state_name to `'prose'` or
`'numeric'`. Only include states that exist in this module's `internal_state`
rows. `'prose'` (default) renders as in-character commentary; `'numeric'` shows
the raw float. Always use `'prose'` for play sessions.

**`cultural_norms`** — JSON object mapping norm_name to prose description. Passed
to Pass 2 when an action touches the relevant domain. Use this for module-specific
behavioral conventions the LLM cannot infer from setting alone: dancing rules,
service area access conventions, feline behavioral rules, etc. `'{}'` is fine for
modules with no special norms.

---

### `location`

```sql
INSERT INTO location (
    id, game_id, name, location_type, description_skeleton,
    social_setting, witness_count, situation_flags
) VALUES ( ... );
```

**`location_type`** — free-form string. The LLM uses this for plausibility checks
during lazy world generation. Use natural English: `'bedroom'`, `'kitchen'`,
`'hallway'`, `'ballroom'`, `'common_room'`, `'garden'`, `'library'`.

**`description_skeleton`** — the starting description of the space. Deliberately
incomplete: it establishes the room without committing to details that haven't
been generated yet. Details are added lazily via `location_detail` on first
query. A good skeleton is 2–4 sentences that convey the size, light, smell, and
dominant feature of the space.

**`social_setting`** — must be one of `'private'`, `'semi_private'`, or
`'public'`. Affects NPC behavior and reputation consequences during adjudication:
- `'private'` — unobserved or nearly so; intimate conversations possible
- `'semi_private'` — small number of known witnesses; moderate reputation effect
- `'public'` — observed by many; actions have significant reputation consequences

Note: `'exterior'` is **not** a valid value and will fail the CHECK constraint.
Outdoor or threshold locations (doorsteps, courtyards, paths) should use
`'public'` with `witness_count=0`. The spatial character of the space is already
captured by `location_type='exterior'` — `social_setting` describes the
reputational context, not the indoor/outdoor distinction.

**`witness_count`** — approximate number of people in the space at game start.
Updated dynamically as characters move. Match this to the number of characters
seeded at this location.

**`situation_flags`** — JSON array of natural-language strings passed to Pass 2
as active conditions. Examples: `["evening", "fire_lit", "guests_present"]`,
`["dark", "3am", "humans_asleep"]`. These are transient conditions; they can be
added, removed, or modified during play by adjudication outcomes.

---

### `location_connection`

```sql
INSERT INTO location_connection (
    location_a_id, location_b_id, connection_type, is_passable, passage_note
) VALUES ( ... );
```

**Critical constraint: `location_a_id < location_b_id` always.** The schema
enforces this with a `CHECK` constraint. One row encodes a bidirectional
connection; `db.get_location_connections()` queries both directions. If you
write the IDs in the wrong order the INSERT will fail — this is the most common
connection authoring error.

**`connection_type`** — must be one of: `'open'`, `'door'`, `'stairs'`,
`'squeeze'`. `'stairs'` is specifically important: the Pass 1 prompt has explicit
rules for movement phrases involving stairs (`'go upstairs'`, `'climb to X'`,
`'head up to X'`), and the engine exercises this type in regression tests.

**`is_passable`** — `1` (passable, default) or `0` (blocked). An impassable
connection exists in the graph and appears in context packets, but the engine
rejects any move targeting a location on the other side. Use this for locked
doors, sealed passages, or spaces the player cannot currently enter.

**`passage_note`** — NULL for standard connections. When set, gives the LLM
semantic context for what kind of barrier applies and what it costs to attempt
passage. Key distinction:
- `'locked'` — physically impassable; requires a key or forced entry
- `'closed by convention'` — unlocked but socially impassable; entry is possible
  at reputational cost; Pass 2 adjudicates the consequence

---

### `game_instance`

```sql
INSERT INTO game_instance (id, game_id, status, start_time_minutes, current_time_minutes)
VALUES (1, 1, 'ready', <start>, <start>);
```

`start_time_minutes` and `current_time_minutes` must both be set to the same
value at seed time — the module's canonical opening moment. Time is in minutes
past midnight: 3:00 AM = 180, 8:00 PM = 1200, noon = 720.

`status` must be `'ready'` for the engine to start a session. Do not leave it
as the default `'pending'`.

`id` is always `1` for a fresh single-module database.

---

### `character`

The most complex table. Column groups in the schema:

**Identity fields** (`name`, `role`, `species`, `gender`, `pronouns`,
`description`, `apparent_status`, `current_location_id`):

- **`role`** — must be one of: `'player'`, `'npc_active'`, `'npc_background'`,
  `'npc_object'`, `'player_option'`.
  - `'player'` — the player character. Exactly one per module.
  - `'npc_active'` — full psychological record; OCEAN, goals, skills, attitudes.
  - `'npc_background'` — minimal record; name, location, description only.
  - `'npc_object'` — a non-character agent that participates in scenes through
    physical action only (doors, mechanisms, environmental entities). Combine with
    `speech_filter='silent: ...'`. The engine and Pass 2 handle these like NPCs,
    but Pass 3 renders them through physical description, not dialogue.
  - `'player_option'` — a selectable protagonist for modules using
    `player_definition_mode='choose'` (future; not yet implemented).

- **`species`** — free-form string; defaults to `'human'`. Used by Pass 3 for
  rendering and by Pass 1 for capability inference. Examples: `'human'`,
  `'felis_catus'`, `'felis_catus_winged'`.

- **`gender`** — free-form string or NULL. NULL means the LLM infers from
  name/species/context. Accepted values: `'male'`, `'female'`, `'nonbinary'`,
  `'neuter'`, or any author-defined value. For characters whose gender is genuinely
  unknown or does not map to familiar categories, use NULL.

- **`pronouns`** — JSON array or NULL (LLM infers). When set, must be an array
  of `{"case": "<case_name>", "form": "<pronoun>"}` objects. Case labels are
  English keywords regardless of module language:

  ```json
  -- she/her
  [{"case":"nominative","form":"she"},
   {"case":"accusative","form":"her"},
   {"case":"genitive","form":"her"}]

  -- he/him
  [{"case":"nominative","form":"he"},
   {"case":"accusative","form":"him"},
   {"case":"genitive","form":"his"}]

  -- they/them
  [{"case":"nominative","form":"they"},
   {"case":"accusative","form":"them"},
   {"case":"genitive","form":"their"}]
  ```

- **`apparent_status`** — what other characters perceive this character's social
  role to be. May differ from actual role when hidden motivation is in play.
  Examples: `'guest'`, `'Keeper of the Hidden Hostel'`, `'militia officer'`.

**OCEAN traits** (`ocean_openness` through `ocean_neuroticism`):

All floats in `[0.0, 1.0]`. All five may be NULL (player characters typically
have no seeded OCEAN). Seed these to reflect honest psychology, not scripted
outcomes. A character with low agreeableness and high neuroticism will generate
their own difficult behavior from those traits; do not try to script it.

General anchors:
- 0.0–0.25: very low (notable trait; rare)
- 0.25–0.45: below average
- 0.45–0.55: average / unremarkable
- 0.55–0.75: above average
- 0.75–1.0: very high (notable trait)

**`maslow_tier`** — must be one of: `'physiological'`, `'safety'`, `'belonging'`,
`'esteem'`, `'self_actualization'`. This is the character's current dominant need
level, used as a priority-override mechanism when lower-tier needs are threatened.
It is a behavioral modifier, not a strict psychological theory. A character in
active fear should be at `'safety'`; one who feels secure and respected is likely
at `'esteem'` or `'self_actualization'`.

**`emotional_state`** — a natural-language qualitative string. Examples:
`'curious'`, `'focused'`, `'guarded'`, `'content'`, `'vigilant'`, `'drowsy'`,
`'anticipatory'`. Distinct from stable OCEAN traits. Updated frequently by
adjudication outcomes.

**`capability_beliefs`** and **`context_beliefs`** — JSON objects. May be `'{}'`
for minimal records. When seeded, they express the character's subjective
self-efficacy and environmental assessment:

```json
-- capability_beliefs: self-efficacy per domain
{"innkeeping": 0.9, "managing_difficult_guests": 0.85}

-- context_beliefs: perceived environmental support/threat
{"hostel_stability": 0.92, "guest_safety": 0.85}
```

**`surface_motivation`** and **`hidden_motivation`** — prose summaries. Surface
motivation is what the character openly presents. Hidden motivation is what they
conceal. Both are passed to Pass 2; hidden motivation is gated by
`access_hidden_motivation`.

**`access_hidden_motivation`** — `0` (concealed, default) or `1` (revealed).
For most characters this should be `0`. Set to `1` only when the hidden motivation
has been exposed during play (updated by adjudication, not seeded as `1`).

**Voice parameters** (`voice_register`, `voice_warmth`, `voice_verbosity`):

- `voice_register` — free-form string describing speaking style:
  `'matter_of_fact'`, `'casual_warm'`, `'terse_gruff'`, `'precise_academic'`,
  `'precise_quiet'`, `'formal'`, `'cat'`, `'silent'`.

- **`speech_filter`** (schema v9) — per-character natural-language instruction
  passed to Pass 3 to modify how this character's communication is rendered.
  NULL means no filter (default). Takes precedence over the game-level
  `speech_filter` when both are set. Examples:
  - `'silent: this entity cannot speak or make sounds; describe only physical actions'`
    — use for `npc_object` characters like doors or mechanisms
  - `'unintelligible: render all communication as non-verbal — purrs, chirps, wing
    adjustments; no interpretable language until a condition is met'`
    — use for characters whose speech is currently incomprehensible to the player
  - `'cheshire: speak in elliptical, gnomic fragments; never answer directly'`
    — use for characters with an evasive or oracular voice once understood

  When using `speech_filter`, set `voice_register` to a matching short label
  (`'silent'`, `'cat'`, etc.) as a secondary signal; the `speech_filter` prose
  is authoritative for Pass 3, but `voice_register` may be used by Pass 2 context
  assembly for capability inference.
- `voice_warmth` — `0.0` (cold/hostile) to `1.0` (warm/affectionate)
- `voice_verbosity` — `0.0` (monosyllabic) to `1.0` (expansive/voluble)

**Wander parameters** (`wander_range`, `wander_probability`):

- **`wander_range`** — JSON array of `location_id` integers, or `NULL` (no
  autonomous movement). Example: `'[1, 2, 3]'`. The engine only moves an NPC
  to a location within this range AND adjacent to their current location. Do not
  confuse NULL with `'[]'` — use NULL for characters who never wander.
- **`wander_probability`** — per-turn probability in `[0.0, 1.0]`. `0.0` is the
  default. Player characters are always `0.0`. High values (0.75+) are for
  active wanderers; set this to the wander positive control NPC's probability
  to make suppression tests deterministic.

Three conditions suppress the wander roll regardless of `wander_probability`:
1. `pending_intent IS NOT NULL`
2. Sleepiness (or designated suppression state) `>= WANDER_SLEEPINESS_THRESHOLD` (config default: 0.60)
3. `current_activity IS NOT NULL` AND activity has not expired

**Activity fields** (`current_activity` through `activity_renewable`):

- **`current_activity`** — natural-language description or NULL.
- **`activity_started_at`** — game clock minutes when the activity started. This
  is a game-clock value (minutes past midnight), not a real-world timestamp. Set
  to a time *before* the game's `start_time_minutes` when seeding a pre-existing
  activity. The engine checks `started_at + estimated_duration <= current_time`
  for expiry.
- **`activity_estimated_duration`** — in game clock minutes. NULL means
  open-ended (engine never auto-clears on time alone).
- **`activity_duration_confidence`** — float in `[0.0, 1.0]` or NULL. Values
  at or above `ACTIVITY_AUTO_CLEAR_CONFIDENCE` (config default: 0.60) allow the
  engine to auto-clear the activity when it expires. Below this threshold, only
  Pass 2 may clear it via `activity_updates`.
- **`activity_renewable`** — `0` (default) or `1`. A renewable activity is never
  auto-cleared by time alone regardless of confidence; Pass 2 must clear it
  explicitly. Use for open-ended ongoing behaviors (`'standing watch at the door'`).

**Seeding a pre-game activity:** if a character is mid-activity at game start,
set `activity_started_at` to a clock value before `start_time_minutes`. Example:
game starts at 1200 (8:00 PM), character has been cooking since 1140 (7:00 PM)
with a 90-minute duration — the activity expires at 1230, giving 30 minutes of
remaining activity at game start.

**`pending_intent`** — natural-language string or NULL. Distinct from
`current_activity`: pending intent is a social commitment or queued intention
(deferred obligation), not an ongoing physical activity. It suppresses wander.
Examples: `'wants to dance; will accept any partner when a set forms'`,
`'intends to approach the player before the evening ends'`.

---

### `character_goal`

```sql
INSERT INTO character_goal
    (character_id, goal_name, goal_type, priority, orientation, scope)
VALUES ( ... );
```

**`goal_name`** — drawn from the Ford-Nichols 24-goal taxonomy, stored as a
natural-language string. The LLM evaluates semantic relevance. Common values:
`'belonging'`, `'understanding'`, `'safety'`, `'exploration'`, `'equity'`,
`'self_determination'`, `'resource_acquisition'`, `'mastery'`,
`'social_responsibility'`, `'entertainment'`.

**`goal_type`** — `'surface'` (openly pursued) or `'hidden'` (concealed;
subject to `access_hidden_motivation` on the character record). Hidden goals are
available to Pass 2 adjudication but not to Pass 1 or player-facing context.

**`priority`** — float in `[0.0, 1.0]`. How strongly this goal drives behavior
relative to the character's other goals. 0.80+ is dominant; 0.40–0.60 is moderate.

**`orientation`** — `'approach'` (motivated toward the goal) or `'avoidance'`
(motivated away from its negation or threat). Safety goals are typically
`'avoidance'`; belonging goals are typically `'approach'`.

**`scope`** — `'within_person'` (aimed at changes in oneself: growth, skill,
self-regulation) or `'person_environment'` (aimed at changes in the external
world). Understanding and self-determination goals are usually `'within_person'`;
exploration and resource_acquisition are usually `'person_environment'`.

---

### `character_skill`

```sql
INSERT INTO character_skill (character_id, skill_name, skill_level, intrinsic_motivation)
VALUES ( ... );
```

**`skill_name`** — open natural-language taxonomy. No canonical list. The LLM
evaluates semantic relevance at adjudication time. Specificity is encoded in the
term: `'cat hunting technique'` is narrow; `'stealth'` is broad. Seed the skills
that are relevant to this character's history and likely actions.

**`skill_level`** — float in `[0.0, 1.0]`. Rough labels: 0.0–0.2 novice,
0.2–0.4 apprentice, 0.4–0.6 journeyman, 0.6–0.8 master, 0.8–1.0 virtuoso.

**`intrinsic_motivation`** — float in `[0.0, 1.0]` or NULL (purely instrumental).
How much the character enjoys exercising this skill for its own sake. A value
of 1.0 means the character seeks opportunities to use it spontaneously.

---

### `internal_state`

```sql
INSERT INTO internal_state (
    character_id, state_name, value, display_mode,
    is_involuntary, passive_rate_per_minute
) VALUES ( ... );
```

**`state_name`** — natural-language string: `'boredom'`, `'sleepiness'`,
`'curiosity'`, `'fatigue'`, `'hunger'`, `'anxiety'`.

**`value`** — float in `[0.0, 1.0]`. 0.0 = absent/minimum; 1.0 = overwhelming.

**`display_mode`** — `'prose'` (default, rendered as in-character commentary)
or `'numeric'` (raw float, for development/testing).

**`is_involuntary`** — `0` (default) or `1`. If `1`, the engine can fire an
involuntary event when the state value crosses a threshold. The hairball mechanic
in I Am a Cat uses this. For most states, use `0`.

**`passive_rate_per_minute`** — float or NULL. Applied each turn after the clock
advances: `new_value = clamp(value + rate * elapsed_minutes, 0.0, 1.0)`. Positive
rates accumulate toward 1.0; negative rates decay toward 0.0. NULL means the
state only changes when Pass 2 explicitly updates it.

Use passive drift for physiological states with genuine background change:
sleepiness, hunger, thirst, fatigue. Do not use it for activity-dependent states
(impatience, excitement) — manage those entirely through Pass 2.

**Satisfying physiological states without an item system:** DAVE does not require
an item or inventory system to model consumption. When a player asks for food or
drink, Pass 2 adjudicates the social interaction and applies a negative
`internal_state_delta` to the relevant state (e.g., `hunger` drops by −0.40 if
Marta serves a meal). Pass 3 narrates the result. No persistent item record is
created or consumed. This pattern works well for any state that can be satisfied
through a plausible social/narrative action: a character brings food, offers a
drink, provides rest. Seed the state high enough to be narratively present at
game start; let passive drift keep it rising; let Pass 2 adjudication resolve it
when the player acts. An item system becomes worth adding only when you need
persistent carrying, transferable objects, or partial consumption across turns.

**Wander suppression via sleepiness:** the engine suppresses a character's wander
roll when their sleepiness value is at or above `WANDER_SLEEPINESS_THRESHOLD`
(config default: 0.60). Only the state named `'sleepiness'` triggers this
suppression; other state names do not. If you want a different state to act as
a suppressor, it needs a config change, not just a seed change.

---

### `faction`

```sql
INSERT INTO faction (id, game_id, name, description) VALUES ( ... );
```

**`name`** — snake_case slug used as a key in Pass 2 outcome JSON. Must be
unique within a `game_id`. Examples: `'bennet_family'`, `'meryton_neighborhood'`,
`'hosts_of_the_hostel'`. Changing this after play has started breaks any
`faction_reputation_changes` outcome entries that reference the old name.

**`description`** — prose passed verbatim to the LLM in the `faction_reputations`
block of the Pass 2 context packet. Explain what the faction values, how it judges
characters, and what kinds of actions raise or lower standing. This is the LLM's
only guide for how to generate `faction_reputation_changes` in outcome JSON.

---

### `character_faction_reputation`

```sql
INSERT INTO character_faction_reputation (character_id, faction_id, reputation, notes)
VALUES ( ... );
```

**`reputation`** — float in `[0.0, 1.0]`. `0.5` = neutral/unknown (default
starting value for a character who has no established history with a faction).
`0.0` = complete disgrace or ostracism. `1.0` = exceptional standing.

**`notes`** — human-readable explanation of why standing is at its current value.
Passed alongside the float to Pass 2 so the LLM has narrative context for
reputation decisions. Update this whenever the reputation changes significantly
during play. For seed values: `'Newly arrived; no history with this faction'` is
sufficient for a default start.

Seed reputation rows for: (a) the player character, and (b) any NPC whose faction
standing meaningfully affects adjudication of other characters' behavior toward
them.

---

### `character_attitude`

```sql
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES ( ... );
```

**`attitude`** — float in `[-1.0, 1.0]`. `-1.0` = hostile/contemptuous;
`0.0` = neutral/unknown; `1.0` = warm/trusting. Missing rows are treated as
`0.0` at runtime (the database creates them on first update). Seed only the
non-neutral attitudes that matter for play; let the engine create neutral rows
as interactions generate them.

**`attitude_type`** — `'surface'` (observable) or `'hidden'` (concealed;
subject to `access_hidden_motivation` on the character holding the attitude).

**Seeding strategy:** at minimum seed all non-zero attitudes toward the player
character, and any NPC-to-NPC attitudes that are dramatically significant or
needed for wander/social suppression tests.

**There is no self-attitude.** Do not insert a row where `character_id = target_id`.

---

### `location_detail`

```sql
INSERT INTO location_detail (location_id, detail, is_valid, invalidation_condition)
VALUES ( ... );
```

Most locations should have no pre-seeded details — the lazy generation code path
fires on first entry and stores the result. Seed a detail when: (a) you want to
exercise the retrieval code path in tests, or (b) there is a canonical fact about
the location that must be true from the start (e.g. the always-burning fire in
the Hidden Hostel common room).

**`detail`** — a natural-language statement about the location: a specific
observable feature, object, or condition. One detail per row.

**`is_valid`** — `1` (currently true) or `0` (invalidated by a world event).

**`invalidation_condition`** — natural-language description of the event that
would invalidate this detail. NULL means the detail is considered permanent unless
explicitly invalidated by the engine. Example: `'fire goes out or is significantly
altered'`.

---

### `character_visited_location`

```sql
INSERT INTO character_visited_location (character_id, location_id)
VALUES ( ... );
```

Pre-populate this for characters who know parts of the map at game start. The
BFS pathfinding system requires the player to have previously visited a location
before naming it as a multi-hop destination.

**Always include the player character's starting location.** If this is missing,
multi-hop navigation from the opening location will not work.

NPCs do not use visited-location tracking for navigation (the engine moves them
directly). Pre-populating visited locations for NPCs is optional but useful for
test coverage and for modules where NPC familiarity with the space is relevant.

---

### `item`

```sql
INSERT INTO item (game_id, name, description, current_location_id, properties, is_confirmed)
VALUES ( ... );
```

Items are physical objects that persist across turns. They exist either at a
location (`current_location_id` set, no `character_item` row) or in a character's
possession (`character_item` row present, `current_location_id` NULL). The engine
enforces the either/or at the application layer.

**`name`** — short, unambiguous canonical name within the module.
Examples: `'sencha canister'`, `'blue shawl'`, `'leather-bound journal'`.
This is the name used in outcome JSON when referencing the item.

**`description`** — full prose description passed to Pass 2 and Pass 3 when the
item is in scope. Should describe appearance, condition, and salient properties.
May be NULL for player-claimed items not yet adjudicated. Seeded items should
always have a description.

**`current_location_id`** — NULL when the item is held by a character (see
`character_item`). Set when the item is at a location and not currently carried.

**`properties`** — JSON object for module-specific attributes that don't warrant
a schema column. Defaults to `'{}'`. Examples:
```json
{"weight": "light", "container": true, "capacity": "small"}
{"material": "silk", "condition": "well-mended"}
{"readable": true, "language": "unknown"}
```

**`is_confirmed`** — `1` (default; real item) or `0` (player-claimed placeholder
not yet adjudicated by Pass 2). Seeded items are always `1`; the engine creates
unconfirmed items via `item_instantiations` in Pass 2 outcome JSON.

**Seeded vs. lazy-instantiated items:** seed only items that are definitively
present at game start. Items the player mentions mid-play ("I have a book in my
pack") are created by the engine on demand; do not pre-seed speculative items.

---

### `character_item`

```sql
INSERT INTO character_item (character_id, item_id, slot, acquired_at_minutes)
VALUES ( ... );
```

Join table recording which character holds which item and how.

**`slot`** — how the character is carrying or wearing the item. Must be one of:
`'right_hand'`, `'left_hand'`, `'both_hands'`, `'mouth'`, `'worn'`, `'pocket'`,
`'in_pack'`, `'carried'`. Use `'in_pack'` for items in a bag or container; use
`'carried'` when the carrying modality is unspecified.

**`acquired_at_minutes`** — game clock minutes when the character acquired the
item, or NULL for items seeded at game start. Seeded items always use NULL.

**UNIQUE constraint:** `item_id` is unique in `character_item` — an item can only
be held by one character at a time.

**Ordering:** insert the `item` row first; use `last_insert_rowid()` to reference
its id in the `character_item` insert immediately following. This keeps seeded
item+inventory pairs together and readable:

```sql
INSERT INTO item (game_id, name, description, properties)
VALUES (1, 'sencha canister', '...', '{"weight": "light"}');

INSERT INTO character_item (character_id, item_id, slot)
VALUES (1, last_insert_rowid(), 'in_pack');
```

---

## reset_instance.sql conventions

The reset script restores all mutable state to seeded starting values without
touching stable world data. Run between playthroughs.

### Opening

```sql
PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;
```

Wrap the reset in a transaction so it either fully completes or fully rolls back.
(The Hidden Hostel reset omits `BEGIN TRANSACTION` — add it for robustness.)

### What to reset

| Table | Reset method | Notes |
|---|---|---|
| `game_instance` | `UPDATE` clock and status | Set `current_time_minutes = start_time_minutes`, `status = 'ready'` |
| `character` | `UPDATE` per character | Reset `current_location_id`, `emotional_state`, `maslow_tier`, `pending_intent`, all activity fields |
| `internal_state` | `UPDATE value` per row | Do not reset `passive_rate_per_minute` (stable config) |
| `character_attitude` | `DELETE` all + `INSERT` | Simpler and more reliable than UPDATE; avoids leaving orphaned rows from play-created attitudes |
| `character_faction_reputation` | `DELETE` all + `INSERT` | Same reason as attitudes |
| `character_visited_location` | `DELETE` all + `INSERT` | Re-populate from seed |
| `item` / `character_item` | `DELETE` all for `game_id`, then re-INSERT seed items | Delete `character_item` rows first (FK dependency), then `item` rows, then re-seed |
| `action_log` | `DELETE WHERE game_id = N` | Comment out to preserve play history |
| `location_detail` | `DELETE` generated details + restore seeded details | Delete rows for locations that had no seed detail; re-insert seed details for those that did |

### What NOT to reset

Leave untouched: `game`, `location`, `location_connection`, character OCEAN traits,
character goals, character skills, character pronouns, character descriptions,
`wander_range`, `wander_probability`, `speech_filter`, `faction`,
`npc_player_history` (if any). `speech_filter` is stable character configuration,
not mutable play state — it does not need to be reset even if the engine modifies
it during play (which it does not currently do).

### DELETE + INSERT pattern for attitudes and reputations

Do not use `UPDATE` for attitudes and reputations — play may have created new rows
(new NPC-to-NPC attitudes, new faction relationships) that `UPDATE` would not
remove. The correct pattern is:

```sql
-- Delete ALL rows involving characters in this module
DELETE FROM character_attitude
WHERE character_id IN (1, 2, 3, ...) OR target_id IN (1, 2, 3, ...);

-- Re-insert canonical starting attitudes
INSERT INTO character_attitude (character_id, target_id, attitude, attitude_type)
VALUES ( ... );
```

Use the full character ID list for the module — not just the ones with seeded
attitudes — so that any attitudes created dynamically during play are also cleared.

---

## Common mistakes

**`location_a_id` must be less than `location_b_id`.** The schema enforces this
with `CHECK(location_a_id < location_b_id)`. Writing them in the wrong order
causes the INSERT to fail. Always check the IDs before writing the connection row.

**`game_instance.status` must be `'ready'`.** The default is `'pending'`. If you
forget to set this, the engine will refuse to start and report that no active
instance was found.

**Both `start_time_minutes` and `current_time_minutes` must be set.** The schema
default for both is `-1` (sentinel for unseeded). A value of `-1` also causes the
engine to refuse to start.

**`wander_range` is a JSON array string, not NULL.** A character who should not
wander gets `wander_range = NULL`, not `wander_range = '[]'`. The engine checks
`IS NOT NULL` on this field; an empty JSON array would be read as a valid (empty)
range, not as "no wandering."

**`activity_started_at` is in game clock minutes, not wall time.** It is an
integer representing minutes past midnight on the in-game day, matching the scale
of `game_instance.current_time_minutes`. It is not a Unix timestamp and not a
SQLite datetime string.

**Pre-game activities must start before `start_time_minutes`.** If you seed a
character as mid-activity at game start, `activity_started_at` must be earlier
than `game_instance.start_time_minutes`. The engine computes expiry as
`started_at + estimated_duration <= current_time`; if started_at is in the future
the activity will never expire correctly.

**Hidden motivation is concealed by default.** `access_hidden_motivation` defaults
to `0` in the schema. You do not need to set it explicitly — but if you want to
confirm it in the seed for clarity, `0` is correct. Never seed a character with
`access_hidden_motivation = 1` unless you intend the hidden motivation to be
visible from the start of play.

**`character_visited_location` must include the player's starting location.**
Omitting this silently breaks multi-hop navigation from the opening scene.

**`faction.name` is a key, not a label.** Pass 2 outcome JSON references factions
by their `name` slug. If you rename a faction after play has started, existing
`faction_reputation_changes` outcome entries that use the old name will fail to
match. Treat faction names as stable identifiers.

**Each module has its own `game_id`.** All tables have a `game_id` column. All
rows for a module must share the same `game_id`. When multiple modules share a
database (like Meryton, which uses `game_id=2`), the `game_id` is the isolation
boundary. For fresh single-module databases, always use `game_id = 1`.
