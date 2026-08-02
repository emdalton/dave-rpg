# Player Character Profile — Emergent Psychology

*Design note, 2026-08-01. Status: designed, not yet implemented.*
*Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic).*

---

## Core principle

For NPCs, OCEAN scores, goal weights, and Maslow tier are authored values — the
designer knows who these characters are. For the player character, these fields
are *output*, not input. The engine observes what the player does and builds the
psychological profile over time from behavior. The player does not fill out a
character sheet; they reveal themselves through play, and the model becomes more
accurate with each session.

This is consistent with the quiet-world design: the engine is noticing, not judging.
The profile is internal and not displayed to the player. It exists so the engine
can understand the player's actions more accurately and surface things they will
find interesting.

---

## Initial state

The Green Room introduction (Fate Aspects) provides the first seed data — a High
Concept, a Trouble, and additional Aspects give Pass 1 and Pass 2 early material
to work from. OCEAN values and goal weights start as NULL (unknown), not as neutral
defaults. The distinction matters: NULL means "no data yet," not "average person."
Pass 2 should treat unknown values as genuinely open, not as 0.5.

Maslow tier starts as `belonging` by default — the player has arrived somewhere
safe and is orienting socially — but is updated as play reveals more.

---

## Inference from behavior

The engine infers profile updates from patterns in the `action_log`. Individual
actions are weak signals; repeated patterns across a session or across sessions
are meaningful. Suggested inference rules:

**OCEAN:**

- `ocean_openness`: elevated by exploring new locations unprompted, asking unusual
  questions, engaging with the liminal and strange, trying things without knowing
  the outcome.
- `ocean_conscientiousness`: elevated by tidying up, making the bed, returning
  borrowed items, completing accepted tasks, following through on stated intentions.
  Lowered by leaving things unfinished without explanation.
- `ocean_extraversion`: elevated by initiating conversations with multiple NPCs
  per session, lingering in social spaces, introducing topics unprompted.
- `ocean_agreeableness`: elevated by offering help before being asked, deferring
  to NPC preferences, clearing the table, small acts of consideration.
- `ocean_neuroticism`: inferred from response to setbacks and surprises — does the
  player adapt and continue, or dwell, or avoid the situation that caused difficulty?

**Goals (Ford-Nichols):**

- `understanding` / `exploration`: player goes to new locations without a specific
  reason; asks questions about history, lore, how things work.
- `belonging`: player builds relationships over multiple sessions, remembers NPC
  names and details, returns to people they've met.
- `resource_provision` / `social_responsibility`: player helps repeatedly, including
  when not asked; completes tasks that benefit others with no obvious personal gain.
- `self_determination`: player ignores suggestions and follows their own path;
  resists implied obligations.
- `mastery`: player practices or studies things, returns to skills they've used before.

**Maslow tier:**

Derived from internal state rather than set directly. The physiological layer
(`hunger`, `fatigue`) is already implemented as drifting `internal_state` values.
If these are frequently elevated, the player is operating under physiological
pressure. Belonging and esteem emerge from social engagement patterns — a player
who is building relationships and completing tasks is operating at the belonging
or esteem tier. Self-actualization is a long-term inference from sustained,
intrinsically motivated exploration and helping.

---

## How the profile is used

**Pass 2 context.** The PC's current profile (whatever is known) is included in
the Pass 2 context packet alongside NPC profiles. Pass 2 uses it to adjudicate
NPC responses — a player who has demonstrated conscientiousness gets a different
reading from Marta than one who leaves things where they fall. NPCs in this world
are perceptive; they notice character over time.

**Quest presentation.** The generation pass considers the PC's profile when
selecting which hooks to surface. A high-Openness player finds the world keeps
producing interesting corners; a high-Agreeableness player finds that people
approach them more readily. This is a soft influence, not a gate — any player
can encounter any type of quest. The profile shapes likelihood, not access.

**Attitude propagation.** NPC-to-NPC attitude propagation already handles reputation
spreading. The PC's profile adds a layer: NPCs form impressions from observed
behavior as well as from what others say. The Bookseller who has watched the player
spend an hour in the stacks and ask good questions will have a different baseline
impression than one who has only heard the player mentioned in passing.

---

## Update mechanism

Profile updates are written to `character_evolution` (existing table) at natural
moments — end of session, or when a pattern becomes clear enough to warrant it.
Updates are small adjustments, not sudden shifts. The inference pass should be
conservative: one generous action does not make someone Agreeable; a sustained
pattern does.

The PC's Fate Aspects remain a parallel record — the narrative self-description
the player gave at the start. The OCEAN profile that emerges over time may confirm,
complicate, or quietly contradict those Aspects. That tension is interesting and
need not be resolved.

**Inconsistent players.** A player who behaves inconsistently — exploring one
session, staying close to home the next; helpful sometimes, indifferent other times
— will not accumulate a confident profile. This is not a failure state. Low
confidence means the engine has less to go on when selecting what to surface, so
the world presents a wider and more varied mix rather than one tuned to a known
style. Inconsistency is its own kind of character and the engine accommodates it
naturally: stay uncertain, keep things varied. The engine notices; it does not judge.

---

## Implementation notes

- PC OCEAN fields should be nullable from first insert; do not default to 0.5.
- The inference pass is a new lightweight module, likely running at session end.
- Pass 2 prompt should handle partial profiles gracefully — "openness: unknown,
  conscientiousness: 0.72 (3 sessions of data)" is useful context even when
  incomplete.
- The Maslow tier derivation from internal_state values needs a small piece of
  engine logic to translate float levels into tier labels.
- `character_evolution` log entries for PC should note the behavioral evidence
  that prompted the update, not just the delta, for transparency and debugging.
