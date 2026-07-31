# Quest Mechanics Design — The Vintage Village

*Design completed 2026-07-30. Status: designed, not yet implemented.*
*Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic).*

---

## Core pattern

Small, everyday tasks ("microquests") generated fresh each session from current NPC
state. Three active at a time across hostel and village combined, never queued or
accumulated between sessions. NPCs solve their own problems when the player is absent.

---

## Generation mechanism

Each quest-eligible NPC carries a **tendency description** — a prose field describing
the kinds of small disruptions plausible for this character given their role and
psychology. This likely lives in `context_beliefs` or a new dedicated field (schema
decision deferred until implementation). Example:

> "prone to misplacing small tools and valuables; sometimes has an errand she would
> welcome help with; occasionally lonely on quiet evenings"

At session start, a lightweight **generation pass** runs over quest-eligible NPCs.
The LLM receives the NPC's tendency, their OCEAN profile and `surface_motivation`,
the current season (from `game_state`, when implemented), time of day, and items
present at their usual location. It generates a specific `pending_intent` for this
session:

> "Has just noticed a hole worn through the bottom of her sewing basket and is
> worried her silver thimble has fallen through somewhere. Will mention it to anyone
> who seems kind — doesn't want to impose, but hopes someone will offer to help."

This `pending_intent` is written to the DB and persists for the session. The standard
pending_intent discharge mechanism handles the rest. No separate quest-tracking
system is required.

**Density target:** three active hooks per session, distributed across hostel and
village. Density is controlled by authoring: only selected NPCs carry quest tendencies.

---

## Task categories

Three plausible categories, each with a natural home in the existing schema:

**Displaced items.** An NPC's possession is missing or in an unexpected place. The
item exists in the DB with an unexpected `loc_id`. Lazy-generated when the hook is
created; the item appears at a plausible location for the player to find. Resolution:
player delivers or retrieves the item → `pending_intent` discharged → `character_attitude`
improves.

**Errands.** Something needs to go from one place or person to another — a letter, a
parcel, a message, a loaf of bread from the Tearoom to the Portmaster's Office.
No new item necessarily required; the `pending_intent` describes the chain. Resolution:
player completes each step → `pending_intent` discharged on each NPC in the chain.

**Social needs.** An NPC's `internal_state` is elevated (lonely, bored, worried) and
they would benefit from company or conversation. No item or delivery involved.
Resolution: player engages meaningfully → internal_state nudged, `character_attitude`
improves.

---

## Temporal behavior

The quest pool is a **current-state snapshot**, not an accumulated backlog. A month
can pass in the world between sessions; NPCs without active player involvement resolve
their own situations in that time. When the player arrives, the generation pass looks
at who is present and what their state is *right now*, and generates three hooks from
that. There is no record of everything that went unsolved while the player was away.

Quests that the player started but did not complete within a session are an edge case
to resolve during implementation — likely they are simply regenerated differently next
session, consistent with the above principle.

---

## Social reward

Helping improves `character_attitude` from the helped NPC and may improve reputation
with the `village_community` faction (to be created — separate from
`hosts_of_the_hostel`). NPC-to-NPC attitude propagation handles word spreading: the
weaver mentions the traveller's help to the tearoom keeper, and the keeper warms
slightly without any direct player interaction. No explicit reputation display; the
player experiences standing through NPC behavior.

---

## NPC proactivity mechanism

NPCs with active quest hooks must initiate contact when the player is present. The
player should not need to approach strangers and ask what they need.

**NPC-arrival trigger (existing):** when an NPC wanders into a location the player
occupies, Pass 2 receives `newly_arrived_npcs` and fires the `pending_intent` as the
NPC's opening action. This works for NPCs who seek the player out.

**Player-arrival trigger (needed, not yet implemented):** the symmetric case — the
player enters a location where a quest NPC is already sitting — currently has no
equivalent trigger. Pass 2 should receive a `player_just_arrived` signal and check
whether any NPC present has a `pending_intent` warranting immediate initiation. This
is a Pass 2 prompt/context change, not a schema change. (The Meryton Assembly
experience confirmed this gap: young men who should have asked Elizabeth Bennet to
dance did not reliably initiate because no arrival signal existed for the co-presence
case.)

**pending_intent wording:** quest hooks should use language that tells Pass 2 to fire
on co-presence, not only on deliberate player approach: "will mention it to anyone
who seems kind," "will catch the eye of anyone who looks helpful." The phrasing is
the mechanism.

---

## Implementation scope

All prerequisite schema elements are in place (`pending_intent`, `internal_state`,
`character_attitude`, `item.loc_id` for displacement, the full location graph). What
remains:

1. Add tendency field to eligible NPCs — `context_beliefs` or schema change (decide
   at implementation time).
2. Author tendency descriptions for quest-eligible NPCs — seed work, per-character.
3. Write session-start generation pass — new Python module or hook in `engine.py`.
4. Implement player-arrival trigger in Pass 2 prompt/context — engine change.
5. Create `village_community` faction — seed work.
6. For testing before the generation pass is built: author initial `pending_intent`
   values directly in `reset_instance.sql` as hand-written starters.

---

## Tagline

"The Village... where you're never just a number."

*(The double meaning is intentional: warm village community, and a pointed comment
about what DAVE is doing that most RPGs do not.)*
