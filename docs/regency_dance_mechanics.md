# Regency Country Dance — Gameplay Mechanics Reference

*Design notes for the Netherfield Ball DAVE module. Compiled from general
knowledge of Regency period social customs. Verify against chapter_17_18.txt
and the Ball article in References/ where specific details matter.*

---

## The structure of an evening

A private ball (like the one at Netherfield) typically ran from roughly 9pm
to 2–4am. The evening was divided into sets of dances, with supper occurring
around midnight as a midpoint break. A full evening might contain 12–20
individual dances grouped into sets.

**Mechanically significant fixed points:**

| Event | Approximate time | Significance |
|---|---|---|
| Opening dance | ~9pm | Host/principal guests open; first partner choice is a public statement |
| Supper dance | ~midnight | Most intimate slot; gentleman escorts partner to supper |
| Supper | ~midnight–1am | 30–45 min; seated with supper partner; sustained private conversation |
| Final dance | ~2am | Closing set; often Sir Roger de Coverley or similar; another significant partner signal |

---

## Set structure and partner commitment

**This is the central mechanical constraint of the module.**

- Dances were grouped into *sets*. A set typically comprised two or three
  individual dances performed with the same partner — a commitment of roughly
  20–30 minutes.
- Once you accepted a set with a partner, you were bound to them for the
  entire set. You could not leave early to dance with someone else.
- **The refusal rule:** If a lady declined to dance a particular set, she was
  expected to sit out that entire set. Refusing one gentleman and then
  accepting another for the same set was a serious social offense. This rule
  creates genuine stakes in every refusal decision.
- **The two-set maximum:** Dancing more than two sets with the same partner
  in one evening was tantamount to a public declaration of romantic interest —
  widely observed and commented upon. Three sets with the same partner would
  be extraordinary and would generate immediate gossip. This constraint shapes
  the whole evening's dance allocation.

**Gameplay implication:** The dance card is a limited resource with strategic
allocation. Accepting Collins for two sets costs Elizabeth the same two slots
she might have used with Darcy or Wickham. Every acceptance forecloses other
options for that set. The two-set maximum means even a highly desirable partner
(Darcy) cannot dominate Elizabeth's evening.

---

## The supper dance

The supper dance is the most socially loaded single slot of the evening. The
gentleman who dances it with a lady escorts her into the supper room, seats
her, and shares the meal with her — roughly an hour of close, semi-private
company during which sustained conversation is possible without the
interruptions of dance figures.

Accepting the supper dance from someone is a significant signal. In the context
of the Netherfield Ball, who dances the supper dance with Elizabeth, and who
dances it with Jane, are both plot-relevant.

---

## Conversation during dancing

Country dances were longways sets — two lines of couples facing each other,
processing through figures in turn. This structure creates a distinctive
conversation rhythm:

- When a couple is "at the top" working through figures, they are physically
  occupied and can exchange only brief remarks between movements.
- When a couple is "standing out" waiting their turn lower in the set, they
  have more sustained conversation opportunity — but others in the set can
  observe and partially overhear.
- The dance thus produces an *interrupted* conversation: exchanges in fragments,
  with pauses enforced by the figures, and partial audience awareness at all times.

**Gameplay implication:** Dialogue during a dance should feel different from
dialogue in a private room — more fragmented, more public, with both parties
aware they are being watched. The Darcy–Elizabeth dance conversation in Chapter
18 is a masterclass in this: charged exchanges punctuated by the structure of
the dance, both of them performing composure while saying pointed things.

---

## Introductions and eligibility to dance

At a private ball, the host was responsible for introductions. You could not
properly request a dance from someone to whom you had not been formally
introduced. This is less constraining at Netherfield than at a public assembly
(where a master of ceremonies handled introductions for strangers) because the
guest list was curated — but it does mean that a new arrival without
introductions would be limited until the host performed them.

**For the module:** All principal characters (Darcy, Bingley, Wickham,
Collins, Jane, Charlotte) will have been introduced to Elizabeth before the
ball. A mechanic for newly-arrived or unknown characters needing introduction
may still be useful for minor NPCs.

---

## Specific dances of the period

- **Country dances (longways sets):** The dominant form. Progressive — couples
  work their way down the set over multiple figures. The music and figures were
  widely known; choosing which dance to call was the host's or musician's
  prerogative.
- **Sir Roger de Coverley:** A traditional longways country dance, commonly
  used to close a ball. Its use as a closing dance is confirmed in Austen's
  own work (*Emma*) and period sources.
- **Quadrilles:** Becoming fashionable in this period (especially post-1815)
  but still somewhat avant-garde for a Hertfordshire county ball in 1812.
  Probably not at Netherfield; use with caution.
- **Waltzes:** Highly controversial. The close hold (gentleman's hand on
  lady's waist) was considered scandalous by many. Almost certainly not at
  Netherfield in 1812; would generate significant negative comment if
  attempted.

---

## Social observation as gameplay

Attending a ball involved active surveillance of others as a normal social
activity. Guests were expected to notice and mentally catalog:

- Who danced with whom, and how many sets
- The dress and appearance of other guests (this was not considered rude;
  it was the point)
- Who was present and conspicuously absent (Wickham's absence from
  Netherfield is immediately noted by Elizabeth)
- Who was seated with whom at supper
- Behavior that reflected on family reputation (Mrs. Bennet's loud
  conversation, Lydia's flirting, Mr. Collins's dancing)

**Gameplay implication:** "Observe the room," "look for Wickham," "watch
Darcy," and "notice what Jane is doing" are all natural player actions at
a ball. The social observation mechanic is not peripheral — it is one of
the primary activities of the evening alongside dancing and conversation.

---

## The Collins problem

Mr. Collins presents a specific mechanical challenge. He will ask Elizabeth
to dance (it would be rude to refuse a family member's guest, and Mrs. Bennet
will exert pressure). He is a poor dancer — Austen specifies this. Dancing
with him is:

- Socially costly in terms of how Elizabeth appears to onlookers
- Embarrassing due to his ineptitude and conversation
- Time-consuming (the two-set maximum applies; he may attempt both)
- Unavoidable without significant social cost and family conflict

The Collins dances function mechanically as a tax on Elizabeth's dance card
and a source of reputation/composure pressure.

---

## Key constraints summary for schema design

1. **Dance card slots** — a finite number of sets in the evening; each set
   can hold one partner commitment per player
2. **Two-set maximum** — a hard social rule per partner pair
3. **Refusal = sit out** — declining a set forecloses that slot entirely
4. **Supper dance** — a special slot with extended social consequence
5. **First and last dances** — elevated social signal value
6. **Conversation rhythm** — interrupted by figures; partially public
7. **Introduction prerequisite** — must be introduced before dancing
8. **Observation as action** — social surveillance is a core activity,
   not a passive background
