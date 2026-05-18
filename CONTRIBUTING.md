# Contributing to DAVE RPG Engine

Thank you for your interest in contributing. DAVE is open source and community-extensible contributions to engine code, module content, database schema, and documentation are all welcome.

---

## Getting Started

1. Fork the repository and create a branch from `main`.
2. Make your changes with clear, well-commented code. All code in this repository is intended for eventual publication and should be readable as a standalone artifact, not merely functional.
3. Open a pull request with a description of what you changed and why.

---

## Areas for Contribution

**Engine core** — The three-pass loop (intent parsing, outcome adjudication, prose rendering), context assembly, database read/write, and lazy world generation logic.

**Schema** — SQLite table definitions and migration scripts. Schema changes must include a migration script. The schema version number is embedded in the database and must be incremented with any structural change.

**Modules** — Seed data, game records, NPC records, location records, and structured seeding scripts for new or existing modules. See the Source Documentation requirement below.

**Tests** — Adjudication ground-truth examples generated during Sonnet prototyping. These are used to evaluate local model parity and should be logged systematically.

**Documentation** — Design documents, contributor guides, and module seeding notes.

---

## Source Documentation Requirement

All reference material used in module seeding must be documented with source and license before the pull request is merged. This is a firm requirement, not a best practice.

Preferred sources are Creative Commons licensed or in the public domain:

- [Project Gutenberg](https://gutenberg.org) — plain text editions of public domain literature
- [OpenStax](https://openstax.org) — CC-licensed humanities and science texts
- [Internet Archive](https://archive.org) — digitized historical primary sources
- [Wikimedia Commons](https://commons.wikimedia.org) — visual reference under open licenses
- University press open-access imprints

For each source used in seeding, record: title, author, date, source URL or archive reference, and license. This documentation lives alongside the module seed data in the `modules/` directory.

This standard exists for two reasons: legal clarity for contributors and adopters, and to support the project's educational use case, which depends on demonstrable open licensing of source material.

---

## Code Style

- Python is the primary implementation language.
- All functions and modules should be commented for readability by someone who did not write them.
- SQL schema files should include comments explaining field semantics, not just field names — especially for float fields with defined ranges and behavioral semantics.
- Avoid magic numbers; define constants with explanatory names.

---

## Schema Changes

- Every schema change requires a migration script in `schema/migrations/`.
- The migration script must be named with the new schema version number: `migrate_v{N}_to_v{N+1}.py`.
- The `schema_version` field in the database must be updated by the migration script.
- Document the reason for the schema change in the migration script header.

---

## Module Content

New modules should include:

- A game record defining genre, tone, era, and relevant cultural norms
- Seed records for all named NPCs with OCEAN traits, Ford-Nichols goal weights, Maslow tier, and (where applicable) hidden motivation
- Seed records for all named locations
- Source documentation for any reference material used (see above)
- A brief design note explaining the module's purpose and which engine mechanics it primarily exercises

---

## Questions

Open an issue for design questions, architecture discussions, or anything that doesn't fit neatly into a pull request.
