# Meryton Assembly — Character Design

*Working document. OCEAN values, motivations, starting emotional states, and
seed notes for all characters present at the Chapter 3 assembly. To be
translated to seed.sql once schema additions (passage_note, pending_intent,
reputation floats) are confirmed.*

*Design principle: seed honest values, not canonical plot outcomes. Characters
should generate their own behavior from their psychology. Minor catastrophes —
social missteps, wandering, indiscretions — emerge from truthful seeding rather
than being scripted.*

---

## OCEAN scale notes

All values 0.0–1.0. The LLM adjudicates behavior from these values and the
character's stated motivations; it does not need to be told what specific
actions to take. Honest seeding produces authentic behavior.

| Trait | Low end | High end |
|---|---|---|
| Openness | Conventional, prefers routine, resistant to new ideas | Curious, imaginative, seeks new experiences and perspectives |
| Conscientiousness | Impulsive, unreliable, acts without forethought | Principled, organized, reliable, follows through |
| Extraversion | Avoids social engagement, prefers solitude | Seeks social engagement, energized by company, expressive |
| Agreeableness | Critical, competitive, dismissive of others | Warm, cooperative, trusting, wants harmony |
| Neuroticism | Emotionally stable, calm under pressure | Anxious, volatile, easily upset, emotionally reactive |

---

## Primary characters

### Elizabeth Bennet (player character)

| O | C | E | A | N |
|---|---|---|---|---|
| 0.78 | 0.62 | 0.55 | 0.62 | 0.28 |

**Openness:** Elizabeth's defining trait. Intellectually curious, reads widely,
genuinely interested in people and their psychology. Her wit is a product of
openness — she notices things and makes unexpected connections.

**Conscientiousness:** Principled and thoughtful but capable of acting on
first impressions (she will do this with both Wickham and Darcy). Not rigid.

**Extraversion:** Comfortable in social settings, enjoys conversation and
dancing, but doesn't need the spotlight. She observes as much as she
participates.

**Agreeableness:** Warm toward those she loves (Jane especially), capable of
genuine kindness, but not a pushover. She will speak her mind and push back.

**Neuroticism:** Low and stable. The snub doesn't wound her; it amuses her.
Her confidence is genuine, not performed.

**Starting emotional state:** Anticipatory — looking forward to the evening,
curious about Bingley's party.

**Primary motivations:**
- Understanding (making sense of people; her core drive)
- Individuality (maintaining her own perspective; resistance to pressure)
- Social connection (genuine; Jane above all, then Charlotte)

**Internal states at start:**
- composure: 0.78
- social_ease: 0.72
- curiosity: 0.70

---

### Mr. Darcy

| O | C | E | A | N |
|---|---|---|---|---|
| 0.35 | 0.82 | 0.18 | 0.22 | 0.38 |

**Openness:** The key value for his arc. Seeded at 0.35 — higher than his
visible behavior suggests (he performs much lower), reflecting genuine
intellectual curiosity and aesthetic sensibility that his pride suppresses.
Player actions can shift this upward. His Openness is the lever of his
transformation; other traits are more stable. By the end of the novel it
reaches approximately 0.65.

**Conscientiousness:** High and stable throughout the novel. His principles,
reliability, and sense of duty are genuine and do not change — what changes
is *who* his conscientiousness is directed toward.

**Extraversion:** Very low. Large assemblies of strangers are genuinely
uncomfortable for him. His "walking about" is avoidance behavior, not
social performance.

**Agreeableness:** Low surface, moderate underlying. He is dismissive and
proud in public, capable of deep loyalty and warmth in private. Pass 2
should read this as a real gap: his behavior toward strangers does not
reflect his capacity for genuine feeling.

**Neuroticism:** Moderate. He controls his emotions well, but his pride is a
source of ongoing internal friction. His discomfort at the assembly is real.

**Starting emotional state:** Disdainful — performing composure and superiority
to manage genuine social discomfort.

**Primary motivations:**
- Status preservation (protecting his family name and social position)
- Affiliation (with his own circle: Bingley, Georgiana — not strangers)

**Hidden motivation:** Already registering Elizabeth — her reaction to the
snub (amusement rather than distress) has caught his attention in a way he
will not acknowledge. Seed as: *"Has noticed Miss Elizabeth Bennet's response
to his dismissal with unexpected interest; will not act on this."*

**Internal states at start:**
- social_discomfort: 0.72
- composure: 0.80 (controls his discomfort effectively)
- pride: 0.78

**Wander behavior:** Walks the room throughout the evening rather than
staying in one place. High mobility, low engagement. He observes but
does not initiate.

---

### Mr. Bingley

| O | C | E | A | N |
|---|---|---|---|---|
| 0.68 | 0.42 | 0.88 | 0.82 | 0.22 |

**Openness:** Enthusiastic about new people and experiences. Not intellectual
but genuinely curious about others.

**Conscientiousness:** Notably low for a sympathetic character. He means well
and follows through on immediate social commitments, but is easily influenced
and doesn't hold positions under pressure. This is what allows Darcy and his
sisters to separate him from Jane later.

**Extraversion:** Extremely high. Danced every dance, talked of giving a ball
himself, angry it ended early. He is energized by exactly the kind of evening
Darcy finds exhausting.

**Agreeableness:** High and genuine. He finds good in everyone he meets; his
warmth is real, not calculated.

**Neuroticism:** Low. He is buoyant and happy.

**Starting emotional state:** Delighted — he is exactly where he wants to be.

**Primary motivations:**
- Social belonging (genuine enjoyment of people and company)
- Affiliation (warmth; he wants to like and be liked)
- Entertainment (he is having fun)

**Internal states at start:**
- enjoyment: 0.82
- social_ease: 0.90

---

### Jane Bennet

| O | C | E | A | N |
|---|---|---|---|---|
| 0.52 | 0.72 | 0.55 | 0.92 | 0.18 |

**Agreeableness** is Jane's defining trait — the highest in the cast. She
finds good in everyone and expresses criticism reluctantly if at all. This
is both her greatest virtue and her narrative limitation (she cannot easily
process that Bingley's sisters are insincere).

**Neuroticism:** Very low. She experiences happiness and unhappiness quietly.
She will not display strong emotion even when feeling it strongly.

**Starting emotional state:** Quietly hopeful and content.

**Primary motivations:**
- Affiliation (deep; family and genuine connection)
- Harmony (avoidance of conflict; she will absorb difficulty rather than
  create friction)
- Romance (present but private; she hopes without declaring)

---

### Charlotte Lucas

| O | C | E | A | N |
|---|---|---|---|---|
| 0.58 | 0.78 | 0.50 | 0.68 | 0.22 |

**Design note:** Charlotte is Elizabeth's foil and closest friend at this
point. Her high conscientiousness reflects clear-eyed pragmatism — she
understands her situation and the world's constraints and acts accordingly.
Her acceptance of Collins later is not weakness; it is her conscientious
assessment of her options, which are genuinely limited. She should not be
seeded as unhappy or resigned — she is stable and capable.

**Primary motivations:**
- Security (pragmatic; she is aware of her position as an unmarried woman
  of modest means)
- Affiliation (genuine warmth for Elizabeth)
- Understanding (she reads people accurately)

**Starting emotional state:** Pleasant and sociable.

---

### Mrs. Bennet

| O | C | E | A | N |
|---|---|---|---|---|
| 0.32 | 0.42 | 0.92 | 0.45 | 0.88 |

**Mrs. Bennet's defining combination is maximum Extraversion + maximum
Neuroticism.** She cannot contain what she feels; she expresses everything
immediately, loudly, and without filtering for social consequence. Her
Conscientiousness is moderate-low: she applies herself with complete
dedication to one goal (her daughters' marriages) but has no capacity for
broader principled behavior.

This seeding should produce authentic catastrophes without scripting them.
She does not need to be told to say something mortifying; her OCEAN values
will generate it under the right conditions.

**Starting emotional state:** Excited and anxious — the arrival of Bingley's
party is the most important social event of recent memory.

**Primary motivations:**
- Security (her only real goal: financial security for herself and her
  daughters after Mr. Bennet's death)
- Status (her daughters' marriages are status as much as security)

**Internal states at start:**
- anxiety: 0.65
- excitement: 0.80
- composure: 0.22 (low; she is already struggling to contain herself)

---

### Lydia Bennet

| O | C | E | A | N |
|---|---|---|---|---|
| 0.58 | 0.08 | 0.95 | 0.48 | 0.18 |

**Lydia's defining trait is her conscientiousness floor: 0.08.** She is not
malicious — her Agreeableness is middling and her Neuroticism is very low
(she is genuinely unbothered by consequences). She simply does not consider
outcomes before acting. Combined with near-maximum Extraversion, this produces
a character who will go through any open door, speak to any stranger, and
dance with anyone who asks — generating complications through pure spontaneity
rather than intent.

**Wander parameters:** High wander_probability, wide wander_range. She
should move frequently during the session.

**Starting emotional state:** Giddy with excitement.

**Primary motivations:**
- Entertainment (immediate; she wants to have fun right now)
- Status through male attention (she measures success by admiration)
- Sensation (she is drawn to anything novel or exciting)

**Internal states at start:**
- excitement: 0.90
- composure: 0.15

---

## Secondary characters

### Kitty Bennet (Catherine)

| O | C | E | A | N |
|---|---|---|---|---|
| 0.48 | 0.28 | 0.75 | 0.52 | 0.48 |

Lydia's shadow. Less extreme in every dimension. She follows Lydia's lead
and is more easily flustered. Wander_probability: moderate, following Lydia
rather than initiating.

---

### Mary Bennet

| O | C | E | A | N |
|---|---|---|---|---|
| 0.62 | 0.78 | 0.18 | 0.42 | 0.55 |

Bookish, moralizing, wants recognition for accomplishments. High
conscientiousness + low extraversion + moderate neuroticism = the character
most likely to make a pointed observation at the wrong moment and be hurt
when it lands badly. She is mentioned to Miss Bingley as the most accomplished
girl in the neighborhood; she would be aware of and gratified by this.

---

### Miss Bingley (Caroline)

| O | C | E | A | N |
|---|---|---|---|---|
| 0.42 | 0.55 | 0.68 | 0.28 | 0.52 |

Condescending beneath a polished surface. Her low Agreeableness is the key
value — she is watching the room for threats to her social position and her
pursuit of Darcy. At Chapter 3 she has not yet registered Elizabeth as a
threat; she will by Chapter 18.

**Hidden motivation:** Pursuing Darcy; everything is subordinate to this.

---

### Mrs. Hurst (Louisa)

| O | C | E | A | N |
|---|---|---|---|---|
| 0.40 | 0.48 | 0.58 | 0.35 | 0.38 |

Follows Miss Bingley's social lead. Less driven. Generally occupied with her
own comfort. Not actively disagreeable, just indifferent to those outside
her circle.

---

### Mr. Hurst

| O | C | E | A | N |
|---|---|---|---|---|
| 0.28 | 0.35 | 0.22 | 0.42 | 0.32 |

"Merely looked the gentleman." Prefers cards, food, and inactivity to
dancing or conversation. Starting location: card room. He will not move
unless prompted. Not hostile — simply disengaged from everything happening
around him.

---

### Lady Lucas

| O | C | E | A | N |
|---|---|---|---|---|
| 0.45 | 0.55 | 0.68 | 0.62 | 0.42 |

Pleasant neighborhood gossip. Her function in the scene is social
intelligence — she knows who everyone is, what everyone's prospects are,
and is happy to discuss both. Her report on Bingley opened the chapter.

---

## Starting locations

| Character | Location | Notes |
|---|---|---|
| Elizabeth | Ballroom | Seated (sitting out first two sets) |
| Jane | Ballroom (floor) | Dancing |
| Mrs. Bennet | Ballroom (wall seating) | Watching; maximum observational range |
| Lydia | Ballroom (floor) | Dancing; high wander_probability after first sets |
| Kitty | Ballroom (floor) | Dancing; follows Lydia |
| Mary | Ballroom (wall seating) | Seated; unlikely to move |
| Bingley | Ballroom (floor) | Dancing |
| Darcy | Ballroom | Walking the room; mobile NPC, low engagement |
| Miss Bingley | Ballroom | With her party initially; observing |
| Mrs. Hurst | Ballroom | With her party |
| Mr. Hurst | Card Room | Will not move without strong reason |
| Charlotte Lucas | Ballroom | Near Elizabeth initially |
| Lady Lucas | Ballroom (wall seating) | Near Mrs. Bennet; gossiping |

---

## Schema additions flagged by this design

1. **`passage_note` TEXT on `location_connection`** — barrier type for
   non-passable connections (locked / convention / guarded).
2. **`pending_intent` TEXT on `character`** — prerequisite for dance
   commitment tracking and Darcy's hidden interest.
3. **Reputation float(s)** on `character` or a new `character_reputation`
   table — needed for social stakes mechanics. Design question: single float
   or per-faction? For Chapter 3 (one social circle), a single
   `neighborhood_reputation` float may be sufficient; faction split can
   wait for Chapter 2.
4. **`wander_suppression` or `last_interaction_turn`** — already in the
   lower-priority pending list for I Am a Cat; needed here for Darcy (who
   should not wander away mid-conversation if Elizabeth engages him).
