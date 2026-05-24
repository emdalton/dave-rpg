# DAVE RPG Engine — Future Feature Ideas

*Captured May 2026. None of these are scoped or designed; this is a reference list.*

---

## 13. Module chapters / act structure with state forwarding

Observation (2026-05-23): modules don't all need to be published as monolithic single-session experiences. A chapter structure would allow a module to be developed and released incrementally, with each chapter forwarding relevant state (character attitudes, reputation changes, item positions, pending intents) into the next chapter's starting seed.

This connects naturally to the module/instance architectural split (pending v7): once per-playthrough state is properly separated from module definition, "forwarding state to the next chapter" becomes a defined export/import operation on instance state rather than a hack against the seed. The "What if..." premise modifier (feature 6) would also attach per-chapter, enabling branching.

Undeveloped as of capture.

---

## 14. Multiple playable characters per module

Observation (2026-05-23): modules could support a choice of player character rather than a single fixed protagonist. The simplest proof-of-concept is allowing a player to play as Spook in *I Am a Cat* — the world state and NPC cast already exist, and Spook's psychology is established. This would test whether the engine handles a non-default player character cleanly, including: different starting location, different emotional state and internal states, different perception of Toulouse as an NPC.

In the Netherfield Ball context, playing as Darcy, Wickham, or Jane rather than Elizabeth would produce radically different experiences from the same seed — each character has different information, different goals, and different social constraints.

Implementation sketch: a `playable` flag on the `character` table, plus a pre-session character selection step. The engine's existing `role='player'` logic already centralizes player-character handling; the change is making which character holds that role a runtime choice rather than a seed constant.

---

## 11. Fate Point economy

Suggested by playtest observation (2026-05-23): the `partial_success` outcome on the Spook social-correction turn was a textbook Fate compel — an NPC aspect (Spook's incorrigible playfulness) complicated the player's action in an entertaining way, and in the Fate RPG system that moment would award the player a Fate Point. The `partial_success` and `failure` outcome types are already doing the adjudication work; a Fate Point system would add a resource currency on top.

**Mechanic sketch:**

- A named resource pool (e.g. `fate_points`) stored on `game_instance` (or a `player_resource` table for generality across module types).
- Pass 2 issues a `fate_point_award: true` flag in its outcome JSON when it generates a `partial_success` or `failure` with a strong, entertaining narrative beat — i.e., when the complication makes the story better rather than just worse.
- Pass 1 detects spend intent from player input and adds `spend_fate_point: true` to the action record. The engine checks for available points before honoring it; if none are available, Pass 2 is not told the spend was requested.
- Pass 2 prompt: when `spend_fate_point: true` is in the action record, the player has paid a resource for a better outcome — lean toward success or at least reduce the cost of failure. The spend does not guarantee success but shifts the probability.

**Natural-language spend signals for Pass 1 to recognize:**

The signal must come from character voice or explicit effort language — player asides ("I really hope this works") should not trigger a spend. Clear signals:

- *Effort intensifiers* in character voice: "try harder," "push," "give it everything," "strain to," "force it through," "with everything I have"
- *Stakes declarations* in character: "I need this to work," "I cannot afford to fail here," "this matters"
- *Explicit trait invocations*: "use my dignity," "as the senior cat I insist," "I invoke my authority" — natural for Fate-familiar players and intuitive for anyone leaning into character
- *Narrative declarations*: "I declare that..." — classic Fate story-detail spend

Pass 1 prompt note: require that the signal be in-character or clearly about the action, not a player aside. "I really hope this works" is ambiguous and should not trigger a spend unless paired with an effort intensifier.

**Module-level opt-in:** Not all modules use a Fate Point economy. Add a `fate_points_enabled` flag to the `module_flags` JSON on `game` (alongside the `what_if_enabled` flag sketched in feature 6). Starting pool size and award/spend rates are module-level config.

---

## 12. Scene-close segmenting and narrative arc

Playtest observation (2026-05-23): the closing line of the Spook-correction turn ("You did the thing. It is not your fault he is like this.") felt like a natural scene-close — a beat that wraps one narrative unit before the next opens. This suggests a possible feature around detecting or generating explicit scene boundaries.

Undeveloped as of capture. Possible directions:

- Pass 3 could be prompted to signal when it believes a scene has closed (a structured flag alongside the prose), allowing the engine to insert a brief visual/textual break in the output.
- A scene log could track named scenes as discrete narrative units, enabling transcript mode (feature 2) to produce chapter-structured output rather than a flat turn log.
- Scene boundaries might interact with the Fate Point economy (feature 11) — scene close is a natural moment to tally awards, as in the Fate tabletop system.

Not yet clear where this goes. Capturing the observation for later.

---

## 8. MUSH integration

Suggested by a playtester (2026-05-23), who noted that DAVE's prose quality was reminiscent of good MUSH play and proposed wiring the engine to a MUSH server for networked multi-player access.

**What this would require:**

DAVE's turn loop is already structured like a MUSH world engine: it takes a player action, updates world state, and returns prose. The gap is concurrency — DAVE currently assumes one player and one active session. Full MUSH integration needs:

1. *Multi-session world state* — the v7 module/instance architectural split (see implementation_status.md §4) is the prerequisite. Once `instance_id` is threaded through all state tables, multiple concurrent player sessions sharing one world instance become architecturally possible.

2. *Turn coordination* — in a shared world, two players may act simultaneously on the same target. Options: sequential turns with a queue; simultaneous resolution where all pending actions for a game-time tick are adjudicated together in a single Pass 2 call; or a hybrid where independent actions resolve independently and conflicting ones trigger a combined adjudication.

3. *Network transport* — a MUSH protocol layer (or a simpler telnet/websocket server) that routes player input to the engine and returns prose. This is separate from the web-host option (feature 1), which uses HTTP; MUSH clients expect a persistent TCP connection.

**Simpler intermediate path:** Run DAVE as the NPC/world-simulation engine behind a traditional MUSH, rather than as a full replacement. The MUSH handles connection management, player routing, and room/exit bookkeeping; DAVE handles adjudication and prose for NPC interactions and complex world events. This defers the concurrency problem while still providing the NPC quality improvement that makes MUSH play richer.

**Relationship to other features:** Overlaps significantly with feature 5 (multiplayer) and feature 1 (web host). The three are the same architectural need approached from different interfaces: HTTP browser client, multi-user MUSH client, and eventually a desktop/mobile client. Design the session and concurrency layer once; the transport is a skin on top.

---

## 9. Module: Barsoom (Edgar Rice Burroughs)

Suggested as a strong module candidate (playtest 2026-05-23), particularly in a MUSH context where the planetary romance setting and large cast of alien species naturally support multi-player factions.

**Why it works for DAVE:**

- Radically non-human player characters (Red Martians, Green Martians, Tharks, Warhoons) stress-test the species-specific perception and sensory profile systems
- Faction mechanics (Heliumite, Zodangan, Thark tribal politics) are first-class; DAVE's reputation and attitude systems were designed for exactly this
- The social dynamics of Barsoomian honor culture (challenges, debts, alliances) are a natural fit for the Ford-Nichols motivational framework
- A MUSH version with multiple players each playing a different species would be a compelling proof-of-concept for both DAVE and the Barsoom setting

**IP status:**

The early Barsoom novels are in the US public domain — *A Princess of Mars* was published in 1912 (book form 1917), well past the copyright threshold. However, ERB Inc. remains active and holds trademarks on character names, species names, and setting terms; they have historically been aggressive about enforcement. This means:

- *Public domain text* — the novels themselves can be quoted and adapted freely for non-commercial use
- *Trademarks* — "John Carter," "Barsoom," "Tharks," and similar marks may require licensing even when the underlying text is public domain; this distinction matters for any commercial or widely-distributed release
- *Practical path* — for a hobbyist/open-source project, a faithful Barsoom module is likely defensible; for any commercial release or wide distribution, consult the trademark landscape before investing heavily in module design

**Comparison to Amber:** More tractable than the Amber Chronicles (Zelazny died 1995; Amber is still under copyright and requires active estate permission regardless of intent). Barsoom's public-domain status gives a stronger foundation.

---

## 10. Module: Amber Chronicles (Roger Zelazny)

Suggested as a module candidate (playtest 2026-05-23), with the note that the Zelazny estate may have authorized use in MUSH-style games.

**IP caution:** The Amber Chronicles are still under copyright — Zelazny died in 1995 and copyright extends 70 years post-mortem in the US, meaning the works remain protected until at least 2065. Any use requires active estate permission. The claim that MUSH use has been authorized is plausible (the Amber MUSH community has been active for decades and the estate has historically tolerated fan games), but "tolerated" is not the same as "authorized," and explicit permission should be confirmed before investing significant design effort.

**If authorization is confirmed:** Amber is an excellent DAVE module candidate. The pattern system (each Amberite has a unique ability profile) maps naturally onto DAVE's skill taxonomy; the family politics of the Courts of Chaos are exactly the kind of social-diplomatic complexity the engine was designed for; and the multiverse structure (Shadows) supports lazy world generation at a conceptual level — Shadow worlds are, by definition, generated on demand.

---

## 7. Module: Suspended (Infocom port / homage)

Port or homage to the Infocom game *Suspended* (1983, Michael Berlyn). In the
original, the player is a human in a suspended animation capsule who must direct
five robots — each with a completely different sensory profile — to diagnose and
repair a planetary life-support system before it fails.

This is the ideal stress test for the DAVE sensory profile system:

- **Iris** — visual only; excellent sight, no other senses
- **Waldo** — tactile; no sight, navigates and manipulates by touch
- **Sensa** — audio; detects sounds and vibrations the others cannot
- **Poet** — reads and communicates; makes no direct observations
- **Whiz** — computational; processes data but has no sensory apparatus at all
- **Fred** — generalist with degraded abilities across all senses (the "safe"
  but limited robot)

Each robot's sensory profile would be a distinct JSON object on their character
record. The player issues commands to specific robots; the adjudication layer
must reason about what each robot can and cannot perceive from their location.
The human player in the capsule has no direct sensory access to the world at all
— information arrives only through robot reports.

Why this works well for DAVE:
- Directly exercises species/character-specific perception (the engine's next
  major design challenge after I Am a Cat)
- Naturally multiplayer-ready: each robot could be a separate player character
- High replayability: different robot combinations produce different information
  pictures of the same world
- Strong fan recognition: *Suspended* is a cult classic with a devoted following
  who would appreciate a faithful, mechanically rich homage
- Fits the "serious game" framing: resource management, teamwork, systems
  thinking under time pressure

**IP note:** Infocom IP is owned by Activision. Two viable paths:

1. *Homage with original scenario design* — use the robot sensory mechanic and
   general structure, but write original puzzles and setting. No IP issue.

2. *Licensed import* — the standard approach for IP-sensitive content is an
   import scheme that requires users to provide original game files to verify
   their right to use the IP. DAVE could extract scenario data (room
   descriptions, object names, puzzle logic) from a user-supplied Z-machine
   binary and use it to seed the module database, rather than distributing the
   content directly. E owns a physical copy of *Lost Treasures of Infocom*
   (includes all Infocom titles); archive copies of the Z-machine files are
   also available online for verified owners. The Z-machine file format is
   well-documented and there are existing Python libraries for parsing it.

A faithful port with the original scenario is the more interesting project; the
import approach makes it distributable. These can be developed in parallel —
build the engine mechanics against original content first, add the import/verify
layer before any public release.

**The "upgrade" effect:** Running any Infocom title through DAVE effectively
upgrades it. The original games use a parser that matches player input against
a fixed verb-noun vocabulary and resolves puzzles against hard-coded winning
conditions. DAVE replaces the parser with LLM intent recognition and replaces
hard-coded puzzle logic with contextual adjudication. This means a puzzle that
originally required finding object X and using it in place Y might become
solvable multiple ways — or might require more nuanced negotiation with NPCs
who, in DAVE, have actual psychology. Winning conditions change because "winning"
becomes an emergent outcome rather than a flag flip. This is a significant design
challenge for faithful ports and a significant creative opportunity for homages.
Players accustomed to the originals should be warned that DAVE versions play
differently, not just look different.

---

## 6. "What if..." premise modifier

An optional per-instance premise modifier entered by the player at the start of a new module. Examples: "What if Elizabeth Bennet is a vampire?" or "What if Toulouse's house is populated by small mischievous demons that only cats can see?"

When the feature is enabled for a module, the engine prompts the player for a free-text premise modification before the first turn. The modifier is canonicalized via a one-time call to a more capable model (Sonnet or Opus — not Haiku; this requires genuine creative and narrative interpretation), stored in a `premise_modifier` field on the `game` record, and included in every subsequent context packet as an addendum to the standard game premise. All three passes see it.

Implementation sketch:
- `premise_modifier TEXT NULL` on `game` (null = no modifier active)
- Module-level opt-in via a `module_flags` JSON field on `game` (e.g., `{"what_if_enabled": true}`). This field also covers other optional feature toggles (illustrated mode, transcript mode) without proliferating boolean columns.
- One-time pre-session LLM call: takes the player's raw input and the base game premise, returns a canonicalized modifier statement suitable for inclusion in context packets.
- No engine logic changes needed beyond passing the field through context assembly.

---

## 1. Web host option

Run the engine from a browser-based interface rather than a local terminal session. The engine's turn loop is already stateless between calls (all state lives in the database), which makes it naturally suited to a request/response web model — each player turn is a self-contained transaction that requires no persistent server process.

**Hosting target: Tiger Technologies (shared hosting)**

Tiger Technologies does not support persistent applications (no long-running Python server process), but does provide MySQL database hosting. This shapes the architecture:

- **Frontend:** HTML + JavaScript; handles player input and renders prose responses. No framework required — this is a simple form-submit-and-display loop.
- **Backend intermediary:** A thin PHP script or CGI handler receives the player's input, calls the LLM API, writes the result to MySQL, and returns the prose. No persistent process; each request spawns and exits.
- **Database:** SQLite → MySQL migration required. The schema is already relational, so translation should be straightforward; the main work is adapting db.py to use a MySQL connector and updating any SQLite-specific syntax (e.g., `PRAGMA`, `REAL` type affinities, `INSERT OR REPLACE`).
- **LLM API calls:** Made server-side from the PHP/CGI layer; API key stays off the client.

The three-pass engine loop maps cleanly onto three sequential API calls per HTTP request. Session state (which game_instance is active, current_time_minutes, etc.) lives entirely in MySQL — no server-side session memory needed.

**SQLite → MySQL migration notes:**
- SQLite `REAL` → MySQL `FLOAT` or `DECIMAL`; JSON fields → MySQL `JSON` type (available in MySQL 5.7+)
- `PRAGMA foreign_keys = ON` → MySQL enforces foreign keys by default on InnoDB
- `INSERT OR REPLACE` → `INSERT ... ON DUPLICATE KEY UPDATE`
- `AUTOINCREMENT` → `AUTO_INCREMENT`
- Schema migration scripts will need a MySQL variant alongside the SQLite originals

E owns a Tiger Technologies account; hosting modules there is a near-term goal once the engine is stable enough for external play.

---

## 2. Transcript save / assisted writing mode

Option to capture the session's prose output as a formatted transcript file. Framing: DAVE as an assisted creative writing tool, not just a game engine. The player and LLM collaborate on a story; the transcript is the artifact.

Could be as simple as a flag that writes Pass 3 output to a running `.md` or `.txt` file alongside the game session. A richer version might include post-session editing, annotation, or export to a formatted document.

---

## 3. Illustrated mode (media generation + compositing)

Use an image generation model to produce simple illustrations for database entities — characters, locations, items. Layer the images (character sprite over location background, items as overlays) to produce illustrated scene cards for each turn, without requiring full animation.

This maps naturally onto the existing schema: `character`, `location`, and `item` records could each carry an `image_path` field pointing to a generated or hand-authored asset. The compositing layer would be a separate rendering step after Pass 3.

---

## 4. Save / resume / new game (session management)

Players expect to be able to save a session, resume a previous session, start a
fresh playthrough of a module, and eventually maintain multiple save slots.
Currently the engine has no concept of session management: there is one set of
mutable state per module database, and the game always resumes from the last
known state. This is incidental behavior, not a feature.

Full session management requires the module/instance architectural split described
in the implementation status doc (pending v6 migration). Once `game_instance`
holds all per-playthrough state and `instance_id` is threaded through every
state table (`character`, `internal_state`, `item_location`, `action_log`,
`character_visited_location`), the following become straightforward:

- **New game:** create a new `game_instance` row, copy starting state from the
  module definition seed.
- **Save:** the database IS the save — state is always written before prose
  renders. Saving is just recording which instance is the "current" one.
- **Resume:** load the most recent active instance for a given module.
- **Multiple save slots:** multiple `game_instance` rows for the same `game_id`,
  each with its own state snapshot.

Architectural note: the "What if..." premise modifier (feature 6) attaches to a
`game_instance`, not to the module. Session management and premise modifiers
should be designed together.

---

## 5. Multiplayer mode

Each human player selects one character in the game world to play simultaneously. Players share a world state (same database); turns are either simultaneous (resolved together in a single adjudication pass) or sequential (each player takes a turn in order).

Deep architectural implication: the current `GameEngine` is single-player and assumes one `role='player'` character. Multiplayer would require: a turn coordinator, conflict resolution when two players act on the same target simultaneously, and potentially a shared session server so multiple clients can connect to one game instance.

---

## 5. Test script suite

Automated tests covering:

- **Schema integrity** — foreign key constraints, valid enum values, float range constraints
- **Engine pass logic** — context packet structure and required fields for each pass
- **DB write correctness** — that `_apply_outcome()` writes exactly what the outcome specifies
- **LLM stub / mock** — an `LLMClient` implementation that returns canned JSON for deterministic testing without live API calls
- **Round-trip integration tests** — full three-pass turn with a known seed database and a mock LLM, verifying the final database state matches expectations
