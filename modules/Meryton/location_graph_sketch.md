# Meryton Assembly — Location Graph Sketch

*Working document. To be refined against chapter_03.txt and Wikipedia reference
before committing to seed.sql. Building based on the standard Regency provincial
assembly room layout, with specifics from the Hertford civic building model:
large sash windows, ballroom on first floor (UK), corn market and courts on
ground floor.*

---

## Navigable locations (assembly hours)

### Ground floor

**1. Street Entrance / Vestibule**
The public face of the building. Guests arrive and depart here; carriages
are called from this point at the end of the evening. A transitional space
— neither fully inside nor outside — where the social performance begins
before the staircase is even reached. Possible uses: arrivals visible to
those already inside, outdoor air, private conversation away from the crowd.

*description_skeleton:* The street door opens onto a narrow vestibule of
stone flags, lit by a lamp above the entrance. The noise of the assembly
reaches down faintly from above. Through the door, the night air and the
sounds of horses and carriages waiting.

---

**2. Staircase**
The processional spine of the building. Arrivals ascend it visibly; the
landing above gives a vantage point over who is coming up. In a building
of this type the staircase is wide enough for two to pass with ease but not
so grand as to permit anonymous movement. Being seen on the staircase is
being seen.

*description_skeleton:* A broad staircase of dark wood, lit by candles in
wall sconces. The music from the ballroom above grows with each step. The
landing is visible from below; the street door visible from the landing.

*Connections:* Street Entrance (down), Landing (up)

---

### First floor (UK) — assembly rooms

**3. Landing**
The upper hallway connecting the staircase to the assembly rooms. A
semi-private space — less observed than the ballroom, more transient than
the card room. Useful for brief private exchanges, intercepting arrivals,
or retreating momentarily from the press of the ballroom. The large windows
of the building face the street from here; at night, candlelight and darkness
beyond the glass.

*description_skeleton:* The landing is quieter than the rooms beyond,
the music muffled by the closed ballroom door. Tall sash windows face the
street, dark now, with candlelight reflected in the glass. A door to the
left leads to the ballroom; a door to the right to the card room. At the
far end of the landing, two doors stand closed — the corn market below has
its own access, and the passage to the magistrate's room is not for tonight.

*Connections:* Staircase (down), Ballroom (door), Card Room (door),
[Closed] Corn Market passage (locked/closed during assembly),
[Closed] Magistrate's room passage (locked/closed during assembly)

---

**4. Ballroom**
The principal room. Large, rectangular, running the length of the building.
Tall sash windows along one long wall (dark at night, reflecting the
candlelight and the assembled company back at themselves). Musicians at one
end — a small raised platform or gallery. Benches and chairs along the walls
for those sitting out. The center of the floor is cleared for dancing; the
perimeter is for observation, conversation, and the management of social
affairs.

This is where the master of ceremonies (Sir William Lucas) operates —
introducing strangers, calling dances, managing the social machinery of
the evening.

*description_skeleton:* The ballroom is fully lit — candles in wall
sconces and a chandelier overhead, doubled in the dark windows along the
far wall. Two lines of couples are forming for the next set. Along the
walls, chairs are occupied by those sitting out; small groups stand in
conversation near the doors. At the far end, the musicians are tuning.
The room smells of candle wax, powder, and the warmth of many people.

*Connections:* Landing (door), Card Room (internal door or arch)

---

**5. Card Room**
Adjacent to the ballroom; accessible without passing through the main
dancing floor. Occupied by those who prefer cards to dancing — older
guests, gentlemen with no interest in the floor, those conducting quieter
conversations. Later in the evening this room may be rearranged as the
supper room, or supper may be served here alongside the card tables
(to be confirmed against chapter text).

A more private space than the ballroom — less observed, conversations less
easily overheard.

*description_skeleton:* The card room is lit more dimly than the ballroom,
the music from next door reduced to a steady rhythm through the wall. Two
or three tables are occupied; the conversation is quieter here, the company
older on average. A window looks onto the street.

*Connections:* Landing (door), Ballroom (internal door or arch)

---

**6. Ladies' Retiring Room**
A small room accessible from the landing or from a corridor off the
ballroom, reserved for ladies to adjust dress, rest briefly, or conduct
conversations with a degree of privacy unavailable on the main floor.
Gentlemen do not enter. One of the few genuinely private spaces available
to Elizabeth during the evening.

*description_skeleton:* A small room with a dressing table, a mirror,
and two chairs. A maid is in attendance. The sounds of the assembly are
distant here.

*Connections:* Landing (corridor)

---

## Non-passable locations (assembly hours)

These locations exist in the building and may be referenced in conversation
or description, but are not accessible during the assembly. `is_passable = 0`
for all connections into these rooms.

**Note on barrier types:** The reason for non-passability matters for Pass 2
adjudication and should be recorded in a `passage_note` field on
`location_connection` (schema addition needed). A locked door is physically
impassable; a closed-by-convention door is socially impassable — the cost of
entry is reputation damage, not a physical capability. Pass 2 reads the note
and adjudicates the distinction.

---

**7. Supper Room**
Present in the building but unused at this assembly — no supper is served at
the Chapter 3 Meryton ball. The door is closed but not locked. No well-bred
lady would enter an unlit, unoccupied service room during a social occasion;
the barrier is convention and reputation, not a key.

*Future activation:* In Chapter 2 (Netherfield Ball), this room becomes the
most socially significant space of the evening — set with tables, lit, and
the destination of the supper dance partner. `is_passable` flips to 1 at the
supper hour; the passage_note changes from "closed by convention" to "open."

*Future update path (Chapter 1):* The door being unlocked means entry is
possible for a character willing to accept the social cost, or one following
someone who has already gone in (see: Lydia).

*description_skeleton (if entered):* Dark and smelling of cold wood and linen.
Tables folded against the walls, chairs stacked. The noise of the assembly is
muffled. Nothing in here is meant to be seen tonight.

*passage_note:* "Closed by convention — door unlocked, room unlit and unused.
Entering would be considered improper; no well-bred lady would do so without
compelling reason."

---

**9. Corn Market Hall** (ground floor)
By day, a commodities exchange for grain and agricultural produce serving
the Hertfordshire market. A large, utilitarian space — the commercial heart
of the building's daytime life. Closed and dark during the evening assembly.

A door from the landing passage leads toward it; during the assembly this
door is locked or understood to be off-limits.

*Future update path:* Set `is_passable = 1` on this connection if:
— the door is discovered ajar (engine can set this as an event outcome), or
— Lydia has wandered through it (engine sets NPC location, player follows), or
— a `what_if` premise modifier grants Elizabeth relevant skills or motivation.

*description_skeleton (if entered):* Dark. The smell of grain and stone
floors. Tall shuttered windows. Trestle tables along the walls. The noise
of the assembly is faint and distant. This is not where anyone should be
at this hour.

**10. Magistrate's / Assize Room** (first floor, separate wing)
The court space; used for local legal proceedings. Closed during the
assembly. More imposing than the corn market — formal furniture, a raised
bench, the weight of civic authority. Same `is_passable` logic applies.

---

## Connections summary

```
Street Entrance ↔ Staircase
Staircase ↔ Landing
Landing ↔ Ballroom
Landing ↔ Card Room
Landing ↔ Ladies' Retiring Room (corridor)
Landing ↔ [Closed, convention] Supper Room
Landing ↔ [Closed, locked] Corn Market passage
Landing ↔ [Closed, locked] Magistrate's room passage
Ballroom ↔ Card Room (internal)
```

*Schema note: `location_connection` needs a `passage_note` TEXT field to
record barrier type. "locked," "closed by convention," "open" are the
values needed for this module.*

---

## Open questions — resolved from chapter_03.txt

1. **Supper room:** Not mentioned in Chapter 3. No supper served at this
   assembly. Room present but unused; door closed by convention, not locked.
   ✅ Resolved — see location 7 above.
2. **Exterior access:** Not mentioned. No balcony or terrace scene in
   Chapter 3. Treat as no exterior access from first floor.
   ✅ Resolved — omit exterior location for this module.
3. **Master of ceremonies:** No named MC in Chapter 3. Bingley managed his
   own introductions socially. Sir William Lucas is a neighbor (Lady Lucas
   mentioned) but not confirmed as MC. Leave MC role open; introductions
   are handled through social interaction, not a gatekeeper NPC.
   ✅ Resolved — no MC character needed in seed.
4. **Number of sets:** At least 7 (6 named in Mrs. Bennet's account +
   the Boulanger as closing dance). Boulanger confirmed as closing dance.
   ✅ Resolved — seed dance schedule with 7 slots.
5. **Mrs. Bennet's position:** Seated watching, not dancing. Reports
   everything she observes, implying line-of-sight to most of the ballroom.
   Starting location: ballroom (wall seating), not card room.
   ✅ Resolved.

## Open questions — still unresolved

1. Card room confirmed only by inference (Mr. Hurst's character; "merely
   looked the gentleman"). No direct textual evidence from Chapter 3.
   Keep as inferred location; flag in seed comments.
2. Ladies' retiring room likewise inferred from standard assembly layout,
   not mentioned in Chapter 3 text.
