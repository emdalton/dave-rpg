# DAVE Test Coverage Map

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

This document maps each engine feature or mechanic to its test coverage across
all three tiers. Update it whenever a new feature is added or a test is written.

**Tiers:**

- **Tier 1** — no LLM; runs without `--llm` flag; fast. Fixtures: `tmp_db`,
  `hostel_db`, `test_engine` (MockLLMClient), etc.
- **Tier 2** — requires live LLM; run with `pytest --llm`. Structural
  assertions only (shape, adjacency, range checks). Marked `@pytest.mark.llm`.
- **Tier 3** — LLM-as-judge evaluation; run with `pytest --llm-eval`. Expensive;
  assesses prose quality, tone, and semantic correctness. Marked
  `@pytest.mark.llm_eval`.

**Hidden Hostel (HH)** column flags coverage that uses the Hidden Hostel module
database (`hostel_db` / `tmp_hostel_db`). HH is the integration canary: if a
mechanic works generically but breaks in HH's seed data it will show here.

The **Gap / notes** column calls out missing coverage or known issues.

---

## DB Layer (`engine/db.py`)

| Feature | Tier 1 | Tier 2 | Tier 3 | HH | Gap / notes |
|---|---|---|---|---|---|
| Schema version | `test_db:TestSchemaVersion` | — | — | — | — |
| Game record (get, JSON fields) | `test_db:TestGetGame` | — | — | — | — |
| Character get / at_location | `test_db:TestGetCharacter` | — | — | — | — |
| Create character | `test_db:TestCreateCharacter` | — | — | — | — |
| Internal state get/update/delta | `test_db:TestInternalStates` | — | — | — | — |
| `tick_passive_states()` math | `test_db:TestPassiveStateDrift`, `test_mechanics:TestPassiveStateDrift`, `test_internal_state_drift:TestTickPassiveStatesMath` | — | — | `test_hidden_hostel:TestPassiveStateDrift` | No Tier 2 test that the engine *loop* calls tick; gap noted in testing backlog |
| Game clock (get/advance) | `test_db:TestGameClock`, `test_mechanics:TestClock` | — | — | — | — |
| Attitudes (get/update/clamp) | `test_db:TestAttitudes` | — | — | `test_hidden_hostel:TestAttitudes` | — |
| Faction reputation | `test_db:TestFactionReputation` | — | — | `test_hidden_hostel:TestFactionReputation` | — |
| Pending intent (set/clear) | `test_db:TestPendingIntent` | — | — | — | — |
| Activity system (set/clear/expire/renewable) | `test_db:TestActivitySystem` | — | — | — | — |
| Location queries / connections | `test_db:TestLocationQueries` | — | — | — | — |
| `get_all_npcs()` (NPC directory) | `test_context:TestBuildPass1Packet::test_known_characters_includes_all_npcs` | — | — | — | Tested indirectly via context; no isolated db.py unit test |


---

## Character Goals (`character_goal` table / Ford-Nichols MST)

| Feature | Tier 1 | Tier 2 | Tier 3 | HH | Gap / notes |
|---|---|---|---|---|---|
| Marta `resource_provision` goal seeded | `test_hidden_hostel:TestCharacterGoals::test_marta_has_resource_provision_goal`, `test_marta_goal_set_is_complete` | — | — | ✓ | — |
| Goal visibility flag (`include_hidden`) | `test_hidden_hostel:TestCharacterGoals::test_scholar_has_hidden_safety_goal` | — | — | ✓ | Mirrors hidden_motivation access control pattern |
| Wanderer exploration goal seeded | `test_hidden_hostel:TestCharacterGoals::test_wanderer_has_exploration_goal` | — | — | ✓ | — |
| Goal-driven proactive behavior (pending_intent + goal aligned) | `test_hidden_hostel:TestCharacterGoals` (DB shape) | `test_scenario_entrance:TestHiddenHostelEntranceScenario::test_063_marta_offers_rolls_proactively` | — | ✓ | Goal alone driving behavior (no pending_intent) not yet tested — next backlog item |

---

## Mechanics (`engine/mechanics.py`)

| Feature | Tier 1 | Tier 2 | Tier 3 | HH | Gap / notes |
|---|---|---|---|---|---|
| `format_game_time()` | `test_mechanics:TestFormatGameTime` | — | — | — | — |
| BFS pathfinding (adjacent / blocked / self) | `test_mechanics:TestBFSPathfinding` | — | — | `test_hidden_hostel:TestStaircaseConnection`, `TestImpassableConnection` | HH adds impassable-connection and staircase edge cases |

---

## Context Assembly (`engine/context.py`)

| Feature | Tier 1 | Tier 2 | Tier 3 | HH | Gap / notes |
|---|---|---|---|---|---|
| Pass 1 packet — required keys | `test_context:TestBuildPass1Packet::test_required_top_level_keys` | — | — | — | — |
| Pass 1 packet — `known_locations` | `test_context:TestBuildPass1Packet::test_known_locations_includes_all_locations` | — | — | — | — |
| Pass 1 packet — `known_characters` | `test_context:TestBuildPass1Packet::test_known_characters_includes_all_npcs` | — | — | — | No HH coverage; Feature 25 is new |
| Pass 1 packet — player profile / game block | `test_context:TestBuildPass1Packet` (remaining tests) | — | — | — | — |
| Pass 1 packet — hidden motivation absent | — | — | — | `test_hidden_hostel:TestHiddenMotivationAccessControl::test_hidden_motivation_absent_from_pass1_packet` | No generic-db Tier 1 test for this |
| Pass 2 packet — required keys | `test_context:TestBuildPass2Packet::test_required_top_level_keys` | — | — | — | — |
| Pass 2 packet — characters_present / NPCs | `test_context:TestBuildPass2Packet` (Guard present, Hermit absent) | — | — | — | — |
| Pass 2 packet — internal states | `test_internal_state_drift:TestPass2InternalStateContext` | — | — | — | — |
| Pass 2 packet — faction reputations | `test_context:TestBuildPass2Packet::test_faction_reputations_included_when_present` | — | — | — | — |
| Pass 2 packet — pending_intent in NPC profile | `test_context:TestBuildPass2Packet::test_npc_profile_includes_pending_intent_when_set` | — | — | — | — |
| Pass 2 packet — current_activity in NPC profile | `test_context:TestBuildPass2Packet::test_npc_profile_includes_activity_when_set` | — | — | — | — |
| Pass 2 packet — adjacent_locations | `test_context:TestBuildPass2Packet::test_adjacent_locations_in_pass2_packet` | — | — | — | — |
| Pass 2 packet — hidden motivation absent from NPC profile | — | — | — | `test_hidden_hostel:TestHiddenMotivationAccessControl::test_hidden_motivation_absent_from_pass2_npc_profile` | — |
| Pass 3 packet — required keys / outcome / adjacent_locations | `test_context:TestBuildPass3Packet` | — | — | — | — |
| Pass 3 packet — internal states (display filter) | `test_internal_state_drift:TestPass3InternalStatePacket` | — | — | — | Uses `hostel_db`; hunger display filter tested |

---

## Engine Outcome Application (`engine/engine.py` — `apply_outcome_*`)

| Feature | Tier 1 | Tier 2 | Tier 3 | HH | Gap / notes |
|---|---|---|---|---|---|
| Attitude delta | `test_engine:TestApplyOutcomeAttitudeDeltas` | — | — | `test_hidden_hostel:TestAttitudes::test_attitude_delta_applied` | — |
| Internal state delta (clamp) | `test_engine:TestApplyOutcomeStateDeltas` | — | — | — | — |
| Emotional state update | `test_engine:TestApplyOutcomeEmotionalState` | — | — | — | — |
| Location change (adjacent / blocked / non-existent) | `test_engine:TestApplyOutcomeLocationChange` | — | — | — | — |
| Faction reputation delta | `test_engine:TestApplyOutcomeFactionRep` | — | — | — | — |
| Pending intent set/clear | `test_engine:TestApplyOutcomePendingIntent` | — | — | — | — |
| Activity set/clear/clamp confidence | `test_engine:TestApplyOutcomeActivity` | — | — | — | — |
| New NPC creation (no-duplicate guard) | `test_engine:TestApplyOutcomeNewCharacters` | — | — | — | — |
| Activity expiry (engine loop) | `test_engine:TestActivityExpiry` | — | — | `test_hidden_hostel:TestActivityExpiry` | HH adds renewable and wander-suppression interaction |
| NPC wander suppression — pending_intent | `test_engine:TestNPCWanderSuppression::test_pending_intent_suppresses_wander` | — | — | `test_hidden_hostel:TestWanderSuppressionPendingIntent` | — |
| NPC wander suppression — sleepiness | `test_engine:TestNPCWanderSuppression::test_high_sleepiness_suppresses_wander` | — | — | `test_hidden_hostel:TestWanderSuppressionSleepiness` | — |
| NPC wander suppression — active activity | `test_engine:TestNPCWanderSuppression::test_active_activity_suppresses_wander` | — | — | `test_hidden_hostel:TestWanderSuppressionActivity` | — |
| NPC wander — base case (no suppression) | `test_engine:TestNPCWanderSuppression::test_guard_wanders_when_no_suppression` | — | — | `test_hidden_hostel:TestWanderSuppressionSleepiness::test_ginchan_can_wander_when_not_sleepy` | — |
| NPC wander — expired activity does not suppress | `test_engine:TestNPCWanderSuppression::test_expired_activity_does_not_suppress_wander` | — | — | `test_hidden_hostel:TestActivityExpiry::test_activity_expiry_frees_wander_suppression` | — |

---

## Pass 1 — Intent Parsing (LLM)

| Feature | Tier 1 | Tier 2 | Tier 3 | HH | Gap / notes |
|---|---|---|---|---|---|
| Speak action → structured record | — | — | `test_pass1_eval:TestPass1Eval::test_simple_speak_action` | — | — |
| Move: location name → `target_id` | — | — | `test_pass1_eval:TestPass1Eval::test_move_action_resolves_location_name` | — | — |
| Move: varied phrasings (proceed / head to / make our way) | — | — | `test_pass1_eval:TestPass1Eval` (3 tests) | — | — |
| Character alias → `target_character_id` (Feature 25) | `test_context:TestBuildPass1Packet::test_known_characters_includes_all_npcs` (packet shape only) | — | `test_pass1_eval:TestPass1Eval::test_character_name_resolves_to_correct_id`, `test_character_not_at_location_still_resolves` | — | Species disambiguation ("talk to the cat") deferred; requires hostel_db (Gin-chan) |

---

## Pass 2 — Adjudication Contract (LLM)

| Feature | Tier 1 | Tier 2 | Tier 3 | HH | Gap / notes |
|---|---|---|---|---|---|
| Speak action output structure | — | `test_pass2_contract:TestPass2Contract::test_speak_action_has_valid_structure` | — | — | — |
| Move → adjacent location only | — | `test_pass2_contract:TestPass2Contract::test_move_action_location_change_is_adjacent` | — | — | — |
| `elapsed_minutes` plausibility | — | `test_pass2_contract:TestPass2Contract::test_elapsed_minutes_is_plausible` | — | — | — |
| Float fields in [0, 1] | — | `test_pass2_contract:TestPass2Contract::test_float_fields_are_in_range` | — | — | — |

---

## Pass 3 — Prose Rendering (LLM)

| Feature | Tier 1 | Tier 2 | Tier 3 | HH | Gap / notes |
|---|---|---|---|---|---|
| Ambient outcome → prose | — | — | `test_pass3_eval:TestPass3Eval::test_ambient_outcome_prose` | — | — |
| Emotional state change reflected in prose | — | — | `test_pass3_eval:TestPass3Eval::test_emotional_state_change_reflected_in_prose` | — | — |
| No verbal tic pattern | — | — | `test_pass3_eval:TestPass3Eval::test_no_verbal_tic_pattern` | — | — |
| Internal state level surfaced in prose | — | `test_internal_state_drift:TestInternalStateDriftScenario::test_020_hunger_surfaces_in_prose` | — | — | — |
| Internal state decremented after eating | — | `test_internal_state_drift:TestInternalStateDriftScenario::test_030_eating_reduces_player_hunger` | — | — | — |
| NPC spontaneous eating (state + prose) | — | `test_internal_state_drift:TestInternalStateDriftScenario::test_050_npc_spontaneous_eating` | — | — | — |

---

## Item / Container System

| Feature | Tier 1 | Tier 2 | Tier 3 | HH | Gap / notes |
|---|---|---|---|---|---|
| Surface visibility (open / closed container) | `test_item_container:TestSurfaceVisibility` | — | — | — | — |
| Recursive surface nesting | `test_item_container:TestSurfaceVisibility::test_recursive_surface_nesting` | — | — | — | — |
| Item take / place / carry / put (multi-step) | — | `test_item_container:TestItemContainerHierarchy` | — | — | — |

---

## Hidden Hostel Module — Integration

| Feature | Tier 1 | Tier 2 | Tier 3 | HH | Gap / notes |
|---|---|---|---|---|---|
| Staircase connection (passable, type, pathfinding) | — | — | — | `test_hidden_hostel:TestStaircaseConnection` | — |
| Impassable connection (DB, pathfinding blocked) | — | — | — | `test_hidden_hostel:TestImpassableConnection` | — |
| Location detail (seeded vs. lazy) | — | — | — | `test_hidden_hostel:TestLocationDetail` | — |
| Hidden motivation — DB presence + access control | — | — | — | `test_hidden_hostel:TestHiddenMotivationAccessControl` | — |
| Entrance scenario (multi-step Tier 2 end-to-end) | — | `test_scenario_entrance:TestHiddenHostelEntranceScenario` (16 tests) | — | ✓ | Longest integration suite; covers self-definition, item instantiation, NPC interaction, locked room, give item, meal deadline |
| Internal state drift — eating delta (end-to-end) | — | `test_internal_state_drift:TestInternalStateDriftScenario` (5 tests) | — | ✓ | Hunger, eating, NPC spontaneous eating |

---

## Known Coverage Gaps (summary)

- **Character alias resolution — species disambiguation** — the two Tier 3 tests cover name-based resolution and cross-location resolution, but species disambiguation ("talk to the cat") is not yet tested. Requires a hostel_db fixture in test_pass1_eval.py (Gin-chan is the only non-human NPC in the hostel module). Also add a new PASS1_CRITERIA rubric criterion `character_id_valid_in_context` is now live; the existing rubric criterion `speak_has_target_character` remains the structural gate.
- **Engine loop calls `tick_passive_states()`** — no dedicated Tier 2 test verifies the loop itself advances passive states over elapsed turns. The math is solid at Tier 1; the wiring is implicit in the Tier 2 scenario tests.
- **`get_all_npcs()` unit test** — the DB method is tested only indirectly via the Pass 1 packet; a direct `test_db:TestGetCharacter`-style test is missing.
- **Post-Pass-2 validation/retry layer** — deferred; no coverage at any tier (by design).
- **Player self-definition** — partially covered in `test_scenario_entrance:test_030_self_definition_and_item_instantiation`; no isolated unit test.
- **Mid-play item instantiation** — covered only inside the entrance scenario; on the testing backlog for an isolated test.
