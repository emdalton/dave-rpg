# DAVE RPG Engine — Future Feature Ideas

*Captured May 2026. None of these are scoped or designed; this is a reference list.*

---

## 1. Web host option

Run the engine from a browser-based interface rather than a local terminal session. This would require a server layer (likely a thin Python web framework) wrapping the current `GameEngine` loop, with the player's input arriving via HTTP rather than `stdin` and the prose response returned as a JSON payload to the frontend.

Architectural note: the engine's turn loop is already stateless between calls (all state lives in the database), which makes it naturally suited to a request/response web model.

---

## 2. Transcript save / assisted writing mode

Option to capture the session's prose output as a formatted transcript file. Framing: DAVE as an assisted creative writing tool, not just a game engine. The player and LLM collaborate on a story; the transcript is the artifact.

Could be as simple as a flag that writes Pass 3 output to a running `.md` or `.txt` file alongside the game session. A richer version might include post-session editing, annotation, or export to a formatted document.

---

## 3. Illustrated mode (media generation + compositing)

Use an image generation model to produce simple illustrations for database entities — characters, locations, items. Layer the images (character sprite over location background, items as overlays) to produce illustrated scene cards for each turn, without requiring full animation.

This maps naturally onto the existing schema: `character`, `location`, and `item` records could each carry an `image_path` field pointing to a generated or hand-authored asset. The compositing layer would be a separate rendering step after Pass 3.

---

## 4. Multiplayer mode

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
