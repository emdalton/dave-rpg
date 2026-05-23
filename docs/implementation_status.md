# DAVE RPG Engine — Implementation Status

*Living document. Update at the end of each session before committing.*
*Last updated: 2026-05-22, session 5 (closing).*

---

## How to use this document

Read this file at the start of each session before touching any code. It tells
you where things stand without requiring you to grep through the schema or engine.
The pending work section is the authoritative queue; update it whenever items
complete or new items are added.

---

## Repository layout

```
RPG/
├── CLAUDE.md                  — project instructions for Claude (read first)
├── docs/
│   ├── design_v05.md          — full design document (architecture, data model,
│   │                            psychological frameworks, module specs)
│   ├── future_features.md     — five longer-term feature ideas
│   └── implementation_status.md  — THIS FILE
├── engine/
│   ├── engine.py              — main game loop (GameEngine class); orchestrates
│   │                            passes, writes DB, handles NPC wander + involuntary events
│   ├── context.py             — context packet assembly for all three passes;
│   │                            queries DB and filters to action-relevant fields
│   ├── db.py                  — Database class; all SQL reads and writes;
│   │                            returns plain dicts
│   ├── config.py              — env-var configuration (DB path, LLM backend, log level)
│   └── llm/
│       ├── base.py            — LLMClient abstract base class; LLMError, LLMJSONError
│       ├── claude.py          — Claude (Anthropic API) backend
│       └── ollama.py          — Ollama (local model) backend stub
├── modules/
│   ├── i_am_a_cat/
│   │   ├── i_am_a_cat.db      — live SQLite database for this module
│   │   ├── seed.sql           — full seed data (characters, locations, items, etc.)
│   │   ├── seed_v3.sql        — v3 additions (location_connection; NPC wander params)
│   │   ├── seed_v4.sql        — v4 additions (character_visited_location for Toulouse)
│   │   ├── seed_v5.sql        — v5 additions (game_instance record; passive rates)
│   │   ├── seed_v6.sql        — v6 additions (gender + pronouns for all characters)
│   │   └── sample_transcript_01.md  — first full play session transcript
│   └── Netherfield_Ball/      — placeholder; not yet implemented
├── schema/
│   ├── schema.sql             — canonical schema with full field-semantic comments;
│   │                            reference this before adding any new fields
│   └── migrations/
│       ├── migrate_v1_to_v2.sql
│       ├── migrate_v2_to_v3.sql
│       ├── migrate_v3_to_v4.sql
│       ├── migrate_v4_to_v5.sql
│       └── migrate_v5_to_v6.sql
└── tests/                     — empty; test suite is future work
```

---

## Schema version history

**v1 — Initial schema**
Core tables: `schema_version`, `game`, `location`, `location_detail`,
`location_connection` (added v3), `character`, `character_goal`,
`character_attitude`, `character_skill`, `character_visited_location` (added v4),
`action_log`, `item`, `item_location`, `internal_state`, `involuntary_event`.

**v2** — Involuntary event support on `internal_state` (`involuntary_event_type`,
`involuntary_trigger_probability`, `involuntary_min_interval_turns`,
`last_involuntary_turn` fields). Intrinsic motivation on `character_skill`
(`intrinsic_motivation` float).

**v3** — `location_connection` table (explicit adjacency graph, `is_passable` flag).
`wander_range` (JSON list of location IDs) and `wander_probability` (float) on
`character`.

**v4** — `character_visited_location` table. Supports quick-move pathfinding
(BFS, Option C): player can name any previously-visited destination and the engine
computes the path. NPCs are not subject to this restriction.

**v5** — `game_instance` table (per-playthrough metadata: status, start/current time, premise_modifier). `passive_rate_per_minute` (REAL, NULL) on `internal_state` for background state drift. In-game clock advanced by Pass 2's `elapsed_minutes` output each turn.

**v6** — `gender` (TEXT, NULL) and `pronouns` (TEXT/JSON, NULL) on `character`. Gender label and case-indexed pronoun array for Pass 3 prose rendering. Case labels are English regardless of module language (language-neutral schema key); form values are in the module's target language.

**Current version: 6.** Next migration will be v7 (module/instance split — see pending work §3).

---

## Engine feature status

| Feature | Status | Notes |
|---|---|---|
| Three-pass LLM loop (intent → adjudication → prose) | ✅ Complete | |
| Database layer (db.py) | ✅ Complete | |
| Claude backend | ✅ Complete | |
| Ollama backend | ⬜ Stub only | Phase 2 target |
| Involuntary events (hairball) | ✅ Complete | Rolls per turn in engine.py |
| NPC autonomous wander | ✅ Complete | Per-turn roll in engine.py |
| Multi-step pathfinding (BFS) | ✅ Complete | Handles NPC and item interruptions |
| Visited-location tracking | ✅ Complete | Updated on each move |
| Pass 1 location name→ID resolution | ✅ Complete | `known_locations` dict in packet |
| In-game clock | ✅ Complete | `game_instance.current_time_minutes`; advanced by Pass 2's `elapsed_minutes` |
| Passive state decay | ✅ Complete | `passive_rate_per_minute` on `internal_state`; `db.tick_passive_states()` |
| Gender + pronouns | ✅ Complete | `character.gender` and `character.pronouns` (JSON); passed to Pass 3 via `characters_referenced` |
| Token usage logging | ✅ Complete | Per-call debug log + session total (INFO) in `claude.py`; `token_totals()` method |
| Search mode (`search` action type) | ⬜ Not started | See pending work #2 |
| Wander mode (`wander` action type) | ⬜ Not started | See pending work #3 |

---

## I Am a Cat — live game state

*As of session 5 (2026-05-22). Clock has drifted to ~7:00 AM from accumulated testing turns.*
*⚠️ Game needs a clean reset before next serious play session. Run `reset_instance.sql` (see below).*

**Canonical starting state (3:00 AM):**

| Character | Location | Emotional state | Notes |
|---|---|---|---|
| Toulouse (player) | Living Room (1) | restless | |
| Spook | Living Room (1) | playful | male; wander_probability=0.08 |
| Guy | Bedroom (10) | deeply_asleep | |
| The mama | Bedroom (10) | lightly_asleep | |
| Lillis | Basement Main Room (6) | asleep | female Senegal parrot; immobile |

**Starting internal states:**

| Character | State | Starting value | Rate/min | Notes |
|---|---|---|---|---|
| Toulouse | boredom | 0.00 | +0.002 | Failure condition approaches 1.0 |
| Toulouse | hairball_pressure | 0.05 | +0.0003 | |
| Toulouse | hunger | 0.45 | +0.002 | Reaches ~0.63 by 4:30 AM; see hunger mechanic note below |
| Guy | sleepiness | 0.88 | -0.006 | Wakes ~5:27 AM if undisturbed |
| Mama | sleepiness | 0.22 | -0.004 | Wakes ~3:55 AM if undisturbed; light sleeper |
| Spook | boredom | 0.03 | — | |
| Spook | hairball_pressure | 0.31 | +0.0003 | Elevated; involuntary event possible |
| Spook | hunger | 0.38 | — | |

---

## Pending work — priority queue

### ✅ In-game clock + generalized passive state decay (completed session 4)

**Design summary:**
Pass 2 already returns structured JSON. Add an `elapsed_minutes` field to its
required output. The engine accumulates this into `game_clock_minutes` on the
`game` record. Starting time for I Am a Cat is 3:00 AM (180 minutes past midnight).

Passive state drift is generalized: add `passive_rate_per_minute` (REAL, NULL)
to `internal_state`. Signed float — positive accumulates, negative decays. NULL
means engine does not touch the state passively; only Pass 2 changes it. After
each clock tick the engine applies `clamp(value + rate * elapsed_minutes, 0.0, 1.0)`
to all states with a non-null rate. This one mechanism covers: sleepiness/sleep
depth, hunger, thirst, thermal discomfort, air depletion, boredom drift, hairball
background pressure, and any future module-specific physiological state.

Pass 2 retains full authority to override any state value via its outcome JSON
(disturbance-driven drops, activity-driven changes, etc.). The passive rate is
background drift only.

States whose drift depends on character activity (restlessness, impatience) get
`passive_rate_per_minute = NULL` and are managed entirely by Pass 2.

**Calibration for I Am a Cat (starting values — tune during play):**

| Character | State | Rate/min | Rationale |
|---|---|---|---|
| Toulouse | boredom | +0.002 | Accumulates if player is inactive; Pass 2 reduces on interesting actions |
| Toulouse | hunger | +0.002 | Starts 0.45; reaches ~0.7 after 2 hours of play |
| Toulouse | hairball_pressure | +0.0003 | Slow background drift; grooming events add +0.1 each via Pass 2 |
| Guy | sleepiness | -0.006 | 0.88 → 0 in ~147 min (wakes ~5:27 AM); lightens toward morning |
| Mama | sleepiness | -0.004 | 0.22 → 0 in ~55 min (could wake ~3:55 AM); lighter sleeper |

**Tasks:**
1. Schema migration v5: add `game_clock_minutes` (INTEGER DEFAULT 180) and
   `game_start_time_label` (TEXT DEFAULT '3:00 AM') to `game`; add
   `passive_rate_per_minute` (REAL DEFAULT NULL) to `internal_state`.
2. `db.py`: add `get_game_clock()`, `advance_game_clock(minutes)`,
   `tick_passive_states(elapsed_minutes)` (generalizes former `tick_sleep_decay`).
3. `engine.py`: after writing Pass 2 outcomes, call `advance_game_clock` and
   `tick_passive_states`. Include `current_game_time` in context packet.
4. Pass 2 prompt: add `elapsed_minutes` to required output fields; add
   `current_game_time` to context packet (context.py).
5. Seed v5: update `game` record clock fields; set `passive_rate_per_minute` on
   the internal states listed in the calibration table above.

**Future: hairball trigger migration.** The existing involuntary event fields on
`internal_state` (v2) handle the threshold-trigger side. Eventually fold these
into a unified state-hierarchy system where any state with a passive rate can
also declare trigger thresholds. Not tonight — handle after the passive rate
mechanism is stable.

### 1. NPC pending intent (`pending_intent` field)

**Observed need:** When Toulouse grooms Spook and then asks Spook to reciprocate,
Pass 2 has no memory of the earlier social exchange. By the next turn, Spook's
profile shows nothing about the obligation — the LLM re-derives his motivation
from scratch and Spook behaves as though the grooming never happened. This makes
multi-turn social exchanges (reciprocal grooming, negotiated cooperation, deferred
requests) difficult to sustain.

**Design:** Add `pending_intent TEXT NULL` to the `character` table. A natural-language
string describing a deferred social obligation or queued intention, set and cleared
by Pass 2 outcome JSON, visible to Pass 2 in the NPC profile. Consistent with how
`emotional_state` works: the LLM writes it, the LLM reads it, no engine logic
interprets it.

Examples:
- `"owes reciprocal grooming to Toulouse (ears)"` — cleared when Spook grooms Toulouse
- `"intends to investigate the noise from the basement"` — cleared on arrival or distraction
- `"waiting for Toulouse to approach before engaging"` — cleared on contact

This is distinct from `emotional_state` (short-term mood), `internal_state` floats
(physiological), and goals (stable motivational weights). It is closer to a
working-memory slot for social and behavioral commitments — a concept present in
the Ford-Nichols framework under equity and belonging goals.

**Migration sketch (v7 candidate, or bundle with another small change):**
```sql
ALTER TABLE character ADD COLUMN pending_intent TEXT NULL;
-- NULL = no pending intent; LLM ignores field if absent.
-- Set by Pass 2 outcome: add "pending_intent_updates": [{"character_id": N, "intent": "..."}]
-- to the outcome schema. Empty string or explicit null clears the field.
```

Pass 2 context: include `pending_intent` in the NPC profile block (already built
by `_build_character_profile()`). Pass 2 prompt: add `pending_intent_updates` to
required output fields with a note that the LLM should set or clear it based on
whether social obligations are created or fulfilled this turn.

**Also applies to:** conversation commitments ("Guy said he'd get up if Toulouse
persisted"), promised actions by the player character, and anything else that
constitutes a deferred behavioral obligation across turn boundaries.

---

### 2. Hunger-driven wake mechanic (4:30 AM trigger)

**Design:** By approximately 4:30 AM, Toulouse's hunger becomes compelling enough
that he goes to wake Guy for canned food. This is one of the defining daily
rituals of the module — the whole night's arc builds toward it. It should feel
inevitable once hunger crosses a threshold, not random.

**Calibration:** With hunger starting at 0.45 and a rate of +0.002/min, hunger
reaches ~0.63 at 4:30 AM (90 minutes of game time). Whether 0.63 feels compelling
depends on what Pass 2 does with it — but for a dedicated involuntary trigger,
a threshold around 0.70 is more reliable. Options:

1. *Raise starting hunger slightly* (0.55 → reaches 0.73 at 4:30 AM). Simple.
2. *Raise the rate* (+0.003/min → 0.45 → 0.72 at 4:30 AM). Increases urgency
   across the whole session, which may be too much.
3. *Add a hunger involuntary event* at threshold 0.68 with probability 0.25/turn.
   Once hunger crosses 0.68, there's a ~1-in-4 chance each turn that the event
   fires: "Toulouse's hunger becomes urgent; he feels a strong pull toward Guy's
   bedroom and the promise of canned food." Pass 2 incorporates this as a strong
   behavioral pressure — not a forced move, but a compelling one. This is the
   most consistent with the existing involuntary event architecture.

Option 3 is recommended. It makes the wake-Guy sequence an emergent behavior that
the player can lean into or resist, rather than a hard trigger. The involuntary
event description should name Guy specifically so Pass 2 understands the target.

**Reset note:** Starting hunger needs to be recalibrated when the game is reset.
Check seed values before next play session.

---

### 3. Post-Pass-2 validation / retry layer

**Design principle:** The game engine owns all object and character locations.
If Pass 2 adjudication proposes a change that is physically impossible (moving an
NPC to a non-adjacent room, referencing an item the player cannot perceive, moving
a character who is not in `characters_at_location`), the engine must catch it before
applying the outcome and before Pass 3 runs. Pass 3 must only narrate what the engine
has already confirmed and written to the database — it must not describe events that
failed validation.

**Validation layer (between Pass 2 and `_apply_outcome`):**

1. For each entry in `location_change`, verify:
   - The character exists in the DB.
   - `new_location_id` is adjacent to the character's current location
     (already partially enforced in `_apply_outcome`; should be promoted to
     a pre-apply check that can trigger a retry).
   - For NPCs: the character appears in `characters_at_location` in the Pass 2
     context (not hallucinated from an adjacent room or from past turns).

2. For each entry in `item_changes` / `item_location_change` (see §3a below), verify:
   - The item exists in the DB.
   - The item is currently at a location that makes the proposed change reachable.
   - If an NPC is moving an item, the NPC must be in `characters_at_location`.

3. If any violation is found, the engine does NOT apply the outcome. Instead:
   - Rebuild the Pass 2 prompt with a preamble: `"CORRECTION: your previous
     response proposed [X], which is not possible because [Y]. Please re-adjudicate
     the same action with this constraint."` Append the impossibility description.
   - Resend to the LLM (one retry only).
   - If the retry also fails validation, strip the offending fields and apply the
     remainder. Log a warning for post-session review.

**Scope note:** This is medium complexity — it requires a validation function that
mirrors the guards already in `_apply_outcome`, plus retry plumbing in `_process_turn`.
Design validation logic first; retry scaffolding is additive. Do not combine with
the item_location_change work in the same session.

---

### 3a. Item location change and NPC item movement

**Current limitation:** The outcome schema has `item_changes` (updating fields on
existing items) but no mechanism for *moving* an item from one location to another.
This blocks two important gameplay features: NPC item movement (Spook knocking a
toy into another room) and lazy item discovery (Toulouse finding a toy in the hallway
that he passed by earlier without noticing).

**New outcome field: `item_location_change`**

Add to the Pass 2 required output schema:

```json
item_location_change  (list of {item_id, new_location_id, moved_by_character_id};
                       one entry per item that changes physical location this turn.
                       new_location_id must be a valid location_id in the DB.
                       moved_by_character_id must be a character currently in the
                       item's current location. Empty list if no items move.)
```

Engine validation (via the §3 retry layer): confirm item exists, confirm the moving
character is at the item's current location, confirm new_location_id exists.

**Lazy item discovery:** Some items in a location are not immediately visible
(`is_visible = 0` in the item table, or simply not present in the Pass 2 context
because they haven't been discovered yet). When the player searches a room or the
LLM determines the player character would notice the item given their species/state,
Pass 2 can issue an `item_changes` entry setting `is_visible = 1`. This makes the
item appear in subsequent context packets without any schema change. No new table
needed; the existing `is_visible` flag and `item_changes` mechanism are sufficient.
The design question is whether Pass 2 should *always* be given invisible items in
the context so it can adjudicate discovery, or whether the engine should only expose
them under specific conditions (search action, high sensory acuity, etc.).

**NPC item movement:** Spook knocking a toy down the hallway requires `item_location_change`
with `moved_by_character_id = Spook.id`. The engine applies this before Pass 3 runs,
so Pass 3's `characters_present` and location context reflect the new item positions.
For this to work correctly, Spook must be in `characters_at_location` when the move
is adjudicated — the validation layer enforces this.

**Schema note:** No schema change required for `item_location_change`. The engine
implements it as: validate → `UPDATE item SET location_id = ? WHERE id = ?` (if
`location_id` is a direct field) or `UPDATE item_location SET location_id = ? WHERE
item_id = ?` (if items use the `item_location` join table). Check schema.sql for the
current item location storage pattern before implementing.

---

### 4. Search mode (next up)

New Pass 1 action type `search`. "Go look for Spook" triggers directed traversal
of ~3 adjacent locations, brief prose per room checked, LLM adjudicates whether
target is found at each step.

### 2. Wander mode

New Pass 1 action type `wander`. "Wander around" triggers random non-repeating
~3-move traversal. Distinct from search in that no target is specified.

---

### 4. Module / instance architectural split (v7 migration — do before public release)

**Known limitation:** The current schema conflates module definition (static)
with playthrough state (dynamic) throughout — not just in `game` but in
`character` (`current_location_id`, `emotional_state`), `internal_state`
(values), `item_location`, `action_log`, `character_visited_location`. There is
no concept of a playthrough instance. The game always resumes from the last
known state, which is incidental behavior, not a designed feature. Players
expect new game / save / resume / load.

**Phased approach:**

*Phase A (v5 — tonight):* Add a thin `game_instance` table holding per-playthrough
metadata: `current_time_minutes`, `status` ('pending'/'ready'/'active'/'complete'),
`premise_modifier`. The `game` table becomes pure module definition (no new
fields added to it tonight). Other state tables are unchanged — they implicitly
belong to the one active instance. Reset is achieved by re-running
`seed_instance.sql` (see below).

Split seed SQL into two files:
- `seed_static.sql` — module definition: game params, locations, connections,
  character definitions, items. Run once.
- `seed_instance.sql` — starting playthrough state: character locations, internal
  state values, item positions, instance record. Re-running this resets the game.

*Phase B (v7 — future):* Add `instance_id` to every state table (`character`,
`internal_state`, `item_location`, `action_log`, `character_visited_location`).
Enables multiple concurrent instances, true save slots, and the "What if..."
premise modifier feature. Design in conjunction with session management UI.

*Also consider for v6:* A `status` field on the `game` table itself
('pending'/'ready'), analogous to `game_instance.status`, so that an incomplete
module definition (missing required fields, incomplete seed) is also detectable
before any instance is created. Currently the `game` table has no readiness
guard of its own.

**Reference:** `docs/future_features.md` sections 4 (Save/resume) and 6 (What if).

---

## Lower-priority pending items

- **Session exit: happiness/wellbeing score.** On exit the engine currently
  reports game time elapsed and Toulouse's raw boredom float. A richer "how
  well did the session go?" metric would combine: primary state value at exit
  (boredom for I Am a Cat), goal achievement (did the player pursue Toulouse's
  named goals?), need satisfaction (hunger managed, hairball avoided), and
  any pending intents that were or weren't fulfilled. The boredom float is a
  reasonable single-state proxy for now. The fuller score requires a
  module-level config declaring which states and goals constitute the outcome
  metric, and a weighted aggregation step at session end. This is also the
  basis for a future "end-of-game score screen" (how bored was Toulouse at
  sunrise? did he get his canned food?).

- **Pricing table maintenance cadence.** `_PRICING_PER_MTOK` in `engine/llm/claude.py`
  carries Anthropic's per-token rates with a "last verified" date. Prices change
  but not on a per-session or per-module schedule. Suggested practice: review
  quarterly (add a calendar reminder), and always when adding a new model string
  to the table. The "last verified" comment in the source is the check — if it's
  more than a few months old at the start of a session, spend 30 seconds
  confirming against https://www.anthropic.com/pricing before a long play run.

- **Clock visibility as a module-level setting.** The engine tracks in-game
  time via `game_instance.current_time_minutes` but deliberately withholds it
  from Pass 1/2/3 context for I Am a Cat — cats don't read clocks, and the
  behavior is correct. However, some modules need explicit time awareness: in
  a Cinderella module, being able to ask "how long until midnight?" or having
  the clock strike audibly are plot-critical mechanics. Design: add a
  `clock_visible_to_player` flag to `module_flags` JSON on `game` (consistent
  with the `what_if_enabled` flag sketched in future_features.md §6). When
  true, the engine includes current_game_time in Pass 1 context and allows
  time-query actions; when false (default), time is withheld as now.

- **Mama's wander range and sleep state**: "Lightly asleep" for the mama can
  mean drowsy but ambulatory — she does get up for the bathroom at night, which
  is realistic. However her current wander_range may be too broad; it should
  probably be limited to Bedroom + Bathroom (and possibly the hallway between
  them) to reflect genuine middle-of-the-night movement rather than wide
  roaming. When she does move, her emotional_state should probably shift to
  something like 'groggy' rather than staying 'lightly_asleep'. Review
  wander_range in seed and consider whether sleepiness threshold should gate
  wander probability (very deeply asleep characters shouldn't wander at all).
- **Bedroom door**: Include all connections with `is_passable` flag in context
  (not passable-only), so the LLM can adjudicate door-opening. Engine validation
  stays passable-only for movement.
- **Item description policy**: Decide on canonical `description` field behavior
  for items (lazy-generated vs. seeded).
- **Null `item_id` on drop actions**: Add better prompt guidance.
- **Character name drift** (guy → papa): Pass 2 sometimes uses "papa" instead
  of "guy." Add normalization note to prompt or seed.
- **NPC wander suppression after interaction**: Wander fires at the top of each
  turn before player input. A character the player just interacted with can
  wander away before the next action is even typed, making multi-turn
  interactions (bath, play session) impossible. Need a suppression mechanism:
  characters should not wander on the turn immediately following an interaction
  with the player. Simplest implementation: track `last_interaction_turn` on
  character (or in the action log) and skip wander roll if the gap is < N turns.
  Alternatively, suppress wander for any character in `characters_present` from
  the previous turn's Pass 2 context.
- **Spook's wander_probability too high**: Currently bouncing between adjacent
  rooms every turn. Reduce wander_probability in seed (current value unknown —
  check seed.sql). A playful cat roams, but not at teleport speed.
- **Perception range — characters_nearby (fix scheduled)**: Pass 2 only
  receives characters at Toulouse's current location. Characters in adjacent
  rooms are invisible to adjudication, even when audible (Spook one room away
  at 3am). Fix: add `characters_nearby` to Pass 2 context — characters in
  adjacent locations with a minimal profile (id, name, species, location name,
  emotional_state). No schema change needed; uses the existing location graph.
  LLM reasons about detectability from species + emotional_state.

- **Sensory profile system (future, medium scope)**: The `characters_nearby`
  fix uses LLM inference for detectability. The full design needs explicit
  sensory values: a per-character receiver profile (hearing, smell, dark vision,
  etc.) and a per-character stimulus output (how detectable they are right now,
  driven by species, activity, and emotional state). These interact: cat hearing
  vs. human hearing; playful Spook vs. deeply asleep Guy.
  This becomes much richer in multi-species or supernatural modules: a vampire
  who senses heartbeats in adjacent rooms; a cat who perceives demons that
  humans can't detect at all; a blind character who navigates entirely by sound
  and smell; a "What if Toulouse's house is populated by small mischievous
  demons only cats can see" scenario. Species-specific perception is one of the
  things that makes non-human player characters feel genuinely alien rather than
  just humans with different numbers. Design questions to resolve: does the
  engine compute detection (stimulus × acuity > threshold → include in context),
  or does it always include nearby stimuli and let the LLM decide what the
  character notices? The second is more consistent with the "LLM handles
  ambiguity" principle. Schema: small JSON profile on `character`
  (e.g. `{"hearing": 0.85, "smell": 0.90, "dark_vision": 0.70}`) plus a
  `sensory_output` float updated by the engine from emotional_state and species.
- **Room content consistency (lazy world gen detail reuse).** Pass 3 currently
  generates room descriptions from the location `description_skeleton` plus
  whatever narrative context it infers. It does not receive the `location_detail`
  records that were generated and stored by earlier turns. As a result, specific
  room contents — the shape of the dining room table, the titles on the living
  room bookshelf, the particular clutter on the coffee table — are regenerated
  fresh each time Pass 3 describes a room, producing inconsistent details across
  turns and sessions. The fix is to include the current valid `location_detail`
  records for the player's current location in the Pass 3 context packet, so
  prose rendering draws from canonical stored facts rather than re-inventing them.
  Pass 2 already receives and generates these details; Pass 3 just isn't getting
  them. This is purely a context packet assembly change in `context.py`
  (`build_pass3_packet`) — no schema or engine changes required.

- **Interaction history compression**: Long sessions will make the history section
  of context packets expensive. Plan a compression strategy.
- **Haiku comparison run**: Run same seed/actions through Haiku to compare
  output quality with Sonnet.
- **Test suite**: Currently empty. At minimum, smoke tests for db.py methods
  and context packet assembly.

---

## Key design decisions (not obvious from code)

**LLM handles language; engine handles logic.** The engine and database own all
state management, threshold evaluation, trigger decisions, and pathfinding. The
LLM's roles are: (1) parse player intent from free text, (2) adjudicate
genuinely ambiguous narrative outcomes and return structured JSON, (3) render
prose. No game logic lives in the LLM; no natural language processing lives in
the engine. This boundary is intentional and should be maintained as the engine
grows. Lazy world generation extends this principle: the LLM generates a detail
on demand, but the engine immediately writes it to the database, after which it
is always retrieved, never regenerated.

**Passive state drift is data-driven, not hardcoded.** The `passive_rate_per_minute`
field on `internal_state` lets any state drift over in-game time without engine
code changes. Adding a new physiological mechanic (thirst, thermal discomfort,
air depletion) requires only seeding the state with a rate — no new engine logic.
States whose drift is activity-dependent (restlessness, impatience) use NULL and
are managed entirely by Pass 2.

**`sleepiness` doubles as sleep depth.** For sleeping characters, the
`sleepiness` internal_state value represents how deeply asleep they are (high =
deep, low = light). For awake characters it represents pressure toward sleep.
The same field serves both states; the LLM interprets it contextually.

**Open skill taxonomy.** Skill names are natural-language strings. The LLM
evaluates semantic relevance at adjudication time. No lookup tables.

**Lazy world generation.** `location_detail` records are generated on first
query and stored permanently (unless invalidated by a subsequent event).

**Boredom as hit points.** Boredom approaching 1.0 is the I Am a Cat failure
condition. This generalizes: internal state degradation replaces hit points as
the stakes mechanic. Other modules use different states (e.g., reputation,
fatigue).

**NPC wander is engine-driven.** NPC movement is a per-turn probability roll in
`engine.py`, not an LLM decision. This keeps wander cheap and prevents
LLM-driven location drift (observed in v2 play sessions before the adjacency
graph was added).

**Path interruptions.** BFS pathfinding can be interrupted by NPCs or items
of interest in intermediate rooms. The engine checks for interruptions at each
step along the computed path and stops Toulouse there, reporting the interruption
to the LLM in the context packet.

**Schema comments are the field reference.** `schema.sql` has full semantic
comments on every field, including float range and behavioral meaning. Read it
before adding or modifying fields.
