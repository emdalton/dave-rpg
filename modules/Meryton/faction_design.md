# DAVE — Faction and Reputation System Design

*Written 2026-05-24. Covers schema design for faction reputation mechanics,
motivated by the Meryton module. Intended as a schema migration before
Meryton seed work begins.*

---

## Motivation

The Meryton/P&P module requires a reputation system that I Am a Cat
deliberately avoided. Elizabeth Bennet's most significant decisions involve
tension between her standing with different social groups — most clearly in
her refusal of Collins, which serves her individual interests at real cost
to her `bennet_family` standing. This tension only has mechanical weight if
factions are tracked as distinct entities with their own reputation floats,
not collapsed into a single reputation value.

The system is designed to be general: any module can define its own factions.
I Am a Cat has no factions; Meryton has three or four; a future multiplayer
module set in a political context might have a dozen.

---

## Factions in the Meryton module

**`bennet_family`**
The Bennet family unit. Elizabeth's primary allegiance and the source of her
most difficult decisions. Actions that protect or advance the family's
security, reputation, or harmony increase standing; actions that embarrass
them, damage their prospects, or defy family interest decrease it.

The Collins refusal (Chapters 19–20, outside this module but motivating the
design) is the paradigm case: a guaranteed financial solution to the entail
problem, refused on principle. Mrs. Bennet's fury is the external expression
of falling `bennet_family` reputation. Elizabeth's internal conflict — she
knows what Collins represents for her sisters — comes from her motivations,
which Pass 2 adjudicates from her OCEAN and goal values.

**`meryton_neighborhood`**
Local social standing. What the Meryton community — the Lucases, the Philipses,
the general neighborhood — thinks of Elizabeth and the Bennets. The primary
public reputation metric for Chapter 3. Behavior that is locally admired
(dancing well, conversing graciously, managing her family's excesses discreetly)
raises this; behavior that draws negative comment lowers it.

**`bingley_circle`**
Bingley, his sisters, and Darcy. Distinct from the neighborhood because their
standards and social reference points are different and higher. Elizabeth can
have strong `meryton_neighborhood` standing and weak `bingley_circle` standing
simultaneously — this is essentially her situation through most of the novel.
Being condescended to by Miss Bingley does not damage her neighborhood
reputation; being embarrassed by Mrs. Bennet at the Netherfield Ball damages
both.

**`lucas_family`** (optional, may fold into `meryton_neighborhood`)
The Lucas family specifically. Their interests don't diverge from the
neighborhood until Charlotte accepts Collins, at which point Charlotte becomes
a personal ally regardless of faction standing. Consider keeping separate if
the Charlotte-Collins arc is included in Chapter 2.

---

## Connection to Fate Point economy

The Collins refusal is a textbook Fate compel:
- An aspect of Elizabeth's situation (family obligation, the entail) creates
  pressure to accept an outcome she doesn't want (Collins).
- Refusing costs `bennet_family` reputation — a real, tracked, mechanical loss.
- Accepting would preserve it but damage her self-determination motivation.
- A Fate Point award for refusing would reflect: you took the worse outcome
  for a dramatically interesting reason.

This connection should be kept in mind when implementing the Fate Point
economy (future_features.md §11). The two systems are designed to work
together: factions give compels mechanical weight; Fate Points reward
accepting them.

---

## Proposed schema

Two new tables. This is a schema migration — version number to be assigned
when implementation begins. Add before any Meryton seed work.

```sql
-- -------------------------------------------------------------------------
-- faction
--
-- Named social groups whose opinion of a character has mechanical weight.
-- Scoped to a game (module); factions are module-specific.
-- I Am a Cat has no factions (no rows for game_id=1).
-- -------------------------------------------------------------------------
CREATE TABLE faction (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id     INTEGER NOT NULL REFERENCES game(id),
    name        TEXT NOT NULL,
    -- Short identifier used in context packets and outcome JSON.
    -- e.g. 'bennet_family', 'meryton_neighborhood', 'bingley_circle'

    description TEXT NOT NULL
    -- Semantic description for Pass 2: what this faction values, how it
    -- judges characters, what kinds of actions raise or lower standing.
    -- Write as if briefing the LLM on the faction's perspective.
);

-- -------------------------------------------------------------------------
-- character_faction_reputation
--
-- A character's standing with a faction. Float 0.0–1.0.
--   0.0 = complete disgrace / ostracism
--   0.5 = neutral or unknown
--   1.0 = exceptional standing / full acceptance
--
-- Tracked primarily for the player character, but can be seeded for NPCs
-- whose faction standing matters to adjudication (e.g. Wickham's standing
-- with the militia regiment).
--
-- Pass 2 updates these via 'faction_reputation_changes' in outcome JSON.
-- Engine applies deltas and clamps to [0.0, 1.0] in _apply_outcome().
-- -------------------------------------------------------------------------
CREATE TABLE character_faction_reputation (
    character_id    INTEGER NOT NULL REFERENCES character(id),
    faction_id      INTEGER NOT NULL REFERENCES faction(id),
    reputation      REAL    NOT NULL DEFAULT 0.5,
    notes           TEXT,
    -- Optional: human-readable note on why standing is at its current value.
    -- Set by seed or by Pass 2 outcome. Included in Pass 2 context.
    -- e.g. "Bennet family grateful for her management of Lydia at the assembly"

    PRIMARY KEY (character_id, faction_id)
);
```

---

## Engine changes required

**`_apply_outcome()` in engine.py:**
Add handling for a new outcome field `faction_reputation_changes`:
```json
"faction_reputation_changes": [
    {"character_id": 1, "faction_id": 2, "delta": -0.08,
     "reason": "Elizabeth refused to manage Mrs. Bennet's outburst"}
]
```
Apply as: `clamp(reputation + delta, 0.0, 1.0)`. Same pattern as
`internal_state_delta`.

**`context.py` — Pass 2 packet:**
Include `faction_reputations` in the player character's profile block:
```json
"faction_reputations": [
    {"faction": "bennet_family", "reputation": 0.62,
     "notes": "Family pleased with her social conduct so far"},
    {"faction": "meryton_neighborhood", "reputation": 0.70, "notes": null},
    {"faction": "bingley_circle", "reputation": 0.45,
     "notes": "Darcy has expressed open contempt; sisters indifferent"}
]
```

**Pass 2 prompt template:**
Add a note that `faction_reputation_changes` is an available output field,
with the same structure as `attitude_delta`. Instruct the LLM to issue
changes when player actions have clear social consequences within a faction's
value system.

---

## Starting reputation values for Elizabeth (Chapter 3 seed)

| Faction | Starting value | Rationale |
|---|---|---|
| `bennet_family` | 0.65 | Respected daughter; no conflicts yet |
| `meryton_neighborhood` | 0.68 | Well-regarded locally; family is a little ridiculous but Elizabeth is not |
| `bingley_circle` | 0.30 | Unknown to them on arrival; Darcy's snub sets a low initial ceiling |

---

## Open questions

1. Should NPC faction reputations be tracked, or only the player's? Wickham's
   standing with the militia is relevant when he appears (Chapter 2); Darcy's
   standing with `meryton_neighborhood` is relevant to how locals discuss him.
   Recommendation: track for any NPC whose faction standing affects Pass 2
   adjudication — start with player only, add NPCs as needed.

2. Single `neighborhood_reputation` for Chapter 3, or split
   `meryton_neighborhood` and `lucas_family` from the start? Recommendation:
   start with three factions (bennet_family, meryton_neighborhood,
   bingley_circle); add lucas_family if the Charlotte-Collins arc is included
   in Chapter 2.

3. Does reputation decay passively (like boredom or hunger in I Am a Cat),
   or is it only event-driven? Recommendation: event-driven only for now.
   Passive reputation decay is a feature for later modules where prolonged
   absence from a social circle would naturally erode standing.
