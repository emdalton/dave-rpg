# DAVE RPG Engine — Test Suite

*Last updated: 2026-05-30. Update this file whenever tests are added, removed, or reorganized.*

---

## Overview

The test suite is organized into three tiers based on cost and what they exercise. Running `pytest` with no flags runs only Tier 1, which is fast and requires no API key. The more expensive tiers are opt-in.

| Tier | Flag | What it tests | Requires |
|---|---|---|---|
| 1 | *(default)* | Engine mechanics, DB layer, context assembly | Nothing |
| 2 | `--llm` | Pass 2 structural output contract | `ANTHROPIC_API_KEY` |
| 3 | `--llm-eval` | Pass 1 and Pass 3 quality via LLM-as-judge | `ANTHROPIC_API_KEY` |

**Quick start:**

```bash
pytest                  # Tier 1 only — fast, no API key
pytest --llm            # + Tier 2 — one real LLM call per test
pytest --llm-eval       # + Tier 3 — two real LLM calls per test (expensive)
```

Tier 2 and Tier 3 tests are skipped automatically unless the appropriate flag is passed.

---

## Tier 1 — Mechanics and Structure (no LLM)

These tests call engine and database methods directly with known inputs and assert exact outputs. They run in about 14 seconds and are the right thing to run after any change to `db.py`, `context.py`, or `engine.py`.

### `tests/test_db.py`

Covers every method in `engine/db.py` that the engine relies on.

- **Schema version** — confirms `schema_version` table is populated on fresh install.
- **Game record** — `get_game()` returns the record with JSON fields parsed; returns None for unknown IDs.
- **Character queries** — `get_character()` by ID; characters at location; excluding a character from a location query; None for unknown IDs.
- **Internal states** — get, update, apply delta with clamping at 0.0 and 1.0.
- **Passive state drift** — `tick_passive_states()`: positive rate increases, negative rate decreases, clamping at both ends, NULL rate is untouched.
- **In-game clock** — initial value, advance, accumulation across multiple advances.
- **Attitudes** — get, apply delta, clamp at ±1.0, create new record when none exists; returns 0.0 for unknown pairs.
- **Faction reputation** — `get_or_create_faction()` is idempotent; apply delta with clamping.
- **Pending intent** — set and clear on a character record.
- **Activity system** — set, clear, and the expiry query: expired activities returned, non-expired not returned, renewable activities not returned, low-confidence activities not returned.
- **Location queries** — get location by ID; `is_location_connected()` in both directions; `get_location_connections()` returns neighbors.
- **Character creation** — `create_character()` inserts a row and returns the full character dict; new character appears in location queries.

### `tests/test_context.py`

Verifies that `build_pass1_packet()`, `build_pass2_packet()`, and `build_pass3_packet()` return correctly shaped dicts given a known database state. Tests check key presence and basic content — not prose quality.

**Pass 1 packet:**
- Required top-level keys present (`player_input`, `game`, `player`, `current_location`, `recent_actions`, `known_locations`).
- `player_input` is preserved verbatim.
- `known_locations` includes all seeded locations.
- Player profile includes current location information.
- Game block has correct genre and tone.

**Pass 2 packet:**
- Required top-level keys present (`game`, `player`, `characters_present`, `current_location`, `action_record`).
- Player profile includes `emotional_state` and `faction_reputations` (with correct faction name key).
- `characters_present` includes NPCs at the player's location and excludes those elsewhere.
- NPC profile includes `pending_intent` when set, `current_activity` when set.
- `current_location` includes `adjacent_locations` list with correct neighbor IDs.

**Pass 3 packet:**
- Required top-level keys present (`game`, `player`, `outcome`, `characters_present`, `adjacent_locations`).
- Outcome dict is embedded and includes `narrative_beat`.
- `characters_present` includes the correct NPCs.
- `adjacent_locations` lists neighbors by name.
- Game block includes `speech_filter`.

### `tests/test_engine.py`

Tests the three main engine subsystems that are independent of LLM output quality. All tests use a `MockLLMClient` — no real LLM calls are made.

**`_apply_outcome()` — processing Pass 2 output fields:**
- *Attitude deltas:* applies delta to existing attitude record; skips malformed entries without crashing.
- *Internal state deltas:* applies delta; clamps at 0.0 (does not go negative).
- *Emotional state:* updates the character's `emotional_state` string.
- *Location change:* moves player to a valid adjacent location; rejects non-existent location IDs; rejects non-adjacent locations.
- *Faction reputation:* applies delta to an existing reputation record.
- *Pending intent:* sets intent text on a character; clears it when explicitly nulled.
- *Activity:* sets `current_activity` with duration, confidence (clamped to 1.0), and renewable flag; clears activity when nulled.
- *New characters:* inserts a new NPC row from a `new_characters` outcome entry; does not create duplicates on repeated calls.

**`_check_activity_expiry()`:**
- Clears an expired high-confidence non-renewable activity.
- Leaves a non-expired activity in place.
- Never auto-clears a renewable activity regardless of elapsed time.
- Never auto-clears a low-confidence activity (below `ACTIVITY_AUTO_CLEAR_CONFIDENCE`).

**`_check_npc_wandering()` — suppression conditions:**
- `pending_intent` suppresses wander.
- Sleepiness at or above `WANDER_SLEEPINESS_THRESHOLD` suppresses wander.
- A non-expired `current_activity` suppresses wander.
- Positive control: Guard with `wander_probability=1.0` and no suppression conditions active moves to the adjacent location.
- An expired activity (past its duration window) does not suppress wander.

### `tests/test_hidden_hostel.py`

37 tests across 8 classes. Uses the Hidden Hostel module (`modules/hidden_hostel/seed.sql`) as a richer test world that exercises features the minimal two-location test world cannot cover. All Tier 1, no LLM calls.

Uses two module-specific fixtures defined at the top of the file (not in `conftest.py`):
- `tmp_hostel_db` — function-scoped; loads schema + Hidden Hostel seed into a temp file, yields a `Database` instance.
- `hostel_engine` — function-scoped; constructs a full `GameEngine` against the hostel DB with a mock LLM. Transitions game_instance from `ready` to `active` on construction (same as production).

**`TestStaircaseConnection` (§A)** — The Common Room ↔ Upper Corridor connection uses `connection_type='stairs'`, a configuration that caused a real regression (session 15). Verifies the connection is passable, typed correctly, traversed by BFS, and that adjacent staircase moves bypass the visited-location guard.

**`TestImpassableConnection` (§B)** — Room B is behind a locked door (`is_passable=0`). Verifies it does not appear in passable neighbours, that BFS returns `reachable=False` even with visit records for all intermediate rooms, and that the connection row exists in the DB with `is_passable=0`.

**`TestWanderSuppressionPendingIntent` (§C)** — The Scholar has `pending_intent` set. Confirms the Scholar is never moved by 20 consecutive wander checks (Suppression 1).

**`TestWanderSuppressionActivity` (§D)** — Marta has an active timed meal prep activity (started=1140, duration=90, not yet expired at clock=1200). Confirms Marta is never moved by 20 wander checks (Suppression 3).

**`TestWanderSuppressionSleepiness` (§E)** — Gin-chan's sleepiness=0.72 exceeds `WANDER_SLEEPINESS_THRESHOLD` (0.60). Three tests: threshold confirmed, suppression holds for 20 checks, and (positive control) movement becomes possible once sleepiness is forced below the threshold.

**`TestActivityExpiry` (§F, §G)** — Four tests covering the full expiry cycle: activity does not clear before clock reaches `started_at + duration`; clears after advancing the clock past expiry; expiry unblocks wander suppression (verified with The Old Soldier, since Marta has `wander_probability=0.0`); a renewable activity is never auto-cleared regardless of elapsed time.

**`TestHiddenMotivationAccessControl` (§H)** — The Scholar has `hidden_motivation` set and `access_hidden_motivation=0`. Three tests: hidden_motivation exists in DB; it is absent from the Pass 1 packet (Pass 1 carries no NPC profiles at all); it is absent from the Pass 2 NPC profile even when `include_hidden=True`, because the access flag overrides.

**`TestFactionReputation` (§I)** — Verifies the `hosts_of_the_hostel` faction exists for game_id=1 and that both the Traveller (rep≈0.40) and Marta (rep≈0.90) have records. Uses `get_or_create_faction(game_id, name=...)` — note the parameter is `name`, not `faction_name`.

**`TestPassiveStateDrift` (§J)** — Curiosity, fatigue, and sleepiness drift at their configured rates over 30 minutes, with correct arithmetic. Two additional tests confirm clamping at 1.0 and 0.0.

**`TestAttitudes` (§K, §L)** — The Old Soldier's attitude toward the Traveller is −0.30 (negative path); Gin-chan's is +0.50 (positive path). Delta application test: +0.10 on −0.30 yields −0.20. Clamping tests: large positive delta clamps at 1.0, large negative at −1.0.

**`TestLocationDetail` (§M)** — Common Room has a pre-seeded `location_detail` (testing retrieval path); Kitchen has none (testing that lazy generation starts clean). Field name in `location_detail` table is `detail`, not `detail_text`.

### `tests/test_mechanics.py`

Tests subsystems that are independent of the full `GameEngine` class.

**Time formatting** — `_format_game_time()` converts minutes-past-midnight to human-readable strings: midnight, 3 AM, noon, half-past-hour, wrap at 1440, values past 1440.

**Passive state drift** — `tick_passive_states()`: zero elapsed changes nothing; positive rate increases value; negative rate decreases value; does not exceed 1.0; does not go below 0.0; NULL rate is untouched.

**In-game clock** — initial value (180 = 3:00 AM), advance adds minutes, accumulates across multiple advances, zero elapsed is a no-op, `get_active_instance()` returns the seeded instance.

**BFS pathfinding** — `_resolve_multistep_move()`: adjacent location returns `reachable=True` with correct `effective_destination_id` and `path_taken`; isolated location returns `reachable=False`; current location is handled without crashing.

---

## Tier 2 — Pass 2 Output Contract (`--llm`)

`tests/test_pass2_contract.py`

Each test builds a real Pass 2 context packet, calls the live LLM, and validates the response structure using `validate_pass2_output()` from `tests/validate.py`. These tests verify that the model respects the output contract — they do not assess narrative quality.

`validate_pass2_output()` checks: all required fields present, `outcome_type` is a known value, `elapsed_minutes` is positive, attitude and state delta magnitudes are within range, character and location IDs referenced in the output exist in the database, location changes are to adjacent locations, activity confidence values are in [0.0, 1.0].

**Current tests:**
- Speak action returns a structurally valid response.
- Move action's `location_change` (if any) targets an adjacent location.
- `elapsed_minutes` is in a plausible range (0, 60] for a social action.
- Float fields are within their specified ranges.

`validate_pass2_output()` is also the planned implementation for the §3 retry layer, which will use it to detect invalid Pass 2 responses before applying them to the database.

---

## Tier 3 — LLM-as-Judge Quality Evaluation (`--llm-eval`)

These tests make two LLM calls each: one to run the real pass, and a second judge call that evaluates the output against a rubric. The judge model defaults to `claude-haiku-4-5-20251001` for cost; override with the `DAVE_EVAL_MODEL` environment variable.

Run infrequently — after prompt template changes, or when you want to verify that a new model handles the passes acceptably before committing to it.

### `tests/test_pass1_eval.py`

Evaluates Pass 1 intent parsing quality. The judge checks: valid `action_type`, plain-English verb, move actions have a `target_location_id`, speak actions have a `target_character_id`, no hallucinated IDs, inferred goal is brief.

**Current tests:**
- `say hello to the guard` → `action_type` in (speak, interact), target resolves to Guard.
- `walk to the Hall` → `action_type=move`, `target_location_id=2`.
- `proceed to the Hall` → `action_type=move`, `target_location_id=2`. (Session 15 fix regression test: formal movement phrasing.)
- `head to the Hall` → `action_type=move`, `target_location_id=2`. (Session 15 fix regression test: informal movement phrasing.)
- `make our way to the Hall` → `action_type=move`, `target_location_id=2`. (Session 15 fix regression test: plural/collective phrasing; target is still player character alone.)

### `tests/test_pass3_eval.py`

Evaluates Pass 3 prose rendering quality. The judge checks: second-person voice, prose reflects the outcome facts, length is 3–6 sentences, no mechanical exposition (raw floats or delta values), no known verbal tic patterns, genre-appropriate register.

**Current tests:**
- Ambient outcome (no state changes) produces appropriately shaped prose.
- Emotional state update is reflected in NPC demeanour without exposing the field name.
- Verbal tic regression: `[verb] with the air/manner of someone who` does not appear.

---

## Test Worlds

### Minimal test world (`tests/fixtures/seed.py`)

Used by `test_db.py`, `test_context.py`, `test_engine.py`, and `test_mechanics.py`. A minimal two-location world seeded inline in Python. Recreated fresh for each test function via the `tmp_db` fixture.

| Entity | Details |
|---|---|
| Game | id=1, genre=adventure, tone=neutral |
| Instance | id=1, status=ready, clock=180 (3:00 AM) |
| Location 1 | Antechamber (player start) |
| Location 2 | Hall (connected to Antechamber via door) |
| Character 1 | Hero — player, at Antechamber |
| Character 2 | Guard — npc_active, at Antechamber, `wander_probability=1.0`, range=[1,2] |
| Character 3 | Hermit — npc_active, at Hall, `wander_probability=0.0` |
| Faction 1 | town_guard — Hero has reputation=0.70 |
| Internal state | Hero boredom=0.10 (+0.002/min), Guard sleepiness=0.50 (-0.003/min) |
| Attitude | Hero→Guard surface=0.60 |

Guard's `wander_probability=1.0` makes wander suppression tests deterministic — without a suppression condition active, Guard always moves.

### Hidden Hostel (`modules/hidden_hostel/seed.sql`)

Used by `test_hidden_hostel.py`. A five-location liminal fantasy inn that exercises every implemented engine feature. Loaded from the real module seed file via the `tmp_hostel_db` fixture.

| Entity | Details |
|---|---|
| Game | id=1, genre=liminal_fantasy, tone=mysterious_whimsical |
| Instance | id=1, status=ready, clock=1200 (8:00 PM) |
| Location 1 | Common Room — public, player start, pre-seeded detail |
| Location 2 | Kitchen — semi_private |
| Location 3 | Upper Corridor — semi_private, connected via **stairs** |
| Location 4 | Room A — private |
| Location 5 | Room B — private, **locked** (is_passable=0 from Upper Corridor) |
| Character 1 | The Traveller — player, Common Room |
| Character 2 | Marta — npc, Kitchen; active meal activity; wander_prob=0.0 |
| Character 3 | The Wanderer — npc, Common Room; wander_prob=0.75, range=[1,2,3] |
| Character 4 | The Scholar — npc, Room A; pending_intent set; hidden_motivation (access=0) |
| Character 5 | The Old Soldier — npc, Upper Corridor; active sharpening activity |
| Character 6 | Gin-chan — npc (winged cat), Common Room; sleepiness=0.72 |
| Faction | hosts_of_the_hostel — Traveller rep=0.40, Marta rep=0.90 |
| Attitudes | Old Soldier→Traveller −0.30; Gin-chan→Traveller +0.50 |
| Internal states | Traveller curiosity +0.001/min; Marta fatigue +0.002/min; Gin-chan sleepiness −0.001/min |

Activity expiry reference: Marta's activity expires at clock 1230 (started 1140 + duration 90). Old Soldier's expires at 1230 (started 1170 + duration 60). Both have confidence ≥ 0.60 and renewable=0, so `_check_activity_expiry()` will auto-clear them once the clock advances past 1230.

---

## Fixtures and Shared Infrastructure

**`tests/conftest.py`** — shared pytest fixtures:
- `tmp_db` — function-scoped; creates a fresh temp SQLite file, applies schema and seed, yields a `Database` instance, cleans up on teardown.
- `mock_llm` — a `MockLLMClient` pre-loaded with `PASS1_MINIMAL`, `PASS2_MINIMAL`, and `PASS3_PROSE` responses in sequence.
- `test_engine` — a fully initialised `GameEngine` backed by `tmp_db` and the mock LLM client. The mock is injected by patching `engine.llm.get_llm_client` during `__init__`, then replaced directly on the instance.
- `MockLLMClient` — configurable fake LLM. Accepts a list of responses (returned in order), a single dict (always returned as JSON), or a single string (always returned as text). Records all calls in `_call_log` for inspection.

**`tests/fixtures/responses.py`** — canned LLM responses used by both the mock client and Tier 2/3 tests as starting points. Includes `PASS1_MINIMAL`, `PASS1_MOVE`, `PASS2_MINIMAL`, and a full set of `PASS2_WITH_*` variants covering every `_apply_outcome()` code path.

**`tests/fixtures/eval_rubrics.py`** — rubric definitions and prompt builders for Tier 3 judge calls. `build_pass1_eval_prompt()` and `build_pass3_eval_prompt()` produce structured prompts that ask the judge to return a JSON verdict with per-criterion pass/fail flags, a score, and notes.

**`tests/validate.py`** — `validate_pass2_output(outcome, db, game_id)` returns a list of error strings (empty = valid). Used by Tier 2 tests and intended as the implementation for the §3 retry layer.

---

## Extending the Suite

**Adding a Tier 1 test against the minimal world:** add a method to the appropriate class in `test_db.py`, `test_context.py`, `test_engine.py`, or `test_mechanics.py`. Use the `tmp_db` or `test_engine` fixture. No markers needed.

**Adding a Tier 1 test against the Hidden Hostel:** add a method to the appropriate class in `test_hidden_hostel.py`, or add a new class there. Use the `tmp_hostel_db` fixture for DB-only tests or `hostel_engine` for tests that call engine methods. No markers needed. The fixture and character ID reference table are at the top of the file.

**Adding a Tier 2 test:** add a method to `TestPass2Contract` in `test_pass2_contract.py` with the `@pytest.mark.llm` marker already on the class. Call `self._call_pass2()` and validate with `validate_pass2_output()`.

**Adding a Tier 3 test:** follow the pattern in `test_pass1_eval.py` or `test_pass3_eval.py` — see the module docstrings for step-by-step guidance and suggested cases to add.

**When a context packet key changes:** `test_context.py` will fail, which is the intended signal. Update the test to match the new key and note the change here.

**When `_resolve_multistep_move()` return shape changes:** update `TestBFSPathfinding` in `test_mechanics.py`, `TestStaircaseConnection` and `TestImpassableConnection` in `test_hidden_hostel.py`, and the return shape description in this document.

**When a new engine feature needs Tier 1 coverage:** add the corresponding scenario to the Hidden Hostel seed (`modules/hidden_hostel/seed.sql`) and a test class in `test_hidden_hostel.py`. If the feature involves a new wander suppression condition or a new context packet field, also add a test in `test_engine.py` or `test_context.py` using the minimal world. Update `docs/module_authoring.md` if the feature introduces new seed conventions.

**Known gotcha — `get_or_create_faction` parameter name:** the method signature is `get_or_create_faction(game_id, name, description="")`. The parameter is `name`, not `faction_name`. Pass it as a keyword argument to avoid confusion.
