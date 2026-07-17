# DAVE Paper — Consolidated Working Notes

**Date consolidated:** 2026-07-13  
**Sources:** Desktop Cowork session + Laptop Cowork session (same day) + Grizabella design sketch  
**Status:** Pre-draft; argument structure and literature landscape established  
**Next action:** Decide on Grizabella Phase 1 prototype timing relative to submission; draft argument skeleton

---

## 1. Venue and Framing

**Primary candidate:** *Minds and Machines* (Springer)  
Current editor-in-chief: Mariarosaria Taddeo (Oxford). Scope: philosophy of mind, AI, cognitive science. Publishes research articles, critical exchanges, and reviews. Recently publishing LLM-focused philosophy (e.g., "Language and Thought: The View from LLMs," 2025). Good fit for a paper that grounds an architectural claim in cognitive theory.

**Secondary candidates if M&M doesn't fit:** *AI & Society* (sociological/STS angle, serious games framing); *British Journal of Educational Technology* or *Journal of Learning Analytics* (if serious games / learning application is foregrounded).

**Framing decision:** DAVE as a **social simulation engine**, not a game engine. Vocabulary: "agent," "simulation," "interlocutor" in abstract and introduction. "Narrative simulation environment" or "text-based social simulation" preferred over "RPG" or "virtual world" (the latter is slightly dated post-metaverse hype cycle).

**Tone note:** The paper's argument is architectural but its justification is cognitive-scientific and philosophical. Lead with theory; derive architecture from theory; demonstrate with two implementations.

**Open source asset:** DAVE is publicly clonable (emdalton/dave-rpg). This is unusual and valuable for a theoretical paper — readers who disagree with the architectural claims can verify them. Also enacts the paper's own commitment to transparency.

---

## 2. Core Theoretical Claim

LLMs are structurally the **associative system** in Sloman's (2002) dual-process model: they operate on similarity, soft constraints, and pattern completion. They are not a degraded or incomplete version of a rule-based reasoner — they are a different kind of engine. Tufekci (2026) calls them "plausibility engines," which is intuitive but imprecise. The Sloman framing is more precise and more useful because it explains *why* the failure modes are what they are: LLMs fail at hard-constraint tasks not incidentally but because hard constraints belong to the rule-based system, which they structurally lack.

This framing is now present in the literature (see §6), but the specific connection to the architectural solution — building the rule-based system externally and scaffolding it around an associative LLM core — is not yet named or developed as a design principle. That is the paper's contribution.

**Brain architecture as a richer grounding for the two-systems argument:** The System 1 / System 2 framing is useful but the popular version (Kahneman) is sometimes dismissed as oversimplified. A stronger grounding draws on actual neuroscience: the brain is not a general processor but a set of specialized, coordinated subsystems — Broca's and Wernicke's areas for language production and comprehension, the hippocampus for episodic memory indexing (reconstruction, not storage), prefrontal cortex for working memory and executive function, cerebellum and basal ganglia for automatic/procedural patterns. The brain uses the right tool for the job, coordinating specialist subsystems rather than routing everything through a single general reasoner. This maps directly onto the architectural argument: a reliable AI system likewise requires coordinated specialist components (associative LLM + typed external state store + constraint enforcement layer) rather than a single monolithic model asked to do everything. The hippocampus/RAG analogy is worth noting: the hippocampus doesn't store memories directly, it indexes and helps reconstruct them — structurally similar to retrieval-augmented generation. The prefrontal cortex maintaining active working memory is structurally more similar to injected state: always present in executive context, not retrieved by similarity. This neuroscience parallel strengthens the theoretical argument for M&M and is more defensible than the pop-psychology System 1/2 framing alone.

**Important framing caveat (added 2026-07-13):** The point of invoking cognitive neuropsychology is *not* that AI systems should emulate specific brain structures, nor that AGI requires replicating human neuroscience. The point is narrower and more useful: specialized components handling different types of tasks is a proven approach to solving general problems, as evidenced by the fact that humans already do this. If the goal is systems that can address the general range of problems humans care about, recognizing that humans use different cognitive tools for different problem types is instructive. Crucially, this is not an argument for replicating human fallibility — human memory is reconstructive, emotionally colored, subject to interference and motivated distortion. DAVE's architecture explicitly avoids these failure modes by using a database for canonical state. The analogy motivates specialization and coordination as design principles; it does not prescribe replicating the human system's weaknesses.

**Connection to the 2008 heuristics paper (Dalton, 2008):** The argument that heuristic/associative thinking is not a flawed version of rule-based thinking but a qualitatively different system, with its own strengths, failure modes, and relationship to conscious deliberation, is directly relevant. The 2008 paper argued for a bicameral model in human cognition; this paper argues that reliable AI systems require building the same bicameralism architecturally, because the LLM provides only one chamber. (The 2008 paper need not be cited formally unless it was published; it can inform the argument without appearing in the bibliography.)

---

## 3. The Architectural Principle

**Central claim:**

> Treat the LLM as a stateless associative reasoner. Externalize all state that must persist into a typed, structured store. Inject required state explicitly at each reasoning pass based on record type and injection rules — not semantic similarity.

This is a claim about reliable LLM behavior in general, not just about games. Its generality is the paper's strength.

### 3.1 The Key Distinction: Retrieved Memory vs. Injected State

| | Retrieved Memory | Injected State |
|---|---|---|
| **Examples** | Mem0, RAG, MemoryOS, Park et al. 2023 memory streams | DAVE context packets, Grizabella ground_rules table |
| **Retrieval mechanism** | Semantic similarity at query time | Record type + injection rule at write time |
| **Relevance determination** | Inferred by the retrieval system | Declared by the schema designer |
| **Failure mode** | Relevant facts not retrieved if query doesn't semantically match | Table gets large; eviction policy needed |
| **Theoretical basis** | Associative system (similarity, soft constraints) | Rule-based system (hard constraints, always-applicable) |
| **Best for** | Episodic recall, large corpora, "maybe relevant" content | Ground rules, canonical world state, always-on facts |

**The philosophical point:** Retrieved memory is itself an associative operation — it retrieves by similarity. This means the associative system is being used to supply facts that require the rule-based system to enforce. For ground rules, canonical world state, and always-applicable constraints, this is the wrong retrieval mechanism by design. Injected state is not merely more reliable by degree; it embodies a different theory of what it means for a system to "know" something that must always be present.

### 3.2 Representation matches the tool (addition 2026-07-16)

"Treat the LLM as a qualitative reasoner" is not only a claim about *structure* (inject state rather than retrieve it) — it is also a claim about *representation*. Injected state can still be encoded in a form that mismatches the LLM's reasoning mode. The DAVE implementation provides a concrete self-critical case: OCEAN personality traits are stored as precise floats (`ocean_openness = 0.88`) and injected correctly into every Pass 2 context packet. No engine code performs arithmetic on them — no comparisons, thresholds, or weighted sums. The LLM is simply told to "apply OCEAN traits consistently," which means it interprets 0.88 as something like "highly open to new experience." The float is doing the work of an adjective.

This is a category mismatch even when the structural choice (inject, don't retrieve) is correct: the representation is quantitative; the reasoning is qualitative. The floats are preserved because a future rule-based layer — attitude decay rates, wander probability weighting, behavioral threshold triggers — could genuinely compute on them. Until such a layer exists, they are adjectives stored as numbers. The design principle that follows: when no downstream engine code will perform arithmetic on a value, prefer a qualitative representation and let the LLM reason from it directly.

**Paper-relevant framing:** This is an honest self-critical observation, not a flaw that undermines the architecture. A system explicitly designed around the qualitative-reasoner principle still found numeric representation creeping in, driven by programming habits formed around tools that require numeric inputs. Naming this explicitly in the case study makes the architectural argument more credible — it shows the principle is under active pressure, which means it requires deliberate enforcement, which means it is a real design decision and not an obvious one.

**Direct quote (E., 2026-07-16):** *"Asking an LLM to evaluate a numerical value and make a decision based on it seems incongruous."* This is a usable sentence for the paper.

### 3.4 Tasks that genuinely require both systems in sequence (addition 2026-07-16)

Some tasks cannot be completed by either system alone and require them to work in strict sequence: the associative system extracts, the rule-based system computes. The family tree example is clean: "How many cousins does Ryo have?" cannot be answered reliably by an LLM reading a prose corpus, because (a) relationship references are scattered across many passages and may be missed, (b) cousin relationships require transitive graph traversal (parent's sibling's child) that LLMs perform unreliably at scale, and (c) the LLM cannot hold an arbitrarily large family network in working memory with guaranteed accuracy. The correct architecture is:

1. **Associative pass (LLM):** Read the corpus and extract all familial relationship statements into structured records — "Ryo's uncle Kenji," "Kenji has a daughter, Satsuki" — a task of pattern recognition and natural-language interpretation.
2. **Rule-based pass (database + engine):** Construct a linked graph from the extracted records and run a standard graph traversal to count first cousins. The arithmetic is exact; no LLM judgment is involved.

This is not a workaround for LLM weakness — it is the correct division of labor. Asking the LLM to do the graph traversal too would be using the wrong tool for the second task. Asking the database to extract relationship references from prose would be using the wrong tool for the first.

**Relevance to DAVE in "author companion" mode:** An author-facing mode that can answer structural questions about the fiction being built ("how many cousins does Ryo have?", "who has met the magistrate?", "which characters were present at the funeral?") would require exactly this pattern. The LLM extracts facts from the narrative record; the database maintains the structured world state; the engine queries it. This is an extension of the same architecture DAVE already uses for gameplay, applied to authoring support. Worth noting as a design direction — and as evidence that the bicameral architecture generalizes beyond social simulation to any domain where natural-language knowledge must be made computationally queryable.

**Human parallel (strengthens the theoretical argument):** This two-pass pattern mirrors what a human does when faced with the same question about their own family. A person who knows their family well could not answer "how many cousins do I have?" from memory alone if their father was one of nine children — they would need to externalize: write down the siblings, look up or recall their children, count. Working memory cannot hold the whole graph. The architecture is not compensating for an AI deficiency; it is replicating a cognitive strategy humans already use when a task genuinely exceeds in-context capacity. This grounds the architectural choice as natural and generalizable rather than as an engineering workaround for LLM weakness. It also connects cleanly to the neuroscience framing in §2: the brain offloads to paper (or a database) because the prefrontal cortex's working memory has finite capacity, not because the brain is deficient. The external store is part of the cognitive system, not a prosthetic for a broken one.

**For the paper:** This example sharpens the theoretical claim. The argument is not that the LLM should be used *only* for qualitative reasoning and the database *only* for storage — it is that each component should be used for the task type it is suited to, and that a system handling real-world complexity will encounter both task types, often within a single user query. The family tree case makes this concrete without requiring any game-specific context.

**Additional bridge cases — to develop (2026-07-16):** The family tree example should not stand alone. A small collection of cases with the same structure — natural-language comprehension step (associative) followed by a computation or traversal step (rule-based), with the human version recognizable — would be more persuasive than one. The strongest cases are those where attempting the whole task in working memory (or in a single LLM pass) produces a confident-sounding but unreliable result. *[E. to add more cases here as they occur.]*

### 3.3 The Centipede's Dilemma (constraint on the consistency-checking extension)


Forcing implicit associative inferences into explicit propositional form before checking them may degrade the quality of the adjudication itself — the same centipede's dilemma identified in the heuristics literature (Gladwell, 2005; Gigerenzer, 2007). This constrains the scope of consistency checking: it works at the boundary between structured output and prose (catching Pass 3 errors), but a system that tries to extract logical forms from Pass 2 adjudication in order to verify it risks impairing the associative reasoning it depends on. This is an important honesty point for the paper; it limits the architecture's self-verification capability.

---

## 4. The Three-Pass Architecture

### 4.1 DAVE's Three Passes (established)

1. **Pass 1 — Intent Parsing:** Free-text input → structured action record (cheap, small context, fast model)
2. **Pass 2 — Outcome Adjudication:** Full context packet injected from DB → structured outcome JSON with all state changes (expensive, large context, most capable model). All adjudication results written to DB *before* Pass 3 runs.
3. **Pass 3 — Prose Rendering:** Structured outcome → player-facing prose (moderate cost, creative task)

### 4.2 Separation of Cognitive Functions as Reliability Mechanism

The three passes deliberately separate three cognitively distinct operations:
- **Interpretation** (Pass 1): What did the agent intend?
- **Deliberation** (Pass 2): What are the consequences, given full world state?
- **Expression** (Pass 3): How should this be communicated?

This separation is a reliability mechanism, not just an engineering convenience. In single-pass systems, the model can "complete" deliberation and inadvertently satisfy its own completion signal without producing user-facing output. Pass 2 outputs *structured data*, not prose; the model cannot finish Pass 2 and accidentally complete the user turn. Pass 3 is a mandatory, separate step whose sole function is response generation. (This failure mode has been observed empirically in single-pass OWUI sessions.)

### 4.3 Extension to General AI Assistants

The same three-pass logic applies to AI assistant infrastructure:

1. **Pass 1 — Intent Classification:** User message → structured task record (type, complexity, tools required, model tier). Also the correct place to make **model routing decisions** — cheap classification enables principled dispatch.
2. **Pass 2 — Task Execution:** Assembled context + appropriate tools/model → structured result
3. **Pass 3 — Response Generation:** Structured result → user-facing response prose

Conditional execution: a full three-pass loop on every turn is unnecessary. Pass 1 classifies complexity; simple turns short-circuit to immediate response; complex/multi-tool turns execute the full loop. Even conditional three-pass is sufficient to make the architectural argument.

---

## 5. Evidence Structure: Two-Domain Argument

**Primary case — DAVE:** Complex social simulation. NPC attitudes, motivations, faction dynamics, lazy world generation. Full three-pass architecture. Demonstrates the principle at full complexity. The psychological modeling (OCEAN + Ford-Nichols 24-goal taxonomy + Maslow as priority override) is directly engaging the cognitive science literature on motivation and social cognition — this grounds the simulation in theory, not just narrative convention. Maslow's role here is specifically as a computational priority-override in the NPC motivation stack: an NPC in survival desperation won't pursue self-actualization. The paper should present this as a design decision for the motivation model, not as a philosophical claim about the hierarchy as a universal theory of human value. An extension to AI assistants — a system that notices a user's agitation in their messages and gently suggests a break and something to eat — is an extrapolation of the same principle to a different domain, and worth at most a sentence if mentioned at all; it is not part of the paper's argument.

**Secondary case — Grizabella memory layer:** Personal AI assistant with structured ground rules, user profile, and project context injected into every system prompt. Simpler domain (no three-pass loop required for basic operation). Demonstrates the same principle in a different domain (game engine → AI assistant infrastructure). See Grizabella design sketch for schema and implementation plan.

**Implementation note (updated 2026-07-13):** The Grizabella prototype should be implemented as an **MCP server** rather than as an OWUI-specific filter function. MCP (Model Context Protocol) is a de facto standard for LLM tool and context integration; implementation details are therefore platform-agnostic and familiar to anyone in the LLM field. This also makes the system more broadly useful and open-sourceable without tying it to OWUI's architecture. The architectural principle (injected state via typed records, not semantic retrieval) is unchanged; only the delivery mechanism changes. The paper should describe the MCP implementation, not the OWUI filter, for generality.

**Timeline note:** Realistic proof-of-concept completion: end of August 2026. Designing and running comparative test cases (Mem0-only vs. injected-state vs. hybrid; comparison against LLMs with different context window sizes) will require additional time in September or beyond. This affects the DAVE paper submission timeline — see §8.

**Argument structure:** Same architectural pattern solves analogous reliability problems in two unrelated domains → generalizability claim. The Grizabella case should be brief in the paper (a paragraph or two plus the schema as evidence). The full Grizabella system description belongs in a separate publication or implementation report.

**Empirical component (if available):** Grizabella Phase 3 evaluation — comparing Mem0-only vs. injected-state vs. hybrid, measuring ground rule adherence rate, token cost, latency. If Phase 1-3 prototype is built before submission, this provides empirical evidence for the theoretical claim and distinguishes the paper from a pure design paper.

---

## 6. Literature Landscape

The field is moving fast. The following is a framing map, not a complete review. The goal is to identify where the paper's contribution sits relative to existing work.

### 6.1 Dual-Process Theory and LLMs

The framing of LLMs as System 1 / associative is now present in the literature:

- **Coda-Forno et al. (2025)** — "Exploring System 1 and 2 communication for latent reasoning in LLMs." Directly relevant; examines how System 1 and 2 interact in LLM reasoning. [arxiv](https://arxiv.org/html/2510.00494v1)
- **Birkbeck paper** — "Dual-process theory and decision-making in large language models." [eprints.bbk.ac.uk](https://eprints.bbk.ac.uk/id/eprint/56681/)
- Reasoning model literature (o1, DeepSeek-R1 and successors) explicitly frames extended reasoning tokens as a move toward System 2. A 2025 survey: "A Survey of Efficient Reasoning for Large Reasoning Models." [arxiv](https://arxiv.org/pdf/2503.21614)

**E's positioning:** The dual-process framing of LLMs is established. The contribution here is (a) using Sloman's (2002) more precise formulation rather than Kahneman's popular version, (b) deriving a specific architectural solution from the theory, and (c) connecting to the heuristics/intellectual styles literature (Gigerenzer, Gladwell, Riding & Cheema) to ground the argument in cognitive psychology.

### 6.2 Social Simulation with LLMs

- **Park et al. (2023)** — "Generative Agents: Interactive Simulacra of Human Behavior." [ACM DL](https://dl.acm.org/doi/fullHtml/10.1145/3586183.3606763). The foundational paper. 25 agents in a virtual town. Uses natural language **memory streams** retrieved by semantic similarity. DAVE's architecture is a direct contrast: typed records injected by record type, not retrieved by similarity. This is a key positioning comparison.
- **"LLM-Based Social Simulations Require a Boundary" (2026).** [arxiv](https://arxiv.org/pdf/2506.19806). Argues for constraints/boundaries in social simulation. DAVE's architecture provides these constraints structurally.
- **PAVE (2025)** — "A Cognitive Architecture for Legitimate Violation in Generative Agent Societies." [arxiv](https://arxiv.org/pdf/2605.19351). Cognitive architecture for agent societies; potentially relevant to NPC modeling.
- **"LLM Agents That Act Like Us" (2025).** [arxiv](https://arxiv.org/html/2503.20749v4). Accurate human behavior simulation; relevant to the reliability question.
- **"A Quest for Information: Enhancing Game-Based Learning with LLM-Driven NPCs" (2025).** [CESCG](https://cescg.org/wp-content/uploads/2025/04/A-Quest-for-Information-Enhancing-Game-Based-Learning-with-LLM-Driven-NPCs-2.pdf). Directly adjacent: LLM-driven NPCs in educational games. Review for positioning.

### 6.3 Memory Architectures for LLM Agents

- **MemoryOS / MemOS (EMNLP 2025 Oral)** — Hierarchical memory OS for personalized AI agents. [GitHub (BAI-LAB)](https://github.com/BAI-LAB/MemoryOS); [ACL Anthology](https://aclanthology.org/2025.emnlp-main.1318.pdf). Uses OS metaphor; tiered storage (short/mid/long-term); retrieval-based. Closest existing work to Grizabella's approach but does not make the injected-vs-retrieved distinction. Key comparison.
- **MemTensor MemOS (2025)** — "Self-evolving memory OS for LLM & AI Agents." [GitHub](https://github.com/MemTensor/MemOS). Hybrid retrieval, cross-task skill reuse.
- **"From Storage to Experience: A Survey on the Evolution of LLM Agent Memory Mechanisms" (2025).** [arxiv](https://arxiv.org/pdf/2605.06716). Survey paper; use to map the landscape.
- **Mem0, Zep, Graphiti, LangMem, Cognee, LlamaIndex** — commercial/open memory frameworks, all primarily retrieval-based. The absence of a typed injection layer in all of these is the gap the paper addresses.
- **"Goal-Directed Search Outperforms Goal-Agnostic Memory Compression" (2025).** [arxiv](https://arxiv.org/pdf/2511.21726). Retrieval quality for memory; relevant to comparison.
- **RAG reliability literature** — "Retrieval-Augmented Generation: A Comprehensive Survey" (2025) [arxiv](https://arxiv.org/html/2506.00054v1); "Towards Context-Robust LLMs" (2025) [arxiv](https://arxiv.org/pdf/2502.14100). Documents RAG failure modes (over-reliance on retrieved context, semantic mismatch, irrelevant retrieval). Supports the paper's critique.

### 6.4 Multi-Pass and Multi-Stage Pipelines

- **Multi-LLM verification pipelines** — agent-based pipelines with extractor, retriever, checker, and judge roles. Related but focused on verification, not on the separation of interpretation/deliberation/expression as a reliability mechanism.
- **SEAR (2025)** — Schema-based evaluation and routing for LLM gateways. [arxiv](https://arxiv.org/pdf/2603.26728). Related to Pass 1 as model router.
- **ADOPT (2025)** — Adaptive dependency-guided joint prompt optimization for multi-step LLM pipelines. [arxiv](https://arxiv.org/pdf/2512.24933). Multi-step pipeline optimization.
- The specific three-pass structure with deliberate cognitive function separation as a **reliability** mechanism does not appear to be named in the literature. This is a contribution.

### 6.5 What Is Not in This Paper (Separate Paper)

The epistemological argument developed in a parallel session — claim taxonomy, epistemic hierarchy as grouping parameter, hermeneutic layering, consistency-checking as a research direction — is a separate contribution fully developed in §7 below. It should not be included in the M&M architecture paper, which would become unfocused.

---

## 7. The Epistemology Paper (Separate Contribution)

**Developed:** 2026-07-12 (laptop session) and continued 2026-07-13  
**Status:** Ideas fully developed in conversation; not yet drafted; literature review needed

### 7.1 Core Contributions

1. **Taxonomy of claim types.** Five categories with distinct epistemological properties:
   - *Grounded empirical* — testable, tested, correctable by evidence (evolution, climate science, vaccine efficacy)
   - *Normative* — value weightings, not subject to correspondence truth but assertable as facts about the speaker's commitments
   - *Methodological* — epistemic rules for how to update beliefs (trust peer review, require replication); neither purely empirical nor purely normative
   - *Authority-based* — trust in a source, ranging from correctable institutional trust (scientific consensus) to unconditional personal authority (tribal/religious)
   - *Structurally deferred empirical* — claims with the surface form of empirical predictions but arranged to be unfalsifiable within actionable timeframes ("humans will adapt," eschatological Earth-use doctrine)

2. **Epistemic hierarchy as grouping parameter.** The ordering of these claim types is not a universal truth to be imposed but a *parameter* that varies across worldviews. Two documents are consistent with each other not because they agree on facts but because they apply the same ordering of epistemic categories. The hierarchy is the clustering variable for consistent document collections — and for detecting inconsistent *application* of one's own stated hierarchy (motivated reasoning as a within-document consistency violation).

3. **Hermeneutic layering.** The hierarchy doesn't just order claim types — it defines what counts as a valid interpretive move within the system (the enclosing epistemology). Midrash, Talmudic interpretation, Catholic exegesis, legal hermeneutics, and Kuhnian paradigms are all examples: the outer framework determines not just what ranks higher but what registers as a coherent argument at all. Two documents can share claim types and surface hierarchy and still be incommensurable because their enclosing epistemologies define the moves differently.

4. **Worldview-consistency checking as a tractable alternative to truth verification.** The question "is this claim true?" requires a ground truth the system cannot adjudicate. The question "is this claim consistent with this worldview's hierarchy?" is tractable without resolving the underlying epistemological dispute. This reframes the document-filtering/LLM-verification problem in a way that sidesteps the political impossibility of neutral truth labels while still being useful and principled.

5. **The is-ought gap as a principled scope limit.** Hume's is-ought gap establishes that normative conclusions cannot be derived from empirical premises alone — a value premise is always required. Two people can share the same epistemic hierarchy, both highly valuing empirical evidence and both aware of the same research, and arrive at different normative conclusions because they hold different prior values. One may know the scarcity-and-cognition research well and conclude a normative obligation of care toward people in poverty; another may know the same research and not conclude any such obligation, because care is not a prior value they hold. Both worldviews can be internally consistent. The consistency checker can evaluate whether normative conclusions are consistent with *stated* value commitments plus the empirical evidence as the worldview reads it — inference-validity checking. What it cannot do, and should not claim to do, is adjudicate whose value premises are correct. Stating this as a principled limitation is itself part of the paper's contribution: the checker's scope is coherence, not the correctness of values. This also suggests a refinement to the normative category: normative claims are not uniform. Some are purely value weightings with no empirical content. Others embed empirical assumptions that can be evaluated independently. Affect-driven normative claims (revulsion, discomfort with the unfamiliar, strong identification with in-group judgments) are often in the second category — the affective grounding is real, but the empirical model underlying the claim may be wrong or incomplete, and the checker can flag that mismatch without adjudicating the value itself.

6. **Application to LLM output verification and document filtering.** A consistency-checking system that makes epistemic hierarchies explicit — and distinguishes empirical anchors (justifiable by evidence) from normative anchors (stated as values) from methodological commitments — is more honest and more useful than existing fact-checking approaches, which collapse everything into a single true/false axis. Retrieving documents by hierarchy-consistency rather than topical similarity is a research direction not currently in the literature.

### 7.2 Venue

**Primary:** *Social Epistemology* (Taylor & Francis). Explicitly covers collective knowledge, trust in institutions, and the social dimensions of knowledge formation. The "who to trust when models constitute a 'who'" framing maps directly onto the journal's scope. The hierarchy-as-grouping-parameter argument — about how epistemic communities form and maintain coherence — is precisely the kind of contribution this journal publishes.

**Secondary:** *Philosophy & Technology* (Springer) if the AI application is foregrounded over the epistemological framework. *Synthese* if a more formal epistemology framing is preferred. *AI & Society* if the sociological dimensions of AI knowledge claims are the hook.

**Possible public-facing version:** *Aeon* or *Noema* for a long-form essay version accessible to non-specialists. Different register, same ideas; good for finding the liminal-space audience faster.

### 7.3 Literature to Engage

**Philosophy of science / epistemology:**
- Popper — falsifiability as the demarcation criterion; the clean statement of what would falsify evolution
- Lakatos — protective belt; how pseudoscientific theories absorb disconfirmation through auxiliary hypotheses
- Kuhn — paradigms as enclosing epistemologies; paradigm shifts as changes in what counts as a valid argument
- Gadamer, Ricoeur — philosophical hermeneutics; the hermeneutic circle; tradition as interpretive context
- Fricker — *Epistemic Injustice* (2007); credibility deficits and excess; relevant to authority-based claims
- Longino — *Science as Social Knowledge* (1990); social dimensions of scientific knowledge production

**NLP / computational approaches:**
- Argument mining: IBM Project Debater; Reed & Dunne (University of Dundee / Argument Web); claim-premise identification
- Stance detection: NLP classification of support/opposition/neutral toward a claim — closest existing tool
- Epistemic modality detection in biomedical NLP: certainty, hedging, source attribution
- Natural Language Inference (NLI): entailment/contradiction between premise-hypothesis pairs (SNLI, MultiNLI)
- Fact-checking pipelines: ClaimBuster (claim detection) → evidence retrieval → verdict; and their limitations

**Education and care ethics:**
- **Nel Noddings** — Argues that the dominant analytical critical thinking framework is too narrowly rule-based and neglects relational, caring, contextually attentive modes of knowing. Different domains of human concern require different epistemological approaches — care reasoning is neither reducible to nor rankable against analytical reasoning. This maps directly onto the claim taxonomy: normative and relational claims require modes of reasoning (attentiveness to particular cases, relational context, emotional attunement) that the rule-based system doesn't capture, and treating them as deficient versions of empirical reasoning misses what they are. Noddings also connects to the intellectual styles literature in the 2008 paper (Dalton, 2008) — she is arguing for the wholist/field-dependent side of that spectrum as a legitimate epistemological mode, not a deficit. Important for the epistemology paper's argument that different claim types belong to different epistemological modes, and that the hierarchy of modes is itself a parameter rather than a universal.

  Specific references (E. is already familiar with these):
  - Noddings, N. (1994). *Educating for Intelligent Belief or Unbelief*. Teachers College Press. [Most directly relevant to the claim taxonomy and epistemic hierarchy argument — the title alone signals the topic.]
  - Noddings, N. (2002). *Starting at home: Caring and social policy*. University of California Press.
  - Noddings, N. (2004). The aims of education. In D. J. Flinders & S. J. Thornton (Eds.), *The curriculum studies reader* (pp. 331–334). Routledge.
  - Noddings, N. (2006). *Critical lessons: What our schools should teach*. Cambridge University Press. [Directly relevant — her critique of how critical thinking is taught connects to Paul critique in 2008 paper.]

**The gap to establish:** None of the existing NLP literature combines claim-type classification + hierarchy identification + within-document hierarchy-consistency checking. The components exist; the integrated system and the epistemic-hierarchy-as-parameter framing do not.

### 7.4 Connection to the Architecture Paper

The two papers share the dual-process theoretical foundation but apply it differently. The architecture paper asks: given that LLMs are associative engines, how do you build reliable systems around them? The epistemology paper asks: given that LLMs are plausibility engines, how do you evaluate the epistemic quality of what they produce and what they are trained on? The architecture paper is about design; the epistemology paper is about evaluation and knowledge claims. Together they establish a coherent scholarly position about AI reliability at both levels.

---

## 8. Open Questions (Architecture Paper)

**Paper scope:**
- Does the Grizabella piece belong in this paper or as a follow-on? Lean: brief inclusion for generalizability; full system as a separate implementation/evaluation report.
- First authorship and co-authors? (Affects how much Grizabella content to include if it involves other contributors.)
- Is this a design paper or an empirical paper? Depends on whether Grizabella Phase 3 evaluation is built before submission. A design paper with a planned evaluation is publishable; an empirical paper is stronger.

**Timeline (updated 2026-07-13):**
- Grizabella MCP prototype (Phase 1): target end of July 2026
- Comparative evaluation (Phase 3): September–October 2026 at earliest
- DAVE paper draft: October–November 2026 if waiting for empirical data; earlier if submitting as design paper with evaluation as future work
- Preprint posting: as soon as a solid draft exists, independent of journal submission timeline
- Consider posting architecture paper preprint before empirical data is complete — establishes the design argument with a timestamp, and the empirical paper can follow as a separate submission or an updated preprint

**Framing for M&M:**
- Primary frame: philosophy of memory (injected vs. retrieved as two theories of what it means to "know" something persistently) — fits M&M's cognitive science angle.
- Secondary frame: cognitive architecture (externalized rule-based system scaffolded around an associative LLM core) — also fits.
- Avoid foregrounding the game context in the abstract; let it emerge in the implementation section.

**AI disclosure:**
- M&M likely has an AI disclosure policy; check before submitting.
- This paper was developed in conversation with Claude (Anthropic) as a thinking partner. The architectural ideas, design decisions, and framing are E's; the conversation was a sounding board. This is analogous to discussing ideas with a colleague, not ghostwriting. A paper *about* LLM limitations developed with appropriate AI disclosure has a certain self-referential integrity.

**Empirical component:**
- Grizabella Phase 1 prototype: SQLite DB + OWUI filter function + seeded preferences. Modest scope; could be built quickly.
- Phase 3 evaluation: Mem0-only vs. injected-state vs. hybrid, measuring ground rule adherence. This is the empirical evidence that would strengthen the submission significantly.

---

## 8. Next Steps (Suggested Priority Order)

1. **Read the literature** identified in §6 — especially Coda-Forno et al. (2025), the Birkbeck dual-process paper, Park et al. (2023) carefully, MemoryOS (EMNLP 2025), and "LLM-Based Social Simulations Require a Boundary" (2026). These are the closest existing work and define the positioning. For the epistemology paper, start with Lakatos and the argument mining survey literature; also Noddings (see §7.3). **Literature access note:** Most AI/CS papers are freely available on arXiv or Semantic Scholar (semanticscholar.org often has full PDFs). The Unpaywall browser extension finds legal free versions of paywalled papers automatically. JSTOR provides 100 free articles/month to unaffiliated researchers. ResearchGate often has author-posted copies. A UNH campus trip may still be needed for older philosophy and education sources (Noddings, Lakatos, Fricker, Gadamer) not available through open channels — worth batching those into a single trip rather than going for individual papers.
2. **Decide on Grizabella prototype timing** — build Phase 1 before or after drafting? Building first gives empirical grounding; drafting first clarifies what the prototype needs to demonstrate.
3. **Draft argument skeleton** — one-page outline of the argument in order: theory → principle → DAVE case → Grizabella case → comparison to existing work → implications. Not prose; just the logical sequence.
4. **Post preprints early** — see §9 for strategy. Preprints establish a timestamp for ideas described in interviews and presentations before journal review completes.
5. **Check M&M and *Social Epistemology* submission guidelines and AI disclosure policies.**
6. **Consider the blog post** as a faster path to finding the liminal-space audience — write alongside or before the journal papers; different register, same ideas. *Aeon* or *Noema* for the epistemology argument; a technical blog or Substack for the architecture argument.

---

## 9. Preprint Strategy

### Why preprints matter here

Journal review cycles run 12–18 months or longer. Preprints establish a dated, findable, citable record of the work now — before review begins. This is directly relevant given that the ideas in both papers were developed before and described in professional contexts (interviews, presentations) without the formal scholarly record to back them up. A preprint on a recognized repository closes that gap.

### What preprints are and are not

A preprint is a version of a paper posted to a public repository before (or during) peer review. It is not considered "published" for the purposes of journal submission. Most major publishers, including Springer (M&M) and Taylor & Francis (*Social Epistemology*), explicitly permit preprints posted before submission or during review — this is now standard practice in many fields. The key is to verify the specific journal's policy in its submission guidelines before posting; this is usually a one-paragraph check.

### Repositories

- **arXiv** (arxiv.org) — cs.AI or cs.CL sections for the architecture paper. Largest preprint repository; well-indexed by Google Scholar, Semantic Scholar. Standard in AI/CS research. Posts appear within 1–2 business days.
- **PhilArchive** (philarchive.org) / **PhilPapers** — philosophy-specific repositories; well-indexed in the philosophy community. Natural home for the epistemology paper. Cross-posting to both arXiv and PhilArchive maximizes cross-community reach.

### Practical steps

1. Finalize a draft (need not be the final journal version — repository versions can be updated as the paper evolves).
2. Check the target journal's preprint policy (usually under "Submission Guidelines" or "Open Access").
3. Post to the appropriate repository. The repository assigns a DOI and timestamp.
4. List on CV as: *Author (Year). Title. Preprint. arXiv:XXXX [or PhilArchive:XXXX]. Under review at Journal Name.*
5. Update the repository record and CV entry when accepted and published.

### Self-referential note

A paper about LLM limitations and epistemic transparency that is itself transparent about its development process — including its use of an LLM as a thinking partner, disclosed appropriately per journal policy — has a certain integrity. The preprint version is a good place to include a methods note about the development process that the journal version might handle differently.

---

## 10. Related Documents

- `Grizabella Structured Memory Layer — Design Sketch (DAVE-derived).md` — full schema, filter design, implementation plan, evaluation design
- `DAVE_paper_notes_2026-07-13.md` — original desktop session notes (superseded by this document)
- `docs/implementation_status.md` — current DAVE engine status (read before touching code)
- `docs/module_authoring.md` — module authoring conventions
- `emdalton/dave-rpg` — public repo; open source asset for the paper
