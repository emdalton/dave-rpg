# DAVE RPG Engine — God-Mode Design Specification

*Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)*

*Status: DESIGN COMPLETE — all decisions resolved 2026-07-16. Ready for implementation.*

---

## 1. Overview

God-mode is an authoring and world-instantiation mode for the DAVE engine. When
active, the player's input is treated as having two simultaneous registers:

- **Player actions** ("I walk into the apothecary") — adjudicated normally
- **World assertions** ("Bustling behind the counter is an aged kappa with
  half-moon spectacles") — accepted as authoritative world-building facts,
  canonized into the database, and rendered back in Pass 3

The primary use case is collaborative world instantiation during play: the
author describes the world into existence while moving through it, and the
engine makes those descriptions permanent. The Vintage Village module — which
seeds many locations as skeletons with no pre-populated NPCs — is the motivating
test case.

God-mode is an authoring tool, not a player experience feature. It is never
on by default and is not stored in module data.

---

## 2. Activation ✅

God-mode is activated by a CLI flag at engine startup:

```bash
DAVE_DB_PATH=modules/vintage_village/vintage_village.db python3 -m engine --god-mode
```

Or equivalently via environment variable (for scripts and web launcher config):

```bash
DAVE_GOD_MODE=1 DAVE_DB_PATH=... python3 -m engine
```

The flag sets a boolean on the `GameEngine` instance at construction time
(`self.god_mode: bool`). It has no effect on the database schema and leaves
no trace in the saved game state. Removing the flag on the next run returns
the engine to normal play mode; all canonized content persists regardless.

CLI-only for now. The web frontend (`web/game.py`) has no concept of this flag.
A future session can add a per-session toggle in the web UI if needed.

---

## 3. Input classification

God-mode changes how the engine interprets player input before the three-pass
loop runs.

### 3.1 Classification heuristics ✅ (preliminary)

Pass 1 in god-mode receives the full raw input and classifies each sentence or
clause as either a **player action** or a **world assertion**:

| Signal | Classification |
|--------|---------------|
| Starts with "I " (first-person volitional) | Player action |
| Starts with "There is / There are / There was" | World assertion |
| Starts with `<NPC name> has / is / was / carries` | World assertion |
| Scene description in third person or passive voice | World assertion |
| Interior description of a place the player just entered | World assertion |

The example input —

> "I walk into the apothecary. Bustling behind the counter is an aged kappa
> with half-moon spectacles. He uses a rolling stepladder to reach the medicinal
> ingredients in the upper drawers of the storage unit, which extends the height
> of the room and the width of the back wall."

— contains one player action (sentence 1) and two world assertions (sentences
2–3). Mixed input is the normal case, not the exception.

**Classification is LLM-evaluated in Pass 1**, not rule-based string matching.
The prompt instructs the LLM to classify each sentence/clause and extract
accordingly — robust to stylistic variation without needing a parser.

**Backend note:** god-mode Pass 1 classification is more cognitively demanding
than normal Pass 1 intent parsing. It should run on a stronger model than Haiku
or Mistral Small. Current preference: **Qwen 3.5** (or Sonnet if available).
This can be configured as a separate model setting from the main game-loop model.

**Pure-action input in god-mode:** if the player types only "I sit down at the
counter" with no world assertions, the god-mode path always runs — Pass 1
returns an empty `world_assertions` list, canonization in Pass 2 is a no-op,
and Pass 3 renders normally. This keeps the code path consistent and allows
the player to navigate and test content without inputting new details.

---

## 4. The three-pass loop in god-mode

### 4.1 Pass 1 — Intent parsing + assertion extraction ✅

**Normal Pass 1** returns an `action_record` with `action_type`, `target`,
`item`, `inferred_goal`.

**God-mode Pass 1** returns the same `action_record` fields **plus** a
`world_assertions` list. Each assertion is a typed object:

```json
{
  "action_record": {
    "action_type": "move",
    "target_location_id": 9
  },
  "world_assertions": [
    {
      "type": "npc_description",
      "location_id": 9,
      "name": "The Apothecary Keeper",
      "species": "kappa",
      "gender": "male",
      "description": "An aged kappa with half-moon spectacles, working behind the counter.",
      "apparent_status": "proprietor"
    },
    {
      "type": "location_detail",
      "location_id": 9,
      "detail": "A rolling stepladder leans against a storage unit that extends the full height of the room and the width of the back wall. The upper drawers are labeled in small, careful script."
    },
    {
      "type": "item",
      "location_id": 9,
      "name": "rolling stepladder",
      "description": "A wooden stepladder on small casters, used to reach the upper drawers of the back storage unit.",
      "location_description": "leaning against the storage unit along the back wall"
    }
  ]
}
```

**Assertion types** (see Section 5 for full definitions):
- `location_detail` — a descriptive fact about a place
- `npc_description` — a new character to create, or additional description of
  an existing one
- `npc_attribute` — a specific attribute update for a named existing NPC
  (attitude, trait, emotional state)
- `item` — a new item to instantiate at a location or in a character's
  possession
- `spatial_relation` — where an NPC or item is within a location (maps to
  future `character.position_item_id` / `item.location_description`)

**Cross-location assertions are accepted.** The author may be building the world
ahead of their character's position ("In the tea house, there is a sleeping cat
on the counter" — said while in the apothecary). Pass 2 canonizes them normally;
the rendered description appears when the player visits.

### 4.2 Pass 2 — Canonization ✅ (in god-mode)

**Normal Pass 2** adjudicates outcomes from game world state and NPC psychology.

**God-mode Pass 2** has a different job: **canonization gatekeeper**. It
receives:
- The `action_record` from Pass 1 (movement/action still processed normally)
- The `world_assertions` list from Pass 1
- The existing canonical state for all relevant locations and characters

For each assertion, Pass 2:
1. Checks whether a conflicting fact already exists in the canon
2. If **no conflict**: emits the assertion as a `new_location_details`,
   `new_characters`, or `item_instantiations` entry — the normal output fields
   the engine already knows how to write to the DB
3. If **conflict**: logs the contradiction and emits a
   `god_mode_contradiction` entry (see Section 6)

The normal game-outcome fields (`attitude_delta`, `narrative_beat`,
`internal_state_delta`, etc.) are still computed for the player action component
of the turn, using the same adjudication logic as normal mode. God-mode does not
suspend social mechanics or narrative consequences — it adds canonization on top.

**God-mode Pass 2 canonizes only explicit player assertions; unprompted lazy
generation is suppressed.** The author controls what exists; the engine does not
add details without being asked. If the engine generates something accidentally
(e.g., in a prompt that doesn't fully separate the two modes), the author can
override it — the `<override>` meta-channel command or a subsequent contradicting
assertion will correct it.

### 4.3 Pass 3 — Scene rendering ✅

**Normal Pass 3** renders the outcome of the player's action.

**God-mode Pass 3** renders the outcome of the player's action **plus** a
description of the scene as it now exists with the newly canonized details.
On a turn where the player moved to a new location and asserted world details,
Pass 3 should give a full arrival description that naturally incorporates those
details — not a list of what was just added, just a seamless scene render.

**Contradiction rendering:** ✅ If Pass 2 detected a contradiction between a
player assertion and existing canon, Pass 3 surfaces it as a natural parenthetical
or aside in the prose — not a system error, not an interruption, just a note
woven into the description:

> *The kappa behind the counter looks up at your arrival — elderly, focused,
> half-moon spectacles perched on their nose. (The record has them as male;
> your description says female — noted.)*

The wording should be light and non-intrusive. It is the author's decision
whether to accept the contradiction or correct it; the engine does not block
or revert.

---

## 5. World assertion types

### 5.1 `location_detail` ✅
A descriptive fact about a location. Maps directly to a new row in
`location_detail`. Fields: `location_id`, `detail` (prose string),
`invalidation_condition` (optional — defaults to null).

Conflict check: does any existing `location_detail` row for this location
describe the same physical feature? If so, contradiction. Otherwise, add.

### 5.2 `npc_description` ✅
A new NPC to create at a location, or additional description of an existing NPC.
Fields: `location_id`, `name`, `species`, `gender` (optional), `description`,
`apparent_status` (optional), plus optional OCEAN traits if the player supplies
enough to infer them.

If an NPC with this name already exists at this location: treat as an update
to `description` only; do not overwrite OCEAN traits, goals, or attitudes
already set. If any supplied attribute contradicts the existing record, flag as
contradiction.

If no NPC with this name exists: create via `new_characters` (same mechanism as
normal lazy NPC creation, but with `role='npc_active'` rather than
`npc_background` since god-mode NPCs are intentionally authored).

**NPC naming:** Pass 1 assigns a provisional name from the description ("The
Apothecary Keeper") when the player doesn't supply one. The provisional name is
displayed in Pass 3 when the NPC is created, so the author knows what handle
is in the DB. The author is encouraged to supply names when introducing NPCs;
names can be changed later. The engine does not prompt for a name mid-turn.

### 5.3 `npc_attribute` — deferred to Phase 2

A specific attribute update for a named existing NPC. The motivating use case
is personality description: "Maurice the kappa is known in the village for being
hardworking and attentive to detail, as well as for having a fondness for sweets."

**Phase 1 handling:** personality assertions of this kind are stored as an
update to the character's `description` field. This is already in the Pass 2
context packet and is the natural home for qualitative character notes. It does
not touch OCEAN float values.

**Why not OCEAN floats:** OCEAN traits are stored as precise floats but consumed
exclusively by the LLM as qualitative signals — there are no engine-side
calculations that compare or accumulate them. Overwriting a carefully seeded
float with an inferred value from a natural-language assertion would add false
precision without adding information. The floats are preserved as seed data
because a future rule-based layer (attitude decay rates, wander probability
weighting, emergent behavior thresholds) could genuinely use them as numbers;
they are not dropped, just not overwritten by god-mode in Phase 1.

**Phase 2 scope:** when `npc_attribute` is implemented, it should support
`emotional_state` and `attitude_toward_player` freely (these are already
qualitative fields). OCEAN float overrides should require explicit numeric
syntax and are out of scope until a rule-based consumer exists for them.

### 5.4 `item` ✅
A new item to instantiate at a location or in a character's possession. Fields
match `item_instantiations` already supported by the normal engine.

Conflict check: does an item with the same name already exist at this location?
If so, treat as a description update via `item_changes` rather than a new
instantiation.

### 5.5 `spatial_relation` — not needed as a separate type

New locations are only reachable by moving from existing locations (a new
place is always described relative to the entry point by which the player
arrives). This means spatial relations are implicit in the navigation graph
and do not require a separate assertion type. Within-location positioning
(where an NPC stands, where an item sits) is captured adequately in
`location_detail` strings and `item.location_description` without a
structured relation type.

---

## 6. Contradiction handling ✅

A contradiction occurs when a player assertion in god-mode conflicts with a fact
already stored in the canonical database.

**Engine behavior:**
1. The contradicting assertion is **not written** to the DB
2. A `god_mode_contradiction` note is added to the turn's action log
   (appended to the existing `raw_outcome` JSON column on the `action_log` row)
3. Pass 3 surfaces the contradiction as a light parenthetical in the
   rendered prose (see Section 4.3)

The player can resolve a contradiction by:
- Accepting the existing canon (doing nothing — the contradiction note fades)
- Re-asserting in a subsequent turn with the corrected value, if they prefer
  the original canon
- Using the `<override>` meta-channel command (existing mechanism) to directly
  set a field value if they want to force the change without the god-mode path

The engine does **not** automatically revert, overwrite, or block on a
contradiction. The author is always in control.

---

## 7. Pass 1 output schema (god-mode)

The god-mode Pass 1 prompt returns a JSON object with this top-level shape:

```json
{
  "action_record": { ... },
  "world_assertions": [ ... ]
}
```

The `action_record` follows the existing Pass 1 schema exactly. The
`world_assertions` list may be empty if no world-defining content was detected.

This is a new prompt template (`PASS1_GOD_MODE_PROMPT_TEMPLATE`) that replaces
`PASS1_PROMPT_TEMPLATE` when `self.god_mode` is true.

---

## 8. Engine code changes (planned)

| Component | Change |
|-----------|--------|
| `engine/config.py` | Add `GOD_MODE` bool (default False); read from env var `DAVE_GOD_MODE` |
| `engine/__main__.py` | Add `--god-mode` CLI flag; set `config.GOD_MODE = True` |
| `engine/engine.py` | `GameEngine.__init__` accepts `god_mode: bool`; branch in `_process_turn()` on `self.god_mode`; new `PASS1_GOD_MODE_PROMPT_TEMPLATE`; new `_canonize_assertions()` method called before normal Pass 2 |
| `engine/db.py` | Probably no changes needed — `add_location_detail()`, `create_character()`, `create_item()` already exist |
| `engine/engine.py` | Pass 3 prompt: god-mode variant includes `god_mode_contradictions` list in context |

No schema changes required. All assertion types map to existing DB write paths.

---

## 9. Out of scope for first implementation

- Web frontend god-mode toggle
- `npc_attribute` assertion type (OCEAN/goal overrides)
- `spatial_relation` assertion type (depends on character position feature)
- Cross-session god-mode activity log / authoring audit trail
- Undo/revert for god-mode canonizations (use reset_instance.sql)
- God-mode for the player's own character (asserting new aspects, skills, etc.)

---

## 10. Design decisions summary

All questions resolved as of 2026-07-16.

| # | Question | Decision |
|---|----------|----------|
| A | Pure-action input in god-mode | Always god-mode path; empty `world_assertions` is a no-op ✅ |
| B | Classification method | LLM-evaluated; backend should be Qwen 3.5 or stronger (not Haiku) ✅ |
| C | Web frontend exposure | CLI-only for now ✅ |
| D | Cross-location assertions | Accepted; canonized normally ✅ |
| E | Unprompted lazy generation in god-mode Pass 2 | Suppressed; author controls what exists ✅ |
| F | NPC naming when no name supplied | Provisional name from description; shown in Pass 3 note ✅ |
| G | `npc_attribute` assertion type | Deferred to Phase 2; personality description goes in `location_detail` for now ✅ |
| H | `spatial_relation` assertion type | Not needed as separate type; spatial context is implicit in the navigation graph ✅ |
| I | `god_mode_contradiction` storage | Appended to `raw_outcome` JSON column in `action_log` ✅ |

---

## 11. Example turn trace (god-mode)

**Player input:**
> "I walk into the apothecary. Bustling behind the counter is an aged kappa
> with half-moon spectacles. He uses a rolling stepladder to reach the medicinal
> ingredients in the upper drawers of the storage unit, which extends the height
> of the room and the width of the back wall."

**Pass 1 output:**
```json
{
  "action_record": { "action_type": "move", "target_location_id": 9 },
  "world_assertions": [
    {
      "type": "npc_description",
      "location_id": 9,
      "name": "The Apothecary Keeper",
      "species": "kappa",
      "gender": "male",
      "description": "An aged kappa with half-moon spectacles, working behind the counter.",
      "apparent_status": "proprietor"
    },
    {
      "type": "location_detail",
      "location_id": 9,
      "detail": "A storage unit extends the full height of the room and the width of the back wall. Its upper drawers hold medicinal ingredients; they are reachable only by stepladder.",
      "invalidation_condition": "storage unit removed or significantly altered"
    },
    {
      "type": "item",
      "location_id": 9,
      "name": "rolling stepladder",
      "description": "A wooden stepladder on small casters, used to reach the upper drawers of the back storage unit.",
      "properties": {"weight": "medium", "portable": true},
      "location_description": "leaning against the storage unit along the back wall"
    }
  ]
}
```

**Pass 2 canonization:**
- Apothecary has no existing NPCs → create The Apothecary Keeper (kappa, male)
- Apothecary has no existing location details → add storage unit detail
- Apothecary has no rolling stepladder → instantiate item

No contradictions detected.

**Pass 3 output (approximate):**
> The door of the apothecary swings open onto a dim, herb-scented room. Behind
> the counter, an aged kappa looks up from whatever he was measuring —
> half-moon spectacles catching the lamplight, bright eyes considering you
> briefly before returning to his work. Along the back wall, a storage unit
> climbs from floor to ceiling, its drawers labeled in tiny careful script.
> A rolling stepladder leans ready at one end. The smell of the place is
> complicated: something sweet, something medicinal, something you don't
> have a name for.
