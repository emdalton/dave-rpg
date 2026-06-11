# DAVE RPG Engine — Future Feature Ideas

*Captured May–June 2026. None of these are scoped or designed; this is a reference list.*
*Last updated: 2026-06-10.*

---

## 27. Module candidate: Sherlock Holmes / Victorian London (Conan Doyle)

*Captured 2026-06-10.*

Conan Doyle died 1930; the original Holmes stories (1887–1927) are public domain in most jurisdictions. A Holmes-adjacent DAVE module requires no author permission and can be published freely. The Victorian London setting has an extensive body of independent public-domain historical material (period maps, newspaper archives, social surveys, Booth's poverty maps, court records) that can be used to build the world independently of the Holmes canon.

**Player character direction:** Playing *as* Holmes is the wrong design choice — it asks the player to out-deduce a character defined by impossible genius, which is either trivial or frustrating. The stronger approach is a player character who moves through the same world by entirely different means: social intelligence, relationships, networks Holmes cannot or would not access. Irene Adler is a strong candidate: an American opera singer living independently in London, financially self-sufficient, occupying an ambiguous social position (cultured and admired, but outside the respectable marriage track) that generates natural tension with Victorian class norms. "Outwit Holmes" is a potential win condition with genuine motivational power.

**The women of Victorian London:** The Holmes period (1887–1927) coincides with a remarkable concentration of women doing historically significant and underrepresented things. Florence Nightingale was still alive (she died 1910) and would be a figure of enormous reputation in the world. Ada Lovelace is slightly earlier (died 1852) but her circle and legacy would still be present in memory and in the scientific community. The era also produced Mary Seacole, Annie Besant, Josephine Butler, Octavia Hill, and a rich network of women navigating medicine, social reform, suffrage, and the arts — a parallel social world Holmes's Baker Street network would never reach. Surfacing this cast and letting the player move through their networks is a strong design goal independent of the mystery structure.

**Why it works for DAVE:** Victorian London's social stratification — class, profession, criminal networks, imperial connections, servant hierarchies — maps well onto DAVE's faction and reputation systems. The deduction mechanic (physical observation → inference) is not naturally modeled by DAVE's social adjudication layer and is best set aside in favor of DAVE's actual strengths: attitude, reputation, and relationship-based information asymmetry. A player character who knows the right people learns things Holmes never would.

**Relationship to Benjamin January:** both are period mystery settings with social complexity as a primary driver. The Holmes case is the cleaner starting point for an independent prototype because the source material is public domain and no author relationship is required.

---

## 26. Module candidate: Benjamin January series (Barbara Hambly)

*Captured 2026-06-10. No current path to author; revisit when proof of concept is established.*

Barbara Hambly's Benjamin January mystery series is set in New Orleans in the 1830s–1840s (antebellum period). Benjamin January is a free Black man — a surgeon and musician — navigating a social world defined by intricate and legally codified status distinctions: free people of color, enslaved people, Creole families, American newcomers, the Catholic Church, European expatriates, and the plaçage system (formalized long-term relationships between free women of color and white men, with legal protections for property and children). Hambly is noted for the quality of her historical research.

**Why it works for DAVE:** The social complexity is exceptional and exactly what the adjudication layer was designed for. Status, faction, and reputation operate on multiple simultaneous axes — race, class, religion, language, nationality — and a player navigating this world must understand that the same action reads very differently depending on who is present and what role they occupy. The mystery structure provides a natural objective and win condition. The setting is rarely represented in games.

**Source note:** E's knowledge of the plaçage system comes primarily from this series. The institution is also E's reference point for understanding Neumeier's "Red Ink Wife" category in the Tuyo world.

**Status:** Copyright held by Hambly; no personal connection to the author. Flag as a candidate when DAVE has a proof of concept strong enough to approach an author with no prior relationship. The historical setting (1830s–1840s New Orleans) means extensive public-domain period research material is available independently of the novels themselves.

---

## 25. Proper noun alias table (character and location disambiguation)

*Captured 2026-06-10.*

Characters and locations in fiction are referred to by many names: full name, short name, title, relationship term, pronoun, epithet. In the Tuyo world, "Ryo," "Ryo inGara," "the young warrior," "my tuyo," and "the boy" may all refer to the same person in different passages and from different points of view. An LLM ingesting the text for world-bible extraction cannot reliably resolve these without a lookup.

A `character_alias` table (and equivalent for locations) would map variant references to canonical entity IDs. This serves two purposes:

- *Ingestion pipeline:* during extraction passes, the system consults the alias table to resolve ambiguous references before creating or merging entity records. An existing world companion (such as Tuyo Vol. 1) can seed the alias table before ingestion begins, since it lists canonical names and common variants.
- *Game engine (Pass 1/Pass 2):* when a player refers to a character by a non-canonical name ("the Caterpillar," "that blue worm," "the hookah creature"), Pass 1 can resolve it against the alias table rather than failing or guessing. This is already partially handled by the `known_locations` dict in the Pass 1 context packet; a proper alias system extends the same pattern to characters and other named entities.

**Static vs. dynamic aliases.** Most aliases are static — "Marta" and "the innkeeper" both resolve to char_id=2 unconditionally. Some are dynamic: which character "Miss Bennet" refers to in Meryton depends on whether Jane has married yet. Before Jane's wedding, "Miss Bennet" = Jane (the eldest unmarried daughter); after, it shifts to Elizabeth. The alias table needs a `valid_when` condition field (null for unconditional aliases; a structured or natural-language condition for state-dependent ones) that Pass 1 can evaluate against the current game state.

Dynamic alias conditions should reference faction membership and role rather than any dedicated status field. "Miss Bennet" → Jane Bennet is valid while Jane's role in the Bennet family faction is 'unmarried eldest daughter.' Once Jane's faction membership shifts to a Bingley household faction as 'wife,' the condition resolves differently. This is consistent with the existing faction schema and avoids adding marital_status or similar fields that bake in cultural assumptions.

**The engine must not encode relationship assumptions.** Marital and relationship status is faction membership plus role — not a dedicated schema field. This is not merely a matter of Regency naming conventions. An engine designed for use with original fiction cannot assume what kinds of relationships exist, how many parties they involve, how long they last, what legal standing they carry, or what titles they confer. The Tuyo world illustrates why: Neumeier's system distinguishes Jewel Wives (primary wives, full legal status), Red Ink Wives (long-term concubines with specific legal protections for children, analogous to the *placée* institution in antebellum Creole New Orleans), Summer Wives (contracts under one year), One Candle Wives (legal status for the duration of one candle's burning), and Talon Wives (women who marry a group of eight soldiers and travel with them in the field, with considerably better status than typical camp followers). Each has distinct rights, distinct social expectations, distinct titles, and would be referenced differently in prose. A schema field called `marital_status` cannot represent this, and an LLM without explicit guidance will flatten all of them into "wife." The faction system with named roles handles all of these without modification.

**Ingestion pipeline implication.** When extracting relationships from prose during ingestion, the extraction prompt must capture the *type* of relationship as a labeled role, not collapse it into a generic category. The world companion is critical here: Neumeier has explicitly defined the Tuyo relationship taxonomy, so the ingestion pipeline can be seeded with it before parsing relationship mentions in the novels. Without that anchor, an LLM would almost certainly collapse the distinctions.

Schema sketch: `entity_alias(alias_id, entity_type TEXT, canonical_id INT, alias TEXT, valid_when TEXT NULL, source TEXT NULL)` where `entity_type` is 'character' or 'location', `canonical_id` references the appropriate table, `valid_when` encodes any state condition, and `source` notes provenance. The alias table is populated during seed/ingestion and extended during play as new references are encountered.

Fantasy proper nouns are particularly important here — names like "Aras," "inGara," "the Peacock Desert," or "the city in the starlit lands" have no prior existence in any model's training data and cannot be resolved from general knowledge. They must be provided explicitly. This is the same principle as DAVE's `known_locations` dict: the engine tells the LLM what the world contains; it does not rely on the LLM to know.

---

## 24. DAVE as author's assistant platform

*Captured 2026-06-10.*

DAVE's three-pass architecture (parse intent → reason over structured context → render output) is not specific to games. With different prompt prefixes and an ingestion pipeline that builds a structured knowledge base from a novel series, the same engine supports an author's assistant use case:

- *World-bible queries:* "Where was Aras while Tano was at the city in the starlit lands?" "Who are all of Ryo's family members to two degrees?" "How many grandchildren does Marag have?" Retrieved from an indexed and structured DB rather than recalled from model weights.
- *Synthesis and inference:* "Ryo and Aras are traveling from Avaras to the Peacock Desert the year after Ryo gets his scepter — what known characters are they likely to encounter along the way?" The model reasons over retrieved context rather than generating from training knowledge.
- *Companion writing:* author asks for a draft entry on a character, place, or concept. System retrieves all relevant passages, synthesizes what's established, flags gaps and contradictions, drafts an entry. Author confirms; confirmed entries enter the canonical DB and improve subsequent queries.
- *Consistency checking:* flag passages where stated facts contradict earlier established canon. More reliable via RAG over the actual texts than via model recall.

The author's assistant and game engine modes share the same infrastructure: the same database schema (with modest additions for source references, confidence flags, and alias tables), the same context packet assembly, the same RAG retrieval layer. The prompt prefix determines what the LLM does with the information.

**Data sovereignty is the key differentiator.** Commercial hosted APIs require authors to submit their work to third-party infrastructure with uncertain data retention policies. A locally-deployed DAVE instance (or one hosted under NDA by a trusted operator) means the author's unpublished material, internal notes, and world inconsistencies never leave controlled infrastructure. This is a qualitatively different guarantee — not a policy, but an architecture.

**Proof of concept path:** the game engine (DAVE as RPG) is the proof of concept for the author's assistant. A working Hidden Hostel or Meryton demo with a solid Sonnet/Salamandra pipeline demonstrates the core architecture to a prospective author partner. The author's assistant features (ingestion pipeline, confirmation loop, alias table, companion writing mode) are built on top of that foundation. See also Feature 25 (alias table) and `docs/ai_concepts_in_dave.md` for extended discussion.

**First target author:** Rachel Neumeier (rachelneumeier.com), 13-book Tuyo world with existing Vol. 1 world companion. Has publicly expressed concern about feeding manuscripts to commercial APIs. Approach after proof of concept is solid. See memory note `project_dave_neumeier.md`.

---

## 23. Semantic action log retrieval (RAG over play history)

*Captured 2026-06-09.*

Currently the Pass 2 context packet includes recent action log entries ordered
by time. For small modules this is sufficient — a few dozen turns of history
fits comfortably in the context window. For larger or longer-running games,
time-ordered recency is a poor proxy for relevance: a promise made twenty turns
ago, or a character's prior emotional state in a specific situation, may matter
more than the last three turns.

**The idea:** embed action log entries (and potentially location_detail records
and NPC history) as vectors, then at context assembly time retrieve the N most
semantically similar entries to the current action. This gives the LLM recall
of relevant history beyond the recency window.

**Where this becomes useful:**

- Long campaigns where plot threads from earlier in the session affect current
  adjudication (a debt acknowledged, a secret overheard, a past slight).
- Modules with large location graphs where detailed generated descriptions
  accumulate in location_detail over many visits.
- NPC continuity across long sessions: "the last time you spoke with the
  Scholar about this topic" retrieved even if fifty turns have passed.

**Current architecture notes:** The engine does not need this for Hidden Hostel,
Meryton, or the planned Wonderland module at current scale. The action_log table
already has the right structure for this (text narrative_beat per turn, timestamps,
character references). The `recent_actions` field in the Pass 2 packet is where
retrieved entries would go. Implementation would require an embedding model, a
vector store or SQLite-based ANN index, and a retrieval step in context.py.

**Revisit when:** a module's play session accumulates enough history that
time-ordered recency produces clearly worse adjudication than a pilot with
semantic retrieval, or when a module's location_detail volume makes selective
retrieval necessary.

---

## 19. Common Corpus model support and author module development

*Captured 2026-06-01.*

### 19a. Salamandra 7B as the local inference target

The current Phase 2 local model target is Mistral 7B via Ollama. A preferred
alternative — on ethical grounds and for multilingual capability — is
Salamandra 7B (Barcelona Supercomputing Center), trained on Common Corpus
(public domain and openly licensed sources only, no copyrighted training data).
Salamandra 7B is available via Ollama.

**Why this matters:**

- Common Corpus training eliminates the ethical concern of using copyrighted
  material in the model's training data. This is a meaningful distinction for
  a project that builds modules on public domain literature.
- Multilingual capability is a genuine asset: a Salamandra-backed module could
  support Spanish or Catalan text natively, and similar Common Corpus models
  from other language communities (e.g. Pleias for French) could support their
  respective languages.
- Hardware trajectory: 7B models at interactive speeds will be feasible on
  inexpensive consumer hardware within the next year or two, as inference
  efficiency and accessible GPU/unified-memory hardware continue to improve.

**Expected trade-off:** Pass 2 adjudication quality may be below Mistral 7B on
complex social reasoning — Common Corpus models have generally had less RLHF and
instruction-following training than the mainstream fine-tuned models. Pass 1
(structured JSON extraction) and Pass 3 (prose generation) should be comparable.
Fine-tuning is the lever to close the gap (see 19b).

**Implementation:** The Ollama backend stub (`engine/llm/ollama.py`) needs to
be completed before any local model can be tested. Once complete, Salamandra 7B
should be testable by setting `DAVE_OLLAMA_MODEL=salamandra` (or whatever the
Ollama model string is). No engine changes required beyond the Ollama backend.

---

### 19b. Fine-tuning for Pass 2 adjudication

If Salamandra 7B (or any 7B Common Corpus model) proves insufficient for Pass 2
on complex social modules, fine-tuning is the most tractable path to improvement.

**Why this is well-scoped:**
Pass 2 has a constrained, well-defined input/output format. DAVE already has a
mechanism for generating ground-truth examples — Sonnet serves as the
construction tool for seeding module data and generating exemplary adjudication
outputs. A fine-tuning dataset of DAVE-format context packets paired with high-
quality Pass 2 adjudication outputs (Sonnet-generated, human-reviewed) is
achievable without a large corpus. The target task is narrow: structured JSON
adjudication with OCEAN + MST reasoning, not general instruction following.

**Dependency:** Sufficient ground-truth examples from real play sessions and
construction runs. The test suite's ground-truth adjudication examples
(`tests/test_pass2_contract.py`) are a starting point.

---

### 19c. Author module development pipeline (longer-term)

*The most speculative of the three, but the highest-value use case if it becomes
feasible.*

Authors who want to build a DAVE module from their own published or unpublished
work face a distinct set of requirements from the current development workflow:

1. **Privacy:** Their manuscript must not be sent to a commercial API. The model
   must run locally or on a explicitly trusted service.
2. **Training data ethics:** Authors are likely to resist using a model trained
   on copyrighted works — including, potentially, their own works ingested
   without consent by a commercial model provider.
3. **Module construction capability:** The current workflow (E writes seed SQL
   manually, Sonnet assists with character/location design) requires deep
   familiarity with the DAVE schema. An author workflow would need a much
   higher-level interface: "here is my novel; here are the characters and scenes
   I want to make playable; generate the module seed."

The third requirement is the hard one. Extracting structured character profiles
(OCEAN traits, goals, relationships, attitudes), location graphs, and faction
dynamics from prose fiction requires a model with substantially more capability
than 7B. The current estimate is that this task needs something in the range of
a frontier model (Sonnet-class or better). No Common Corpus model at that
capability level exists as of mid-2026, but the trajectory of the field suggests
this gap will close within a year or two — particularly as Common Corpus expands
and training compute becomes more accessible to non-commercial organizations.

**The near-term partial solution:** A human-assisted pipeline where the author
provides structured input (character descriptions, relationships, locations) via
a guided form or template, and a 7B Common Corpus model assists with OCEAN
inference and goal taxonomy mapping from that structured input. This is lower
capability than full prose-to-module extraction but avoids the frontier-model
dependency and keeps everything local.

**The longer-term goal:** A local or trusted-hosted frontier-class Common Corpus
model that can read a novel (or selected chapters) and generate a DAVE module
seed — characters with full psychological profiles, location graph, faction
structure, and starting attitudes — from the prose directly, with author review
and correction. This is genuinely aspirational as of mid-2026 but worth
designing toward.

---

## 22. Module: The Fall of the House of Usher (Edgar Allan Poe)

*Captured 2026-06-03. Lower priority than features 20 and 21; suggested as a good candidate for Sonnet as construction tool since the adaptation approach is less developed.*

**IP status:** Poe died 1849. Completely public domain worldwide; no concerns.

**Why it works for DAVE:**

A small-cast chamber piece with a single clear objective (escape the house before it falls) and a central mystery structured as hidden motivation. Roderick Usher's knowledge — that something is wrong with Madeline, that the house is alive, that the ending is coming — is the engine of the story. The player character is the unnamed narrator, arriving as a friend summoned by Roderick's mysterious letter, with no initial knowledge of what is happening.

**Core mechanics it exercises:**

- Hidden motivation: Roderick knows far more than he reveals. His `hidden_motivation` conceals his awareness of Madeline's condition and the nature of their family curse. His visible behavior is manic hospitality and creative collaboration; his actual state is a man who knows he is dying and has summoned the narrator as a witness, not a rescuer.
- Small cast, high intensity: The cast is essentially three characters (narrator, Roderick, Madeline). Every interaction is weighted.
- Escape as objective: The engine's existing route/location system handles physical escape; the interesting adjudication is whether the player understands what is happening and leaves *in time*.
- Atmosphere and pacing: Pass 3 has significant work to do in maintaining Poe's tone — oppressive, suffocating, building dread. The prose rendering prompt for this module would need specific atmospheric guidance.

**Design challenge:** The story has a predetermined ending in the source text — Madeline returns, Roderick dies, the house falls. The design question is whether to treat this as an open "what if" (the player might prevent the collapse, might escape early, might find a different resolution) or to lean into inevitability, making the horror the slow recognition of what cannot be changed. E does not yet have a strong view on this; it may be worth discussing before the module is designed. Sonnet as construction tool is the right approach here since the adaptation path is less obvious.

**Comparison to Alice and Dracula:** Shorter source text; less complex social mechanics; no faction system needed. The challenge is tone, not scale. Lower priority as of capture but a tractable module when the horror-genre question is resolved.

---

## 21. Module: Dracula (Bram Stoker)

*Captured 2026-06-03. Priority module alongside feature 20 (Alice/Wonderland).*

**IP status:** Stoker died 1912. Completely public domain worldwide; no concerns.

**Why it works for DAVE:**

The epistolary structure of *Dracula* — told entirely through diary entries, letters, and telegrams — maps directly onto one of DAVE's most interesting design possibilities: partial knowledge. Each character in the novel has access to different pieces of the puzzle. Jonathan Harker knows what he saw in Transylvania; Mina knows what she wrote and what was written to her; Van Helsing understands what the others cannot name. A DAVE module built on Dracula can be designed so the player's character knows only what their journal contains — and the engine maintains that boundary rigorously.

**Recommended opening: Transylvania (Jonathan Harker as player)**

The Transylvania section is the natural starting point:

- Harker arrives at Castle Dracula as a solicitor completing a real estate transaction. His mission is legitimate, ordinary, and professional. Dracula's hospitality is genuine in surface form — courteous, attentive, intellectually engaged. The horror accumulates through details that are individually explicable.
- This setup works with the engine's existing mechanics. Dracula's `hidden_motivation` conceals his nature entirely; his visible attitude toward Harker is warmly proprietorial. He is not threatening Harker — he is studying him, enjoying him, preparing.
- The player's actions in Transylvania have real consequences for what Harker knows when he eventually escapes. A player who explores thoroughly, reads the documents Dracula leaves accessible, and pays attention to what the three women in the castle are doing will reach Mina's chapters with more to work with than a player who stays obedient and incurious.

**The "knowing player" design challenge:**

Most players who choose a Dracula module will know the story. Making Harker's early deference and cooperation feel reasonable — rather than obviously foolish — is the central tone design problem. Two approaches:

1. *Naturalistic play:* Trust that Dracula's social presence (high charisma, status, plausible explanations for every anomaly) will make the player's compliance feel earned rather than ignorant. The engine adjudicates Dracula's social pressure the same way it would any high-status NPC with strong persuasion skill; the player character is not stupid for responding to it.
2. *What-if as the explicit frame:* Players who know the ending can choose to go off-script. Harker who refuses to be a polite prisoner, who attempts escape on night one, who confronts Dracula directly — these are natural "what if" inputs that produce a different story. The engine supports this without modification; the module simply needs to design for it rather than assuming canonical compliance.

E considers Dracula "very easy to prepare" — the source text is clear, the characters are richly developed, and the social dynamics map cleanly onto existing engine mechanics.

**Later chapters:** Once the Transylvania opening is stable, later chapters (Whitby, London, the hunt) can be added. The epistolary structure means chapter sequencing (feature 13) is load-bearing for the full novel arc — each chapter's player character may be different (Harker, Mina, Van Helsing's group). This is a longer-term design consideration; the Transylvania opening stands alone.

---

## 20. Module: Return to Wonderland (Lewis Carroll / original design)

*Captured 2026-06-03; substantially revised 2026-06-10.*

**IP status:** Carroll died 1898. Completely public domain worldwide; no concerns. The Tenniel illustrations are also public domain. The module design is original (adult-Alice framing) and does not reproduce Carroll's text.

**Concept: adult Alice returns**

Alice is now a young woman. As a child she slipped between worlds; her family dismissed her accounts, though one scholar believed her. The White Rabbit arrives in distress — the Queen of Hearts has become a tyrant. Alice must decide what to do about it.

The central tension: childhood access to Wonderland was effortless. As an adult returning to a changed place, Alice brings different capabilities and different constraints. The characters she knew remember child-Alice; adult-Alice must re-establish who she is.

**Why it works for DAVE:**

Wonderland is a social world structured entirely around absurd authority, arbitrary rules, and characters who take their own logic completely seriously. Every Wonderland character has coherent internal psychology (within their own framework) and responds to Alice's behavior based on how it maps onto their values — the Queen's volcanic authority, the Hatter's time-trapped obsession, the Caterpillar's philosophical detachment. This is exactly what DAVE's social adjudication layer was built for.

**Win condition: NPC happiness, not trial victory**

The win condition is the aggregate happiness (internal states and attitudes) of Alice's NPC friends — not defeating the Queen or winning a trial. Multiple solution paths are equally valid:

- *Joan of Arc:* build coalitions, raise social pressure, organize resistance
- *Diplomat:* negotiate with the Queen, find her grievances, address them directly
- *Trickster:* use Wonderland's own logic against the court
- *Quiet restoration:* help individual friends one by one, shift the social fabric without confrontation

The same Wonderland, the same characters, the same Queen — but genuinely different stories depending on who Alice is. If only one path is satisfying, the module has failed.

**The Queen's hidden motivation (key design decision):**

The Queen is tractable, not a final boss. "Off with their heads!" is almost never carried out, suggesting the court is humoring her. E's hypothesis: the Queen is terrified of being forgotten or ignored. Making her feel secure and seen may be sufficient. The diplomatic path requires high-agreeableness skills and careful attitude management, not confrontation. The Queen's `hidden_motivation` is the design decision that determines whether the diplomatic and trickster paths feel satisfying or cheap — design it first.

**Player self-definition: who did Alice become?**

At game start, Alice's capabilities depend on who the player thinks she grew up to be. The White Rabbit serves double duty as the inciting character and the character-creation interface — his question ("But Alice, what have you *become* these years? What do you know now?") is both in-character and a skill-seeding prompt. Examples:

- *Chess grandmaster:* sees the situation as chess — pieces, positions, the right sacrifice at the right moment. Most natural for strategic/systems play.
- *Philosopher:* argumentation, paradox-handling (extremely Wonderland-appropriate — Wonderland logic is a kind of philosophy), patience. Most natural for the diplomatic and trickster paths.
- *WWI nurse:* has seen real death and real tyranny. Wonderland's theatrical executions that never happen read very differently through this lens — she may arrive with almost no fear of the Queen, which is its own power. Most likely to feel genuine compassion for what's beneath the Queen's rage.
- *Expert chef:* social warmth through hospitality, knowledge of hosting customs; may win characters over through food and care. A Hidden Hostel–style approach inside Wonderland.

The open skill taxonomy already handles this — no rigid skill list, the adjudicator evaluates semantic relevance at resolution time. A gymnast Alice getting past the card soldiers has a different story than a philosopher Alice doing it; both are mechanically valid.

**History mechanic:**

Characters who knew child-Alice have prior attitude data that doesn't match the current player character. Design options: seed skepticism/disappointment (she was gone a long time), seed positive nostalgia (creates pressure to live up to it), or have characters react to adult-Alice's confidence and changed manner as something genuinely new. This is an unresolved design question; seed it carefully and playtest.

**Target players (named, not hypothetical):**

- *Dave (E's husband, engine namesake):* expert tabletop RPG moderator, Dragon Age / Baldur's Gate fan. Likely favors the coalition-building / Joan of Arc approach — strategic, direct, systems mastery.
- *Their daughter:* plays many games, writes fan fiction. Likely favors character relationships, emotional beats, creative lateral solutions.
- *E:* suggested the diplomatic path herself. Finds win conditions in making everyone satisfied rather than defeating anyone.

All three should be able to play and feel like they're playing *their* Alice.

**Signature mechanic: size as internal_state float**

- `size` as a float on Alice's `character_internal_state`: 0.0 = Drink-Me tiny, 0.5 = normal, 1.0 = Eat-Me giant (physically disruptive, cannot fit through doors, frightening to small creatures).
- Items (Eat-Me cake, Drink-Me bottle, mushroom pieces) have a `size_delta` property in their JSON. Pass 2 applies the delta clamped to [0.0, 1.0].
- `passage_note` on location connections encodes size requirements: "requires size < 0.3 to pass" on the tiny door, "blocked if size > 0.8" on normal doorways.
- At 0.0, Alice cannot reach most interactive objects. At 1.0, she cannot fit through most exits and her presence frightens nearby characters (automatic attitude penalty from creatures under 0.4 size).

**Logical puzzles as social adjudication:**

Wonderland's riddles ("Why is a raven like a writing desk?") are not meant to have correct answers. Pass 2 adjudicates these as social interactions: what matters is Alice's confidence, creativity, and willingness to engage on Wonderland's own terms. A brilliant wrong answer may win more attitude than a mumbled right one.

**Through the Looking Glass as follow-on:**

A cleaner objective structure — Alice must cross the chessboard to become a queen. Each square = a new scene, each piece encounter = a social challenge. Maps well onto DAVE's location graph with `passage_note` encoding chess-square adjacency rules. Looking Glass is the planned sequel, not the starting point. The chess grandmaster backstory connects directly to this module's framing.

**Salamandra vs. Sonnet seed generation benchmark:**

The Wonderland module seed will be built with Sonnet (existing construction practice). A parallel run using Salamandra 7B is planned for comparison. Because *Alice's Adventures in Wonderland* is Project Gutenberg text and almost certainly in Common Corpus, Salamandra is recalling rather than extracting — this is a known-content test. What it measures is structured output quality, schema adherence, OCEAN inference, and goal/motivation description quality on DAVE's specific prompt format. The comparison establishes how far apart Sonnet and Salamandra are on known content, setting realistic expectations for the gap on genuinely unknown material (e.g. the Tuyo ingestion use case). See `docs/ai_concepts_in_dave.md`.

---

## 17. Pre-session Pass 0: MST-to-pending-intent initialization

*Captured 2026-05-26 during Meryton seed design.*

A lightweight pre-session LLM call that runs once at the start of each new
session (or when a new game_instance is created). It reads each character's
`character_goal` entries and the current scene context (module premise,
location, time of day, other characters present) and derives a
scene-appropriate `pending_intent` for each character, writing the results
to `character.pending_intent` before the first player turn.

**Why this matters:**

Currently, `pending_intent` is hand-seeded in `seed.sql` and reset in
`reset_instance.sql`. This works for a single module in a single starting
scene, but it requires manual re-seeding whenever a character appears in a
new context — a new chapter, a new scene, or a "What if..." premise. A
character's MST goals are stable across chapters; their tactical
`pending_intent` is scene-specific. Pass 0 bridges them automatically.

**Example:** Elizabeth Bennet's goal "belonging — genuine connection with
Jane, Charlotte, and her family" is the same at every assembly. Pass 0
translates it to "wants to dance; will accept a partner if asked" for
Chapter 3, and might translate it differently for Chapter 2 if the
circumstances have changed. Mrs. Bennet's security goal always produces a
ballroom-and-observe intent at any social occasion.

**Connection to chapter sequencing:** Once chapter-to-chapter state
forwarding is implemented (feature 13), Pass 0 ensures that characters
carried forward from a previous chapter arrive in a new scene with
contextually appropriate intent rather than stale seed values. This makes
the same character records reusable across an entire module arc without
manual re-seeding for each chapter.

**Implementation sketch:**

- Runs as a single LLM call (Haiku is sufficient — this is intent inference,
  not prose generation) before `_render_opening_scene()`.
- Context: each character's name, species, goals (name, priority, orientation),
  current emotional_state, and a brief scene description from the `game` record.
- Output: `[{character_id, pending_intent}]` — the same structure as
  `pending_intent_updates` in the Pass 2 output schema. Engine writes them
  exactly as it would for mid-session updates.
- Module-level opt-in: `"pass0_enabled": true` in `module_flags` JSON on
  `game`. Defaults to false; existing modules with hand-seeded intent are
  unaffected until opted in.
- A `pass0_override` TEXT NULL field on `character` would allow specific
  characters to bypass Pass 0 with a hard-coded intent (e.g., Darcy's refusal
  to dance is canonical and should not be re-derived).

**Dependency:** Requires `module_flags` JSON field on `game` (sketched in
feature 6). Otherwise no schema changes needed beyond the existing
`pending_intent` field on `character`.

---

## 16. What-if: "Elizabeth Bennet, Agent of the Crown"

A `what_if` premise modifier for the Meryton module. Elizabeth is working
undercover for British intelligence — hunting free traders and foreign agents
operating through Hertfordshire society. Her social position (a gentleman's
daughter, welcome at every assembly, unremarkable to anyone who doesn't look
closely) is the cover. Her intelligence, boldness, and powers of observation
are the qualifications.

Arose in the context of the Meryton location graph: the locked doors in the
civic building (corn market, magistrate's room) would make sense to attempt if
Elizabeth had a reason to be in restricted areas. An Agent of the Crown would
have that reason and the skills — lock-picking, surveillance, reading people —
that a well-bred young lady would otherwise not plausibly possess.

**What this exercises:**
- `what_if` premise modifier system (feature 6) — the canonical delivery mechanism
- Hidden motivation on Elizabeth: her visible purpose is attending the assembly;
  her actual purpose is surveillance or contact with an asset
- The locked location connections become meaningful obstacles rather than set
  dressing — the engine adjudicates capability (does she have the skill?) and
  consequence (was she seen?) rather than simply refusing entry
- Service passages become operationally useful rather than socially forbidden
- Wickham as a suspect rather than a love interest — or both

**Tone:** Adventure rather than comedy, though Austen's irony survives the
genre shift. Miss Bingley's condescension is still insufferable; Mrs. Bennet
is still a hazard to any covert operation; Darcy is still watching Elizabeth
with unsettling attention, for reasons that may not be romantic.

**The Darcy twist:** It will eventually emerge that Darcy is also an Agent
of the Crown. This reframes the entire dynamic: his inscrutability is
tradecraft, not arrogance; his obsessive attention to propriety is
operational discipline; he cannot expose Wickham without revealing how he
knows what he knows. His famous letter to Elizabeth stops being a wounded
gentleman's self-defense and becomes an intelligence briefing he has been
trying to find a way to deliver for three chapters. Neither agent can
acknowledge the other without blowing their cover — which gives their
antagonism an entirely new engine. Elizabeth's refusal of Collins reads
differently too: a woman running an active operation cannot afford to be
installed at the Hunsford parsonage under the thumb of Lady Catherine's
household.

*Not scoped. Depends on what_if modifier system (feature 6) and the Meryton
module reaching a stable playable state first.*

---

## 15. Module: The Three Musketeers (Alexandre Dumas)

Suggested 2026-05-24 as the best first test case for combat mechanics.
Dumas died 1870; the novel (1844) is completely public domain worldwide —
no IP concerns.

**Why this works better than Barsoom for introducing combat:**
Barsoom combat is constant and culturally central — you cannot build a
meaningful Barsoom module without designing combat as a primary mechanic.
Three Musketeers allows combat to be developed as *one resolution path
among many*, embedded in rich social and political context. A duel is
preceded by an insult, a challenge, negotiation over seconds and location,
and an audience — all interactions the engine already handles well. The
sword fight itself is the least interesting part mechanically; the social
scaffolding around it is where DAVE's strengths lie.

**Player character:** D'Artagnan arriving in Paris — a young Gascon outsider
with high swordsmanship, low court manners, and low political awareness.
Structurally similar to Elizabeth Bennet at the assembly: low status, high
capability, navigating an established social order that doesn't yet take him
seriously. Strong starting arc.

**Faction system workout:**
- King's Musketeers (Athos, Porthos, Aramis, de Tréville)
- Cardinal's Guards (Richelieu, Rochefort)
- The Court (Louis XIII, Anne of Austria)
- Various noble houses and agents

**Hidden motivation showcase:** Milady de Winter is one of the great
hidden-motivation characters in literature — her visible persona and actual
agenda are almost entirely opposed. Rochefort and Richelieu similarly.

**Combat mechanics needed:**
- Skill floats: `swordsmanship`, relevant physical attributes
- Injury as internal_state (wound severity: 0.0 = unhurt, 1.0 = mortally
  wounded; passive rate = healing over time with rest)
- Pass 2 adjudicates combat outcomes from skill floats + situational factors;
  same pattern as social adjudication
- Duels have social preconditions (challenge issued, seconds agreed) that
  the engine tracks before combat resolves

**IP:** Completely clear. Public domain worldwide.

---

## 13. Module chapters / act structure with state forwarding

Observation (2026-05-23): modules don't all need to be published as monolithic single-session experiences. A chapter structure would allow a module to be developed and released incrementally, with each chapter forwarding relevant state (character attitudes, reputation changes, item positions, pending intents) into the next chapter's starting seed.

This connects naturally to the module/instance architectural split (pending v7): once per-playthrough state is properly separated from module definition, "forwarding state to the next chapter" becomes a defined export/import operation on instance state rather than a hack against the seed. The "What if..." premise modifier (feature 6) would also attach per-chapter, enabling branching.

Undeveloped as of capture.

---

## 14. Multiple playable characters per module

Observation (2026-05-23): modules could support a choice of player character rather than a single fixed protagonist. The simplest proof-of-concept is allowing a player to play as Spook in *I Am a Cat* — the world state and NPC cast already exist, and Spook's psychology is established. This would test whether the engine handles a non-default player character cleanly, including: different starting location, different emotional state and internal states, different perception of Toulouse as an NPC.

In the Netherfield Ball context, playing as Darcy, Wickham, or Jane rather than Elizabeth would produce radically different experiences from the same seed — each character has different information, different goals, and different social constraints.

Implementation sketch: a `playable` flag on the `character` table, plus a pre-session character selection step. The engine's existing `role='player'` logic already centralizes player-character handling; the change is making which character holds that role a runtime choice rather than a seed constant.

---

## 11. Fate Point economy

Suggested by playtest observation (2026-05-23): the `partial_success` outcome on the Spook social-correction turn was a textbook Fate compel — an NPC aspect (Spook's incorrigible playfulness) complicated the player's action in an entertaining way, and in the Fate RPG system that moment would award the player a Fate Point. The `partial_success` and `failure` outcome types are already doing the adjudication work; a Fate Point system would add a resource currency on top.

**Mechanic sketch:**

- A named resource pool (e.g. `fate_points`) stored on `game_instance` (or a `player_resource` table for generality across module types).
- Pass 2 issues a `fate_point_award: true` flag in its outcome JSON when it generates a `partial_success` or `failure` with a strong, entertaining narrative beat — i.e., when the complication makes the story better rather than just worse.
- Pass 1 detects spend intent from player input and adds `spend_fate_point: true` to the action record. The engine checks for available points before honoring it; if none are available, Pass 2 is not told the spend was requested.
- Pass 2 prompt: when `spend_fate_point: true` is in the action record, the player has paid a resource for a better outcome — lean toward success or at least reduce the cost of failure. The spend does not guarantee success but shifts the probability.

**Natural-language spend signals for Pass 1 to recognize:**

The signal must come from character voice or explicit effort language — player asides ("I really hope this works") should not trigger a spend. Clear signals:

- *Effort intensifiers* in character voice: "try harder," "push," "give it everything," "strain to," "force it through," "with everything I have"
- *Stakes declarations* in character: "I need this to work," "I cannot afford to fail here," "this matters"
- *Explicit trait invocations*: "use my dignity," "as the senior cat I insist," "I invoke my authority" — natural for Fate-familiar players and intuitive for anyone leaning into character
- *Narrative declarations*: "I declare that..." — classic Fate story-detail spend

Pass 1 prompt note: require that the signal be in-character or clearly about the action, not a player aside. "I really hope this works" is ambiguous and should not trigger a spend unless paired with an effort intensifier.

**Module-level opt-in:** Not all modules use a Fate Point economy. Add a `fate_points_enabled` flag to the `module_flags` JSON on `game` (alongside the `what_if_enabled` flag sketched in feature 6). Starting pool size and award/spend rates are module-level config.

---

## 12. Scene-close segmenting and narrative arc

Playtest observation (2026-05-23): the closing line of the Spook-correction turn ("You did the thing. It is not your fault he is like this.") felt like a natural scene-close — a beat that wraps one narrative unit before the next opens. This suggests a possible feature around detecting or generating explicit scene boundaries.

Undeveloped as of capture. Possible directions:

- Pass 3 could be prompted to signal when it believes a scene has closed (a structured flag alongside the prose), allowing the engine to insert a brief visual/textual break in the output.
- A scene log could track named scenes as discrete narrative units, enabling transcript mode (feature 2) to produce chapter-structured output rather than a flat turn log.
- Scene boundaries might interact with the Fate Point economy (feature 11) — scene close is a natural moment to tally awards, as in the Fate tabletop system.

Not yet clear where this goes. Capturing the observation for later.

---

## 8. MUSH integration

Suggested by a playtester (2026-05-23), who noted that DAVE's prose quality was reminiscent of good MUSH play and proposed wiring the engine to a MUSH server for networked multi-player access.

**What this would require:**

DAVE's turn loop is already structured like a MUSH world engine: it takes a player action, updates world state, and returns prose. The gap is concurrency — DAVE currently assumes one player and one active session. Full MUSH integration needs:

1. *Multi-session world state* — the v7 module/instance architectural split (see implementation_status.md §4) is the prerequisite. Once `instance_id` is threaded through all state tables, multiple concurrent player sessions sharing one world instance become architecturally possible.

2. *Turn coordination* — in a shared world, two players may act simultaneously on the same target. Options: sequential turns with a queue; simultaneous resolution where all pending actions for a game-time tick are adjudicated together in a single Pass 2 call; or a hybrid where independent actions resolve independently and conflicting ones trigger a combined adjudication.

3. *Network transport* — a MUSH protocol layer (or a simpler telnet/websocket server) that routes player input to the engine and returns prose. This is separate from the web-host option (feature 1), which uses HTTP; MUSH clients expect a persistent TCP connection.

**Simpler intermediate path:** Run DAVE as the NPC/world-simulation engine behind a traditional MUSH, rather than as a full replacement. The MUSH handles connection management, player routing, and room/exit bookkeeping; DAVE handles adjudication and prose for NPC interactions and complex world events. This defers the concurrency problem while still providing the NPC quality improvement that makes MUSH play richer.

**Relationship to other features:** Overlaps significantly with feature 5 (multiplayer) and feature 1 (web host). The three are the same architectural need approached from different interfaces: HTTP browser client, multi-user MUSH client, and eventually a desktop/mobile client. Design the session and concurrency layer once; the transport is a skin on top.

---

## 9. Module: Barsoom (Edgar Rice Burroughs)

Suggested as a strong module candidate (playtest 2026-05-23), particularly in a MUSH context where the planetary romance setting and large cast of alien species naturally support multi-player factions.

**Why it works for DAVE:**

- Radically non-human player characters (Red Martians, Green Martians, Tharks, Warhoons) stress-test the species-specific perception and sensory profile systems
- Faction mechanics (Heliumite, Zodangan, Thark tribal politics) are first-class; DAVE's reputation and attitude systems were designed for exactly this
- The social dynamics of Barsoomian honor culture (challenges, debts, alliances) are a natural fit for the Ford-Nichols motivational framework
- A MUSH version with multiple players each playing a different species would be a compelling proof-of-concept for both DAVE and the Barsoom setting

**IP status:**

The early Barsoom novels are in the US public domain — *A Princess of Mars* was published in 1912 (book form 1917), well past the copyright threshold. However, ERB Inc. remains active and holds trademarks on character names, species names, and setting terms; they have historically been aggressive about enforcement. This means:

- *Public domain text* — the novels themselves can be quoted and adapted freely for non-commercial use
- *Trademarks* — "John Carter," "Barsoom," "Tharks," and similar marks may require licensing even when the underlying text is public domain; this distinction matters for any commercial or widely-distributed release
- *Practical path* — for a hobbyist/open-source project, a faithful Barsoom module is likely defensible; for any commercial release or wide distribution, consult the trademark landscape before investing heavily in module design

**Comparison to Amber:** More tractable than the Amber Chronicles (Zelazny died 1995; Amber is still under copyright and requires active estate permission regardless of intent). Barsoom's public-domain status gives a stronger foundation.

---

## 10. Module: Amber Chronicles (Roger Zelazny)

Suggested as a module candidate (playtest 2026-05-23), with the note that the Zelazny estate may have authorized use in MUSH-style games.

**IP caution:** The Amber Chronicles are still under copyright — Zelazny died in 1995 and copyright extends 70 years post-mortem in the US, meaning the works remain protected until at least 2065. Any use requires active estate permission. The claim that MUSH use has been authorized is plausible (the Amber MUSH community has been active for decades and the estate has historically tolerated fan games), but "tolerated" is not the same as "authorized," and explicit permission should be confirmed before investing significant design effort.

**If authorization is confirmed:** Amber is an excellent DAVE module candidate. The pattern system (each Amberite has a unique ability profile) maps naturally onto DAVE's skill taxonomy; the family politics of the Courts of Chaos are exactly the kind of social-diplomatic complexity the engine was designed for; and the multiverse structure (Shadows) supports lazy world generation at a conceptual level — Shadow worlds are, by definition, generated on demand.

---

## 7. Module: Suspended (Infocom port / homage)

Port or homage to the Infocom game *Suspended* (1983, Michael Berlyn). In the
original, the player is a human in a suspended animation capsule who must direct
five robots — each with a completely different sensory profile — to diagnose and
repair a planetary life-support system before it fails.

This is the ideal stress test for the DAVE sensory profile system:

- **Iris** — visual only; excellent sight, no other senses
- **Waldo** — tactile; no sight, navigates and manipulates by touch
- **Sensa** — audio; detects sounds and vibrations the others cannot
- **Poet** — reads and communicates; makes no direct observations
- **Whiz** — computational; processes data but has no sensory apparatus at all
- **Fred** — generalist with degraded abilities across all senses (the "safe"
  but limited robot)

Each robot's sensory profile would be a distinct JSON object on their character
record. The player issues commands to specific robots; the adjudication layer
must reason about what each robot can and cannot perceive from their location.
The human player in the capsule has no direct sensory access to the world at all
— information arrives only through robot reports.

Why this works well for DAVE:
- Directly exercises species/character-specific perception (the engine's next
  major design challenge after I Am a Cat)
- Naturally multiplayer-ready: each robot could be a separate player character
- High replayability: different robot combinations produce different information
  pictures of the same world
- Strong fan recognition: *Suspended* is a cult classic with a devoted following
  who would appreciate a faithful, mechanically rich homage
- Fits the "serious game" framing: resource management, teamwork, systems
  thinking under time pressure

**IP note:** Infocom IP is owned by Activision. Two viable paths:

1. *Homage with original scenario design* — use the robot sensory mechanic and
   general structure, but write original puzzles and setting. No IP issue.

2. *Licensed import* — the standard approach for IP-sensitive content is an
   import scheme that requires users to provide original game files to verify
   their right to use the IP. DAVE could extract scenario data (room
   descriptions, object names, puzzle logic) from a user-supplied Z-machine
   binary and use it to seed the module database, rather than distributing the
   content directly. E owns a physical copy of *Lost Treasures of Infocom*
   (includes all Infocom titles); archive copies of the Z-machine files are
   also available online for verified owners. The Z-machine file format is
   well-documented and there are existing Python libraries for parsing it.

A faithful port with the original scenario is the more interesting project; the
import approach makes it distributable. These can be developed in parallel —
build the engine mechanics against original content first, add the import/verify
layer before any public release.

**The "upgrade" effect:** Running any Infocom title through DAVE effectively
upgrades it. The original games use a parser that matches player input against
a fixed verb-noun vocabulary and resolves puzzles against hard-coded winning
conditions. DAVE replaces the parser with LLM intent recognition and replaces
hard-coded puzzle logic with contextual adjudication. This means a puzzle that
originally required finding object X and using it in place Y might become
solvable multiple ways — or might require more nuanced negotiation with NPCs
who, in DAVE, have actual psychology. Winning conditions change because "winning"
becomes an emergent outcome rather than a flag flip. This is a significant design
challenge for faithful ports and a significant creative opportunity for homages.
Players accustomed to the originals should be warned that DAVE versions play
differently, not just look different.

---

## 6. "What if..." premise modifier

An optional per-instance premise modifier entered by the player at the start of a new module. Examples: "What if Elizabeth Bennet is a vampire?" or "What if Toulouse's house is populated by small mischievous demons that only cats can see?"

When the feature is enabled for a module, the engine prompts the player for a free-text premise modification before the first turn. The modifier is canonicalized via a one-time call to a more capable model (Sonnet or Opus — not Haiku; this requires genuine creative and narrative interpretation), stored in a `premise_modifier` field on the `game` record, and included in every subsequent context packet as an addendum to the standard game premise. All three passes see it.

Implementation sketch:
- `premise_modifier TEXT NULL` on `game` (null = no modifier active)
- Module-level opt-in via a `module_flags` JSON field on `game` (e.g., `{"what_if_enabled": true}`). This field also covers other optional feature toggles (illustrated mode, transcript mode) without proliferating boolean columns.
- One-time pre-session LLM call: takes the player's raw input and the base game premise, returns a canonicalized modifier statement suitable for inclusion in context packets.
- No engine logic changes needed beyond passing the field through context assembly.

**Playtest observation (2026-05-25) — premise injection works naturally without special infrastructure:**

In a live playtest of *I Am a Cat*, the player simply declared a premise mid-session
in the normal input field: *"All cats have wings, and I am no exception. Mine are
velvety black and impeccably groomed. Spook's are chaotic black and white..."*
The engine treated this as a `wait` action (correct: no physical action occurred)
and logged it to the action_log. Every subsequent pass maintained the premise
consistently — subsequent prose described the character's wings as settled and
groomed, Spook's feathers as ruffled and structurally embarrassing, and a move
action entered as "flap over to the dining room" was correctly parsed as `move`
with the right target_id and rendered with full wing mechanics intact.

This demonstrates that **the LLM maintains player-declared premises naturally
through the `recent_actions` context window without any special code.** The
explicit `premise_modifier` infrastructure may be considerably simpler than
originally sketched — the canonicalization pass and module-level opt-in may be
unnecessary for most uses. A minimal implementation:

1. If `game_instance.premise_modifier` is non-null, prepend it as a fixed line
   in every Pass 2 and Pass 3 context packet — "Active premise: [text]".
2. Recognize a player input of the form "premise: [text]" (or a natural in-character
   declaration that Pass 1 identifies as world-establishing rather than action) and
   write it to `game_instance.premise_modifier`. Subsequent turns see it in every
   context packet rather than only in recent_actions.

The second step solves the one real limitation of the implicit approach: a premise
declared through normal input only persists as long as it stays in the
`recent_actions` window. In a long session, it would gradually fade. Storing it in
`game_instance.premise_modifier` and including it in every context packet ensures
it never drops out of scope.

**Natural delivery mechanism — in-character opening prose:**

The most elegant delivery for modules like Meryton is in-character opening prose
that the player writes as the first input of the session. Example:

*"As I alight from the carriage, I use the distraction of my mother and sisters to
discreetly check the revolver in its hidden pocket in my gown. Tonight may be the
end of my career as an agent of the Crown, but I have tracked my quarry these past
six months, and now he is within range. My family will likely disown me before the
night is through, but they will be provided for."*

Pass 1 would parse this as a `wait` or a new action type `premise_declaration`,
write the text to `game_instance.premise_modifier`, and all subsequent passes would
maintain Elizabeth as an armed intelligence operative at a Regency assembly — without
any pre-session dialogue, mode prompts, or special UI. The player simply arrives
in character. This is consistent with the design principle that the LLM handles
language and the engine handles state; the premise is state, so it should be
stored once and reliably included, not re-inferred from prose history.

See also feature 16 (Elizabeth as Agent of the Crown) for a fully worked-out
what-if scenario that would exercise this mechanic.

---

## 1. Web host option

Run the engine from a browser-based interface rather than a local terminal session. The engine's turn loop is already stateless between calls (all state lives in the database), which makes it naturally suited to a request/response web model — each player turn is a self-contained transaction that requires no persistent server process.

**Hosting target: Tiger Technologies (shared hosting)**

Tiger Technologies does not support persistent applications (no long-running Python server process), but does provide MySQL database hosting. This shapes the architecture:

- **Frontend:** HTML + JavaScript; handles player input and renders prose responses. No framework required — this is a simple form-submit-and-display loop.
- **Backend intermediary:** A thin PHP script or CGI handler receives the player's input, calls the LLM API, writes the result to MySQL, and returns the prose. No persistent process; each request spawns and exits.
- **Database:** SQLite → MySQL migration required. The schema is already relational, so translation should be straightforward; the main work is adapting db.py to use a MySQL connector and updating any SQLite-specific syntax (e.g., `PRAGMA`, `REAL` type affinities, `INSERT OR REPLACE`).
- **LLM API calls:** Made server-side from the PHP/CGI layer; API key stays off the client.

The three-pass engine loop maps cleanly onto three sequential API calls per HTTP request. Session state (which game_instance is active, current_time_minutes, etc.) lives entirely in MySQL — no server-side session memory needed.

**SQLite → MySQL migration notes:**
- SQLite `REAL` → MySQL `FLOAT` or `DECIMAL`; JSON fields → MySQL `JSON` type (available in MySQL 5.7+)
- `PRAGMA foreign_keys = ON` → MySQL enforces foreign keys by default on InnoDB
- `INSERT OR REPLACE` → `INSERT ... ON DUPLICATE KEY UPDATE`
- `AUTOINCREMENT` → `AUTO_INCREMENT`
- Schema migration scripts will need a MySQL variant alongside the SQLite originals

E owns a Tiger Technologies account; hosting modules there is a near-term goal once the engine is stable enough for external play.

---

## 2. Transcript save / assisted writing mode

Option to capture the session's prose output as a formatted transcript file. Framing: DAVE as an assisted creative writing tool, not just a game engine. The player and LLM collaborate on a story; the transcript is the artifact.

Could be as simple as a flag that writes Pass 3 output to a running `.md` or `.txt` file alongside the game session. A richer version might include post-session editing, annotation, or export to a formatted document.

---

## 3. Illustrated mode (media generation + compositing)

Use an image generation model to produce simple illustrations for database entities — characters, locations, items. Layer the images (character sprite over location background, items as overlays) to produce illustrated scene cards for each turn, without requiring full animation.

This maps naturally onto the existing schema: `character`, `location`, and `item` records could each carry an `image_path` field pointing to a generated or hand-authored asset. The compositing layer would be a separate rendering step after Pass 3.

---

## 4. Save / resume / new game (session management)

Players expect to be able to save a session, resume a previous session, start a
fresh playthrough of a module, and eventually maintain multiple save slots.
Currently the engine has no concept of session management: there is one set of
mutable state per module database, and the game always resumes from the last
known state. This is incidental behavior, not a feature.

Full session management requires the module/instance architectural split described
in the implementation status doc (pending v6 migration). Once `game_instance`
holds all per-playthrough state and `instance_id` is threaded through every
state table (`character`, `internal_state`, `item_location`, `action_log`,
`character_visited_location`), the following become straightforward:

- **New game:** create a new `game_instance` row, copy starting state from the
  module definition seed.
- **Save:** the database IS the save — state is always written before prose
  renders. Saving is just recording which instance is the "current" one.
- **Resume:** load the most recent active instance for a given module.
- **Multiple save slots:** multiple `game_instance` rows for the same `game_id`,
  each with its own state snapshot.

Architectural note: the "What if..." premise modifier (feature 6) attaches to a
`game_instance`, not to the module. Session management and premise modifiers
should be designed together.

---

## 5. Multiplayer mode

Each human player selects one character in the game world to play simultaneously. Players share a world state (same database); turns are either simultaneous (resolved together in a single adjudication pass) or sequential (each player takes a turn in order).

Deep architectural implication: the current `GameEngine` is single-player and assumes one `role='player'` character. Multiplayer would require: a turn coordinator, conflict resolution when two players act on the same target simultaneously, and potentially a shared session server so multiple clients can connect to one game instance.

---

## 5. Test script suite

Automated tests covering:

- **Schema integrity** — foreign key constraints, valid enum values, float range constraints
- **Engine pass logic** — context packet structure and required fields for each pass
- **DB write correctness** — that `_apply_outcome()` writes exactly what the outcome specifies
- **LLM stub / mock** — an `LLMClient` implementation that returns canned JSON for deterministic testing without live API calls
- **Round-trip integration tests** — full three-pass turn with a known seed database and a mock LLM, verifying the final database state matches expectations
