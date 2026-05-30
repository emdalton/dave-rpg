# DAVE RPG Engine — Implementation Status

*Living document. Update at the end of each session before committing.*
*Last updated: 2026-05-29, session 17 (open).*

---

## Session 17 opening notes (2026-05-29)

**This session:** Movement parsing test coverage; documentation updates.

**Completed this session:**

- `tests/test_pass1_eval.py`: Added three Tier 3 (`--llm-eval`) regression tests for
  the session 15 MOVEMENT PHRASES fix — `proceed to the Hall`, `head to the Hall`,
  `make our way to the Hall`. All assert `action_type=move` + `target_location_id=2`
  and pass the LLM-as-judge rubric.
- `docs/test_suite.md`: Updated Tier 3 / Pass 1 eval section to list the three new tests.

**Carried forward from session 16 / 15:**
- Phillips spelling fix (id=18 and all references) — §6 remainder
- Verbal tic review: scan Haiku transcript for `[verb] with the air of someone who`
- §7: Logging to file + transcript auto-save

---

## Session 16 closing notes (2026-05-27)

**This session:** Automated test suite — three-tier pytest architecture, full coverage
of all engine mechanics, context packet assembly, and LLM output contracts.

**Completed this session:**

- `pytest.ini`: test discovery config, pythonpath, marker registration for `llm` and
  `llm_eval` tiers. Custom CLI flags (`--llm`, `--llm-eval`) skip expensive tests by default.
- `tests/__init__.py`, `tests/fixtures/__init__.py`: package markers.
- `tests/fixtures/seed.py`: minimal two-location test world (game + instance + 2 locations
  + 3 characters + 1 faction + internal states + attitudes). All schema column names verified
  against schema.sql.
- `tests/fixtures/responses.py`: canned LLM responses for all three passes — `PASS1_MINIMAL`,
  `PASS1_MOVE`, `PASS2_MINIMAL`, `PASS2_WITH_*` variants (attitude delta, state delta,
  location change, invalid location change, faction rep, pending intent, activity set/clear,
  new character, emotional update), `PASS3_PROSE`, `EVALUATOR_RESPONSE_SCHEMA`.
- `tests/fixtures/eval_rubrics.py`: LLM-as-judge rubrics and prompt builders for Pass 1
  and Pass 3 evaluation (`PASS1_RUBRIC`, `PASS3_RUBRIC`, `build_pass1_eval_prompt`,
  `build_pass3_eval_prompt`). Defaults to `claude-haiku-4-5-20251001` for cost-efficient
  evaluation via `DAVE_EVAL_MODEL` env var.
- `tests/validate.py`: `validate_pass2_output()` — structural validation of Pass 2 JSON
  (required fields, float ranges, ID references, adjacency checks). Designed for dual use:
  test suite (Tier 2) and future §3 retry layer.
- `tests/conftest.py`: shared fixtures — `MockLLMClient` (configurable list/dict/single
  responses, call recording), `schema_sql` (session-scoped), `tmp_db` (function-scoped
  temp SQLite), `mock_llm`, `test_engine` (patches `get_llm_client` during init).
- `tests/test_db.py`: Tier 1 — schema version, game/character queries, internal states,
  passive drift, clock, attitudes, faction reputation, pending intent, activity system,
  location queries, character creation. ~25 tests.
- `tests/test_context.py`: Tier 1 — Pass 1/2/3 packet structure. All key names verified
  against actual `build_*_packet()` output (several wrong assumptions corrected during
  development: `characters_at_location` → `characters_present`, `location` →
  `current_location`, `action` → `action_record`, `faction_name` key, adjacent_locations
  nested inside `current_location` for Pass 2, name-only in Pass 3).
- `tests/test_engine.py`: Tier 1 — `_apply_outcome()` (attitude/state/emotion/location/
  faction/pending_intent/activity/new_character), `_check_activity_expiry()` (expired/
  non-expired/renewable/low-confidence), `_check_npc_wandering()` (three suppression
  conditions + positive control + expired activity does not suppress). ~25 tests.
- `tests/test_mechanics.py`: Tier 1 — `_format_game_time`, `tick_passive_states`, clock,
  BFS pathfinding. All independent of engine mock.
- `tests/test_pass2_contract.py`: Tier 2 (`--llm`) — real Pass 2 call; structural/
  mechanical assertions via `validate_pass2_output()`.
- `tests/test_pass1_eval.py`: Tier 3 (`--llm-eval`) — real Pass 1 + LLM-as-judge.
- `tests/test_pass3_eval.py`: Tier 3 (`--llm-eval`) — real Pass 3 + LLM-as-judge.

All Tier 1 mechanics verified by running assertion logic directly against the live DB
(pytest not available in sandbox; suite is ready for `pytest` on E's machine).

**To run the suite:**
```
cd ~/dev/RPG
pip install pytest          # if not already installed
pytest                      # Tier 1 only (fast, no LLM)
pytest --llm               # + Tier 2 (Pass 2 contract; requires ANTHROPIC_API_KEY)
pytest --llm-eval          # + Tier 3 (Pass 1/3 LLM-as-judge; slow and expensive)
```

**Pending from this session:**
- None. Test suite entry in lower-priority pending updated to ✅ below.

---

## Session 13 closing notes (2026-05-26)

**This session:** Schema v8 migration — timed activity system (§5a). All engine
components updated. Migration applied to live meryton.db and verified.

**Completed this session:**

- `schema/migrations/migrate_v7_to_v8.sql`: adds five `current_activity` fields
  to `character` table (idempotent; runs cleanly; v8 row inserted in `schema_version`).
- `schema/schema.sql`: bumped to v8; five activity fields with full semantic comments
  added to character table definition.
- `engine/config.py`: `ACTIVITY_AUTO_CLEAR_CONFIDENCE = 0.60` added (env-overridable
  as `DAVE_ACTIVITY_AUTO_CLEAR_CONFIDENCE`).
- `engine/db.py`: three new methods — `set_character_activity()`,
  `clear_character_activity()`, `get_characters_with_expired_activities()`.
- `engine/context.py`: `current_activity`, `activity_duration_confidence`,
  `activity_renewable` added to `_build_character_profile()`. Fields only present in
  profile when `current_activity` is non-null (avoids cluttering profiles of idle NPCs).
- `engine/engine.py`:
  - `_check_activity_expiry()` new method: mechanically clears expired activities
    once per turn, before wandering.
  - `_check_npc_wandering()`: Suppression 3 added (non-expired `current_activity`
    suppresses wander roll; expiry logic accounts for renewable, confidence, and duration).
  - `_apply_outcome()`: `activity_updates` handler added (set or clear per-NPC activity
    from Pass 2 outcome; validates confidence range and renewable flag).
  - `PASS2_PROMPT_TEMPLATE`: `activity_updates` and `npc_initiated_actions` output
    fields documented with full specification for Pass 2.
  - `_render_opening_scene()`: `activity_updates: []` and `npc_initiated_actions: []`
    added to synthetic_outcome.
- `modules/Meryton/seed.sql`: SESSION 13 block added — Sir William Lucas (id=14) and
  Mr. Hurst (id=12) seeded with canonical starting activities.
- `modules/Meryton/reset_instance.sql`: activity reset section added — clears all 19
  characters' activity fields, then re-seeds Lucas and Hurst.
- `modules/Meryton/meryton.db`: v8 migration applied and verified. Reset applied;
  both activity seeds confirmed in live DB.

**Pre-v8 prerequisite work (completed in session 12 block of session 13):**
- Cloakroom (location 14) added to location graph, seed.sql, and live DB.
- Bennet women arrival positions corrected (Jane/Mary/Mrs. Bennet → vestibule,
  Lydia/Kitty remain in ballroom).
- Mrs. Bennet description and pending_intent corrected.
- Pre-session Pass 0 captured as future feature #17.

**Pending from this session:**
- Pass 2 `npc_initiated_actions` output field (§5b): prompt already updated to
  document the field; `_apply_outcome()` logs it via action_log (no additional DB
  state needed beyond the log). No schema work required; field is live.
- `character_item` table design and implementation (§3a)
- Haiku comparison run on Meryton (task #7)
- Dance-commitment fix: Pass 2 should write `pending_intent` on both dance partners
  AND `activity_updates` for the initiator at the same time (belt-and-suspenders until
  a full dance state tracking feature is designed)

**Also completed this session (session 14, 2026-05-26):**
- `_current_game_time()` helper — fixes started_at=0 bug (three stale reads fixed)
- Character descriptions corrected and expanded: Thomas Philips (nephew→son, cousin
  to Elizabeth added), Charlotte/Sir William/Lady Lucas (family links added)
- Reciprocal attitudes seeded: Jane→Elizabeth (0.72s/0.90h), Charlotte→Elizabeth
  (0.75s). Added to reset_instance.sql.
- Pass 2 RELATIONSHIP REFERENCES rule added to PASS2_PROMPT_TEMPLATE.
- Lazy NPC creation: `db.create_character()`, `new_characters` handler in
  `_apply_outcome()`, field documented in Pass 2 prompt. Maria Lucas is first test.

**Also completed this session (session 15, 2026-05-26):**
- Haiku playtest run: `DAVE_CLAUDE_MODEL=claude-haiku-4-5-20251001` confirmed
  working; started_at=1212 correctly set; activity auto-expiry working.
- Dance duration calibration: Haiku set country dance duration=8 min (too short;
  should be 20–30). Pass 2 prompt updated: DURATION CALIBRATION block added
  giving Regency reference points for country sets, cotillions, social exchanges,
  and cards.
- Dance commitment belt-and-suspenders: Pass 2 now instructed to set
  activity_updates for BOTH player and NPC partner when dance is committed,
  AND to set pending_intent on the NPC partner. Player character now explicitly
  included in activity_updates for dance commitments (exception to prior rule).
- Movement parsing: Pass 1 prompt updated with explicit MOVEMENT PHRASES rule:
  "move to X", "walk to X", "proceed to X", "head to X", "make our way to X",
  "lead to X", "go up to X", "as we go to X" → action_type "move".

**Verbal tic status:** "[action] with the [air/manner] of someone who [clause]"
observed in Sonnet run. Haiku run not yet analysed for same pattern. Instruction
deferred until confirmed in Haiku.

**Planned next session:**
- Test lazy NPC creation: reset and playtest; ask about Maria Lucas; confirm
  new_characters fires and she appears in future context packets.
- §7: Logging to file + transcript auto-save (stdout cleanup)
- Verbal tic: review Haiku transcript; add Pass 3 anti-instruction only if needed.
- Movement parsing: ✅ Verified and covered by Tier 3 tests in session 17.

---

## Session 12 closing notes (2026-05-26)

*Session 12 was merged into session 13 (same evening). See session 13 notes above.*

---

## Session 11 closing notes (2026-05-25)

**This session:** Meryton module first playtests; engine fixes from observations;
design work on timed activity, NPC initiative, and character inventory.

**Completed this session:**

**Meryton playtest fixes:**
- Sir William Lucas starting location: Ballroom (4) → Landing (3) in seed.sql,
  reset_instance.sql, and live meryton.db. Confirmed working: he greets arrivals
  at the top of the stairs.
- `adjacent_locations` added to Pass 3 context packet in `context.py`. Both
  prompt templates updated with navigation rule (weave exits into arrival prose),
  no-repeat rule (vary imagery across turns), and tighter length guidance
  (3–4 sentences routine; 5–6 max for significant moments).
- Dance-seeking `pending_intent` seeded for all 19 characters. Confirmed
  working: John Lucas and William Goulding both responded to Elizabeth
  positioning near the forming set; Pass 2 fired NPC initiative through
  narrative judgment; faction reputation updated for composed conduct.
- I Am a Cat: `seed_v7.sql` created and applied — Guy wander_probability
  0.05 → 0.20, Mama 0.03 → 0.10, now that sleepiness suppression is in place.

**Design notes captured (implementation_status.md §5):**
- §5a: `current_activity` timed system with confidence/duration/renewable
  fields; pending question on `world_event` table deferred.
- §5b: NPC initiative via Pass 2 extension (`npc_initiated_actions` output
  field); general reaction-context principle replacing clock-based triggers.
- §5c: pending_intent seeding (completed this session).
- §5d: `is_monitoring` / Elizabeth's awareness field.

**Design notes captured (design_v05.md §2.4):**
- Player-driven detail creation: players can call plausible details into
  existence; engine allows and tracks them. Lazy creation for consumables;
  plausibility enforced by Pass 2; major items require grounding.

**Character inventory design note added (implementation_status.md §3a):**
- `character_item` join table with slot vocabulary (right_hand, left_hand,
  both_hands, mouth, worn, pocket, carried); species capacity (humans two
  hand slots, cats mouth only); lazy consumable creation; major item cost
  principle; hands_occupied open question.

**Lower-priority notes added:**
- NPC arrival awareness (wander into player's location not narrated)
- Dance state not tracked (Pass 2 invents who is dancing)

**The John Lucas incident (canonical §5a failure case):**
John Lucas committed to dancing with Elizabeth; his `pending_intent` was
correctly cleared on commitment. With nothing to suppress his wander roll,
he immediately wandered to the supper room area mid-bow, leaving Elizabeth
standing in the forming set. Pass 2 correctly adjudicated failure and updated
her pending_intent. Clear demonstration that §5a (`current_activity` with
wander suppression) is the next engine priority.

**Pending from this session:**
- §5a `current_activity` implementation — the immediate next priority
- Pass 2 prompt update: explicit `npc_initiated_actions` output field (§5b)
- Pass 2 prompt update: dance commitments must write `pending_intent` on both
  partners immediately (short-term fix pending §5a)
- `character_item` table design and implementation (§3a extension)

**Planned next session:**
- Implement §5a: `current_activity` fields on `character` (schema v8 migration),
  engine expiry/suppression logic, Pass 2 `activity_updates` output field
- Then: Pass 2 `npc_initiated_actions` output field (§5b)
- Then: Haiku comparison run on Meryton (task #7)

---

## Session 10 closing notes (2026-05-25)

**This session:** Meryton module character seeding (complete cast + dance partners),
pre-snub starting state design, reset infrastructure, and opening scene engine feature.

**Completed this session:**

**Meryton seed — character additions:**
- `Miss Bingley` and `Mrs. Hurst`: internal states added (Miss Bingley:
  `composure` 0.85, `self_satisfaction` 0.72, `social_vigilance` 0.52;
  Mrs. Hurst: `comfort` 0.78, `social_ease` 0.68); key attitudes added
  (Miss Bingley surface warmth toward Darcy; Mrs. Hurst toward husband and Bingley)
- `Sir William Lucas` (id=14): full character seed — host/facilitator role,
  mobile wander (ballroom/landing/card room), internal states, faction reputations
  for both neighborhood and bingley_circle, attitudes toward key characters
- Five named dance-partner NPCs (ids 15–19): `Mr. Robinson`, `John Lucas`,
  `Edward Long`, `Thomas Philips`, `William Goulding` — thin seeds with OCEAN
  values, 1–2 goals, faction reputations, and attitudes toward Elizabeth

**Meryton seed — starting state and context:**
- Pre-snub starting state adopted: scene opens as Elizabeth arrives at the
  vestibule (location 1), not mid-assembly. Elizabeth↔Darcy attitudes reset
  to 0.0 (strangers on arrival); Darcy `emotional_state` updated to `reserved`;
  his `hidden_motivation` cleared (interest develops during play)
- Elizabeth `character_visited_location` cleared (arriving now)
- Elizabeth's `bingley_circle` reputation updated to 0.05 (unknown on arrival)
- `game.cultural_norms` updated with two new keys: `gentlemen_scarcity`
  (assembly imbalance, European wars context) and `local_families` (nearby
  properties and known family names for Pass 2 world-building)
- `Mr. Bennet` confirmed absent — stays home; not seeded

**Meryton module infrastructure:**
- `modules/Meryton/reset_instance.sql` created — resets all dynamic state
  (character locations, emotional states, pending_intent, internal states,
  attitudes, faction reputations, visited locations, game_instance clock)
  to canonical vestibule-start values without wiping the database.
  Wrapped in a transaction; action_log cleared by default (comment out to preserve history).
  Usage: `sqlite3 modules/Meryton/meryton.db < modules/Meryton/reset_instance.sql`
- `meryton.db` re-seeded fresh from `schema/schema.sql` + `seed.sql`

**Engine:**
- `OPENING_SCENE_PROMPT_TEMPLATE` added to `engine.py` — distinct from
  `PASS3_PROMPT_TEMPLATE`; instructs the renderer to establish the opening
  scene rather than narrate an action outcome
- `_render_opening_scene()` method added to `GameEngine` — runs a single
  Pass 3 call with a synthetic ambient outcome at session start; LLM failure
  degrades gracefully to the old "You are [name]" fallback
- `run()` updated to call `_render_opening_scene()` instead of printing bare name
- Second-person rule ("the player character is 'you', not named by name") added
  explicitly to both `OPENING_SCENE_PROMPT_TEMPLATE` and `PASS3_PROMPT_TEMPLATE`
- Opening scene confirmed working on I Am a Cat; prose quality strong on first run

**Pending from this session:**
- `character_design.md` is missing Sir William Lucas — minor documentation debt;
  add his entry before the Netherfield Ball design work begins

**Planned next session:**
- Re-seed Guy and Mama `wander_probability` to honest values in I Am a Cat
  (carried from session 9; sleepiness suppression now handles the rest)
- First Meryton engine test / playtest against `meryton.db`

---

## Session 9 closing notes (2026-05-24)

**This session:** Engine v7 changes, schema.sql canonicalization, and module
database setup. All seven §1a engine items completed.

**Completed this session:**

**Schema fixes:**
- `schema.sql` corrected — v2 columns missing from the canonical file were
  added: `is_involuntary`, `involuntary_trigger_type`, `involuntary_trigger_param`,
  `involuntary_event_description` on `internal_state`; `intrinsic_motivation` on
  `character_skill`. These were in the migration chain but had not been folded
  in when schema.sql was made canonical.
- `schema.sql` now inserts a schema_version row at the bottom so fresh-install
  databases correctly report MAX(version)=7.
- `migrate_v6_to_v7.sql` made idempotent: `CREATE TABLE IF NOT EXISTS`,
  `CREATE INDEX IF NOT EXISTS`, and `WHERE NOT EXISTS` guard on the
  schema_version INSERT. `ALTER TABLE ADD COLUMN` statements still emit a
  harmless message on re-run (SQLite has no IF NOT EXISTS for columns).
- Migration script headers for v1→v2 updated to match the canonical-file
  convention established in v2→v3 and v3→v4.

**Module databases:**
- `modules/i_am_a_cat/i_am_a_cat.db`: v7 was already applied in a prior
  session. Cleaned up duplicate schema_version v7 row. No further migration needed.
- `modules/Meryton/meryton.db`: created fresh from `schema/schema.sql` +
  `modules/Meryton/seed.sql`.

**Engine v7 changes (all §1a items):**
- `db.py`: four new methods — `get_character_faction_reputations`,
  `update_faction_reputation`, `get_or_create_faction`,
  `update_character_pending_intent`. Also: `get_location_connections` now
  returns `passage_note`.
- `context.py`: `faction_reputations` added to player profile block in
  `build_pass2_packet`; `pending_intent` added to `_build_character_profile`
  (appears for player and all NPCs); `passage_note` included in
  `adjacent_locations` when non-null.
- `engine.py`: Pass 2 prompt template documents `faction_reputation_changes`
  and `pending_intent_updates` output fields; `_apply_outcome` handles both;
  `_check_npc_wandering` suppresses wander roll when `pending_intent` is
  non-null or sleepiness ≥ threshold.
- `config.py`: `WANDER_SLEEPINESS_THRESHOLD = 0.60` (env-overridable as
  `DAVE_WANDER_SLEEPINESS_THRESHOLD`).

**Pending from this session:**
- Re-seed Guy and Mama's `wander_probability` to honest values now that
  sleepiness suppression is implemented — currently near-zero as a proxy for
  the missing suppression.

**Planned next session:**

- Tweak I Am a Cat `wander_probability` for Guy and Mama (seed_v3.sql or
  direct DB update) — now safe to use honest values; sleepiness suppression
  handles the rest
- Begin engine testing against Meryton DB (first Meryton play session or
  targeted action testing)

---

## Session 8 closing notes (2026-05-24)

**This session:** Repository reorganization and schema v7 migration. No engine
code written; no seed work yet.

**Completed this session:**

- Repository file organization established (see design decisions below)
- `schema/migrations/migrate_v6_to_v7.sql` written — faction tables,
  passage_note, pending_intent
- `schema/schema.sql` updated to reflect full v7 state (location_connection
  appended; pending_intent in character; faction and
  character_faction_reputation appended)

**Key design decisions this session:**

- `references/` directory created and gitignored. Local research copies
  (Wikipedia pages, source texts, images) are not published. Each module
  has a committed `references.md` in its module directory listing sources
  with URLs — this is the published record of what was consulted.
- Reference subdirectories: `references/regency/` (general Regency-era
  material, reusable across modules), `references/pride-and-prejudice/`
  (novel text and character articles), `references/netherfield-ball/`
  (Basildon Park / Netherfield location research),
  `references/meryton/` (assembly rooms location research, floorplan).
- `docs/regency_dance_mechanics.md` moved from Netherfield_Ball module
  folder; noted as engine-level design though somewhat module-specific —
  may be subsumed into Meryton/Netherfield_Ball docs later.
- Faction allegiance is modeled via MST goals in `character_goal` (e.g. a
  'belonging' goal scoped to a specific faction by its description), not as
  a separate field. `character_faction_reputation` tracks how a faction views
  a character; allegiance (how the character relates to the faction) is
  motivational and belongs in the goal framework.
- Factions may be created dynamically during play (new family unit on
  marriage, political alliances, etc.) — the schema supports this without
  modification; Pass 2 issues a `create_faction` outcome and the engine
  inserts the row before applying reputation changes.
- Directory naming convention for new directories: lowercase kebab-case.
  Existing module directories (Netherfield_Ball, Meryton) retain mixed case;
  rename deferred.

---

## Session 7 closing notes (2026-05-24)

**This session:** Meryton module design — location graph, character seeding,
faction system design. No engine code written.

**Completed this session:**
- `engine/__main__.py` added (carried over from session 6)
- Playtest transcript reviewed; prose quality confirmed strong on Haiku
- Module directory renamed from `Netherfield_Ball` to `Meryton` (reflects
  broader scope: Chapter 3 assembly first, Netherfield Ball as Chapter 2)
- `regency_dance_mechanics.md` — dance card rules, set structure, supper
  dance significance, social observation as gameplay
- `location_graph_sketch.md` — 10 locations; 6 navigable, 4 non-passable;
  barrier types distinguished (locked vs. convention); connections summary;
  open questions resolved against chapter_03.txt
- `character_design.md` — OCEAN values, motivations, starting emotional
  states, internal states for full Chapter 3 cast
- `faction_design.md` — faction system schema design; proposed tables
  (`faction`, `character_faction_reputation`); engine changes required;
  starting reputation values for Elizabeth

**Key design decisions this session:**
- Chapter 3 (first Meryton assembly) precedes Netherfield Ball as Chapter 1
  of the module — more player agency, unformed relationships, introduction
  mechanic exercised
- Factions designed now rather than retrofitting: `bennet_family`,
  `meryton_neighborhood`, `bingley_circle` for Chapter 3
- Darcy's Openness is the primary arc float; player may shift it faster than
  canonical — this is an intentional test of the mechanic
- NPC behavior is honest to character, not constrained to canonical plot
  outcomes; minor catastrophes emerge from seeded values (Lydia C=0.08,
  Mrs. Bennet N=0.88)
- `passage_note` TEXT field needed on `location_connection` to distinguish
  locked vs. convention barriers
- Supper room present but unused at Chapter 3; activates in Chapter 2

**Planned next session:**
- Schema migration for faction tables (new version, after v6)
- `passage_note` field on `location_connection`
- Begin seed.sql for Meryton Chapter 3
- Read chapter_17_18.txt for Netherfield Ball character/location analysis

---

## Session 6 closing notes (2026-05-23)

**This session:** Playtest with a friend (skilled programmer, cat person, Fate system fan).

**Playtest outcome:**
- Rating: "Very amusing"
- The playtester said it reminded them of good games played on a MUSH — specifically that it "passes the Turing test" in that context. This is a strong signal from a MUSH veteran that the three-pass architecture is achieving its intended effect.

**Design threads raised by the playtester:**

1. **MUSH integration** — The playtester proposed wiring DAVE to a MUSH to allow networked play. The engine's architecture is a natural fit (stateless turn loop, DB as canonical state). The main gap is concurrent multi-session support; the v7 instance/session split is the prerequisite. See `future_features.md` for the full design note (feature 8).

2. **Module candidates from licensed/public-domain IP:**
   - *Amber Chronicles* (Roger Zelazny) — the playtester believes the estate has authorized use in MUSH-style games; needs verification before investing design effort. Still under copyright (Zelazny died 1995). See `future_features.md` for IP caution note.
   - *Barsoom* (Edgar Rice Burroughs) — strong module candidate. Early novels (from 1912) are US public domain. ERB Inc. holds trademarks and is active; situation is more complex than copyright alone but more tractable than Amber. See `future_features.md`.

**Completed this session:**
- Added `engine/__main__.py` so the engine can be launched with `python -m engine`
- Ran `reset_instance.sql` to restore 3:00 AM starting state before playtest

**Planned next session:** Prioritize based on playtest observations. Consider:
- NPC pending intent (§1) — likely most impactful for multi-turn social exchanges
- Characters nearby / perception range fix — affects how interesting the world feels when NPCs are off-screen

---

## Session 5 closing notes (2026-05-22)

**Completed this session:**
- Gender + pronouns schema (v6 migration), seeded for all I Am a Cat characters
- `characters_referenced` in Pass 3 context (pronoun consistency)
- `characters_present` in Pass 3 context (NPC presence authority)
- NPC authority rules added to both Pass 2 and Pass 3 prompt templates
- Pass 2 `location_change` spec strengthened: movement consistency rule +
  NPC authority note (only issue entries for NPCs in characters_at_location)
- Token usage logging per call + session total with cost estimate (claude.py)
- Named-location move pre-apply fix: all moves now go through
  `_resolve_multistep_move` regardless of adjacency; staircase navigation fixed
- `reset_instance.sql` written for clean game resets
- Design notes captured: validation/retry layer (§3), item_location_change +
  lazy item discovery + NPC item movement (§3a), pending_intent (§1),
  hunger-driven wake mechanic (§2)
- CLAUDE.md updated with "Engine owns all state; LLM does not" principle

**Active LLM backend clarification:** The game is being run on Haiku (not
Sonnet), which serves as a working lower bound for Phase 2 local model
feasibility. If I Am a Cat is playable on Haiku, a well-prompted Mistral 7B
or similar local model is a realistic target. An alternative deployment path —
Haiku-hosted with Patreon access to cover API costs — was discussed and is
viable. The three-pass architecture makes backend swapping transparent to the
rest of the engine.

**Planned next session:** Playtest with a friend (skilled programmer,
cat person, Fate system fan) on laptop. Run `reset_instance.sql` before the
session to restore 3:00 AM starting state. The playtester may have design suggestions —
Fate's approach to player agency and outcome granularity (succeed at a cost, etc.)
is potentially relevant to Pass 2 outcome types. Worth discussing after the playtest.

⚠️ **Before next play session:** Run `reset_instance.sql` to reset the clock and
all character state. Current game clock has drifted to ~7:00 AM from testing.

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
├── references/                — gitignored; local research copies for module
│   │                            development. Each module has a committed
│   │                            references.md listing sources with URLs.
│   ├── regency/               — general Regency-era material (reusable)
│   ├── pride-and-prejudice/   — P&P novel text and character articles
│   ├── netherfield-ball/      — Basildon Park / Netherfield location research
│   └── meryton/               — Meryton assembly rooms research, floorplan
├── modules/
│   ├── i_am_a_cat/
│   │   ├── i_am_a_cat.db      — live SQLite database for this module
│   │   ├── seed.sql           — full seed data (characters, locations, items, etc.)
│   │   ├── seed_v3.sql        — v3 additions (location_connection; NPC wander params)
│   │   ├── seed_v4.sql        — v4 additions (character_visited_location for Toulouse)
│   │   ├── seed_v5.sql        — v5 additions (game_instance record; passive rates)
│   │   ├── seed_v6.sql        — v6 additions (gender + pronouns for all characters)
│   │   └── sample_transcript_01.md  — first full play session transcript
│   ├── Meryton/               — active module; Chapter 3 (first Meryton assembly)
│   │   ├── meryton.db              — live SQLite database (schema.sql + seed.sql)
│   │   ├── seed.sql                — full module seed (13 locations, 13 chars, 3 factions)
│   │   ├── character_design.md     — OCEAN, motivations, emotional states for cast
│   │   ├── faction_design.md       — faction system design and starting reputations
│   │   ├── location_graph_sketch.md — 13 locations; connections, barrier types, passage_notes
│   │   └── references.md           — committed list of sources with URLs
│   └── Netherfield_Ball/      — future chapter placeholder (P&P Ch. 18);
│                                 dormant until inter-chapter carry is designed
├── schema/
│   ├── schema.sql             — canonical fresh-install schema through v7; run this
│   │                            + seed.sql only for new databases (no migrations needed)
│   └── migrations/
│       ├── migrate_v1_to_v2.sql
│       ├── migrate_v2_to_v3.sql
│       ├── migrate_v3_to_v4.sql
│       ├── migrate_v4_to_v5.sql
│       ├── migrate_v5_to_v6.sql
│       └── migrate_v6_to_v7.sql   — idempotent (IF NOT EXISTS throughout)
└── tests/                     — pytest suite; three tiers (see session 16 notes)
    ├── conftest.py            — shared fixtures (MockLLMClient, tmp_db, test_engine)
    ├── validate.py            — validate_pass2_output() (also §3 retry layer candidate)
    ├── test_db.py             — Tier 1: Database method tests
    ├── test_context.py        — Tier 1: context packet assembly tests
    ├── test_engine.py         — Tier 1: _apply_outcome, expiry, wander suppression
    ├── test_mechanics.py      — Tier 1: time formatting, passive drift, clock, BFS
    ├── test_pass2_contract.py — Tier 2 (--llm): Pass 2 structural contract
    ├── test_pass1_eval.py     — Tier 3 (--llm-eval): Pass 1 LLM-as-judge
    ├── test_pass3_eval.py     — Tier 3 (--llm-eval): Pass 3 LLM-as-judge
    └── fixtures/
        ├── seed.py            — minimal two-location test world
        ├── responses.py       — canned LLM responses for all three passes
        └── eval_rubrics.py    — PASS1_RUBRIC, PASS3_RUBRIC, prompt builders
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

**v7** — `faction` table (module-scoped named social groups with LLM-facing
descriptions). `character_faction_reputation` table (character standing with
a faction, 0.0–1.0, updated by Pass 2 `faction_reputation_changes` outcome
field). `passage_note` TEXT NULL on `location_connection` (semantic barrier
description for Pass 2 — distinguishes physically locked from
convention-closed connections). `pending_intent` TEXT NULL on `character`
(working-memory slot for deferred social obligations; set/cleared by Pass 2
`pending_intent_updates` outcome field).

**v8** — Timed activity system on `character`: five new fields —
`current_activity` TEXT NULL (natural language description of ongoing activity),
`activity_started_at` INT NULL (game clock minute at apply time, set by engine),
`activity_estimated_duration` INT NULL (estimated minutes; NULL = open-ended),
`activity_duration_confidence` REAL NULL (0.0–1.0; drives auto-expiry logic),
`activity_renewable` INT NOT NULL DEFAULT 0 (1 = persists past estimated end).
Engine: `_check_activity_expiry()` clears expired non-renewable high-confidence
activities each turn. `_check_npc_wandering()` Suppression 3 holds NPCs in place
during non-expired activities. Pass 2 `activity_updates` output field sets,
updates, or clears activities. Motivation: John Lucas incident (session 11) — NPC
wandered mid-dance when pending_intent was cleared on commitment. See §5a.

**Current version: 8.**

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
| Timed activity system (§5a) | ✅ Complete | `current_activity` on `character` (v8); wander Suppression 3; `_check_activity_expiry()`; Pass 2 `activity_updates` |
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

### §6. Meryton character description and relationship review

Revealed by 2026-05-26 playtest. Substantially completed session 16 (2026-05-29).

**Completed (session 14):** Thomas Philips description corrected (nephew → son,
Elizabeth's first cousin); Charlotte, Lady Lucas, Sir William descriptions updated
with family links; Pass 2 RELATIONSHIP REFERENCES rule added to prompt.

**Completed (session 16):** Maria Lucas (id=20) added; Jane→Elizabeth and
Charlotte→Elizabeth attitudes backfilled into seed.sql; reset_instance.sql
updated throughout for id=20.

**Remaining — spelling error:**
- The correct spelling is "Phillips" (Mrs. Bennet's sister is Mrs. Phillips, the
  attorney's wife). The character name, descriptions, and all seed references
  currently use "Philips" (one l). Affects: character name (id=18), all
  description strings referencing Mr./Mrs. Philips, seed.sql, reset_instance.sql,
  and the live meryton.db. A straightforward find-and-replace but touches many
  lines — do as a dedicated pass before next public playtest.

---

### §7. Logging and transcript output (next session)

Revealed by 2026-05-26 playtest. httpx INFO messages and engine log lines
currently appear inline with game prose, breaking immersion. Transcripts of
good play sessions are worth saving automatically.

**Logging cleanup:**
- In `engine/engine.py` `main()`: add a `logging.FileHandler` writing to
  a timestamped log file (e.g. `logs/meryton_YYYYMMDD_HHMMSS.log`).
- Suppress `httpx` INFO to WARNING: `logging.getLogger("httpx").setLevel(logging.WARNING)`.
- Set stderr handler to WARNING or ERROR so only genuine problems reach the
  terminal during play. Engine debug/info goes to file only.
- `DAVE_LOG_LEVEL` env var continues to control file log verbosity.

**Transcript save:**
- Add `--transcript` flag (or `DAVE_TRANSCRIPT_PATH` env var) to `main()`.
  If set, engine writes all player-visible prose (opening scene + all Pass 3
  output) to the specified file, one turn per entry with a turn separator.
- If no path given, auto-generate a timestamped filename in `transcripts/`
  and write there by default (so a transcript is always saved).
- Player input lines should also be captured (with `> ` prefix) so the
  transcript reads as a dialogue, not just responses.

---

### ✅ Schema v7: faction, character_faction_reputation, passage_note, pending_intent (completed sessions 8–9)

Migration written (`schema/migrations/migrate_v6_to_v7.sql`) and made idempotent.
`schema/schema.sql` is canonical through v7. Applied to `i_am_a_cat.db`; Meryton
DB created fresh. All engine changes wired (see §1a below — all completed).

---

### ✅ §1a. Engine changes for v7 fields (completed session 9)

All seven items complete:

1. `_apply_outcome()` handles `faction_reputation_changes` — applies deltas,
   clamps to [0.0, 1.0], updates `notes`, uses `get_or_create_faction` for
   dynamic faction creation during play.
2. `_apply_outcome()` handles `pending_intent_updates` — sets or clears
   `pending_intent` on named character rows.
3. `context.py` Pass 2 packet: `faction_reputations` in player profile block
   (faction slug, reputation, notes, description).
4. `context.py` Pass 2 packet: `pending_intent` in every character profile
   via `_build_character_profile()`.
5. `context.py`: `passage_note` included in `adjacent_locations` when non-null.
6. Pass 2 prompt template documents both new output fields.
7. Wander loop: suppressed when `pending_intent` non-null (social commitment).
8. Wander loop: suppressed when sleepiness ≥ `WANDER_SLEEPINESS_THRESHOLD`
   (0.60, env-overridable). I Am a Cat sleeping NPCs can now be re-seeded
   with honest base wander values.

**Still pending:** Re-seed Guy and Mama `wander_probability` to honest values.

---

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

**Character inventory / held items**: The engine currently has no concept of a
character holding an item. Items exist at locations only. There is no character-
item relation. Consequence: when Elizabeth picks up two glasses of negus and
gives one to Charlotte, none of this is written to the DB — the glasses don't
exist as items, the engine doesn't know their hands are occupied, and no spill
risk is tracked. Observed in Meryton playtest session 11.

**Decided design:**

A `character_item` join table (not a `held_by` field on `item` — the join table
supports multiple carried items per character and a slot/grip system):

```sql
character_item (
    character_id  INT  NOT NULL,
    item_id       INT  NOT NULL,
    slot          TEXT NOT NULL,  -- see slot vocabulary below
    acquired_at   INT  NULL       -- game clock minutes; for duration/expiry tracking
)
```

Slot vocabulary (initial set; extendable per module):
- `right_hand`, `left_hand` — explicitly in hand; enforce species capacity
- `both_hands` — two-handed grip (rifle, large object); occupies both slots
- `mouth` — for species without hands (cats carrying toys; dogs fetching)
- `worn` — clothing, scabbard, holster; accessible but not in hand
- `pocket` — small items not actively held
- `carried` — generic for items that don't fit the above

Species carrying capacity is defined per character (or per species default):
humans have two hand slots; cats have no hand slots but one mouth slot. The
engine enforces slot conflicts — D'Artagnan with a sword in `right_hand` cannot
also hold a pistol in `right_hand`. He can have a pistol in `left_hand`, or a
holstered pistol in `worn`.

Pass 2 output: `item_pickup` / `item_drop` / `item_give` events (or extend
`item_location_change` to include `slot` and `recipient_id`). Engine validates
slot availability before applying.

**Lazy item creation for consumables**: glasses of negus, letters, fans, dance
cards, candles — not seeded. Pass 2 generates them on first meaningful
interaction; the engine writes them to `item` + `character_item` canonically
(same pattern as `location_detail`). Until created, they exist only as
narrative. This generalises: most minor props in any module need not be pre-
seeded. The world fills in on contact.

**Major items may require narrative justification**: A sword, a significant sum
of money, a horse — these should either be pre-seeded (they exist in the world
and can be found or bought) or require a Fate-point-style narrative cost to
introduce mid-play. The exact mechanism is deferred; the principle is that
minor consumables appear lazily for free, while major or plot-significant items
need grounding. This connects to future Fate-inspired outcome types (succeed at
a cost, introduce a complication).

**`carried_items` in Pass 2 character profile context**: once the table exists,
the engine includes each character's carried items (slot + item name/description)
in their profile block. Pass 2 then knows hands are occupied and can adjudicate:
spill risk if bumped, the need to set a glass down before joining a set, a sword
in hand as implicit threat in a confrontation, a letter in pocket as
conversational leverage.

**Open question — hands_occupied tracking**: whether "hands occupied" is best
represented as a derived engine computation (count items in hand slots, compare
to species capacity) or as an explicit boolean/integer state visible in context.
Leaning toward derived — the slot system makes it computable — but the exact
form in the Pass 2 context packet is not yet decided.

This is a natural extension of §3a below and should be designed together with it.

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

### ✅ §5. Timed activity system (`current_activity`) — v8 (completed session 13, 2026-05-26)

*Design developed in Meryton playtest session 11 (2026-05-25). Implemented session 13.
Addresses: dance state not tracked; NPCs not taking autonomous social action; Elizabeth
unable to monitor characters she cares about without explicitly asking.*

#### ✅ 5a. `current_activity` fields on `character`

Four new fields:

```sql
current_activity          TEXT NULL,   -- natural language: "dancing with Thomas Philips"
activity_started_at       INT  NULL,   -- game clock minutes when activity began
activity_estimated_duration INT NULL,  -- minutes; NULL = genuinely open-ended
activity_duration_confidence REAL NULL, -- 0.0–1.0: how precisely to enforce expiry
activity_renewable        INT  NOT NULL DEFAULT 0  -- 1 = persists past expiry unless interrupted
```

Engine expiry behavior driven by confidence and renewable flag:

- **High confidence, non-renewable** (dance set: duration=30, confidence=0.90,
  renewable=0): engine clears the activity mechanically when
  `activity_started_at + activity_estimated_duration <= current_time_minutes`.
  No LLM judgment needed; the music stops.
- **Low confidence, renewable** (conversation: duration=20, confidence=0.15,
  renewable=1): engine does not auto-clear at expiry. Activity persists until
  Pass 2 explicitly clears it (via `activity_updates` with `activity: null`)
  or a new activity overwrites it. The duration is a rough estimate only.
- **Moderate, non-renewable** (fetching punch: duration=5, confidence=0.60,
  renewable=0): clears mechanically; duration is approximate but bounded.

Interruption always goes through Pass 2 regardless of confidence or renewability:
Pass 2 issues `activity_updates` with `activity: null` to clear.

Pass 2 output field:
```json
activity_updates: [{character_id, activity, duration_minutes, confidence, renewable}]
```
Engine computes `activity_started_at` from current game clock at time of apply.

Wander suppression: characters with a non-expired `current_activity` do not roll
for wander. This replaces the current `pending_intent`-based suppression for
activity-bound cases (pending_intent remains for social obligations).

**Lazy generation**: `current_activity` is NULL by default. Pass 2 generates it
on demand when Elizabeth observes a character. Once written, it is canonical until
it expires or is overwritten. Elizabeth does not need to know what Lady Lucas is
doing until she looks; once she does, that becomes durable world state.

**Pending question — `world_event` table**: Activities generated by Pass 2 are
already captured in the `action_log` via the `pass2_outcome` JSON column. For
characters to discuss past events ("did you not dance with Mr. Robinson earlier?"),
those events need to be surfaceable in the Pass 2 context at relevant moments.
The existing `recent_actions` window in the Pass 2 packet handles this for the
short term. The open question is whether a separate `world_event` table is
warranted — indexed by character and game time, queryable by Pass 2 context
builder when assembling character profiles — or whether compressing the action_log
(already in the lower-priority pending list) is sufficient. Decision deferred;
do not implement `world_event` until the action_log compression strategy is clear.

---

#### 5b. NPC initiative via Pass 2 extension ("reaction context") — prompt live as of session 13

**Current limitation**: NPCs only act in response to player input. Thomas Philips
approaching Charlotte to dance was described in Pass 3 prose (triggered by the
player mentioning Charlotte), but was never a real engine event — no
`activity_update` was written, so it was immediately lost. Elizabeth will never
be asked to dance unless she engineers it herself.

**Design principle**: Pass 2 already has everything needed to resolve NPC initiative
— it has the characters at the location, their pending_intents, attitudes, and
the just-adjudicated outcome. The right approach is to extend Pass 2's output to
include NPC-initiated actions in the same call, not to introduce a separate trigger
mechanism or clock-based pass.

The analogy: when a tabletop GM says "the dancing is starting," they
automatically check whether any NPC asks a player character to dance. When a
barroom brawl breaks out, they check who is drawn in. These are not separate
clock events — they are natural reactions to outcomes that the GM resolves in the
same beat.

**Implementation**: Add `npc_initiated_actions` to the Pass 2 output schema:

```json
npc_initiated_actions: [
  {
    "character_id": 18,
    "action": "asks Charlotte Lucas to dance",
    "target_id": 5,
    "activity": "dancing with Charlotte Lucas",
    "duration_minutes": 30,
    "confidence": 0.90,
    "renewable": false
  }
]
```

The Pass 2 prompt gets a new instruction: after adjudicating the player's action,
check whether any NPCs in the scene have `pending_intent` values that the current
situation would activate — a dance starting, a social introduction, a notable
event anyone present would react to. Resolve these as `npc_initiated_actions`.
The engine writes the resulting `activity_updates` and `pending_intent_updates`
exactly as it would for player-driven outcomes.

**"In range" scope**: For now, `characters_present` (same location as player)
is the reaction pool. As `characters_nearby` is added (see lower-priority pending),
loud or notable events can expand the reaction pool to adjacent locations. The
scope passed to Pass 2 defines the range: a quiet personal interaction affects
only those present; a scene-wide event (the music starting, a commotion) can
in principle reach the whole ballroom.

**NPC initiative is not exhaustive**: Not every pending_intent fires every turn.
Pass 2 exercises the same narrative judgment a GM does — it activates NPC
initiative when the situation makes it natural. A young man with "wants to dance"
pending_intent does not ask someone to dance every single turn; he waits for the
right moment (a set forming, a lull in his conversation, an introduction).
Seeding honest pending_intents and trusting Pass 2's judgment is the intended
design. We are not building a full NPC behavior tree.

**Player time-advance action**: New Pass 1 action type `wait`. "I sit out this
dance," "I wait for the end of the set" — Pass 2 advances the clock by the
remaining time on the most relevant active activity in context (or ~30 minutes
for a dance set). Passive state drift applies; expired activities are cleared;
NPC initiative runs as part of the same Pass 2 call, so the "end of set" moment
produces partner reassignments naturally.

---

#### 5c. `pending_intent` seeding for social behavior

**Immediate fix (no schema change)**: Seed dance-seeking `pending_intent` values
in `modules/Meryton/seed.sql` and `reset_instance.sql` for all characters who
should be seeking partners. Suggested values:

- All young women present (Elizabeth, Jane, Lydia, Kitty, Charlotte):
  `"wants to dance; will accept a partner if asked"`
- Young men present (Bingley, Robinson, John Lucas, Edward Long, Thomas Philips,
  William Goulding): `"wants to dance; will seek a partner when a new set is called"`
- Darcy: leave NULL or `"present but not intending to dance with strangers"` —
  his refusal is canonical and his eventual asking of Elizabeth is the dramatic arc
- Mary: `"content to observe; will dance if asked but will not seek it"`
- Mrs. Bennet / Lady Lucas / Mrs. Hurst: social spectators; no dance intent

This is a seed change only and can be applied before the NPC action round is
built. It seeds the state the engine will eventually act on, and gives Pass 2
something accurate to work with in the meantime when describing NPC behavior.

---

#### 5d. `is_monitoring` — Elizabeth's awareness field

Elizabeth naturally tracks certain characters more closely than others. Jane's
situation with Bingley, her younger sisters' behavior, Charlotte's evening — these
are things Elizabeth observes passively, not just when she explicitly looks.

**Design**: A `monitoring_targets` JSON field on the player character (or a
`character_monitoring` table if multiple observers are needed later):

```json
monitoring_targets: [
  {"character_id": 4, "reason": "sister; Jane's interest in Bingley"},
  {"character_id": 3, "reason": "Bingley; relevant to Jane"},
  {"character_id": 5, "reason": "close friend"},
  {"character_id": 7, "reason": "sister; Lydia requires supervision"},
  {"character_id": 8, "reason": "sister"}
]
```

The engine includes monitored characters' `current_activity` in the Pass 2 context
even if they are not at Elizabeth's current location — a lightweight ambient
awareness. Pass 2 can incorporate notable monitored events into the narrative beat
without the player having to ask ("across the room, you notice Jane is still with
Bingley"). This is not the same as `characters_nearby` (which is proximity-based);
it is an explicit attention model for the player character.

Seeding: `monitoring_targets` is a module-specific player configuration, set in
`seed.sql` and reset by `reset_instance.sql`. Elizabeth's targets above are the
canonical Meryton Chapter 3 set.

Schema: add `monitoring_targets TEXT NULL` (JSON) to `character`. Alternatively,
defer as a JSON key inside a future `player_config` field. No new table needed
for Phase 1.

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
- **Dance state not tracked — Pass 2 invents who is dancing**: The engine has
  no concept of "dancing" vs. "sitting out." When Pass 2 describes an NPC
  approaching a partner to dance, that narrative is not written to the DB.
  One wander roll later, the committed dancers have physically separated and
  Pass 2 has no memory of the pairing — it re-invents the floor state from
  scratch each turn using Austen context. Observed in Meryton session 11:
  Thomas Philips described as approaching Charlotte to dance, then wandered
  away, then both were described as sitting out.
  Short-term fix: add explicit Pass 2 prompt guidance that dance commitments
  must be written as `pending_intent` entries on both characters when
  established (e.g. `"dancing this set with Charlotte Lucas"`), and that
  wander is suppressed for characters with a dance-related pending_intent.
  Longer-term fix: proper dance card mechanic (see Netherfield Ball design
  notes, section C) — a structured per-set commitment table. The
  `pending_intent` workaround is sufficient for Meryton Chapter 3 playtesting
  but will not scale to the Netherfield Ball's choreographed evening structure.
- **NPC arrival awareness**: When an NPC wanders into the player's current
  location, the player currently has no way of knowing until they explicitly
  look around. Fix: in `_check_npc_wandering()`, track which NPCs moved into
  the player's location on that pass; include a `newly_arrived_npcs` list in
  the Pass 2 context packet; add a prompt note that Pass 2 may incorporate
  notable arrivals into the narrative beat based on salience and room
  crowdedness (Darcy entering is hard to miss; a minor dancer in a packed
  ballroom might slip by). No schema change needed. First observed in Meryton
  playtest session 11 (2026-05-25).
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
- ✅ **Test suite**: Implemented session 16 (2026-05-27). Three-tier pytest
  architecture in `tests/`. Tier 1 (no LLM): db.py, context.py, engine mechanics
  (~75 tests). Tier 2 (`--llm`): Pass 2 structural contract via `validate_pass2_output()`.
  Tier 3 (`--llm-eval`): LLM-as-judge evaluation for Pass 1 intent parsing and Pass 3
  prose. `validate_pass2_output()` in `tests/validate.py` is also the planned
  implementation for the §3 retry layer.

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

---

## Netherfield Ball — pre-implementation design tasks

*Added 2026-05-23. Design work required before schema or seed work begins.*

The Netherfield Ball module will exercise mechanics that I Am a Cat deliberately
avoided. The following design questions must be resolved before coding starts.
None of these are scoped yet; this is a checklist to work through in order.

### A. Source document analysis

Primary sources for schema design:

- **P&P Chapters 17–18** — the Netherfield Ball itself. Extract from the full
  text already in `modules/Netherfield_Ball/`. Chapter 17 is setup; Chapter 18
  is the event. These establish the event sequence, who dances with whom, when
  supper occurs, and the social confrontations that constitute the module's
  dramatic spine.
- **P&P Chapter 3** — the first Meryton assembly. Establishes prior relationship
  state (Darcy's snub, Elizabeth's first impression) that all characters carry
  into the Netherfield Ball.
- **Basildon Park floorplan** — already in `References/`. Room layout and
  connections drive the location graph. Map rooms to game locations before
  seeding.
- **Character Wikipedia articles** — already in `References/`. Use for seeding
  OCEAN traits and motivations *at the time of the Netherfield Ball*, before
  later revelations. Darcy's attraction is present but suppressed; Wickham's
  agenda is entirely hidden from Elizabeth.
- **Ball (dance event) article** — already in `References/`. Verify that it
  covers the mechanically-relevant Regency specifics: partner commitment for a
  full set, the rule that declining a set means sitting it out entirely, supper
  partner conventions, significance of first and last dances.

The LLM can be relied on for general Regency customs, fashion description,
period food, and period-appropriate dialogue without explicit seeding. Austen
is among the most thoroughly trained-on authors; the Netherfield Ball
specifically is well-covered. Add reference material only where gameplay
mechanics require canonical specificity.

### B. Reputation and faction system design

I Am a Cat has no faction or reputation mechanics. The Netherfield Ball is
driven by them. Design questions:

- Is reputation a single float or a per-faction set of floats? (Bingley's
  circle, the Meryton neighborhood, Lady Catherine's set are meaningfully
  distinct audiences for Elizabeth's behavior.)
- How does reputation interact with the failure condition? Pure humiliation
  approaching 1.0, or a composite of reputation damage + unmet goals?
- Does the schema need a `faction` table, or is the existing `character_attitude`
  table sufficient if attitudes are tracked bidirectionally between all
  characters, not just toward the player?

### C. Dance card mechanics

Dances are structured social commitments — the core resource allocation mechanic
of the module. Design questions:

- Schema: a `dance_commitment` table linking character pairs to a set number
  within the evening's schedule? Or model as `pending_intent` entries on
  characters?
- Engine: does the engine enforce the "sit out a set you declined" rule, or does
  Pass 2 adjudicate it?
- How does the dance schedule interact with the in-game clock?

### D. Timed event schedule

The ball has a known structure: arrival, opening dances, supper, later dances,
departure. This is a sequence of scheduled world events, not player-driven
actions. Design questions:

- Represent as a table of events with `trigger_time_minutes` thresholds?
- Does the engine fire these as a variant of the involuntary event mechanism,
  or is a new scheduled-event concept needed?
- Which events are hard-triggered (supper is announced at a fixed time) vs.
  soft (departure depends on player state)?

### E. Inter-NPC relationship modeling

Darcy and Wickham have history that neither will disclose to Elizabeth. Other
NPC pairs also have established relationships (Bingley–Darcy, Jane–Bingley,
Collins–Lady Catherine). The current schema tracks `character_attitude` between
any two characters, which covers this — but the context packet only currently
surfaces attitudes toward the player.

- Pass 2 context: should NPC-to-NPC attitudes be included? At minimum,
  characters in the same scene should know about each other's presence and
  general disposition.
- Hidden information: Wickham's goals are almost entirely hidden from Elizabeth.
  This is the first real test of the `hidden_motivation` access-control flag
  in the schema.

### F. Pending intent implementation (prerequisite)

The `pending_intent` field on `character` (pending work §1) is a prerequisite
for the dance card and inter-NPC relationship mechanics. Wickham's concealed
agenda and dance commitments both need a durable per-character intent slot.
Implement this before seeding the Netherfield Ball.

### G. Failure condition and win state

What does Elizabeth want from the Netherfield Ball, and what constitutes
failure? Candidates:
- Social reputation float (humiliation approaching 1.0)
- A goal-satisfaction composite: avoid Collins, manage Jane's interests,
  navigate Wickham/Darcy tension without social damage
- An open emergent outcome where the LLM assesses Elizabeth's state at
  session end rather than a hard threshold

The "boredom as hit points" principle from I Am a Cat generalizes here, but
the specific mechanic needs design before the `internal_state` seed can be written.
