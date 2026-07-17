# DAVE RPG Engine — Implementation Status

*Living document. Update at the end of each session before committing.*
*Last updated: 2026-07-17, session 39 (closed).*

---

## Session 38 notes (2026-07-16)

*Session was conducted detached from the RPG project folder; no code was
committed. Design work only.*

**Completed this session:**

- **Vintage Village module — seed and reset scripts written
  (`modules/vintage_village/seed.sql`, `modules/vintage_village/reset_instance.sql`):**
  - Full module extending the Hidden Hostel into a small iyashikei village.
    Hostel locations and NPCs inherited unchanged; five village locations added
    (Village Lane, Kitchen Garden, Apothecary, Bookshop, Tea House).
  - Two new NPCs: The Bookseller (stays in Bookshop) and The Villager (wanders
    the lane actively, high wander probability). Apothecary and Tea House have
    no pre-seeded NPCs — both are skeleton locations for lazy generation /
    god-mode authoring.
  - Wanderer's wander_range extended to include Village Lane.
  - Bookshop seeded with three items; Kitchen Garden seeded with three items.
    All other village location items are lazy-generated on first visit.
  - Green Room character creation enabled (same as Hidden Hostel).
  - Schema v15. DB verified: 9 characters, 11 locations, 10 connections, 28
    items, 1 special_capability. FK-clean, integrity_check ok.
  - Reset script verified: all mutable state resets correctly, items and
    special_capability restored, action_log cleared.

- **God-mode design specification (`docs/god_mode.md`):**
  - Full design doc written; all 9 open questions resolved. Ready for
    implementation. Key decisions:
    - Activated by `--god-mode` CLI flag or `DAVE_GOD_MODE=1` env var; no
      schema changes required; leaves no trace in saved game state.
    - Pass 1 in god-mode returns `action_record` + `world_assertions` list.
      Classification is LLM-evaluated (Qwen 3.5 or stronger, not Haiku).
    - Assertion types: `location_detail`, `npc_description`, `item`.
      `npc_attribute` and `spatial_relation` deferred to Phase 2.
    - Pass 2 in god-mode is a canonization gatekeeper: writes assertions via
      existing DB paths; suppresses unprompted lazy generation; detects and
      logs contradictions without blocking.
    - Pass 3 renders a full arrival scene incorporating newly canonized
      details; surfaces contradictions as light parentheticals.
    - Cross-location assertions accepted; CLI-only for now.
    - Personality assertions stored in character `description` field; OCEAN
      floats not touched by god-mode.
  - Implementation plan: `engine/config.py` (GOD_MODE bool), `engine/__main__.py`
    (--god-mode flag), `engine/engine.py` (god_mode branch, new prompt
    template, `_canonize_assertions()` method). No schema or `db.py` changes
    needed.

- **OCEAN float / qualitative representation note (added to `docs/implementation_status.md`
  design decisions section, session 38):**
  - OCEAN traits are fed to the LLM as raw floats but consumed exclusively as
    qualitative signals — no engine arithmetic uses them. This is an instance
    of the numeric-representation habit the engine's own design principles
    warn against: a description string would do the same Pass 2 job with less
    false precision. Floats are preserved (a future rule-based layer could use
    them) but god-mode does not overwrite them from natural-language assertions.

- **Paper working notes updated (`docs/DAVE_paper_working_notes_consolidated.md`):**
  - New §3.2: representation mismatch — qualitative reasoners and numeric
    values (OCEAN float observation as self-critical case study).
  - New §3.4: hybrid computation tasks — family-tree / cousin-counting as the
    concrete illustration of why both symbolic and associative reasoning are
    needed; human analogue included.

**Pending / known issues (carried forward from session 37, unchanged):**

- Full pytest suite not run against session 37 changes (movement fix,
  prose-length fix + backstop, NPC arrival awareness, interaction-history fix,
  reset script). Run `source .venv/bin/activate && pytest` before treating
  those as fully verified.
- Prose length fix (session 37) did not hold — needs stronger mechanism.
- Character position spec (`docs/character_position_design.md`) — design only;
  implementation not started.
- Personal action/item-history attribution — not yet a numbered future_features
  entry.
- `future_features.md` #31 (NPC sleep depth) and #32 (item-interruption
  module-dependency) — open design questions, not decided.
- Session 37 git commits not confirmed as actually run.

---

## Session 39 notes (2026-07-17)

**Completed this session:**

- **Vintage Village database built and verified
  (`modules/vintage_village/vintage_village.db`):**
  - Built from `schema/schema.sql` + `modules/vintage_village/seed.sql`.
  - Verified: integrity_check ok, FK-clean, all expected row counts confirmed
    (9 chars, 11 locs, 10 connections, 28 items, 1 special_capability).
  - Reset script verified end-to-end: clock resets to 1200, traveller returns
    to loc 6, description/gender/pronouns nulled, items and special_capability
    restored, action_log cleared.

- **Vintage Village registered in web frontend (`web/config.py`):**
  - Added to `AVAILABLE_MODULES` with `game_id=1`, correct db and reset_script
    paths, and lobby description.

**Pending / known issues (carried forward):**

- All session 37 / 38 items above still apply.
- God-mode implementation not yet started — design complete, implementation
  is the next session's first priority.

---

## Session 37 notes (2026-07-07)

*Covers three I Am a Cat playtests spanning 2026-07-05 through 2026-07-07,
worked in a single continuous session.*

**Completed this session:**

- **Movement bug — SINGLE-HOP CEILING rule (`engine/engine.py`,
  `PASS2_PROMPT_TEMPLATE`):**
  - Root cause, traced through `transcripts/i_am_a_cat_20260705_155203.txt`,
    `logs/i_am_a_cat_20260705_155203.log`, and `action_log`: a compound
    command bundling implicit navigation with an interaction ("walk on them,
    sit my fluffy butt on their face and meow for food") was classified by
    Pass 1 as `interact`, not `move`, bypassing the router entirely. Pass 2
    then narrated a full three-hop journey (Living Room → Main Stairs → Upper
    Hallway → Bedroom, ending "at the foot of the bed") while only emitting a
    one-hop `location_change` (to Main Stairs) — the next turn correctly
    adjudicated from the true DB location (Main Stairs) and re-narrated
    climbing the same stairs, reading as an inexplicable regression to the
    player.
  - Fix: new rule inserted after MULTI-STEP MOVEMENT — when `action_record`
    has no `route` key, Pass 2 may move the player at most one adjacent hop,
    and the narrative must not describe arrival beyond what `location_change`
    can truthfully encode.
  - Confirmed via a later playtest (2026-07-06, "go upstairs to the
    bedroom"): a clearly-targeted move correctly triggers the pre-existing
    router (`Multi-step move: Living Room → Bedroom`), showing the bug is
    specific to freehand/compound commands, not the router itself.
  - Verified: `python3 -m py_compile` clean; `PASS2_PROMPT_TEMPLATE.format()`
    succeeds (no unescaped-brace `IndexError`); content assertions confirm
    the new rule text is present. **Not run against the full pytest suite**
    — no `pytest`/network access in this working environment; flagged for E
    to run locally before treating this as fully verified.

- **Prose length — fix attempted, did not hold (`engine/engine.py`
  `PASS3_PROMPT_TEMPLATE`, `engine/config.py`):**
  - Diagnosis: the existing "3–4 sentences routine / 5–6 max significant"
    rule was being exceeded 2–3x on Haiku (96–174 words measured against an
    implied ~40–90 word target), partly via short-sentence-fragment stacking
    that inflates sentence count without reducing actual length ("Options.
    Considerations. The stairs await.").
  - Fix attempted: replaced the abstract sentence-count instruction with a
    tone-neutral worked exemplar (short/long examples) plus an explicit
    anti-fragment-stacking callout. Added `PASS3_LENGTH_THRESHOLD_ROUTINE`
    (90) / `PASS3_LENGTH_THRESHOLD_SIGNIFICANT` (150) to `config.py`
    (env-overridable, validated in `validate()`), and a
    `_check_pass3_length()` helper that logs — never truncates or
    retries — when rendered prose exceeds threshold, keyed on
    `narrative_point_delta`, called from both Pass 3 render sites
    (`_process_turn()` and `_render_move_blocked()`).
  - Verified statically (py_compile, `.format()` success, content
    assertions) and functionally (the logging fires correctly in play).
  - **Outcome: the logging backstop works exactly as designed, but the
    underlying prompt fix did not reduce length.** Playtest 2026-07-07, six
    consecutive turns: 157, 134, 158, 162, 130, 189 words — all against the
    90-word routine threshold, no clear improvement over the pre-fix
    diagnostic session (96–174 words), and one turn (189) worse than
    anything measured before the fix. Open, unresolved going into next
    session: a prompt-level nudge — whether phrased as a sentence count or
    demonstrated via exemplar — does not reliably constrain Haiku's output
    length on its own. No persistent design doc exists for this fix (the
    draft spec stayed in scratch space and was never copied into `docs/`);
    this session-notes entry is its only durable record so far.

- **Character position / sub-location — design spec only, not implemented
  (`docs/character_position_design.md`, new file, captured 2026-07-06,
  amended 2026-07-07):**
  - Full design captured for tracking a character's position relative to
    furniture within a location ("in the kitchen, on the counter"):
    `character.position_item_id` + `character.position_description`,
    mirroring `item.location_description`. No property-flag taxonomy on
    furniture — Pass 2 judges plausibility of a proposed spatial relation
    qualitatively, consistent with the narrative-parameters-over-numerical
    principle. Applies to NPCs as well as the player (Hidden Hostel chair
    contention — two characters wanting the same chair — is the motivating
    case E specifically wants supported). Location-match validation mirrors
    the existing `location_change` adjacency check, including resolving
    nested item chains upward to find the eventual location. A
    vehicle/portable-furniture case (a wheelchair moving its rider) is
    resolved as a purely mechanical engine-side cascade on `item_transfers`,
    never LLM-emitted — avoiding the "LLM must remember two things at once"
    failure class already found and fixed for plain movement.
  - New outcome field needed: `position_updates`. New `context.py` plumbing
    needed: occupancy visibility per item in location packets (required, not
    optional, for chair contention to work at all).
  - Deliberately unmodeled: numeric seating capacity; involuntary events
    dislodging a position (both left to Pass 2's qualitative judgment, with
    capacity flagged as a possible fallback if that judgment proves
    unreliable in practice).
  - Open, unresolved: implementation staging (one pass vs. two — §7 in the
    doc).
  - Playtest note added 2026-07-07 (§8 in the doc): confirms the need for
    this spec from the *absence* of the mechanism — with no implementation
    yet, "on the counter" is held together only by Pass 1's 5-turn
    `recent_actions` / Pass 3's 3-turn `recent_prose`, so the counter arrival
    got needlessly re-narrated at least twice more across a single unbroken
    stay on it ("You spring onto the counter…", then two turns later "You
    hop onto the counter by the sink…"). Refined §5's planned Pass 3
    rendering rule accordingly: narrate the transition only on the turn
    `position_updates` actually changes it, not on every turn the position
    happens to still be true.

- **NPC arrival awareness — implemented (`engine/engine.py`,
  `engine/context.py`):**
  - Fixes the "Spook teleporting" observation (2026-07-06 playtest, traced to
    two legitimate single-hop autonomous wander moves — Study→Upper Hallway,
    then Upper Hallway→Main Stairs — both silent by design). `_check_npc_wandering()`
    now returns `{id, name}` for any NPC whose wander move landed them in the
    player's own location; threaded through `run()`/`step()`/`_process_turn()`
    into `build_pass2_packet(newly_arrived_npcs=...)`, surfaced as
    `newly_arrived_npcs_this_turn` (same wiring pattern as
    `involuntary_events_this_turn`). New Pass 2 rule (NPC ARRIVAL AWARENESS)
    lets Pass 2 judge per-arrival salience and have an idle/sociable NPC
    proactively engage via `npc_initiated_actions` — explicitly steered away
    from using a standing `pending_intent` to encode a personality
    disposition ("always wants to play"), since a permanent `pending_intent`
    would suppress that NPC's autonomous wandering (PENDING INTENT IS
    MANDATORY already gates wander on it) — this was a real conflict with
    E's explicit direction to leave Spook's wander behavior unchanged,
    identified and resolved before writing any code.
  - This closes the already-documented "NPC arrival awareness" pending item
    (first observed Meryton playtest, 2026-05-25) — same gap, second module.
  - Verified: py_compile clean; `.format()` succeeds; ran
    `build_pass2_packet()` directly against `i_am_a_cat.db` with the new
    parameter both omitted (defaults to `[]` — confirmed every existing
    `build_pass2_packet()` call site across `tests/` stays compatible) and
    supplied. **Not run against the full pytest suite** (sandbox limitation,
    as above).

- **`modules/i_am_a_cat/reset_instance.sql` — items were never reset
  (fixed):**
  - Root cause: the script's own header comment explicitly excluded items
    from reset on the assumption they're static furniture — invalidated by
    `item_transfers`/`item_changes` making items mutable during play.
    `docs/module_authoring.md`'s documented reset convention already
    specifies items should be `DELETE`d and re-seeded (Hidden Hostel's reset
    script already does this correctly); I Am a Cat's reset script simply
    never implemented it, so a prior session's damage (e.g. the hallway
    runner rug pounced into a permanently "destroyed" description) silently
    carried into every subsequent "fresh" session.
  - Fix: added `DELETE FROM item WHERE game_id = 1` + re-INSERT of all 37
    seeded items (copied verbatim from `seed.sql`, not hand-reconstructed) as
    new section 6; updated the header comment accordingly.
  - Verified functionally: ran the corrected script against a scratch copy
    of the live (pre-fix, already-damaged) DB — 37 items restored, the
    hallway runner's mutated description/quality correctly reset to seed
    values, `PRAGMA foreign_key_check` clean.

- **`_apply_outcome()` interaction-history dead code — fixed
  (`engine/engine.py`):**
  - Root cause: a session-35 change ("`_apply_outcome()` now returns the
    `action_log_id`") added `return action_log_id` directly above the
    existing interaction-history-increment block without moving the block
    ahead of it, making the block unreachable ever since —
    `npc_player_history` silently stopped being incremented during play,
    with no error raised.
  - Fix: moved the `return` to the end of the function, after the
    interaction-history block.
  - Verified functionally: bypassed the LLM-client requirement (no
    `anthropic` package available in this sandbox) by constructing the
    engine via `object.__new__()` and calling `_apply_outcome()` directly
    against a scratch DB copy — confirmed `interactions_since_summary` for a
    co-located player/NPC pair incremented 0→1, and `action_log_id` still
    returns correctly (session 35's Pass-3-prose-writeback dependency
    unaffected).
  - Framed by E as an interim step — current form is player-NPC pairs only,
    a rolling summary rather than a precise fact ledger — toward broader
    personal-history tracking (see below) via the semantic action-log
    retrieval feature already in `docs/future_features.md` #23, which E
    thinks is the better fit for longer games specifically.

- **Two new design-backlog entries added to `docs/future_features.md`**
  (#31, #32; "Last updated" bumped to 2026-07-06):
  - **#32 — item-triggered route interruption should be module/context-
    dependent:** `_resolve_multistep_move()` forces a hard stop for *any*
    visible item at an intermediate location on a multi-hop route,
    contradicting its own comment ("flagged for Pass 2 to adjudicate") —
    surfaced by the hallway runner "major skid" recurring on nearly every
    multi-hop route through it. E's framing: obstacle plausibility is
    module/context-dependent (fits I Am a Cat's cat's-eye-view tone; would
    not usually fit Meryton or Hidden Hostel), not a fixed engine rule, and
    should be rare even where plausible (a human tripping on a loose runner
    is not a common event), not near-guaranteed as it currently is. Options
    recorded (module-tunable, probabilistic, or drop the engine-side hard
    stop and let Pass 2 judge from the item's own description); not decided.
  - **#31 — NPC sleep depth and wake-transition on autonomous wander:** the
    mama wandered from Upper Hallway to the Bathroom while Pass 2/3 kept
    narrating her as asleep, because the wander-suppression gate (sleepiness
    threshold + `current_activity`) never reads `emotional_state`, where
    "asleep" was actually recorded (`light_sleep_disturbed`, `sleepiness`
    value 0.112 — well under the 0.60 suppression threshold). E's framing:
    the wander itself is plausible (a light sleeper waking to use the
    bathroom); the actual gap is that nothing transitions her recorded state
    to reflect being awake (if still sleepy) afterward — implies the engine
    may need to model sleep *depth*, distinguishing light sleepers (can
    plausibly wake and wander) from deep sleepers (Guy — should not wander
    regardless of the sleepiness float). Options recorded (extend
    `current_activity` to represent sleep generally; have the wander event
    itself nudge state; or have Pass 2 re-evaluate sleep state each
    referencing turn); not decided.

- **Design discussion: personal action/item-history attribution — not yet
  written up as its own backlog entry.** Surfaced by asking whether Toulouse
  would recognize the rug as his own handiwork versus a fresh discovery:
  no structural mechanism currently attributes an item's mutated state, or
  an NPC's own past actions, to the specific character who caused them.
  Pass 2 gets zero turn-history at all; Pass 1 gets 5 turns; Pass 3 gets 3;
  nothing beyond an item's current (attribution-free) description persists
  past those windows. E generalized this beyond items to any character
  (player or NPC) needing durable, attributable personal history — e.g. Jane
  should be able to correctly answer "who have you danced with tonight" many
  turns later, and this generalizes to NPC-NPC facts the player never
  witnessed. E's framing: this is a better fit for a precise structured fact
  ledger than for semantic/RAG retrieval (`future_features.md` #23), since
  the ask is exact recall of a fact set, not fuzzy relevance-based retrieval.
  The interaction-history dead-code fix above is treated as an interim,
  narrower step in this direction, not a solution to it.

**Pending / known issues (carried forward):**

- **Full pytest suite has not been run against any of today's changes**
  (movement fix, prose-length fix + backstop, NPC arrival awareness,
  interaction-history fix, reset script). Only manual `py_compile`,
  `.format()` sanity checks, and direct scratch-DB functional tests were
  possible from this working environment — no `pytest` package, no network
  access to install it, and the project's own `.venv` is macOS-native and
  cannot execute here. **E should run `source .venv/bin/activate && pytest`
  locally before treating any of today's changes as fully verified**, and
  before committing.
- Prose length fix did not hold (see above) — needs a stronger mechanism
  next session; the logging backstop confirms the problem persists rather
  than solving it.
- Character position spec (`docs/character_position_design.md`) — design
  only; implementation not started; open staging question (§7 in the doc)
  unresolved.
- Personal action/item-history attribution (items and NPC-to-NPC facts) —
  discussed at length this session; not yet written up as a
  `future_features.md` entry. Next session should give this its own numbered
  entry rather than leaving it only in these session notes.
- `future_features.md` #31 (NPC sleep depth) and #32 (item-interruption
  module-dependency) — both open design questions with recorded options,
  neither decided.
- None of today's git commits (reset script fix, interaction-history fix,
  movement fix, prose-length fix, NPC arrival awareness) have been confirmed
  as actually run — commands were provided to E in-session but committing is
  manual per project convention.

---

## Session 36 notes (2026-07-03)

**Completed this session:**

- **ITEM CONSISTENCY rule (`engine/engine.py`, `PASS2_PROMPT_TEMPLATE`):**
  - Added a rule mirroring the existing MOVEMENT CONSISTENCY pattern: if
    `narrative_beat` describes an item being picked up, carried, installed,
    given, or consumed, that handling MUST be reflected in `item_transfers` or
    `item_changes` the same turn — the engine only updates item DB records from
    those fields, it does not read prose. Includes explicit guidance for the
    "installed/consumed" case (item_transfer to the consuming character, then
    `is_visible=0` via item_changes) since that pattern had no prior worked
    example in the prompt.
  - Root cause: a personal (gitignored, non-public) demo module —
    `modules/suspended_demo/` — surfaced this live. A robot narrated picking up
    and installing a replacement part; the `internal_state_delta` correctly
    fired (confirmed via direct DB query), but the item's own `loc_id`/`char_id`
    never changed — it was never moved via `item_transfers`, leaving the DB
    record contradicting the story.
  - Verified statically: `PASS2_PROMPT_TEMPLATE.format()` still succeeds (no
    unescaped-brace `IndexError`); `python3 -m py_compile engine/engine.py`
    clean; no output field names changed, so `test_pass2_contract.py`'s
    schema-shape assertions are unaffected.
  - Verified against the full test suite (E, local venv): 236 passed, 43
    skipped, no failures — skip count matches the session 35 baseline (the
    same `--llm`-marked Tier 2 tests), so nothing newly skipped either.

- **`remote_capability` table (schema v14) — `schema/schema.sql`,
  `schema/migrations/migrate_v13_to_v14.sql`, `docs/module_authoring.md`:**
  - Schema for cross-location communication and remote sensing (E's design):
    `can_send_to` (owner actively transmits to target; consensual/agentive)
    and `can_detect_from` (owner passively reads target regardless of
    consent), each parameterized by owner, target, and sense. Directional and
    one row per single sense channel (matches `character_attitude`'s
    directional pattern; a robot sending both dialogue and its native sense
    needs two rows). Attachable to a character or an item — exactly one of
    `owner_character_id`/`owner_item_id` set, mirroring the item table's
    `loc_id`/`char_id`/`item_id` pattern; item-owned capabilities resolve
    their effective owner dynamically via whichever character currently
    holds the item.
  - This is schema only, deliberately scoped down from E's full request.
    **Not yet implemented:** `context.py` packet assembly, the Pass 1/2/3
    prompt rules that would consume it, and — the biggest piece — the
    carve-out this requires in the existing "NPC presence is authoritative"
    rule (currently: only describe an NPC as present/acting if they're in
    `characters_present`; a `can_send_to`/`can_detect_from` link needs to
    let a non-co-located character participate anyway, rendered as remote
    rather than physically present). Tracked as the direct fix for the
    cross-location gap noted in `future_features.md` §7 and worked around
    (not solved) in `modules/suspended_demo/`.
  - Verified: fresh install via updated `schema.sql` and the migration path
    (v13 baseline + `migrate_v13_to_v14.sql`) produce byte-identical
    `remote_capability` column definitions (`PRAGMA table_info` compared
    programmatically). CHECK constraints exercised directly: both-owners-set,
    no-owner-set, and invalid `capability` value all correctly rejected;
    valid character-owned and item-owned rows both insert cleanly; no FK
    violations. Not yet run against the Python test suite (no new Tier 1/2
    tests written yet — nothing to test until context.py/prompt integration
    exists).

- **`special_capability` table (schema v15) — rename + broaden `remote_capability`
  (`schema/schema.sql`, `schema/migrations/migrate_v14_to_v15.sql`,
  `docs/module_authoring.md`, `modules/hidden_hostel/seed.sql`,
  `modules/hidden_hostel/reset_instance.sql`):**
  - Design discussion with E (same session) established this is broader than
    "remote": distance is one axis this overrides, concealment (a rock's
    hidden history, a person's hidden emotion) is another, independent one.
    Renamed accordingly.
  - Owner gains `owner_location_id` (a location can have agency — a warded
    room that detects entrants). Target changes from a single required
    character FK to four mutually exclusive options: `target_character_id`,
    `target_item_id`, `target_location_id` (scrying targets a place), and
    `target_description` (free-text filter, e.g. "any distant, real-world
    place" — adjudicated fresh by Pass 2 each time rather than resolved to a
    fixed row; for unenumerable/varying targets).
  - `capability` gains a third value, `'can_affect'` — a write (owner changes
    a target property), distinct from the two existing reads. Scoped by
    design intent to temporary/environmental effects only; permanent
    transformation or a curse imposed on a character routes through
    `character_aspect` + Fate compels instead (already models "something
    imposed on you that you didn't choose" — deliberately not duplicating
    that here). Reuses `sense` to name the affected property rather than
    adding a column.
  - Two new nullable, qualitative (NOT numeric) columns: `distance` (the
    required spatial relationship between owner and target — not just a
    max range; `'touch'` is *stricter* than ordinary co-location, not
    looser) and `typical_duration`/`typical_effort` (free-text calibration
    hints — `'fleeting'`, `'requires focused attention and exhausts
    character'` — deliberately not numbers; E was explicit about not wanting
    Hero-System-weight crunch, Fate-weight narrative signal instead). Actual
    per-use runtime tracking rides on the existing
    `character.current_activity` system, not a new mechanism.
  - Migration recreates the table (SQLite can't ALTER a CHECK constraint or
    an XOR column set in place) — same approach as the v10→v11 `game` table
    migration. No real data existed at v14 to lose (schema-only, zero
    consumers), but the copy step is written correctly anyway per migration
    rules #1/#3 (explicit column list; new columns get literal NULL, not
    read from a table version that didn't have them).
  - Verified the same way as v14: fresh install and the v14-baseline +
    migration path produce byte-identical `PRAGMA table_info` output; CHECK
    constraints exercised directly (two-target-set and invalid-`capability`
    both correctly rejected); FK-clean.
  - **Concrete test case seeded in Hidden Hostel (E's suggestion):** a gray
    crystal sphere in the Common Room, `owner_item_id`-owned,
    `target_description`-targeted ("any distant, real-world place..."),
    `capability='can_detect_from'`, `sense='visual_perception'`,
    `distance='touch'`, `typical_duration='fleeting'`,
    `typical_effort='effortless'`. Schema only — no behavioral effect until
    context.py/prompt integration lands; the item and its description exist
    and are inert until then.
  - **Design ambiguity surfaced by actually seeding this, worth remembering:**
    `distance` is doing double duty. For an item-owned row, it can mean
    either "what relationship a character needs to the *item* to gain the
    capability" (this case: must touch the sphere) or "how far the granted
    capability then reaches to its *target*" (this case: unconstrained by
    design — that's the point of scrying). Only one column exists; this seed
    uses it for the former and leaves the latter implicitly unlimited.
    Revisit if a case needs both constrained at once.
  - **Real bug caught and fixed by testing the full seed→reset cycle, not
    just seed→build:** `reset_instance.sql` does `DELETE FROM item WHERE
    game_id = 1` before re-seeding. With `foreign_keys=ON` and no `ON DELETE`
    clause on `special_capability`'s item references, this would have failed
    outright once a `special_capability` row existed pointing at an item —
    deleting a referenced row with no cascade is a straight FK violation.
    Added a `DELETE FROM special_capability WHERE owner_item_id IN (...) OR
    target_item_id IN (...)` immediately before the item delete, and the
    matching re-seed (re-resolved by item name, not a hardcoded id, since
    the sphere gets a fresh id every reset) after items are recreated.
    Verified end-to-end: build → seed → reset all run clean, FK-checked
    after each step.

**Related, deliberately deferred:**

- Broader "invented facts must stay canon" problem (E's framing, connects to
  the session 35 Meryton `current_activity` grounding fix): Pass 2 has a real
  mechanism for this already — `new_location_details` → `db.add_location_detail()`
  — but nothing mandates its use, and there's no rule distinguishing a
  canon-worthy claim from one-off NPC flavor commentary. Needs E's design input
  on where that line sits before implementing; tracked as a separate, larger
  follow-on, not bundled into this session's fix.

- **Check: does Pass 2 already let perceived warmth diverge from `voice_warmth`?**
  Design discussion (same session, see `CLAUDE.md` "Narrative parameters over
  numerical ones") distinguished self-intrinsic character traits (OCEAN —
  a fact about the character, independent of any observer) from relationally
  perceived qualities (warmth-as-received — inherently observer-dependent; the
  same behavior can land as genuine to one listener and cloying or
  passive-aggressive to another, depending on that listener's own attitude,
  OCEAN, and history with the speaker). `character_attitude` already models
  exactly this kind of per-observer divergence for relationship standing, but
  it's not yet confirmed whether the Pass 2/3 prompt rules let a *listener's*
  own psychology cause `voice_warmth` to land differently for different
  characters, or whether high `voice_warmth` is currently treated as a
  broadcast fact everyone receives identically. Needs a read of the actual
  prompt rules in `engine.py` before deciding whether this needs a fix or is
  already fine. Not yet investigated.

**Pending / in progress:**

- **Need: Tier 2 (`--llm`) test in Hidden Hostel for the ITEM CONSISTENCY rule.**
  Everything verified this session confirms the rule doesn't *break* anything
  (Tier 1 `_apply_outcome()` tests still pass on synthetic outcome JSON) — but
  nothing yet confirms the real model actually *emits* `item_transfers`/
  `item_changes` when a narrative describes an item being picked up, installed,
  or consumed. That's exactly the gap that let the original bug through
  undetected. The tea-making sequence already logged as a test-coverage gap
  (sencha canister → teapot → cups; see testing backlog memory) is a natural
  fit to extend for this — pouring tea or serving rolls is the same "consumed/
  handled" shape as the fuse-install case that surfaced the bug. Test should
  assert the live Pass 2 response actually includes the right item_transfers/
  item_changes entries for such an action, not just that the DB ends up correct
  when fed hand-written outcome JSON.

---

## Session 35 notes (2026-06-28)

**Completed this session:**

- **Blocked-move prose fix (`engine/engine.py`) — closes issue from session 34 diagnosis:**
  - `_render_move_blocked(reason)` method added. When the quick-move guard
    fires (player tries to navigate to an unvisited non-adjacent location),
    the engine now runs Pass 3 on a synthetic `outcome_type="failure"` outcome
    rather than returning the raw constraint string to the player. The raw
    `no_path_reason` is used only as a narrative cue inside the synthetic
    `narrative_beat`; it never reaches player-facing prose.
  - Call site in `_process_turn()` updated accordingly.

- **Pass 2 TARGET PRIMACY rule (`engine/engine.py`):**
  - New rule added to `PASS2_PROMPT_TEMPLATE` after `PENDING INTENT IS MANDATORY`.
  - Rule: the primary outcome must resolve the player's stated action toward
    `action_record.target`. NPC pending_intent discharges for other characters
    are secondary events (go in `npc_initiated_actions`), not the dominant turn
    outcome. Addresses the Bingley/Robinson character confusion from the
    2026-06-27 Meryton playtest.

- **`openai` logger suppressed (`web/app.py`):**
  - Added `"openai"` to the noisy-logger suppression list. Quiets HTTP-level
    chatter from the Scaleway client in the systemd journal.

- **Mock patch target fixed (`tests/conftest.py`, `tests/test_hidden_hostel.py`):**
  - Both `test_engine` (conftest) and `hostel_engine` (test_hidden_hostel)
    fixtures were patching `engine.llm.get_llm_client` (the definition site).
    Corrected to `engine.engine.get_llm_client` (the import site). The wrong
    target silently failed when `ANTHROPIC_API_KEY` was set in the environment;
    the real `ClaudeLLMClient` was being used in Tier 1 tests that claim to
    need no API key.

- **Staircase test corrections (`tests/test_hidden_hostel.py`):**
  - `test_pathfinding_traverses_staircase` and
    `test_pathfinding_adjacent_staircase_skips_visited_guard` assumed the
    Traveller starts at Common Room (1). The seed puts the Traveller at
    Outside the Hostel Door (6). Tests updated to relocate the player to
    Common Room before testing staircase pathfinding.
  - File header updated: location 6 added to topology table; Traveller's
    starting location corrected; connection 1↔6 (the blue door) added.

- **`TestMoveBlockedProse` (§N) — four new Tier 1 tests:**
  - `test_raw_string_does_not_reach_player` — regression guard.
  - `test_pass3_prose_is_returned` — confirms mock prose is returned.
  - `test_pass2_is_skipped` — blocked move triggers exactly 2 LLM calls.
  - `test_player_location_unchanged` — no DB side effects after block.
  - All pass with `source .venv/bin/activate && pytest` (227 passed, 43 skipped).

- **Pass 3 NPC activity rule (`engine/context.py`, `engine/engine.py`):**
  - `current_activity` added to each entry in the `characters_present` context packet.
  - New NPC activity rule in `PASS3_PROMPT_TEMPLATE`: NPCs with null `current_activity`
    must not be described as engaged in specific actions (dancing, playing cards, etc.).
    Addresses Lydia/Kitty dancing hallucination and Jane's mid-session disappearance
    observed in the 2026-06-28 Meryton playtest.

- **Pass 3 anti-repetition — recent prose context (schema v13):**
  - `prose TEXT` column added to `action_log` (migration `migrate_v12_to_v13.sql`).
  - `db.update_action_log_prose(action_log_id, prose)` writes Pass 3 output back after
    each turn. `db.get_recent_prose(game_id, limit=3)` fetches the last N rendered turns.
  - `build_pass3_packet()` includes `recent_prose` (last 3 turns, oldest-first).
  - `_apply_outcome()` now returns the `action_log_id`; `_process_turn()` captures it
    and writes prose back after Pass 3 returns.
  - ANTI-REPETITION rule added to `PASS3_PROMPT_TEMPLATE`: check `recent_prose` for
    repeated phrases, imagery, and internal-state descriptors before writing; use
    different language. Addresses "curiosity hums/prickles" appearing every turn.
  - Cost impact: ~200–600 extra input tokens per Pass 3 call (<10% total per-turn cost).

- **New Tier 1 tests:**
  - `TestActionLogProse` (5 tests in `test_db.py`): empty result before any prose;
    prose written via update appears in get; null rows excluded; chronological order;
    limit respected. Sort uses `id` not `created_at` (sub-second timestamp collision).
  - `TestBuildPass3Packet` extended (2 new tests in `test_context.py`): `recent_prose`
    key present and empty at session start; populated after `update_action_log_prose()`.
  - `test_context.py` also has 2 tests for `current_activity` in `characters_present`
    (null when not set; verbatim when set).

- **`docs/test_suite.md` updated:** §N (TestMoveBlockedProse), TestActionLogProse,
  Pass 3 packet section, Hidden Hostel count corrected to 45 tests / 13 classes.

**Pending / in progress:**

- **Fix 3 — Model quantization (in progress this session):**
  - Mistral Small 3.2 24B is deployed as `mistral-small-3.2-24b-instruct-2506:fp8`
    (fp8 quantized). The `:fp8` suffix selects the quantized variant; omitting it
    uses the full-precision model. Testing whether removing `:fp8` improves Pass 2
    quality (character distinction, pending_intent handling).
  - Config location: `engine/config.py` — `SCALEWAY_DEFAULT_MODEL`.
  - If the full-precision model does not meaningfully improve quality, Mistral Small
    may not be adequate for Pass 2 adjudication at this complexity level.

**Carried forward from session 34:**

- `_record_last_tokens()` in `web/game.py` is a no-op. Budget display €0.0000.
- Pass 3 repetition failure: Mistral Small repeats imagery across turns. Prompt
  hardening or model change needed.
- Issues #63 and #64 are identical (yelling mechanic) — close one as duplicate.
- Green Room: gender/pronouns not extracted by `_run_green_room()`.
- Green Room: NPC reaction to player description (HH Wanderer).
- Green Room: Tier 1 tests (schema, character_aspect CRUD, extraction flow).
- Green Room: Tier 2 test (HH end-to-end with real LLM).
- Tier 1 tests: `GameEngine` web API methods (MockLLMClient).
- Tier 2 test: same-room speech guard (address `characters_nearby` NPC).

---

## Session 34 notes (2026-06-27)

**Completed this session:**

- **Deployment to Grizabella (Scaleway VPS) — closes issue #62:**
  - DAVE web frontend deployed to Grizabella (51.15.211.86, Ubuntu 24.04).
  - Three deployment pitfalls resolved during setup:
    1. Ubuntu 24.04 does not include `python3-venv` by default — `apt install python3-venv` required.
    2. Gunicorn must run single-worker, single-thread (`--workers 1 --threads 1`) because `ACTIVE_SESSIONS` is in-process memory and SQLite does not handle concurrent writes.
    3. `DAVE_LLM_BACKEND=scaleway` must be set explicitly — Scaleway's API is OpenAI-compatible, not Ollama-compatible; it is not the default.
  - Three deployment files committed to the repo: environment template (all three backend options), systemd service template, and a full deployment guide with troubleshooting notes.
  - Service: `/etc/systemd/system/dave-rpg-web.service`; working directory
    `/home/ubuntu/dave-rpg`; venv at `.venv/`; env vars from `dave-rpg.env`
    (EnvironmentFile). Gunicorn: 1 worker, 1 thread, port `127.0.0.1:8001`,
    120 s timeout. Logs: `logs/access.log` + `logs/error.log` in the repo dir.
  - HTTPS at `https://dave.grizabellamemory.net` via Caddy reverse proxy
    (`caddy.service`). Caddyfile: `dave.grizabellamemory.net` → `localhost:8001`
    with gzip, security headers, and Caddy access log at
    `/var/log/caddy/dave-access.log` (readable only with sudo).
  - Backend: Scaleway (`DAVE_LLM_BACKEND=scaleway`,
    `mistral/mistral-small-3.2-24b-instruct-2506:fp8`).
  - All three modules (I Am a Cat, Hidden Hostel, The Meryton Assembly) playable.
  - Turn limit: 50/user; user cap: 10.

- **Local development instance:**
  - DAVE running locally on `http://localhost:5001` via gunicorn.
  - Backend: Scaleway.
  - Confirmed working: I Am a Cat playable (user_dbs/, session/logout flow).

**Known issues identified this session:**

- **Retrieving Grizabella logs:** Flask/DAVE logs go to the systemd journal,
  not the gunicorn error log file (gunicorn doesn't capture stderr by default).
  Command: `ssh ubuntu@51.15.211.86 'journalctl -u dave-rpg-web.service --since "YYYY-MM-DD" --no-pager'`
- `openai._base_client` DEBUG logs not suppressed: the noisy-logger list in
  `web/app.py` covers `httpx`, `httpcore`, `anthropic`, `werkzeug` but not
  `openai`. Add `"openai"` to quiet HTTP-level noise from the Scaleway client.
- **Inference quality issues on Meryton (Mistral Small 3.2 fp8) — diagnosed
  via journalctl:**
  1. **Blocked-move message leak** (`web/game.py`): when the engine blocks a
     quick-move to an unvisited location, the raw string ("You haven't been to
     Supper Room yet") reaches the player directly instead of going through
     Pass 3. The web handler must catch blocked moves and render them as prose.
  2. **Pass 2 character confusion**: when the player spoke to Mr. Robinson
     (attempting to hint about Charlotte), Pass 2 instead fired Mr. Bingley's
     pending_intent, committed both Elizabeth and Bingley to a dance, and
     cleared Bingley's intent — entirely ignoring the actual action target.
     A second dance commitment followed on the very next turn. Likely
     exacerbated by fp8 quantization. Mitigations: (a) add a Pass 2 prompt
     rule that outcomes must be consistent with the Pass 1 `target` character;
     (b) test the non-quantized model (`mistral-small-3.2-24b-instruct-2506`
     without `:fp8`).
  3. **Mr. Robinson's approach and retreat** was correct engine behavior —
     his 3-minute "approaching Elizabeth to ask for a dance" activity expired
     as designed. Not a bug.
  4. **Pass 3 repetition failure**: no-repeat rule poorly followed by Mistral
     Small — same imagery (ballroom hum, card room, curiosity prickling)
     repeated across nearly every turn. Prompt hardening needed.
- Issues #63 and #64 are identical (yelling mechanic) — close one as duplicate.

**Pending / known issues (carried forward):**

- `_record_last_tokens()` in `web/game.py` is a no-op. Budget display €0.0000.
- Green Room: gender/pronouns not extracted by `_run_green_room()`.
- Green Room: NPC reaction to player description (HH Wanderer).
- Green Room: Tier 1 tests (schema, character_aspect CRUD, extraction flow).
- Green Room: Tier 2 test (HH end-to-end with real LLM).
- Tier 1 tests: `GameEngine` web API methods (MockLLMClient).
- Tier 2 test: same-room speech guard (address `characters_nearby` NPC).

---

## Session 33 notes (2026-06-27)

**Completed this session:**

- **Green Room Mode — CLI engine loop (`engine/engine.py`, issue #59):**
  - `GREEN_ROOM_EXTRACTION_PROMPT` template added (module-level constant after
    `PASS3_PROMPT_TEMPLATE`). Requests JSON with fields: `high_concept`, `trouble`,
    `aspects` (0–3), `description`, `skills`, `confirmation_text`.
  - `_run_green_room()` method added. Reads `character_creation_prompt` and
    `character_creation_hint` from `module_flags`; collects multi-line free-text
    character description; calls LLM extraction; writes results to DB before
    `_render_opening_scene()` runs.
  - `run()` wired: calls `_run_green_room()` when `player_definition_mode == 'green_room'`
    and no `character_aspect` records exist for the player (idempotent — resuming a
    session after creation was completed does not repeat the stage).
  - **Follow-up prompts:** if `high_concept` or `trouble` are missing after the first
    extraction pass, targeted follow-up questions are asked for each missing field.
    Follow-up answers are appended to the original input and a second extraction pass
    fills in only the missing fields; everything already extracted is preserved.
  - **Confirmation gate:** after displaying the LLM's interpretation and structured
    summary, the player is asked "Does this look right? (y/n)". If no, a free-text
    correction is collected, appended to the running input, and extraction re-runs.
    Up to 2 refinements (3 total passes); on the final attempt the question is skipped.
    DB writes happen inside the loop (`clear_character_aspects()` at the top of each
    iteration); the confirmed result is always what is stored.

- **Hidden Hostel seed + reset updated:**
  - `modules/hidden_hostel/seed.sql`: `player_definition_mode` changed from `'define'`
    to `'green_room'`; `module_flags` now contains `character_creation_prompt` (liminal-
    arrival framing) and `character_creation_hint` (Fate Core aspect explanation).
    Schema version comment updated to 12.
  - `modules/hidden_hostel/reset_instance.sql`: `DELETE FROM character_aspect WHERE
    character_id = 1` added (clears player aspects so Green Room re-runs on next
    session); stale mirror-invitation comments updated.

- **Playtest (Haiku backend, 2026-06-27):**
  - Full Green Room flow confirmed working end-to-end.
  - Haiku found a Trouble from the unreadable-book detail even when no trouble was
    stated — confirmed the confirmation gate is needed.
  - Three-pass refinement tested: player corrected on first "n", then again, then
    accepted on third pass. All aspect and DB state correct after each iteration.
  - Confirmed: sencha canister is seeded as a real item; lute/journal/book exist only
    in the character description prose and will be instantiated lazily during play.

**Design notes captured (testing_backlog memory):**

- **Green Room gender/pronouns gap:** `_run_green_room()` extracts description but
  does not write `gender` or `pronouns` to the character record. The player's gender
  is in the prose but not in the structured fields Pass 3 uses for pronoun-aware
  rendering. Fix: extend extraction JSON to include `gender` and `pronouns` and call
  `update_player_character()` with those values.
- **NPC reaction to player description:** an NPC (most likely The Wanderer in HH)
  should react to the player's character description/aspects on first encounter.
  Consider extending The Wanderer's `pending_intent` to reference visible character
  cues once `player.description` is populated by Green Room.
- **Aspect displacement on correction:** adding new material in a correction can push
  previously-extracted aspects out of the three-slot limit. The book got displaced
  when the player added apricot preserves in the third pass. Noted; no fix designed yet.

**Pending / known issues (carried forward):**

- Green Room: gender/pronouns not extracted (see design notes above).
- Green Room: NPC reaction to player description (HH Wanderer; see design notes above).
- Green Room: Tier 1 tests (schema, character_aspect CRUD, extraction flow with MockLLM).
- Green Room: Tier 2 test (HH end-to-end with real LLM).
- `_record_last_tokens()` in `web/game.py` is a no-op. Budget display €0.0000.
- Tier 1 tests: `GameEngine` web API methods (MockLLMClient).
- Tier 2 test: same-room speech guard (address `characters_nearby` NPC, assert no
  attitude delta).
- Deployment to Scaleway (gunicorn + config) not yet done.

---

## Session 32 notes (2026-06-23)

**Completed this session:**

- **I Am a Cat — rebuilt template DB and fixed reset_instance.sql:**
  - `modules/i_am_a_cat/i_am_a_cat.db` rebuilt from `schema/schema.sql` +
    `modules/i_am_a_cat/seed.sql`. Root cause: the consolidated seed.sql (which
    correctly uses `loc_id` / v10 column names) had never been applied to build
    a fresh DB. The template had 0 items; schema was at v12 but data was from
    older incremental migrations that predated items being seeded.
  - After rebuild: 37 items, 13 locations, 5 characters, 8 internal states,
    13 visited locations, 13 location connections, schema v12, instance
    `status=ready`, clock at 3:00 AM.
  - `modules/i_am_a_cat/reset_instance.sql` fixed: was deleting all visited
    locations and only restoring location 1. Now restores all 13 locations so
    Toulouse can quick-move anywhere from turn 1, matching the seed.sql design
    intent ("Toulouse knows every room in the house — it is his territory").
  - Module is now web-playable.

- **Lobby and config updates (committed this session):**
  - `web/config.py`: `AVAILABLE_MODULES` extended with `description` field per
    module; renamed "Meryton Assembly" → "The Meryton Assembly" (key rename
    affects user DB filename slug). Also added `game_id` field per module so
    the web layer knows which game_id to pass to `GameEngine` (Hidden Hostel
    and I Am a Cat are 1; Meryton is 2).
  - `web/templates/lobby.html`: module card template updated to display
    `module.description` below the module name.
  - `web/game.py`: removed hardcoded `game_id=1` in the lobby POST handler;
    now reads `game_id` from `module_cfg`. Without this fix Meryton would fail
    to start (its game record is at id=2, not id=1).

**Pending / known issues:**

- `_record_last_tokens()` in `web/game.py` is a no-op. Budget display €0.0000.
- Green Room Mode engine loop still pending (issue #59).
- Tier 1 tests: `GameEngine` web API methods (MockLLMClient).
- Tier 2 test: same-room speech guard (address `characters_nearby` NPC,
  assert no attitude delta).
- Deployment to Scaleway (gunicorn + config) not yet done.

---

## Session 31 notes (2026-06-23)

**Completed this session:**

- **Scaleway serverless inference backend (`engine/llm/scaleway.py`):**
  - New `ScalewayLLMClient` using the `openai` package with custom `base_url`
    pointed at `https://api.scaleway.ai/v1`.
  - Default model: `mistral-small-3.2-24b-instruct-2506`
    (€0.15/M input, €0.35/M output).
  - `engine/config.py`: `SCALEWAY_*` constants added; `validate()` updated to
    accept `"scaleway"` as a valid backend.
  - `engine/llm/__init__.py`: `"scaleway"` branch added to `get_llm_client()`.
  - Playtest confirmed working against Hidden Hostel (Gin-chan winged cat
    description validated as correct, not hallucination).

- **GameEngine web API (`engine/engine.py`):**
  - Six public methods added for the Flask frontend: `needs_green_room()`,
    `get_green_room_config()`, `extract_green_room_character()`,
    `confirm_green_room()`, `get_opening_scene()`, `step()`.
  - All existing CLI methods (`run()`, `_process_turn()`, etc.) untouched.

- **Pass 2 same-room speech guard (`engine/engine.py`):**
  - Added `SPEECH ACTS REQUIRE PRESENCE` rule to the Pass 2 prompt.
  - Directed speech targeting a `characters_nearby` NPC now resolves as
    unanswered — no attitude deltas, no NPC response, prose describes the
    player's words going unanswered.
  - Also corrected stale `characters_at_location` reference to
    `characters_present` in the NPC ACTIONS ARE AUTHORITATIVE rule.
  - GitHub issue #64 filed for the yelling-to-adjacent-room future feature.

- **Schema v12 (`module_flags` column):**
  - `schema/schema.sql` and `schema/migrations/migrate_v11_to_v12.sql`:
    `module_flags TEXT NOT NULL DEFAULT '{}'` added to `game` table.
  - `engine/db.py`: `module_flags` parsed as JSON when loading game row.
  - Completes the schema prerequisite for Green Room Mode (issue #59).
  - `gh issue comment 59` filed noting v12 is committed.

- **Flask web frontend (`web/`):**
  - `web/config.py`: budget constants, slot limit (10), turn limit (50 alpha),
    Turnstile keys (test defaults), module registry with reset script paths,
    LinkedIn contact URL, message strings.
  - `web/user_db.py`: SQLite user schema (registration, login, turns_used,
    budget tracking), thread-safe per-thread connections.
  - `web/app.py`: Flask application factory, `ACTIVE_SESSIONS` dict,
    blueprint registration.
  - `web/auth.py`: landing page, register (with Cloudflare Turnstile), login,
    logout, `login_required` decorator.
  - `web/game.py`: lobby, Green Room, session turn loop, exit; per-user game
    DB provisioning with `reset_instance.sql` applied on every session start
    (ensures clean state regardless of template DB condition).
  - Templates: base.html (parchment theme), index, register, login, lobby,
    session, green_room, green_room_confirm, slots_full, budget_exhausted,
    turns_exhausted.
  - `web/static/style.css`: parchment/sepia CSS with custom properties,
    animated thinking indicator (ellipsis while engine is working).
  - `session.html` JS: localStorage turn history (survives refresh and
    navigation away/back), cleared on new session start and clean exit.
  - `requirements.txt`: added flask, werkzeug, openai, requests, gunicorn.

- **Tests (`tests/test_web_user_db.py`):**
  - 52 Tier 1 tests for `web/user_db.py`: schema init, registration
    validation, authentication, slot management, turn tracking (alpha limit),
    budget tracking (`_compute_cost` arithmetic), `get_user_by_id`.
  - All 52 passing.

**Design decisions recorded:**

- Turn limit (not token budget) is the primary alpha cost gate: 50 turns per
  account at this stage. Token columns retained for future reference.
- Per-user game DBs are always copied fresh from the module template and
  `reset_instance.sql` is run immediately — no resume across browser sessions
  for now.
- `ACTIVE_SESSIONS` dict (in-process) is sufficient for 10-user alpha;
  requires single gunicorn worker.
- localStorage for session transcript: correct tool for client-side history
  persistence in a stateless web game.

**Pending / known issues:**

- `_record_last_tokens()` in `web/game.py` is a no-op (TODO): Scaleway
  client logs token usage at INFO but does not yet expose a
  `get_last_call_tokens()` method. Budget display shows €0.0000. Add
  `get_last_call_tokens()` to `ScalewayLLMClient` next session.
- Green Room Mode engine implementation still pending (issue #59). Schema
  prerequisite (`module_flags` v12) is now committed. Next: `character_aspect`
  table (schema v13?), Green Room engine loop, Hidden Hostel seed update.
- Tier 1 tests for `GameEngine` web API methods (using MockLLMClient).
- Tier 2 test for same-room speech guard: address a `characters_nearby` NPC
  and assert no attitude delta is applied.
- Deployment to Scaleway (gunicorn + config) not yet done.
- Session resume across browser restarts not implemented (always starts fresh).

---

## Session 30 notes (2026-06-16)

**Completed this session:**

- Committed session 29 docs backlog (`docs/implementation_status.md`,
  `docs/module_authoring.md` — item tables and `player_definition_mode`).
- GitHub issue audit: reviewed `docs/future_features.md` against full issue
  list; filed issues for all untracked features except IP-sensitive or
  commercially sensitive module candidates (Barsoom, Amber, Holmes, Hambly,
  Elizabeth as Agent of the Crown, Suspended, nightmare mechanic).
- New issues filed this session: modules Dracula, Usher, Three Musketeers;
  multiplayer mode; Feature 19a/b/c (Salamandra, fine-tuning, author pipeline);
  Features 1, 6, 11, 12, 13, 17, 23, 24, 25; STT/TTS; collaborative writing
  mode; Fate Core character creation (#59); in-location item search (#42).
- `docs/future_features.md`: added §28 (STT/TTS), §29 (collaborative writing
  mode expanded), §30 (Green Room Mode); updated §20 (Wonderland) to reference
  Green Room mode and capture Alice character creation prompt draft.
- `docs/module_authoring.md`: added `'green_room'` to `player_definition_mode`
  documentation.
- BRIA AI FIBO noted as image generation candidate for illustrated mode (#40);
  design notes added to issues #40 and #41.

**Design decisions recorded:**

- Green Room Mode (`player_definition_mode='green_room'`): pre-game
  module-framed character creation stage using Fate Core structure. Module
  author provides `character_creation_prompt` and `character_creation_hint`
  in `module_flags`. Player defines character out-of-character; opening scene
  reflects the result. Solves the data-quality problem of in-world character
  extraction. Named "Green Room" — player prepares backstage before stepping
  onto the stage.
- Green Room delivery: collect definition out-of-character (reliable), deliver
  in-character (the opening scene reflects who the player described). White
  Rabbit greets Alice rather than interviewing her.
- `character_aspect` table needed for Fate Core Aspects (High Concept, Trouble,
  Aspects) — required by both Green Room Mode and Fate Point Economy (#11).
- Hidden Hostel is the test bed for Green Room Mode before Wonderland.

**Next priority: Green Room Mode (issue #59)**

Schema additions required (next schema version):
- `player_definition_mode` CHECK: add `'green_room'`
- New table: `character_aspect(id, character_id, aspect_text, aspect_type)`
  where `aspect_type IN ('high_concept', 'trouble', 'aspect')`
- `module_flags` fields (JSON, no schema change): `character_creation_prompt`,
  `character_creation_hint`

Implementation steps:
1. Schema migration (new version)
2. Green Room engine loop in `engine.py` (pre-`_render_opening_scene()`)
3. Fate Core collection stage: prompt sequence, LLM interpretation call,
   DB writes (character fields + `character_aspect` records)
4. Hidden Hostel: add `character_creation_prompt` to `module_flags`, set
   `player_definition_mode='green_room'`
5. Tests: Tier 1 (schema, aspect table), Tier 2 (HH Green Room end-to-end)

---

## Session 29 notes (2026-06-14)

**Completed this session:**

- GitHub issues: migrated pending work queue to 35 GitHub issues with custom
  labels (`test`, `schema`, `deferred`, `prompt`, `engine`, `priority:high`,
  `module:Meryton`, `module:IAmACat`, `module:HiddenHostel`). Issue #21
  rewritten to capture Goal-driven socialization design (Meryton).
- `CLAUDE.md`: mandatory GitHub issue update instruction added to Git workflow.
- `docs/test_coverage.md`: new document mapping all engine features to Tier 1/2/3
  test locations with gap notes.
- Feature 25 (Pass 1 character alias resolution): two Tier 3 eval tests added to
  `test_pass1_eval.py` (`test_character_name_resolves_to_correct_id`,
  `test_character_not_at_location_still_resolves`). New rubric criterion
  `character_id_valid_in_context` added to `PASS1_CRITERIA`.
- Marta `resource_provision` goal (0.70, surface, approach, person_environment)
  added to `modules/hidden_hostel/seed.sql`.
- `TestCharacterGoals` class added to `test_hidden_hostel.py` (4 Tier 1 tests:
  Marta goal set, Wanderer exploration goal, Scholar hidden safety goal visibility).
- `test_scenario_entrance.py`: test_060 expanded with pre-conditions (both Marta
  mechanisms simultaneously active before move); test_063 added
  (`test_063_marta_activity_persists_after_offer`) verifying current_activity
  persists through a neutral turn after the kitchen entry.
- Module label cleanup: `module:Meryton`, `module:IAmACat`, `module:HiddenHostel`
  labels created and applied to relevant issues (#1, #3, #10, #16, #17, #21).

**Design decisions recorded:**
- pending_intent discharge is LLM-generated (Pass 2 must emit
  `pending_intent_updates` with `intent: null`). Asserting `pending_intent IS NULL`
  in Tier 2 scenario tests is inherently flaky. The correct test is Tier 1 with
  MockLLMClient in `test_engine.py`. Tier 2 scenario tests should assert only
  deterministic DB state (pre-conditions, player location, current_activity).
- Goal-driven behavior: `resource_provision` goal provides motivational ground
  truth for Marta's proactive hospitality; pending_intent remains the runtime
  trigger. Goal-only behavior test (no pending_intent) deferred — see new issues.

**New GitHub issues filed this session:**
- Tier 1 MockLLM test: pending_intent discharge alongside current_activity
- Tier 2 test: Goal-driven NPC behavior without pending_intent

**Test results (session 29 close):**
- `TestCharacterGoals` (Tier 1): 4/4 passed
- `test_scenario_entrance.py` (Tier 2, full suite): 16/19 passed
  - test_030 (almanac instantiation): intermittent LLM variance — pre-existing
  - test_060 (kitchen move): passes with activity assertion only (pending_intent
    assertion removed — LLM-variable)
  - test_063 (activity persists): passes with pending_intent assertion removed

**Pending (carried forward):**
- Issue #2: test_040/055 intermittent LLM routing flakiness (pre-existing)
- Issue #11: mid-play item instantiation isolated test
- Tier 1 MockLLM test: pending_intent discharge alongside current_activity (new)
- Tier 2 test: Goal-driven NPC behavior without pending_intent (new)
- Species disambiguation Tier 3 eval test (hostel_db / Gin-chan)

---

## Session 28 notes (2026-06-10)

**No code changes this session — design and documentation only.**

**New documents:**
- `docs/ai_concepts_in_dave.md` — personal AI terminology reference connecting RAG,
  model parameters vs. training corpus size, the inference stack (base → instruct →
  quantization → format → engine → API), fine-tuning (LoRA/QLoRA, SFT, DPO), and
  DAVE's DB-as-ground-truth architecture to each concept. Includes a section on
  quantization degradation asymmetry across DAVE's three passes, and design notes on
  using DAVE as an author's assistant platform (ingestion pipeline, world-bible
  queries, fine-tuning for prose style, data sovereignty pitch).

**Future features updated (`docs/future_features.md`):**
- Feature 20 rewritten: "Return to Wonderland" — adult Alice, NPC happiness win
  condition, four solution paths, player self-definition via White Rabbit, Queen's
  hidden tractable motivation, history mechanic.
- Feature 24 added: DAVE as author's assistant platform — same infrastructure, prompt
  prefix swap; world-bible queries, consistency checking, companion writing mode;
  Rachel Neumeier / Tuyo world as primary author partner candidate.
- Feature 25 added: Proper noun alias table — static and dynamic aliases; `valid_when`
  condition on faction role; "Miss Bennet" example; Tuyo marriage taxonomy as
  illustration of why relationship assumptions must not be hardcoded.
- Feature 26 added: Benjamin January / Barbara Hambly — antebellum New Orleans
  1830s–1840s; no author connection; revisit after proof of concept.
- Feature 27 added and expanded: Sherlock Holmes / Victorian London — public domain;
  player character direction is Irene Adler or similar (not Holmes); "outwit Holmes"
  as win condition; surfacing the women of Victorian London (Nightingale, Lovelace,
  Seacole, Besant, etc.) as a design goal; DAVE's social intelligence systems as the
  right mechanic, not deduction.

**Pending (carried from session 27, unchanged):**
  - Internal state drift + prose surfacing test (highest priority)
  - Pass 1 character alias resolution (Feature 25)
  - Mid-play item instantiation test
  - Item fill-state property convention
  - test_040/055 intermittent routing issue
  - i_am_a_cat seed.sql v1 column names

---

## Session 27 notes (2026-06-07)

**Completed this session:**

- **Scholar book exchange — working (18/18 passing):**
  - Scholar `pending_intent` updated with explicit gift clause: if a guest gives
    something of genuine value, give "Mysteries of the Hidden Hostel" immediately
    as a permanent gift ("press it into their hands; this is not a loan").
  - Book transfer now happens during test_090 (almanac exchange turn), not test_100.
  - test_090: now asserts both sides — almanac leaves, book arrives same turn.
  - test_100: repurposed as a simple social follow-up (no item assertion).
  - `engine/engine.py` Pass 2 prompt: added BORROW/LOAN note — willing loans are
    physical handovers (item_transfers), same as gifts. No separate loan flag yet.

- **NPC wander ranges tightened for reliable multi-hop corridor test:**
  - Scholar: `[3,4]` → `[4,4]` (Room A only — Scholar is hiding, stays in their room)
  - Wanderer: `[1,2,3]` → `[1,2]` (Common Room + Kitchen — goes where guests are)
  - Upper Corridor (3) is now definitively empty during play; multi-hop test reliable.

- **Playtest reference saved:**
  - `docs/playtests/hidden_hostel_playtest_01.txt` — annotated playtest session
    documenting tea-making sequence, hunger surfacing, player-authored state inference,
    NPC-referenced object instantiation, and item fill-state design notes.

**Design notes captured (memory + testing backlog):**
  - Item fill-state: teapots, cups etc. should track fill_state in properties JSON;
    appropriate for contemplative modules (Hidden Hostel, Meryton). No schema change
    needed — properties blob already supports this.
  - Player-authored state inference: if player writes their own physical state
    ("my stomach growls"), Pass 2 should emit internal_state_deltas to match.
    Complement: passive drift should surface in Pass 3 prose without player input.
  - NPC-referenced object instantiation: Marta saying "work at the smaller table"
    should trigger item_instantiations if no such item exists. Future feature.

**Test results (session 27 close):**
  - `tests/test_scenario_entrance.py`: 18/18 passing (occasional test_040 flakiness
    from LLM routing "go inside" → kitchen; not a code bug)
  - `tests/test_item_container.py`: 10/10 passing (4 Tier 1 + 6 Tier 2)

**Pending:**
  - Internal state drift + prose surfacing test (highest priority next test to write)
  - Mid-play item instantiation test (tea-making sequence from playtest_01)
  - Item fill-state property convention (document in module_authoring.md)
  - NPC-referenced object instantiation (future feature)
  - test_040/055 intermittent: "go inside" sometimes routes to kitchen; investigate
    Blue Door pending_intent wording or Pass 1 move resolution.
  - i_am_a_cat seed.sql: still uses v1 column names, not yet updated.
  - Closed container "open" mechanic: deferred.
  - Pass 1 character alias resolution: currently the `known_locations` dict gives
    Pass 1 explicit name→ID mapping for locations, but no equivalent exists for
    characters. A player typing "ask the innkeeper about the tea" relies on the LLM
    inferring that "the innkeeper" is Marta. This works for well-known source material
    (P&P characters are in the training data) but fails silently for original modules.
    A `known_characters` dict in the Pass 1 context packet (including common aliases
    per character) is the fix — same pattern as known_locations. Some aliases are
    dynamic (e.g. "Miss Bennet" shifts from Jane to Elizabeth after Jane's marriage);
    dynamic aliases are conditioned on faction membership/role. See Feature 25 in
    `docs/future_features.md`.

---

---

## Session 26 notes (2026-06-05)

**Completed this session:**

- **Surface vs. container distinction in item properties:**
  - `surface: true` — open surface (plate, tray, table, worktable); contents always
    visible; recursive walk in context packet
  - `container: true` — closed container (bag, canister); contents NOT shown in context
    (not visible without opening — future mechanic)
  - Updated all seeded furniture and kitchen items: low table, worktable, tray, plate
    all changed from `container: true` to `surface: true` in `seed.sql` and
    `reset_instance.sql`

- **Recursive surface visibility in context packets (`engine/context.py`):**
  - Added `_surface_contents(db, item_id, depth, max_depth=3)` helper — recursively
    collects items on surface items, stopping at closed containers or depth limit
  - `_build_location_context` now calls `_surface_contents` for `surface: true` items;
    closed containers show no contents
  - NPC character profiles also show inventory (added previous session); closed
    containers in NPC packs remain opaque

- **New seeded items in Hidden Hostel:**
  - Common Room (loc_id=1): 3 chairs (sittable), low table (surface)
  - Kitchen (loc_id=2): worktable (surface), tray of hot rolls (surface),
    12 individual hot rolls (item_id=tray), plate (surface)
  - Existing standalone tray removed and replaced with the above hierarchy

- **`engine/llm/base.py` — fence-stripping bug fix:**
  - `call_json` now stops at the first ` ``` ` line after the opening fence,
    discarding any trailing content the LLM adds after the closing fence.
    Prevents "Extra data" JSON parse errors when the LLM echoes input or adds
    explanation text after the code block.

- **`engine/engine.py` — Pass 2 prompt improvements:**
  - `item_transfers.to_item_id` documentation clarified: covers both "on a surface"
    and "inside a container"; explicit instruction to prefer `to_item_id` over
    `to_loc_id` when the player names a specific surface
  - Added rule: items already in a character's inventory (char_id set) do NOT need
    an `item_transfers` entry when the character moves — they travel automatically

- **`tests/test_item_container.py` — new test file:**
  - `TestSurfaceVisibility` (Tier 1, no LLM): 4 tests for the recursive surface walk
    — kitchen tray contents, empty plate, closed container hidden, depth-2 nesting
    (plate on table, rolls on plate). All 4 pass in default suite.
  - `TestItemContainerHierarchy` (Tier 2, --llm): 6 sequential LLM tests for the
    full item manipulation scenario. All 6 passing.

- **`engine/db.py`:** Added `get_items_in_container(container_item_id)` method.

**Test results (session 26 close):**
  - `tests/test_item_container.py`: 10/10 passing (4 Tier 1 + 6 Tier 2)
  - `tests/test_scenario_entrance.py`: 17/18 passing

**Pending / known issues:**
  - `test_scenario_entrance.py` test_100 (Scholar gives book): 17/18 passing, this
    one remains. Scholar inventory is in context; Pass 2 generates correct warm prose
    but never emits item_transfers. Tried: seeding book, NPC inventory in context,
    "may I borrow a book" prompt. Hypothesis: "borrow" is a semantic trap — Pass 2
    reasons no DB transfer is needed for a loan. Next to try: (a) change verb to
    "give" or "share"; (b) add Scholar pending_intent to give a book to a kind guest;
    (c) add `"giftable": true` to book properties. Deferred. (See memory note.)
  - test_040/055 flakiness: "go inside" occasionally routes to Kitchen instead of
    Common Room. Investigate Blue Door routing or door pending_intent wording.
  - Chair single-occupancy (`sittable: true`): chairs typically hold one person.
    Not enforced — Pass 2 expected to handle naturally. Revisit if a module needs
    sitting mechanics to be significant. (Memory note saved.)
  - Hand-slot capacity not enforced: Pass 2 may skip in-hand state and route items
    directly to nearby surfaces. Testing in-hand intermediate state deferred.
  - i_am_a_cat `seed.sql` still uses v1 column names (`location_id`,
    `held_by_character_id`). Needs update before that module is playable.
  - Closed container "open" mechanic: `container: true` items currently hide contents
    but there is no "open container" action yet. Deferred.
  - Add `"format": "json"` to Ollama Pass 1/Pass 2 payloads.

---

## Session 25 notes (2026-06-04)

**Completed this session:**

- **Schema v10: unified item location (loc_id / char_id / item_id)**
  - `schema/schema.sql`: `item` table replaced with v10 definition. Three nullable
    FK columns (`loc_id → location`, `char_id → character`, `item_id → item`) with
    table-level CHECK enforcing exactly one non-null. Added `location_description`
    and `slot` columns. `character_item` table replaced with tombstone comment.
    Indexes updated: `idx_item_location` + `idx_character_item` replaced by
    `idx_item_loc_id` + `idx_item_char_id`.
  - `schema/migrations/migrate_v9_to_v10.sql`: new migration; migrates existing
    item rows and character_item rows; drops character_item; renames item_new → item.
    CHECK constraint correctly placed after all column definitions (SQLite requirement).

- **`engine/db.py` updated for v10:**
  - `get_items_at_location`: `current_location_id` → `loc_id`
  - `get_character_inventory`: JOIN on character_item replaced with direct
    `WHERE char_id = ?` query on item row
  - `create_item`: now takes `loc_id`, `char_id`, `item_id`, `slot`,
    `location_description`; sets all in a single INSERT
  - `transfer_item_to_character`: single UPDATE (sets char_id, clears loc_id/item_id)
  - `transfer_item_to_location`: single UPDATE (sets loc_id, clears char_id/item_id;
    optional `is_confirmed` override for deliberate player drops)
  - `transfer_item_to_container`: new method (sets item_id FK)

- **`engine/engine.py` updated for v10:**
  - `item_transfers` outcome handler added: moves existing items between
    character/location/container; validates exactly one destination; sets
    `is_confirmed=1` on location drops
  - `item_instantiations` handler: rewritten to pass FK directly to `create_item`
    (no two-step create-then-transfer); supports `container_item_id` and
    `location_description`; fallback to player's current location when unspecified
  - `_ALLOWED_ITEM_FIELDS` updated: `current_location_id` removed; `is_visible` and
    `quality` added; FK columns correctly excluded (CHECK requires atomic update)
  - Pass 2 prompt: `item_transfers` field documented; `item_instantiations` updated
    with `container_item_id` and `location_description`; `item_changes` note clarified
  - Fallback outcome schema: `item_transfers: []` added

- **`engine/context.py`: NPC inventory added to character profiles**
  - `_build_character_profile` now includes an `inventory` field for all characters
    (compact: id, name, slot). Pass 2 can now reference item_ids held by NPCs when
    generating `item_transfers` entries (e.g. Scholar giving a book to the player).

- **Hidden Hostel seed and reset updated for v10:**
  - Sencha canister: INSERT now uses `char_id=1, slot='in_pack'`; no character_item row
  - Tray of hot rolls: INSERT uses `loc_id=2`
  - Scholar's book seeded: "Mysteries of the Hidden Hostel" (char_id=4, slot='in_pack')
    — gives Pass 2 a concrete item_id for the Scholar→player gift turn
  - Old Soldier `wander_range` changed from `[1,3]` to `[1,1]` (Common Room only).
    She is stationed near the entrance; wandering to the Upper Corridor was both
    out of character and caused test_110 (multi-hop return) to fail non-deterministically.
  - `reset_instance.sql`: `DELETE FROM character_item` removed; all three seeded
    items restored on reset

- **`tests/test_scenario_entrance.py` updated:**
  - `get_inventory_names` helper: JOIN on character_item replaced with `WHERE char_id=?`
  - Tests 090/100: `@pytest.mark.xfail` removed (item_transfers now implemented)
  - Test docstrings and summary comments updated to reference v10 column names

**Test results (last run, session 25):**
  - 15/18 passing
  - test_040 (enter hostel): LLM nondeterminism — "go inside" occasionally routes
    to Kitchen (2) instead of Common Room (1). Not a code bug; likely a Pass 1
    interpretation issue with the Blue Door pending_intent routing.
  - test_055 (Wanderer pending_intent cleared): cascade from test_040 — if player
    arrived in Kitchen, the greeting turn in test_050 ran without Wanderer present.
  - test_100 (Scholar gives book): Pass 2 generates correct prose but does not emit
    `item_transfers` despite Scholar's inventory (book id=3) now visible in context.
    Cause unclear — may need a stronger prompt instruction or an NPC intent mechanism.

**Pending / known issues:**
  - test_040/055 flakiness: "go inside" routing sometimes lands in Kitchen.
    Investigate Blue Door routing logic or tighten the pending_intent wording.
  - test_100 persistent failure: Scholar gives appropriate prose but no item_transfers.
    NPC giving an item may need explicit support (pending_intent? engine-side NPC action?).
  - Tray of hot rolls sometimes ends up in player inventory (carried whole) instead
    of player receiving a portion. Not a crash; test_065 still passes because "tray
    of hot rolls" contains "roll". Correct behavior would instantiate a "rolls" item.
    Noted as known behavior; portability semantics deferred to next session.
  - NPC notification / reaction mechanic (Old Soldier reacting to Wanderer introductions):
    deferred to future session.
  - Interruptable activities: deferred.
  - i_am_a_cat `seed.sql` still uses v1 column names (`location_id`, `held_by_character_id`);
    not updated since that module is not in active test scope. Needs update before
    the i_am_a_cat module is playable.
  - Add `"format": "json"` to Ollama Pass 1/Pass 2 payloads (`engine/llm/ollama.py`).

---

## Session 24 notes (2026-06-03)

**Completed this session:**

- **Three test failures fixed (`test_scenario_entrance.py`):**
  - `db.py` `get_items_at_location`: added `visible_only: bool = False` parameter;
    when True, adds `AND is_confirmed = 1` to exclude unconfirmed items from
    path-interruption checks. Fixes tests 10 and 12.
  - `test_13`: `action_log` query corrected from nonexistent `game_instance_id`
    column to `game_id`. Fixes test 13.

- **Activity expiry test redesigned (test_10 + test_11):**
  - `test_10` now explicitly sets a reading activity on the player via
    `db.set_character_activity()` with `duration = (1230 - clock_now) + 15`,
    expiring 15 minutes after Marta's 8:30 PM deadline regardless of current clock.
  - `test_11` derives expiry times from stored `activity_started_at +
    activity_estimated_duration` fields (no hard-coded clock values), advances
    to `max(player_expiry, marta_expiry) + 1`, and asserts both activities clear.
    Exercises the `activity_estimated_duration` field end-to-end.

- **Old Soldier moved from Upper Corridor (3) to Common Room (1):**
  - `seed.sql` and `reset_instance.sql` updated: location, description, activity
    description, `surface_motivation`, `wander_range` (`[3,4]` → `[1,3]`),
    and `character_visited_location` entry all updated.
  - Upper Corridor is now empty at session start — the first clean unobstructed
    multi-hop path in the module (Common Room → Upper Corridor → Room A).
  - `test_07` docstring updated to explain the first-visit stop at Upper Corridor
    (BFS requires destination familiarity; adjacent hops skip the check).
  - `test_10` multi-hop return from Room A now asserts direct arrival at Common
    Room (1) in a single turn — serves as the multi-hop correctness check.

- **Test suite result: 11 passed, 2 xfailed, 0 failed.**

**Pending from this session (carried forward):**

- Schema v10: item location redesign (loc_id / char_id / item_id split). See
  session 23 design notes.
- `item_transfers` outcome field (depends on v10). Tests 08/09 remain xfail.
- `test_13` gap: test only delivers the dinner message to the Scholar upstairs.
  A complete version would also go back to the Common Room, tell the Soldier,
  and assert her emotional_state or attitude shifts. Left for a future session.
- Future test idea: when the Wanderer greets the player and introduces Gin-chan,
  if the Wanderer also mentions the Old Soldier (now visible in the Common Room),
  the Soldier should react — at minimum a visible attitude or emotional_state
  shift given her distrust of strangers and negative attitude toward the Wanderer
  (-0.40). Tier 3 / LLM-eval concern. Not yet designed as a test.
- Add `"format": "json"` to Ollama Pass 1/Pass 2 payloads in `engine/llm/ollama.py`.
- Verbal tic review: scan Haiku transcript for `[verb] with the air/manner of someone who`.
- Test coverage for v9 seed elements: tray of hot rolls, multi-part pending_intent,
  `player_character_update` handler.

---

## Session 23 notes (2026-06-03)

**Completed this session:**

- **Mirror mechanic redesigned — moved from prompt engineering to seed/pending_intent:**
  - Blue Door `pending_intent` updated in `seed.sql` and `reset_instance.sql` to
    encode a player-state precondition: invite self-examination before opening;
    do not open or suggest entry until `player.description` is non-null.
  - `seed.sql` Blue Door comment block documents this as the canonical example of
    a pending_intent with a player-state precondition rather than an in-world trigger.
  - `seed.sql` Blue Door `speech_filter` updated to mention mirror/light behavior
    (previously only mentioned opening/closing/scent).
  - `OPENING_SCENE_PROMPT_TEMPLATE` in `engine.py`: removed the fragile mirror-specific
    rule. Replaced with a general rule: render NPC pending_intents as atmospheric
    physical action; npc_object acts but does not speak.
  - Pass 2 `player_character_update` prompt: removed the default mirror-text fallback
    ("The image in the mirror is vague and undefined..."). Simplified null condition:
    set to null if no self-defining statements this turn; do not populate based on
    proximity to a mirror alone.
  - Net result: mirror behavior is now a module design concern (the door seed), not
    an engine concern. The engine's opening scene prompt generalizes to any NPC with
    a pending_intent at the starting location.

**Design note — pending_intent precondition pattern:**
  The Blue Door is the first example of a pending_intent that references player state
  (`player.description is non-null`) as its discharge condition rather than an
  in-world event. This pattern will be useful in other modules: any NPC that needs
  to wait for a player action before advancing a situation can encode the condition
  in natural language in their pending_intent, and Pass 2 evaluates it against the
  context packet. No engine code changes needed.

**Pending from this session (carried forward):**

- Schema v10: item location redesign (loc_id / char_id / item_id split; slot partial
  unique index; container support). See session 23 design notes below.
- `item_transfers` outcome field (depends on v10 schema).
- Mirror mechanic: needs playtest to confirm the pending_intent approach works as
  intended. Run reset + playtest before next commit on this area.
- Rebuild `hidden_hostel.db` fresh from terminal.
- Add `"format": "json"` to Ollama Pass 1 and Pass 2 payloads in `engine/llm/ollama.py`.
- Verbal tic review: scan Haiku transcript for `[verb] with the air/manner of someone who`.
- Test coverage for v9 seed elements: tray of hot rolls, multi-part pending_intent,
  `player_character_update` handler.
- §3a: `item_transfers` outcome field.

**Session 23 design notes — v10 item schema:**
  Agreed design for schema v10:
  - Replace `item.current_location_id` and `character_item` table with three nullable
    FK columns on `item`: `loc_id` (→ location), `char_id` (→ character), `item_id`
    (→ item, for container contents). CHECK constraint enforces exactly one is set.
  - Add `location_description` TEXT NULL — free-text position within the container/
    location/character (Pass 3 flavor; also encodes slot for character-held items).
  - Add `slot` TEXT NULL — normalized exclusive position name (e.g. 'right_hand',
    'worn'). Partial unique index on (char_id, slot) enforces one item per exclusive
    slot; null slot = non-exclusive (multiple items in pack are all slot=NULL).
  - Container capacity: `"container": true` in item.properties JSON — no new column.
  - Location resolution is transitive at query time (recursive CTE); moving a
    container does not cascade-update its contents.
  - Visibility is depth-1 by default; recursive query fires on "open container" /
    "search room" intent.

---

## Session 22 notes (2026-06-03)

**Completed this session:**

- **Default model changed to Haiku:** `engine/config.py` `CLAUDE_MODEL` default
  changed from `claude-sonnet-4-6` to `claude-haiku-4-5-20251001`. Carried from
  session 21 "do first" note. `docs/configuration.md` table updated to match.

- **Phase 2 model target updated to Salamandra 7B:** Across all docs and README,
  Salamandra 7B (Barcelona Supercomputing Center, Common Corpus trained) is now
  the primary Phase 2 target. Mistral 7B remains a supported fallback. Rationale:
  Common Corpus training (public domain + openly licensed only); multilingual
  capability; Apache 2.0. Updated: `README.md`, `docs/design_v05.md`,
  `docs/configuration.md`, `CLAUDE.md`.

- **Token logging promoted to INFO:** `engine/llm/claude.py` token count log line
  moved from DEBUG to INFO so per-call token usage is visible in play sessions
  without enabling full debug output.

- **Feature 19 added:** Three sub-entries in `docs/future_features.md`:
  19a (Salamandra 7B as inference target), 19b (fine-tuning for Pass 2 adjudication),
  19c (author module development pipeline — aspirational).

- **Features 20, 21, 22 added** (module design notes captured from playtester
  suggestions, evening 2026-06-03):
  - Feature 20: Module — Alice's Adventures in Wonderland (priority). Size as
    internal_state float; faction rep path to trial win; logical puzzles as social
    adjudication; Through the Looking Glass as follow-on.
  - Feature 21: Module — Dracula (Bram Stoker) (priority, alongside 20). Epistolary
    = partial knowledge; Transylvania opening with Harker as player; Dracula's
    hidden motivation; "knowing player" design challenge and what-if frame.
  - Feature 22: Module — The Fall of the House of Usher (Poe). Small cast; Roderick's
    hidden motivation; escape objective; tone challenge; lower priority; Sonnet as
    construction tool.

**Pending from this session (carried forward):**

- Mirror mechanic: opening scene may still render a reflection before player has
  defined themselves. One more prompt pass needed.
- Rebuild `hidden_hostel.db` fresh from terminal.
- Add `"format": "json"` to Ollama Pass 1 and Pass 2 payloads in `engine/llm/ollama.py`.
- Verbal tic review: scan Haiku transcript for `[verb] with the air/manner of someone who`.
- Test coverage for v9 seed elements: tray of hot rolls, multi-part pending_intent,
  `player_character_update` handler.
- §3a: `item_transfers` outcome field design (Pass 2 used `item_changes` with `slot`
  field to transfer preserves to Marta — engine correctly rejected it; proper
  transfer mechanism needed).

---

## Session 21 notes (2026-05-31)

**Completed this session:**

- **Opening scene prompt fixed:**
  - Added explicit rule: do NOT narrate the player taking any action (no reaching
    for handles, no stepping forward, no doors opening). Prior sessions produced
    prose that crossed the threshold before the player moved.
  - Removed interior-state inference (the LLM was writing "your curiosity pulls
    you forward" — player interiority belongs to the player).
  - Mirror invitation rule rewritten to be concrete and direct: if
    `player.description` is null, describe the mirror as a surface the player
    can look into — not as already showing a reflection.
  - `engine/context.py` `build_pass3_packet`: `player.description` now included
    in the player summary so the opening scene renderer can check it.

- **Reset script fixed:**
  - `modules/hidden_hostel/reset_instance.sql`: player `description`, `gender`,
    and `pronouns` now cleared to NULL on reset. These are instance state (set
    during play via `player_character_update`); must be null at session start so
    the mirror invitation triggers correctly.
  - Header comments updated: player character fields distinguished from stable
    NPC fields in "What this does NOT touch" list.

- **Tray of hot rolls seeded in kitchen:**
  - `modules/hidden_hostel/seed.sql`: `item` record for "tray of hot rolls"
    placed at Kitchen (location_id=2) with `is_confirmed=1`.
  - Marta's `pending_intent` updated to two-part: (1) offer hot rolls to any
    guest who enters while cooking is in progress; (2) serve the full meal at
    8:30 PM. Tests multi-part pending_intent discharge alongside current_activity.
  - Same changes applied to `modules/hidden_hostel/reset_instance.sql`.
  - Feature coverage table in seed.sql header updated to document the
    multi-part pending_intent test case explicitly. Design rationale: exercises
    pending_intent partially discharging (part 1 fires on guest arrival) while
    part 2 remains live, alongside a concurrent current_activity — a combination
    not previously covered.

- **Brace-escaping guard added:**
  - `engine/engine.py`: comment block added above the prompt template section
    explaining the `str.format()` escaping rule. New literal `{` and `}` in
    template text must be doubled; `{context_json}` is the only single-brace
    placeholder.
  - `CLAUDE.md` Code Standards: one-line note on the same rule added so it is
    visible at session start.

- **Seed header tidied:** schema version corrected to 9; character count updated
  to 7 (includes Blue Door as npc_object); location count updated to 6; stale
  speech_filter PENDING note removed (v9 is live).

- **Playtest: entrance flow confirmed working (Sonnet backend):**
  - Player self-description via mirror captured correctly via `player_character_update`.
  - Wanderer introduced Gin-chan as resident, not pet, as designed.
  - Kitchen entrance: Marta offered hot rolls and returned to work — multi-part
    pending_intent firing correctly alongside active cooking task.
  - Player-offered preserves accepted with attitude shift — emergent reciprocity
    from OCEAN + goals, no special case.

- **Model clarification:** Session ran on Sonnet (config.py default). Haiku is
  the intended Phase 1 test target. Memory note written: change config.py default
  to `claude-haiku-4-5-20251001` at the start of next session.

**Pending from this session (carried forward):**

- **Do first next session:** Change `CLAUDE_MODEL` default in `engine/config.py`
  from `claude-sonnet-4-6` to `claude-haiku-4-5-20251001`. Update
  `docs/configuration.md` default value table to match.
- Mirror mechanic: opening scene may still render a reflection before player has
  defined themselves — LLM reads the invitation rule as license to show one.
  One more prompt pass; try wording that explicitly withholds the reflection
  until the player acts.
- Rebuild `hidden_hostel.db` fresh from terminal (sandbox cannot delete mounted
  files; reset_instance.sql is sufficient for play, clean rebuild is cleaner).
- Add `"format": "json"` to Ollama Pass 1 and Pass 2 payloads in
  `engine/llm/ollama.py`.
- Verbal tic review: scan Haiku transcript for `[verb] with the air/manner of
  someone who` pattern.
- Test coverage for new v9 seed elements: tray of hot rolls, multi-part
  pending_intent pattern, player_character_update handler.

---

## Session 20 notes (2026-05-31)

**Completed this session:**

- **Schema v9 fully landed (seed + reset):**
  - `modules/hidden_hostel/seed.sql` updated with all v9 additions:
    - Location 6 (Outside the Hostel Door): `social_setting='public'`, `witness_count=0`, liminal arrival space with mirror-paned blue door
    - Location 1 connection updated: `(1, 6, 'door', 1, NULL)` — two-way, passable
    - The Traveller: `current_location_id=6`, `gender=NULL`, `pronouns=NULL`, `description=NULL` (undefined until self-definition)
    - The Blue Door (character id=7): `role='npc_object'`, `species='object'`, `current_location_id=6`, `speech_filter='silent: ...'`, `pending_intent='welcome the arriving traveller...'`
    - Gin-chan: `speech_filter='unintelligible: render all communication as non-verbal...'` applied via UPDATE after INSERT
    - `character_visited_location` for The Traveller: `(1, 6)` (Outside only; not yet entered)
    - Item: sencha canister (game_id=1, properties JSON, description with crane engraving)
    - `character_item`: sencha canister in Traveller's pack (`slot='in_pack'`)
  - `modules/hidden_hostel/reset_instance.sql` updated for v9:
    - Traveller reset to `current_location_id=6`
    - Blue Door (id=7) reset block added (location, emotional_state, pending_intent)
    - `character_attitude` and `character_faction_reputation` DELETE/INSERT ranges include id=7
    - `character_visited_location` reset includes `(1, 6)` and `(7, 6)`; location_detail reset includes location 6
    - Items reset section: DELETE all game_id=1 items + character_item, then re-INSERT sencha canister + character_item row
  - Both seed and reset verified against clean build in Python sqlite3 (sandbox lacks sqlite3 CLI binary)

- **Engine item system + player self-definition support (v9 engine):**
  - `engine/db.py`: fixed two stale pre-v9 item query methods (`get_items_at_location` used wrong column `location_id`; `get_items_held_by` used removed column `held_by_character_id`). Replaced both with v9-correct implementations. Added: `get_character_inventory` (joins through `character_item`), `create_item`, `transfer_item_to_character`, `transfer_item_to_location`, `update_player_character`.
  - `engine/context.py`: player inventory now included in Pass 2 packet (`player.inventory`). `speech_filter` now included in all character profiles (Blue Door's `'silent: ...'` and Gin-chan's `'unintelligible: ...'` reach Pass 2). Location item summary updated to v9 fields (`properties`, `is_confirmed`; removed stale `quality`, `held_by_character_id`).
  - `engine/engine.py`: `item_changes` allowed-field list updated to v9 columns. Two new outcome handlers: `item_instantiations` (creates item + places in inventory or at location; includes duplicate guard) and `player_character_update` (writes description/gender/pronouns to player character record). Both handlers added to Pass 2 prompt with full instructions. The default mirror text for undefined players ("The image in the mirror is vague and undefined. Perhaps the mirror needs to be cleaned.") is in the Pass 2 prompt instruction — the LLM supplies it; the engine just applies whatever it gets.
  - Design decision: `player_definition_mode` field is retained in the schema as documentation metadata (module authors signal intent), but the engine does not branch on it. The narrative elements (mirror in the door, opening scene) do the work; the normal turn loop handles player self-description via `player_character_update`.
  - All changes verified: imports clean, inventory query returns sencha canister, context packet contains inventory and Blue Door speech_filter, character update writes correctly.

**Pending from this session (carried forward):**

- Rebuild `hidden_hostel.db` from terminal (`rm` old db + `sqlite3` fresh build from schema + seed)
- Add `"format": "json"` to Ollama Pass 1 and Pass 2 payloads in `engine/llm/ollama.py`
- Verbal tic review: scan Haiku transcript for `[verb] with the air/manner of someone who` pattern
- Test coverage for v9 seed elements (Blue Door npc_object role, sencha canister inventory, location 6, player_character_update outcome handler)
- Playtest the self-definition entrance once hidden_hostel.db is rebuilt

---

## Session 19 notes (2026-05-30)

**Completed this session:**

- **`--transcript` argparse fix:** `--transcript` now accepts an optional PATH argument
  (`nargs='?'`). Bare `--transcript` (no path) auto-generates a timestamped file in
  `transcripts/`, same as the default behavior. Supplying a path still works as before.
  Updated the docstring in `main()` to document the bare-flag form.

- **Hunger as emergent feature (design note):** The Hidden Hostel seed gives The Traveller
  a `hunger` internal state (value=0.65, rate=+0.001/min). No item system or explicit
  "eat food" handler is required. When the player asks Marta for food, Pass 2 adjudicates
  the interaction and applies a negative `internal_state_delta` to `hunger`. The state
  drops, Pass 3 narrates the meal, and the system works without any item-tracking
  machinery. This is documented as a feature of DAVE's architecture: social/narrative
  actions can satisfy physical-state needs through adjudication alone, deferring an item
  system until it adds distinct value.

- **Hidden Hostel seed updates for playability:**
  - `game.tone` → `'iyashikei'` (healing/slice-of-life warmth; unhurried)
  - `internal_state_display` → includes `"hunger": "prose"`
  - Common Room `description_skeleton` rewritten as arrival framing (door clicking shut behind player)
  - The Wanderer gains `pending_intent` to greet the player, introduce Gin-chan, and suggest asking Marta for food
  - New `internal_state` row: The Traveller `hunger = 0.65` (high from travel, drifts up slowly)
  - `reset_instance.sql` updated to match: Wanderer's intent and hunger reset included

- **Playtest validation — emergent attitude and faction outcomes (2026-05-30):**
  A 15-turn Hidden Hostel session (Haiku backend) produced the following end state,
  entirely from adjudication with no hand-coded special cases:

  | Character | Start | End | Driver |
  |-----------|-------|-----|--------|
  | The Wanderer | 0.65 | 0.96 | Warmth + acknowledging his travel experience |
  | Gin-chan | 0.50 | 0.87 | Offering tea as a peer, not a pet |
  | Marta | 0.35 | 0.73 | Helping chop vegetables; quiet, respectful presence |
  | The Scholar | 0.60 | 0.60 | No contact |
  | The Old Soldier | −0.30 | −0.30 | No contact |

  Faction standing (`hosts_of_the_hostel`): 0.40 → 0.97.
  Pass 2 notes: *"Respectful gesture of hospitality toward a hostel resident; tea as shared comfort."*

  Key observations: Marta's shift (wary → warm) came from OCEAN + goals responding to
  collaborative work, with no explicit instruction to reward kitchen help. Faction standing
  jumped on the Gin-chan tea offer, correctly identifying it as the hostel-etiquette moment
  the faction description singles out. The Old Soldier's suspicion was correctly stable — no
  contact, no change. Documented in README as a canonical example of intended engine behavior.

  Also noted: `outcome_type` is NULL in all `action_log` rows — it is not being stored in
  `action_json` by Pass 2. Minor gap; add to action_json storage if needed for analytics.

- **NPC wander narration:** When an NPC wanders into or out of the player's current
  location, the move is currently silent — Pass 3 just sees the NPC already in the new
  position. The Wanderer appeared in the Kitchen on turn 2 with no narrated departure
  from the Common Room. The fix design is already captured in lower-priority notes
  (session 14): pass a `newly_arrived_npcs` list in the Pass 2 context packet.
  This should also cover the Elizabeth Bennet assembly-arrival case. No schema change needed.

- **Item system — motivating use cases from Hidden Hostel playtest:**
  The session demonstrated two distinct item scenarios that lazy ambient instantiation
  cannot cover:
  1. **Known item at game start**: The player arrives carrying a specific object from
     their world (a tin of fine tea, a teacup). This requires an `item` record and
     `character_item` join row seeded at game start. The object persists across turns
     and can be given, lost, or used.
  2. **Player-driven lazy instantiation**: The teapot, linden flower jar, mismatched
     teacups, and painted tray were conjured by the player's descriptions and rendered
     faithfully — but exist only in prose. A cup the player wants to *give* Marta as a
     gift requires a real item record to persist and be referenced in future turns.
  These two cases should be implemented and tested separately. The Hidden Hostel is the
  right test module for both (neutral setting, no faction complexity, gift-giving and
  collecting fit the iyashikei tone).

**Pending from this session (carried forward):**

- Rebuild hidden_hostel.db from terminal (`rm` blocked in sandbox) and run a play session
- Add `"format": "json"` to Ollama Pass 1 and Pass 2 payloads in `engine/llm/ollama.py`
- Verbal tic review: scan Haiku transcript for `[verb] with the air/manner of someone who` pattern

---

## Session 18 closing notes (2026-05-30)

**This session:** Phillips spelling fix (§6 complete); Hidden Hostel test suite.

**Completed this session:**

- **§6 closed:** Fixed Thomas Philips → Thomas Phillips throughout: `modules/Meryton/seed.sql`,
  `modules/Meryton/reset_instance.sql`, `schema/schema.sql`, `schema/migrations/migrate_v7_to_v8.sql`,
  and all affected fields in the live `meryton.db` (name, description, apparent_status,
  faction_reputation notes).

- `tests/test_hidden_hostel.py`: New Tier 1 test file, 37 tests across 8 classes. **37/37 passing.**
  Covers all Hidden Hostel feature coverage goals:
  - §A Staircase connection traversal (Common Room ↔ Upper Corridor)
  - §B Impassable connection (Upper Corridor → Room B blocked)
  - §C Wander suppression: pending_intent (The Scholar)
  - §D Wander suppression: active timed activity (Marta)
  - §E Wander suppression: sleepiness threshold (Gin-chan)
  - §F Activity expiry: non-renewable activity auto-clears after clock passes expiry
  - §G Renewable activity is NOT auto-cleared by engine
  - §H Hidden motivation access control (Scholar, access_hidden_motivation=0)
  - §I Faction reputation (Traveller and Marta in hosts_of_the_hostel)
  - §J Passive state drift (curiosity+, fatigue+, sleepiness−) with clamping
  - §K Negative attitude reads correctly (Old Soldier → Traveller −0.30)
  - §L Attitude delta application and clamping at ±1.0
  - §M Pre-seeded location_detail retrieval for Common Room; Kitchen starts clean

  Uses a `tmp_hostel_db` fixture (function-scoped) that loads the real
  `modules/hidden_hostel/seed.sql` against the canonical schema. A
  `hostel_engine` fixture provides a full `GameEngine` instance with mock LLM
  for tests that call engine methods directly.

**Pending from this session:**
- `docs/test_suite.md`: Updated with Hidden Hostel test descriptions, second test world reference table, extended "Extending the Suite" guidance.

---

## Session 17 closing notes (2026-05-29)

**This session:** Movement parsing test coverage; Hidden Hostel test world module.

**Completed this session:**

- `tests/test_pass1_eval.py`: Added three Tier 3 (`--llm-eval`) regression tests for
  the session 15 MOVEMENT PHRASES fix — `proceed to the Hall`, `head to the Hall`,
  `make our way to the Hall`. All assert `action_type=move` + `target_location_id=2`
  and pass the LLM-as-judge rubric.
- `docs/test_suite.md`: Updated Tier 3 / Pass 1 eval section to list the three new tests.
- `schema/schema.sql`: Fixed v8 schema_version INSERT (was missing; character table had
  v8 activity fields but final version row still said v7).
- `modules/hidden_hostel/seed.sql`: New test world module. 5 locations, 4 connections
  (including staircase 1↔3 and locked 3↔5), 6 characters, full feature coverage. See
  feature coverage list in the file header for full detail.
- `modules/hidden_hostel/reset_instance.sql`: Instance reset script. Verified against
  simulated play mutations — all mutable state restores correctly.
- `README.md`: Added Hidden Hostel to module table; updated build and run commands.

**Incidental findings this session:**
- `schema.sql` v8 version row was missing (fixed above).
- Character-level `speech_filter` field does not exist in the schema. Gin-chan's
  filter is handled via `voice_register='cat'` as an interim signal to Pass 3.
  A schema v9 migration is needed to add this properly. Tracked in pending work below.
- "Potion allows player to understand Gin-chan" is a future mechanic requiring item/
  inventory system + player state modifier. Tracked in pending work below.

**Pending from this session:**
- ~~Phillips spelling fix~~ — **DONE in session 18**
- Verbal tic review: scan Haiku transcript for `[verb] with the air of someone who`
- §7: Logging to file + transcript auto-save
- §8: Schema v9 — character-level `speech_filter` field (for Gin-chan)
- §9: Player self-definition on game start — prompt for name, gender, pronouns, description, belongings (when item system exists). Module-controlled; not used in Meryton or I Am a Cat.
- §11: Allow player to choose from a list of pre-defined characters at game start (alternative to self-definition; useful for modules with fixed casts like Meryton).
- ~~§10: Hidden Hostel test suite~~ — **DONE; 37/37 passing**
- Hidden Hostel: Gin-chan potion mechanic (future; requires items + player state modifier).
  Once unlocked, Gin-chan speaks in the style of Carroll's Cheshire Cat — elliptical, gnomic.
  Hidden knowledge: Gin-chan is the actual founder/creator of the hostel (Marta runs it
  day-to-day). This is seeded in hidden_motivation; the revelation is a discovery mechanic.
- Hidden Hostel: The Old Soldier changed to female (seed.sql updated; reset_instance.sql
  not affected as gender/pronouns are stable data)
- Ollama `format: json` parameter: add `"format": "json"` to the `/api/generate` payload
  in `engine/llm/ollama.py`. Currently omitted; Mistral may wrap JSON in markdown fences,
  which `call_json()` strips — but explicit format enforcement is more robust and should
  be conditional on pass type (Pass 1 and Pass 2 only; Pass 3 is prose).

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

**v9** — Character-level `speech_filter TEXT DEFAULT NULL` on `character` table.
Per-character speech rendering override (NULL = no filter; `'cat'` = meow variants).
Player self-definition support: `player_definition_mode` on `game` table (metadata
only; no engine branching). Item system: `character_item` join table with slot
vocabulary; `item.current_location_id` replaces old `location_id`;
`item.is_confirmed` flag (1 = seeded/canonical, 0 = lazily generated). Engine:
`item_instantiations` and `player_character_update` outcome handlers. Context:
player inventory in Pass 2 packet; `player.description` in Pass 3 packet.
Hidden Hostel: location 6 (Outside the Hostel Door), Blue Door (npc_object id=7),
sencha canister in player pack, tray of hot rolls in kitchen.

**Current version: 9.**

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

### §9. Player self-definition on game start

Some modules have a fixed player character (Elizabeth Bennet in Meryton,
Toulouse in I Am a Cat). Others — like the Hidden Hostel — are designed for an
undefined player who should be able to describe themselves before play begins.

**Design:** A module-level flag (e.g. `player_definition_mode` on the `game`
table) controls whether the self-definition step runs. Values:
- `'fixed'` — no prompt; player character is fully seeded (current behavior).
- `'define'` — engine prompts the player at startup to describe themselves.
- `'choose'` — see §11.

When `player_definition_mode='define'`, the engine runs a brief interactive
step before the opening scene: the player is asked for name, gender/pronouns,
and a short description. Optionally, starting belongings when an item system
exists (§future). A single LLM call parses the player's free-text responses
into structured fields and writes them to the `character` row before play begins.

The Hidden Hostel Traveller should have `gender=NULL` and `pronouns=NULL` in
the seed as an immediate fix; the full self-definition step is implemented as
part of this feature.

Modules that do not use this feature are unaffected. Meryton and I Am a Cat
will not use it.

Affects: `game` table (new `player_definition_mode` column → schema v10+),
`modules/hidden_hostel/seed.sql` (set Traveller gender/pronouns to NULL),
engine startup flow in `engine.py`.

---

### §11. Allow player to choose from a list of pre-defined characters

Some modules may want to offer the player a choice among several pre-defined
characters rather than a blank-slate self-definition (§9). For example, a
Meryton variant could let the player choose to be Elizabeth, Jane, or Charlotte
Bennet — each fully seeded with OCEAN traits, goals, relationships, and
starting reputation.

**Design:** When `player_definition_mode='choose'` on the `game` record, the
engine presents a numbered list of available characters (seeded with
`role='player_option'`) and the player selects one. The selected character's
role is updated to `'player'`; others are set to `'npc_background'` or
removed.

This is complementary to §9, not a replacement. A module can use either or
neither. The two features share the same `player_definition_mode` field.

Affects: `game` table (`player_definition_mode`; same column as §9),
`character` table (new `role` value `'player_option'`), engine startup flow.

---

### §10. Hidden Hostel test suite integration

The Hidden Hostel module was designed to exercise every implemented engine
feature, but the existing pytest suite runs only against the minimal fixture
world in `tests/fixtures/seed.py`. To make the Hidden Hostel actually useful as
a test vehicle, a dedicated test file is needed.

**Proposed scope — `tests/test_hidden_hostel.py` (Tier 1):**

Fixture: a function-scoped `tmp_hostel_db` that builds the Hidden Hostel
database from `schema/schema.sql` + `modules/hidden_hostel/seed.sql` into a
temporary file, yields a `Database` instance, and cleans up.

Tests to cover each design goal:
- Location graph: staircase connection (1↔3) passable; Room B connection (3↔5)
  impassable; multi-hop path Kitchen→Common Room→Upper Corridor→Room A exists.
- Wander suppression (sleepiness): Gin-chan's sleepiness ≥ 0.60 and
  wander_probability > 0; verify engine skips the roll.
- Wander suppression (pending_intent): Scholar has pending_intent set and
  wander_probability > 0; verify engine skips the roll.
- Wander suppression (activity): Marta and Old Soldier have non-null
  current_activity with non-expired durations at start time.
- Wander positive control: Wanderer has no suppression conditions; verify
  wander roll fires (probability 0.75 means it should fire with mocked random).
- Hidden motivation access control: Scholar's hidden_motivation is populated
  and access_hidden_motivation=0; verify Pass 2 packet includes it but Pass 1
  packet does not.
- Faction and reputation: hosts_of_the_hostel exists; player and Marta have
  reputation records with correct starting values.
- Attitudes: verify positive (Wanderer→Traveller), negative (Old Soldier→
  Traveller), and NPC-to-NPC (Old Soldier→Wanderer) attitude rows.
- Visited locations: player seeded at Common Room (1) only; multi-hop BFS
  can route to Room A from Common Room.
- Lazy world generation: Common Room has one pre-seeded location_detail;
  Room A and Room B have none.

Tier 3 additions (optional, separate ticket):
- New `test_pass1_eval.py` tests using the Hidden Hostel DB:
  "go upstairs" → action_type=move, target_location_id=3
  "climb to the upper corridor" → action_type=move, target_location_id=3

---

### §8. Schema v9: character-level speech_filter

The Hidden Hostel module introduced Gin-chan, a winged cat whose vocalizations
should be rendered as meow variants by Pass 3 — the same filter used game-wide
in I Am a Cat. However, the `speech_filter` field currently lives only on the
`game` table (game-level), not on the `character` table.

Adding `speech_filter TEXT DEFAULT NULL` to the `character` table allows
per-character speech filtering without affecting other characters in the same
module. A NULL value means no filter; `'cat'` means Pass 3 renders this
character's speech as meow variants.

**Migration:** `schema/migrations/migrate_v8_to_v9.sql`
  - `ALTER TABLE character ADD COLUMN speech_filter TEXT DEFAULT NULL;`
  - Bump schema_version to 9.
  - Apply to all existing databases (i_am_a_cat.db, meryton.db, hidden_hostel.db).

**Engine:** `engine/context.py` — include `speech_filter` in NPC profile block
  of Pass 3 context packet alongside `voice_register` and `voice_warmth`.

**Pass 3 prompt:** Add instruction: if an NPC's `speech_filter='cat'`, render
  all their speech/vocalizations as meow variants (same rule as the game-level
  filter in I Am a Cat).

**Seed update:** `modules/hidden_hostel/seed.sql` — add `speech_filter='cat'`
  to Gin-chan's INSERT once the migration is applied. Update reset_instance.sql
  to reset this field. Remove the interim `voice_register='cat'` workaround note
  once the migration is in place (though `voice_register='cat'` can remain as it
  also influences voice rendering).

**Related future mechanic:** A potion grants the player temporary ability to
  understand Gin-chan — requires item/inventory system + player state modifier
  that overrides the speech filter for the duration. Design when items are built.

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

**Schema note:** The item location field is `current_location_id` (renamed from
`location_id` in schema v9). The engine implements location change as:
validate → `UPDATE item SET current_location_id = ? WHERE id = ?`.
Character-held items use the `character_item` join table; `current_location_id`
should be NULL when a `character_item` row exists for the item.

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

**OCEAN floats are currently LLM-consumed qualitative signals, not numeric inputs.**
The five OCEAN trait fields (`ocean_openness`, etc.) are stored as precise floats
and passed to Pass 2 in the context packet under `"personality"`. However, the
engine performs no arithmetic on them — no comparisons, thresholds, or weighted
sums. Pass 2 is simply instructed to "apply OCEAN traits consistently," which
means the LLM interprets them qualitatively (0.88 openness reads as "highly
curious and imaginative"). A prose descriptor would do equivalent work for Pass 2.

The floats are preserved because a future rule-based layer could genuinely compute
on them — attitude decay rates, wander probability weighting, behavioral trigger
thresholds. Until such a layer exists, they function as seeded adjectives. Do not
add new numeric precision to the OCEAN system without a concrete arithmetic consumer
in mind. When god-mode canonizes personality assertions, they go into the character
`description` field, not the OCEAN floats. (Design decision: 2026-07-16.)

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
