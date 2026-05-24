# Meryton Assembly — Location Graph Sketch

*Working document. Updated 2026-05-24 to add confirmed design decisions,
resolve open questions, and add service passage cluster.*

*This location graph is designed as a reusable **Regency public assembly hall**
template. The topology (grand entrance, staircase, main rooms, service cluster)
is stable across any module set in a similar venue. Module-specific details —
room descriptions, which rooms are active, faction configurations, character
starting positions — are the parameterization layer. For adaptation to another
module, copy this sketch and adjust the description_skeleton and passage_note
fields; the connection topology requires little or no change.*

*Building model: Shire Hall, Hertford (or similar Hertfordshire civic building).
Large sash windows, ballroom on first floor (UK), corn market and courts on
ground floor, service access at rear.*

---

## Design decisions — confirmed

- **Card room:** Present. Confirmed by architectural inference (the building
  has the space and a Regency assembly of this type would use it), not by
  direct textual evidence from Chapter 3. Flag in seed comments.
- **Ladies' retiring room:** Present. Same basis — standard assembly provision,
  not mentioned in Chapter 3 text. Flag in seed comments.
- **Supper / dining room:** A supper room is present in the building (location
  7 below) but unused at the Chapter 3 assembly — Chapter 3 text makes no
  mention of supper. The door is closed by convention, not locked. In a public
  assembly context, supper arrangements are lighter than at a private house
  ball; there is no separate "dining room" as a distinct location. The supper
  room activates in Chapter 2 (Netherfield Ball), becoming the destination of
  the supper dance partner.
- **Service passages:** Present. A full service cluster (service entrance,
  back stairs, service passage, staging area) is included. These locations are
  physically passable by any character but convention-blocked for upper-class
  characters via passage_note. This supports future "play as staff" character
  options (see future_features.md §14) without requiring schema changes, and
  gives Pass 2 the context to adjudicate class-crossing attempts with
  appropriate social consequences.

---

## Location list

### Ground floor — public

**1. Street Entrance / Vestibule**
The public face of the building. Guests arrive and depart here; carriages
are called from this point at the end of the evening. A transitional space —
neither fully inside nor outside — where the social performance begins before
the staircase is even reached. Arrivals visible to those already inside.

*description_skeleton:* The street door opens onto a narrow vestibule of
stone flags, lit by a lamp above the entrance. The noise of the assembly
reaches down faintly from above. Through the door, the night air and the
sounds of horses and carriages waiting.

*social_setting:* semi_private

---

**2. Staircase**
The processional spine of the building. Wide enough for two to pass with
ease; being seen on the staircase is being seen. The landing above gives a
vantage point over who is ascending.

*description_skeleton:* A broad staircase of dark wood, lit by candles in
wall sconces. The music from the ballroom above grows with each step. The
landing is visible from below; the street door visible from the landing.

*social_setting:* semi_private

*Connections:* Street Entrance (stairs, open), Landing (stairs, open)

---

### First floor — assembly rooms

**3. Landing**
The upper hallway connecting the staircase to the assembly rooms. Less
observed than the ballroom, more transient than the card room. Useful for
brief private exchanges, intercepting arrivals, or retreating momentarily
from the press of the dancing floor. Large sash windows face the street.

*description_skeleton:* The landing is quieter than the rooms beyond, the
music muffled by the closed ballroom door. Tall sash windows face the street,
dark now, with candlelight reflected in the glass. A door to the left leads
to the ballroom; a door to the right to the card room. At the far end of the
landing, two doors stand closed.

*social_setting:* semi_private

*Connections:* Staircase (stairs, open), Ballroom (door, open),
Card Room (door, open), Ladies' Retiring Room (corridor, open),
Supper Room (door, is_passable=0, passage_note below),
Corn Market passage (door, is_passable=0, passage_note below),
Magistrate's room passage (door, is_passable=0, passage_note below)

---

**4. Ballroom**
The principal room. Large, rectangular. Tall sash windows along one long
wall, dark at night, reflecting the assembled company. Musicians at one end.
Benches and chairs along the walls for those sitting out; the center cleared
for dancing. This is where social affairs are managed — introductions,
partnership negotiations, public observation.

Mrs. Bennet's starting position: wall seating, with line-of-sight to most
of the floor (established from Chapter 3 text — she reports everything she
sees).

*description_skeleton:* The ballroom is fully lit — candles in wall sconces
and a chandelier overhead, doubled in the dark windows along the far wall.
Two lines of couples are forming for the next set. Along the walls, chairs
are occupied by those sitting out; small groups stand in conversation near
the doors. At the far end, the musicians are tuning. The room smells of
candle wax, powder, and the warmth of many people.

*social_setting:* public

*Connections:* Landing (door, open), Card Room (open, internal arch or door),
Service Passage (service door, is_passable=1, passage_note below)

---

**5. Card Room**
Adjacent to the ballroom; accessible without crossing the dancing floor.
Occupied by those who prefer cards — older guests, gentlemen with no
interest in the floor, quieter conversations. More private than the ballroom.

*Note: presence inferred from building type and standard assembly practice;
not directly evidenced in Chapter 3 text. Flag in seed comment.*

*description_skeleton:* The card room is lit more dimly than the ballroom,
the music from next door reduced to a steady rhythm through the wall. Two
or three tables are occupied; the conversation is quieter here, the company
older on average. A window looks onto the street.

*social_setting:* semi_private

*Connections:* Landing (door, open), Ballroom (open, internal arch or door),
Service Passage (service door, is_passable=1, passage_note below)

---

**6. Ladies' Retiring Room**
A small room reserved for ladies to adjust dress, rest briefly, or conduct
conversations with a degree of privacy unavailable on the main floor.
Gentlemen do not enter. One of the few genuinely private spaces available
to Elizabeth during the evening.

*Note: presence inferred from standard assembly provision; not mentioned in
Chapter 3 text. Flag in seed comment.*

*description_skeleton:* A small room with a dressing table, a mirror, and
two chairs. A maid is in attendance. The sounds of the assembly are distant
here.

*social_setting:* private

*Connections:* Landing (corridor, open)

---

### First floor — non-passable (upper class convention or lock)

**7. Supper Room**
Present but unused at the Chapter 3 assembly — no supper is served at the
Meryton ball. Door closed by convention, not locked. Entry is possible for a
character willing to accept the social cost; Lydia is the canonical example.

*Future activation (Chapter 2, Netherfield Ball):* is_passable flips to 1 at
the supper hour; passage_note updates to 'open'. The supper room becomes the
most socially significant space of the evening — set with tables, lit, and
the destination of the supper dance partner.

*description_skeleton (if entered):* Dark and smelling of cold wood and
linen. Tables folded against the walls, chairs stacked. The noise of the
assembly is muffled. Nothing here is meant to be seen tonight.

*social_setting:* private

*passage_note:* 'Closed by convention — door unlocked, room unlit and unused.
Entering would be considered improper for a lady without compelling reason.
The social cost is significant; a character with low conscientiousness or
high self-determination motivation might attempt it regardless.'

*Connections:* Landing (door, is_passable=0),
Service Passage (service door, is_passable=1, passage_note below)

---

**8. Corn Market Hall** (ground floor)
By day a commodities exchange. Closed and dark during the evening assembly.
The door from the landing passage is locked during the assembly.

*description_skeleton (if entered):* Dark. The smell of grain and stone
floors. Tall shuttered windows. Trestle tables along the walls. The noise
of the assembly is faint and distant. This is not where anyone should be.

*passage_note:* 'Locked during the evening assembly. Requires a key or
forced entry; no social workaround is available.'

*Connections:* Landing (door, is_passable=0)

---

**9. Magistrate's / Assize Room** (first floor, separate wing)
The court space. Closed during the assembly. More imposing than the corn
market — formal furniture, a raised bench, the weight of civic authority.
Same locked logic applies.

*passage_note:* 'Locked during the evening assembly. Requires a key or
forced entry.'

*Connections:* Landing (door, is_passable=0)

---

### Ground floor — service cluster

**10. Service Entrance / Back Yard**
The rear or side entrance used by staff, deliveries, and hired help. Where
musicians' cases are stacked, where refreshment supplies arrived earlier in
the day, where servants come and go throughout the evening. Entirely normal
for anyone working the event; completely out of place for a guest.

*description_skeleton:* A flagged yard at the rear of the building, lit by
a single lamp above the service door. Stacked crates, a handcart. The sounds
of the assembly are faint up here. The street is accessible around the
corner of the building, but this is not the entrance anyone came to use.

*social_setting:* private

*passage_note (service door to outside):* NULL — open access for staff.

*Connections:* Back Stairs (stairs, is_passable=1,
passage_note='Service stairs — staff only. An upper-class character here
would be conspicuously out of place and likely mistaken for lost or
attempting to leave discreetly.')

---

**11. Back Stairs**
The service staircase connecting the service entrance at ground level to
the service passage above. Narrow, functional, unlit compared to the grand
staircase. Staff move between floors here throughout the evening without
crossing the main rooms.

*description_skeleton:* Narrow stairs of bare wood, lit by a single candle
in a holder on the wall. Sounds of movement above and below. The smell of
food and tallow.

*social_setting:* private

*Connections:* Service Entrance (stairs, is_passable=1,
passage_note='Service stairs — see Service Entrance note.'),
Service Passage (stairs, is_passable=1,
passage_note='Service stairs — staff only.')

---

**12. Service Passage**
The back corridor running behind the ballroom, card room, and supper room
on the first floor. Staff use this to move between rooms and deliver
refreshments without crossing the dancing floor. Service doors open from
here into each of the main rooms.

*description_skeleton:* A narrow corridor, low-ceilinged, smelling of
candle wax and the warmth of the rooms on the other side of the thin walls.
The music is clearly audible through the ballroom door. A series of plain
doors, each leading to one of the assembly rooms.

*social_setting:* private

*Connections:* Back Stairs (stairs, is_passable=1),
Ballroom (service door, is_passable=1,
passage_note='Service entrance to ballroom — staff only. An upper-class
character entering from here would emerge visibly from the wrong side of
the room and attract immediate attention.'),
Card Room (service door, is_passable=1,
passage_note='Service entrance to card room — staff only. Less visible than
the ballroom entrance but still conspicuous.'),
Supper Room (service door, is_passable=1,
passage_note='Service access to supper room — used by staff preparing the
room and, on busier evenings, carrying food. Open to staff at all times.'),
Staging Area (open, is_passable=1)

---

**13. Staging Area / Preparation Room**
A small room off the service passage where refreshments are assembled before
being carried out to the card room or supper room. On a light assembly
evening this is a modest operation — a table with glasses, a few bottles,
a tray or two. The staff member responsible for refreshments works from here.

*description_skeleton:* A small, warm room that smells of wine and pastry.
A table holds trays set for carrying. Bottles are arranged along one wall.
A candle burns on the table. From beyond the door, the muffled beat of the
music.

*social_setting:* private

*Connections:* Service Passage (open, is_passable=1),
Supper Room (door, is_passable=1,
passage_note='Direct access between staging and supper room — service use
only.')

---

## Connections summary

```
Public circuit (upper-class navigation):
  Street Entrance ↔ Staircase (stairs)
  Staircase ↔ Landing (stairs)
  Landing ↔ Ballroom (door)
  Landing ↔ Card Room (door)
  Landing ↔ Ladies' Retiring Room (corridor)
  Ballroom ↔ Card Room (internal, open)

Convention-closed (is_passable=0, social cost to enter):
  Landing → Supper Room (door, passage_note: closed by convention)

Locked (is_passable=0, requires key):
  Landing → Corn Market Hall (door, passage_note: locked)
  Landing → Magistrate's Room (door, passage_note: locked)

Service cluster (is_passable=1 throughout, passage_noted for class context):
  Service Entrance ↔ Back Stairs (stairs)
  Back Stairs ↔ Service Passage (stairs)
  Service Passage ↔ Ballroom (service door)
  Service Passage ↔ Card Room (service door)
  Service Passage ↔ Supper Room (service door)
  Service Passage ↔ Staging Area (open)
  Staging Area ↔ Supper Room (door)
```

*Total locations: 13 (6 navigable public, 3 non-passable, 4 service)*

---

## Open questions — resolved

1. **Supper room:** Not mentioned in Chapter 3. No supper at this assembly.
   Room present but unused; door closed by convention, not locked.
   ✅ Resolved.
2. **Card room:** Present by architectural inference; no Chapter 3 textual
   evidence. Include with seed comment flagging the inference.
   ✅ Resolved.
3. **Ladies' retiring room:** Present by standard assembly provision inference;
   not mentioned in Chapter 3. Include with seed comment.
   ✅ Resolved.
4. **Dining room as separate location:** No. Supper in a public assembly
   context is served in the supper room, not a distinct dining room. The
   supper room (location 7) covers this.
   ✅ Resolved.
5. **Exterior access:** Not mentioned. No balcony or terrace scene in
   Chapter 3. No exterior location on first floor.
   ✅ Resolved.
6. **Master of ceremonies:** No named MC in Chapter 3. Bingley managed his
   own introductions socially; Sir William Lucas is present as a neighbor.
   No MC gatekeeper NPC needed in seed.
   ✅ Resolved.
7. **Number of sets:** At least 7 (6 named in Mrs. Bennet's account +
   Boulanger as closing dance). Boulanger confirmed as closing dance.
   ✅ Resolved — seed dance schedule with 7 slots.
8. **Mrs. Bennet's starting position:** Seated watching, not dancing.
   Line-of-sight to most of the ballroom. Starting location: Ballroom
   (wall seating).
   ✅ Resolved.
9. **Service passages:** Include full service cluster (4 locations).
   Passable to all; convention-blocked for upper-class via passage_note.
   ✅ Resolved.

## Open questions — still unresolved

1. **Card room connection to ballroom:** Internal arch or closable door?
   Affects whether conversation in the card room can be overheard from the
   ballroom. Design as open arch for now (maximizes acoustic permeability);
   revise if a scene requires privacy.
2. **Service entrance ground-floor topology:** The service entrance and street
   entrance are on the same floor but different sides of the building.
   They do not connect internally. A character moving between them would
   go outside and around the building (no game location for this path).
   Acceptable for Chapter 3; revisit if an exterior circuit matters.
