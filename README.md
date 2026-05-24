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

### Planned test modules

| Module | Setting | Primary mechanics exercised |
|--------|---------|----------------------------|
| I Am a Cat | Domestic townhouse, 3am | Object interaction, speech filtering, lazy world generation, emotional state |
| The Netherfield Ball | Pride and Prejudice (Austen, public domain) | Full social mechanics, faction dynamics, art as performance, reputation |
| Locked Room Mystery | Original science fiction | Hidden motivation, consistency enforcement, investigative mechanics |

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
# Clone the repo
git clone https://github.com/emdalton/dave-rpg.git
cd dave-rpg

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Build a module database

Each module database is created from two files: the canonical schema and the module seed. No migration scripts are needed for a fresh install — `schema/schema.sql` incorporates all schema versions.

```bash
sqlite3 modules/i_am_a_cat/i_am_a_cat.db < schema/schema.sql
sqlite3 modules/i_am_a_cat/i_am_a_cat.db < modules/i_am_a_cat/seed.sql
```

Migration scripts in `schema/migrations/` are only needed when upgrading an existing database to a newer schema version. For a new database, always start from `schema/schema.sql`.

### Run with Claude (Phase 1)

```bash
export ANTHROPIC_API_KEY=your_key_here
DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python3 -m engine
```

For debug-level logging (shows raw prompts and LLM responses on stderr):

```bash
DAVE_LOG_LEVEL=DEBUG DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python3 -m engine
```

### Run with Ollama (Phase 2)

Ollama must be installed, running, and have the target model pulled **before** starting the engine. These are separate steps:

```bash
# 1. Install Ollama (macOS)
brew install ollama

# 2. Start the Ollama server (run in a separate terminal and leave it running)
ollama serve

# 3. Pull the model (run in another terminal while the server is up)
ollama pull mistral

# 4. Run the engine
DAVE_LLM_BACKEND=ollama DAVE_DB_PATH=modules/i_am_a_cat/i_am_a_cat.db python3 -m engine.engine
```

Note: `ollama pull` requires the server to be running. Running `ollama pull` before `ollama serve` will fail silently or error.

### Where to find things

- **Database schema and field semantics:** `schema/schema.sql` and `schema/migrations/` — these are the authoritative reference for all table structures. Read them before writing any code that touches the database.
- **Engine configuration:** `engine/config.py` — all tunable parameters with documentation and environment variable overrides.
- **Module seed data:** `modules/<module_name>/seed.sql` — character definitions, locations, items, and starting state for each module.
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

## Local LLM

The engine targets local inference for privacy, offline capability, and cost. All data remains on-device.

- **Primary:** Mistral 7B via [Ollama](https://ollama.com) — ~90% first-try JSON accuracy, 6–7 GB RAM, Apache 2.0
- **Fallback/upgrade:** Llama 3.3 8B — 128K context window, stronger instruction-following

Phase 1 development uses Claude Haiku as the game loop backend — the three-pass architecture is validated at a capability level close to the Phase 2 local model target. Claude Sonnet is used separately as a construction tool for seeding module data and generating ground-truth adjudication examples.

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
