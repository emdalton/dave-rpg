# DAVE RPG Engine — Future Feature Ideas

*Captured May 2026. None of these are scoped or designed; this is a reference list.*

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
