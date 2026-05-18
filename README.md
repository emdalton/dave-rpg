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

Early development. The engine is currently in Phase 1: prototyping with Claude Sonnet to validate data structures and query templates before porting to a local model (target: Mistral 7B via Ollama).

### Planned test modules

| Module | Setting | Primary mechanics exercised |
|--------|---------|----------------------------|
| I Am a Cat | Domestic townhouse, 3am | Object interaction, speech filtering, lazy world generation, emotional state |
| The Netherfield Ball | Pride and Prejudice (Austen, public domain) | Full social mechanics, faction dynamics, art as performance, reputation |
| Locked Room Mystery | Original science fiction | Hidden motivation, consistency enforcement, investigative mechanics |

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

Phase 1 development uses Claude Sonnet for its superior handling of underspecified situations, generating ground-truth adjudication examples that will be used to evaluate local model parity.

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
