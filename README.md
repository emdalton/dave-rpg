# DAVE RPG Engine

**Digitally Adjudicated Virtual Environment**

DAVE is an open-source game engine for text-based narrative RPGs in which diplomacy, relationships, and social dynamics are mechanically as rich as combat is in conventional RPGs. A locally-running language model serves as the natural-language interface and adjudication layer; a relational database holds all canonical world state. The LLM is never the source of truth — the database is.

---

## Why DAVE?

Most RPG engines treat combat as the primary mechanic and social interaction as a scripted afterthought. DAVE inverts this. Players can talk, bluff, bribe, empathize, create art, build alliances, and outwit adversaries with the same expressive freedom that combat-focused engines give to players who prefer action. Non-violent problem solving and conflict resolution are first-class mechanics.

The engine is deliberately modular and is designed to function both as a standalone text-based engine and as an eventual add-on narrative layer for graphical RPG engines.

---

## Architecture

Each player action triggers three sequential LLM calls, each receiving a structured JSON context packet assembled from the database:

1. **Intent Parsing** — free-text input is parsed into a structured action record
2. **Outcome Adjudication** — full context packet is assembled and the LLM adjudicates the outcome as structured data, including attitude deltas, emotional state changes, and narrative beat
3. **Prose Rendering** — the adjudicated outcome is rendered as player-facing prose

All consequences from adjudication are written to the database before prose rendering executes. The world is seeded with skeleton data and details are generated on demand (lazy world generation), stored canonically on first generation and retrieved thereafter.

NPC and player character behavior is grounded in three established psychological frameworks: the Big Five personality traits (OCEAN), Ford and Nichols's 24-goal Motivational Systems Theory taxonomy, and Maslow's hierarchy as a priority-override mechanism.

For full architectural detail, see [docs/design_v05.md](docs/design_v05.md).

---

## Status

Early development. The engine is currently in Phase 1: prototyping with Claude Haiku as the game loop backend to validate that the three-pass architecture is viable at a model capability level close to the Phase 2 local model target. Claude Sonnet is used separately for module construction — seeding character data, writing location graphs, and generating ground-truth adjudication examples. The distinction matters: Haiku running the game is the test; Sonnet building the module is the tooling.

### Modules

| Module | Setting | Primary mechanics exercised | Status |
|--------|---------|-----------------------------|----|
| I Am a Cat | Domestic townhouse, 3am | Object interaction, speech filtering, lazy world generation, emotional state | Playable |
| The Hidden Hostel | Liminal inn between worlds | Test world: full engine feature coverage — staircase navigation, all wander suppression conditions, hidden motivation, faction, NPC-to-NPC attitudes | Playable (test module) |
| The Netherfield Ball | Pride and Prejudice (Austen, public domain) | Full social mechanics, faction dynamics, art as performance, reputation | In development |
| Locked Room Mystery | Original science fiction | Hidden motivation, consistency enforcement, investigative mechanics | Planned |

---

## Setup and Running

### Requirements

- Python 3.10+
- For Phase 1 (Claude backend): an [Anthropic API key](https://console.anthropic.com) with API credits
- For Phase 2 (Ollama backend): [Ollama](https://ollama.com) installed and running

**Hardware requirements for local inference (Phase 2 / Ollama):**
Mistral 7B requires meaningful GPU or Apple Silicon to run at interactive speeds.
On Intel CPUs or machines with less than 16GB RAM, inference will be very slow
(2–5 minutes per LLM call; three calls per turn). Recommended minimum for
acceptable play:

- Apple Silicon Mac (M1 or later) with 16GB unified memory
- Or a machine with a dedicated NVIDIA GPU (8GB VRAM+) running Ollama with CUDA

Phase 1 (Claude API) has no local hardware requirements beyond running Python.

### Installation

```bash
git clone https://github.com/emdalton/dave-rpg.git
cd dave-rpg
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Build a module database

Each module database is built from the canonical schema plus the module seed. No migration scripts are needed for a fresh install — `schema/schema.sql` incorporates all schema versions.

```bash
# I Am a Cat
sqlite3 modules/i_am_a_cat/i_am_a_cat.db < schema/schema.sql
sqlite3 modules/i_am_a_cat/i_am_a_cat.db < modules/i_am_a_cat/seed.sql

# The Hidden Hostel (test world)
sqlite3 modules/hidden_hostel/hidden_hostel.db < schema/schema.sql
sqlite3 modules/hidden_hostel/hidden_hostel.db < modules/hidden_hostel/seed.sql
```

Migration scripts in `schema/migrations/` are only needed when upgrading an existing database to a newer schema version.

### Run

```bash
export ANTHROPIC_API_KEY=your_key_here

# I Am a Cat
DAVE_LOG_LEVEL=WARNING DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python3 -m engine

# The Hidden Hostel (test world)
DAVE_LOG_LEVEL=WARNING DAVE_DB_PATH=modules/hidden_hostel/hidden_hostel.db python3 -m engine
```

`DAVE_LOG_LEVEL=WARNING` keeps the terminal clean during play. The default (`INFO`) includes API transport messages that can clutter the output alongside prose. Use `DEBUG` to see full pass-level detail including raw prompts and LLM responses.

For Ollama (Phase 2 — local model, currently a stub):

```bash
# Start the Ollama server in a separate terminal, then:
DAVE_LLM_BACKEND=ollama DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python3 -m engine
```

For full configuration options — model selection, tuning parameters, test suite setup — see [docs/configuration.md](docs/configuration.md).

### Where to find things

- **Running and configuration:** [docs/configuration.md](docs/configuration.md) — all environment variables, typical session setups, test suite options.
- **Test suite:** [docs/test_suite.md](docs/test_suite.md) — what's tested, how to run each tier, how to extend.
- **Database schema and field semantics:** `schema/schema.sql` — authoritative reference for all table structures and field meanings.
- **Engine configuration defaults:** `engine/config.py` — all tunable parameters with inline documentation.
- **Module seed data:** `modules/<module_name>/seed.sql` — character definitions, locations, and starting state for each module.
- **Design document:** `docs/design_v05.md` — full architectural rationale.

---

## Repository Structure

```
dave-rpg/
├── engine/       # Core engine code
├── modules/      # Game modules and seed data
├── schema/       # SQLite schema definitions and migrations
├── docs/         # Design documents and reference material
└── tests/        # Test cases and adjudication ground truth
```

---

## The engine working as intended

From a Hidden Hostel playtest session (Claude Haiku backend, 2026-05-30):

The player arrived as a hungry traveller, was greeted by the Wanderer (who introduced
Gin-chan as a resident, not a pet, and suggested asking Marta for food), then spent
the session in the kitchen helping Marta with the evening meal and eventually making
linden flower tea, which they brought to the common room and offered to Gin-chan with
genuine courtesy.

The end-of-session attitude and reputation values tell the story:

| Character | Attitude toward player | Starting value |
|-----------|----------------------|----------------|
| The Wanderer | 0.96 | 0.65 |
| Gin-chan | 0.87 | 0.50 |
| Marta | 0.73 | 0.35 |
| The Scholar | 0.60 | 0.60 (unchanged — no contact) |
| The Old Soldier | −0.30 | −0.30 (unchanged — no contact) |

Faction standing with `hosts_of_the_hostel`: **0.97** (from 0.40), with the note:
*"Respectful gesture of hospitality toward a hostel resident; tea as shared comfort."*

Nothing about this outcome was hand-coded. Marta's attitude shift from wary (0.35) to warm
(0.73) came from her OCEAN profile (high conscientiousness), her goals (esteem,
resource acquisition), and accumulated positive interactions — helping chop vegetables,
working quietly alongside her, asking permission before using the kitchen supplies.
The faction standing jump came from recognising Gin-chan as a resident and offering tea
as an equal — exactly the behaviour the hostel's rules single out as mattering.

The Old Soldier's suspicion of strangers persisted unchanged, as it should: the player
never encountered them.

---

## Local LLM

The engine targets local inference for privacy, offline capability, and cost. All data remains on-device.

- **Primary:** Mistral 7B via [Ollama](https://ollama.com) — ~90% first-try JSON accuracy, 6–7 GB RAM, Apache 2.0
- **Fallback/upgrade:** Llama 3.3 8B — 128K context window, stronger instruction-following

Phase 1 development uses Claude Haiku as the game loop backend — the three-pass architecture is validated at a capability level close to the Phase 2 local model target. Claude Sonnet is used separately as a construction tool for seeding module data and generating ground-truth adjudication examples.

### Hardware estimates for local inference

*These estimates are speculative and will be revised as Phase 2 testing progresses. All figures assume 4-bit quantisation (Q4) via Ollama/llama.cpp.*

The three passes have different computational demands:

| Pass | Task | Minimum model size |
|------|------|--------------------|
| Pass 1 — Intent Parsing | Structured extraction; small context | ~3B parameters |
| Pass 2 — Outcome Adjudication | Complex reasoning; large context; many output fields | 7B (simple modules) / 13B+ (complex social modules) |
| Pass 3 — Prose Rendering | Creative writing; tone matching | 7B |

Pass 2 is the bottleneck — it generates the most tokens and requires the most capable model. A single 7B model for all three passes is a reasonable starting point.

Approximate turn times (all three passes, ~600–900 tokens generated total):

| Hardware | Throughput | Est. turn time |
|----------|------------|----------------|
| Modern CPU only | ~10 t/s | 60–90 sec — too slow for interactive play |
| Apple Silicon M2 Pro, 16GB | ~35–45 t/s | 13–25 sec — acceptable |
| NVIDIA RTX 3060 12GB | ~55–70 t/s | 8–15 sec — comfortable |
| Apple Silicon M2 Max, 32GB | ~30–40 t/s for 13B | 15–30 sec for complex modules |
| NVIDIA RTX 3090 24GB | ~80–100 t/s | 6–10 sec — comfortable |

For simple modules (Hidden Hostel, I Am a Cat) with a 7B model: an M2 Pro Mac or a machine with an RTX 3060 12GB is the practical minimum for interactive play. For socially complex modules (Meryton, with 20+ characters and dense faction mechanics), 13B is recommended for Pass 2, which requires 16GB+ VRAM or Apple Silicon with 32GB+ unified memory.

### Longer-term target

The engine's design is intended to be viable on consumer hardware including future game consoles (PlayStation 5 successor class and equivalents). More selectively trained or fine-tuned models — smaller models with deeper specialisation in the specific tasks each pass performs — may significantly lower these requirements. Voice control is a natural fit for the existing pass architecture and is a long-term design goal. These remain aspirational targets; current development proceeds via the Claude API.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. The core engine is and will remain open source. Contributions to engine code, module content, schema design, and documentation are all welcome.

All reference material used in module seeding must be documented with source and license. Preferred sources are Creative Commons licensed or in the public domain.

---

## Educational Use

DAVE has an explicit educational dimension. Modules built on public domain literature (Austen, Conan Doyle) and historical figures (Nightingale, Lovelace, Babbage) are designed to be usable in literature, history, and statistics courses. The engine's architecture — which requires students to reason about character motivation, social context, and evidence — supports genuine pedagogical goals rather than retrofitting game mechanics onto existing curricula.

---

## Name

DAVE is named for Dave, an outstanding tabletop RPG moderator, in recognition of the craft and care that good game mastering requires — and which this engine aspires to replicate in software.
