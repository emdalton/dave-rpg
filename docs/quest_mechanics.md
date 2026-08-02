# Quest Mechanics Design — The Vintage Village

*Design completed 2026-07-30. Updated 2026-08-01. Status: designed, not yet implemented.*
*Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic).*

---

## Core pattern

Small, everyday tasks ("microquests") generated fresh each session from current NPC
state. Three active at a time across hostel and village combined, never queued or
accumulated between sessions. NPCs solve their own problems when the player is absent.

---

## Generation mechanism

Quest hooks are derived directly from each NPC's existing psychological profile —
`character_goal` weights, OCEAN scores, `maslow_tier`, and `internal_state` — rather
than from a separately authored tendency field. The psychological data already encodes
what kinds of situations are plausible for this character; the generation pass
synthesizes a specific `pending_intent` from it.

At session start, a lightweight **generation pass** runs over quest-eligible NPCs.
The LLM receives the NPC's goal weights, OCEAN scores, `maslow_tier`, `internal_state`,
`surface_motivation`, the current season (from `game_state`, when implemented), time
of day, and items present at their usual location. It generates a specific
`pending_intent` for this session:

> "Has just noticed she's out of tarragon and is in the middle of making lunch. Will
> ask anyone who comes into the kitchen if they could pick some from the garden."

This `pending_intent` is written to the DB and persists for the session. The standard
pending_intent discharge mechanism handles the rest. No separate quest-tracking
system is required.

Hand-authored `pending_intent` values in `reset_instance.sql` remain valid for
specific, pre-designed hooks — the generative mechanism and seed values coexist.

**Density target:** three active hooks per session, distributed across hostel and
village. Density is controlled by authoring: only selected NPCs are quest-eligible.

**Example derivation (Marta):** high conscientiousness (0.88) + `resource_provision`
goal (0.70) → distressed by small gaps in her ability to provide, even trivial ones.
`belonging` goal (0.80) + herbalism skill → motivated to help village community members
she cannot physically reach. `maslow_tier` = `esteem` + long tenure at a liminal
threshold → the major arc source (see below).

---

## Task scale

Quest hooks span three scales. The psychological profile drives which scale is
appropriate for a given NPC's current disequilibrium.

**Neighbor-favors (minor).** A householder asks anyone nearby for something small
when their hands are full. The right mental model is not "quest" but ordinary
social fabric — the kind of request you'd make of a neighbor. Done in minutes.
Examples: "I'm out of tarragon — could you pick some from the garden?"; "Could
you keep an eye on this pie while I chop onions?" No DB complexity required;
resolution is immediate and the reward is warmth, not points. Festival periods
naturally multiply these because Marta and other hosts are genuinely overwhelmed.

**Village errands (medium).** Something needs sourcing from the village — an
ingredient that's run out, a supply that didn't arrive, a remedy needed by someone
the NPC can't physically reach. Grounded in actual world-state: items present,
quantities, what happened last session. The player who was present for a busy
evening has context; a fresh arrival just sees an NPC looking harried and learns
why. Multiple valid routes through the village; no single correct path; locations
and characters visited for the first time are lazy-generated on arrival. Examples:
Marta short of fresh milk after a busy cheese night; a remedy needed by the Weaver
whose hand is injured. Resolution: item delivered or need met → `pending_intent`
discharged → `character_attitude` improves; village faction reputation may improve.

**Arcs (major).** A persistent disequilibrium rooted in the NPC's `maslow_tier`
or a long-standing unresolved situation. Not a task but a situation the player
gradually uncovers over multiple sessions by asking the right questions of the
right people. No single resolution path; the player's approach shapes what
resolution looks like. Example: see Marta arc below.

## Task categories (within scale)

Within each scale, hooks fall into three categories:

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

## The Marta arc (example major quest)

Room B at the end of the upper corridor has been locked as long as anyone can
remember; the world parameters note that Marta will not discuss it. The room is a
gate to another world — consistent with the hostel's established nature as a liminal
space where guests arrive from impossible origins. Marta is its keeper in a literal
sense, not just an innkeeper, and has been here, at this door, for a very long time,
for a reason she does not discuss.

The disequilibrium surface: a player who pays attention notices she lingers sometimes
at the foot of the stairs, looking up. Her work is as reliable as ever (conscientiousness
holds). The gap is in the small social moments. Gin-chan has almost certainly been in
that room. The Bookseller knows things about the hostel's history, obliquely. The
gossips know something happened, even if they don't know what. None of them will
hand the player a dossier — this is a world of quiet people — but questions asked
the right way, over several visits, accumulate into a picture: who the room belonged
to, what their relationship to Marta was, why they left or why they could not stay,
and what it would mean to Marta to have word of them.

Resolution is genuinely open. What the player brings back — a message, a person,
news, or simply an evening's company without questions — shapes what resolution
looks like. None of this needs to be pre-scripted; the world has enough people
and enough gaps that player curiosity does the generation work, and everything
discovered is stored and stays consistent.

---

## Social reward

Helping improves `character_attitude` from the helped NPC and may improve reputation
with the `village_community` faction (to be created — separate from
`hosts_of_the_hostel`). NPC-to-NPC attitude propagation handles word spreading: the
weaver mentions the traveller's help to the tearoom keeper, and the keeper warms
slightly without any direct player interaction. No explicit reputation display; the
player experiences standing through NPC behavior.

**Gossips as social infrastructure.** Two benign gossips — not malicious, just
genuinely interested in everyone and everything — are the visible face of the
attitude propagation mechanic. They know what happened, who helped whom, who is
unwell, who is courting whom. Their function in the quest network is load-bearing:
they are how Marta thanking you quietly in the kitchen becomes the Portmaster
warming to you without any direct interaction. They should be authored characters,
not lazy-generated, because the network depends on them. Their narratively noisy
presence also provides contrast with the hostel's quieter residents — this is
a world of quiet people, mostly, but not exclusively.

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

1. Write session-start generation pass — new Python module or hook in `engine.py`.
   Input to the LLM: goal weights, OCEAN scores, `maslow_tier`, `internal_state`,
   `surface_motivation`, season/time, items at location.
2. Implement player-arrival trigger in Pass 2 prompt/context — engine change.
3. Create `village_community` faction — seed work.
4. Author two gossip characters — seeded NPCs, not lazy-generated.
5. For testing before the generation pass is built: author initial `pending_intent`
   values directly in `reset_instance.sql` as hand-written starters.

Note: no tendency field is required. The generation pass reads directly from the
existing psychological schema.

---

## Tagline

"The Village... where you're never just a number."

*(The double meaning is intentional: warm village community, and a pointed comment
about what DAVE is doing that most RPGs do not.)*
