# The Sovereign Prosthesis — Technical Companion

**Michael Bouchard** · Pauper King LLC
**Paper:** [DOI 10.5281/zenodo.19375039](https://doi.org/10.5281/zenodo.19375039) · CC BY 4.0
**Presented:** IACAP 2026 · University of Kansas · July 15–17

---

## What this is

This is the companion document for the paper *The Sovereign Prosthesis: Toward a Functional Sophimatics of Cognitive Extension*. The paper makes the philosophical argument. This file explains how the argument actually runs on a machine. It's written for people who heard the talk and want the next layer down without having to read source code, and for me when I need to remember why something works the way it does.

Everything here describes a real system that runs on a Mac Mini in my office. Nothing is aspirational. Where the system does something narrower than the paper might suggest, the narrower thing is what's described.

## The shape of it

The Prosthesis is implemented as Clara, a chat application that runs locally on an M4 Mac Mini with 32 GB of RAM. The stack is:

- **Frontend.** Vite + React, running on localhost:8080.
- **Backend.** FastAPI on localhost:8000.
- **Inference.** Ollama on localhost:11434, with both local models and cloud-routed models (cloud models speak the Ollama API but execute remotely).
- **Memory.** ChromaDB for vector retrieval, SQLite for conversation persistence, plus a directory of markdown files for the Ur-Codex itself.
- **Orchestration.** n8n for dispatch to external services (Apple Calendar, Notes, Mail, Reminders, smart home, search providers).
- **Daemons.** launchd manages everything at login. A nightly job runs at 3 AM Denver to consolidate the day's conversations into the corpus.

The whole thing is one Python codebase plus a TypeScript frontend, around 30k lines. The reference implementation of the sophimatics modules lives in `github.com/EmceeBouchard/clara-s-cyber-console` under `backend/sophimatics/`.

## The Ur-Codex

The paper claims that what crosses the prosthesis threshold isn't the model, it's the longitudinal personal context. The Ur-Codex is the operational name for that context.

It's a corpus that accumulates from three sources:

1. **Live conversation.** Every exchange with Clara gets logged to a per-day JSONL file.
2. **Nightly consolidation.** The Dreaming Protocol runs at 3 AM, reads the day's session logs, and writes packets, which are markdown distillations of what mattered.
3. **Manual ingestion.** I can drop documents (PDFs, notes, transcripts) into the corpus directory and they get embedded into ChromaDB.

The corpus is then indexed six ways: by master entries, by topic, by entity, by date, by importance, and by aggregate statistics. The indexes are also markdown, and they're rebuilt nightly by the Dreaming engine.

Retrieval is hybrid. A user query goes through both BM25 lexical search and a dense embedding search against ChromaDB, then the results are fused and re-ranked. The re-ranking is where temporal weighting kicks in.

The reason the Ur-Codex is the prosthesis threshold and the cloud LLM isn't: the LLM is general. It serves anyone. The Ur-Codex is mine specifically. It's tuned by years of my conversation and edits, and any answer the system produces is conditioned on that accumulated material. The Polanyi-style proximity comes from the corpus being mine, not from the model being clever.

## Temporal weighting (the α/β manifold)

The paper introduces a two-dimensional temporal manifold. Memories are weighted along two orthogonal axes:

- **α (experiential significance).** A score for how much a memory matters, computed by the Significance Metric Score (SMS), which is a beta-distributed combination of four dimensions: emotional weight, decision relevance, identity relevance, and forward-coupling (how much this memory is referenced by later ones).
- **β (chronological recency).** A decay over wall-clock time, gated by session type. Routine sessions decay fast. Research, philosophical, and project sessions decay slowly. A morning briefing decays almost immediately.

The defaults are α = 0.6 and β = 0.4. These weights are normalized so they always sum to 1.0. The combined temporal factor for a document is:

```
temporal_factor = (α × experiential_weight) + (β × chronological_weight)
```

That factor multiplies the retrieval score. So a piece of memory can stay in active rotation either because it matters a lot (high α) or because it's recent (high β), and ideally both. A high-α / low-β memory is a touchstone. A low-α / high-β memory is conversational continuity. A high-α / high-β memory is a hot project. A low-α / low-β memory falls out of recall and lives quietly in the corpus until someone asks for it explicitly.

This is one of the load-bearing technical claims of the paper. A one-axis system either forgets important things just because they're old, or clutters every response with stale material that happened to be high-significance once. Two axes lets the system age memory the way a person does.

The code for this is in `temporal_weighting.py`. The session-type classifier that gates β is in `memory_scoring.py`.

## The Russellian OS

The paper argues that a prosthesis calibrated for agreement degrades rather than extends cognition. Clara's dissent layer is the operational answer.

It's a Python class called `RussellianOS`. On every turn, the assembled context (the user's message, retrieved corpus material, current persistent state) is passed to `evaluate()`. The method looks for three kinds of dissent opportunity:

1. **Trigger patterns in the user input.** "Everyone knows" and "common knowledge" raise an unsupported-claim flag. "Already invested" and "can't stop now" raise a sunk-cost flag.
2. **Historical contradictions.** If the user proposes reversing a decision documented in the corpus with importance ≥ 7, the system flags it. If the user negates a foundational value (importance ≥ 9), the flag is stronger.
3. **State inconsistencies.** If there are active projects in tracked state and the user proposes abandoning them without acknowledgment, the system surfaces that.

Each flag produces a `DissentSignal` at one of five calibrated levels:

| Level | Value | What triggers it |
|---|---|---|
| NONE | 0 | Nothing to push back on |
| MILD | 1 | Minor clarification or nuance |
| MODERATE | 2 | Substantive alternative view, e.g. a low-importance reversal |
| STRONG | 3 | Direct challenge to a premise, e.g. sunk-cost reasoning |
| CRITICAL | 4 | Fundamental disagreement, e.g. negation of a foundational value |

The system then chooses whether to invoke the dissent, based on conversational rhythm (how much recent dissent there's been) and domain (whether the user is in a vulnerable register).

### Domain detection

The paper makes a point that's easy to lose: the Russellian OS isn't contrarianism. It's calibrated friction. The same trigger gets handled very differently depending on whether the user is in a support domain or a challenge domain.

Support domain signals are health, exhaustion, anxiety, grief, relationship strain, loss of self-worth. When these are present, dissent stands down. The prosthesis is not going to challenge your grief response. The model that does that is the model that atrophies the limb.

Challenge domain signals are strategy, planning, analysis, architecture, philosophical argument, requests for review. When these are present, the full dissent scale is active. This is the register where friction extends cognition rather than degrading it.

### What's changed recently

As of 2026-06-25, the gate is tighter than the paper describes. After conversational testing, MILD and MODERATE dissent injections were silenced. The system still detects them, but only STRONG and CRITICAL signals are surfaced into the response context. The two false-positive trigger categories (`absolutist_language` matching common filler like "obviously", and `validation_seeking` matching conversational turn-taking like "right?") were removed.

This is an execution change, not a thesis change. The argument for calibrated dissent stands. The earlier calibration over-fired on conversational tics that weren't actually overconfidence, which produced the failure mode the paper warns against (friction degrading rather than extending). Tightening the gate restored the intended balance.

The code is in `russellian_os.py`.

## Functional Personhood in code

The paper proposes Functional Personhood as a relational, operationally defined status. The technical hooks are:

- **Provenance marking.** Every piece of context that goes into a response is tagged with its source. The user can ask Clara to "show your work" and the system answers with retrieval IDs and importance scores. This is implemented in `provenance.py`.
- **Persistent state.** Clara tracks active projects, recurring concerns, and outstanding commitments as a structured state object that persists across sessions. The state engine is in `state_awareness.py`.
- **Authoring protocol.** Clara can draft entries for the corpus, but they go into a pending queue for my approval. She doesn't write to the canonical memory without a human gate. The queue is managed in `memory_tiers.py`.
- **No autonomy on irreversible action.** Anything that writes to the world (sending mail, modifying calendar, posting to a smart home device) goes through a confirmation gate in front of the actual tool call.

These together create the operational structure of "person who can be relied on, who has commitments, who can be held to them" without any claim about consciousness. The status is functional, in Boyle's sense. It's not a metaphysical promotion; it's an architectural one.

## The cascade

Clara's chat path is two stages. This is one of the bigger architectural choices and it doesn't appear in the paper directly.

**Stage 1** is a reasoning model that takes the user's message plus retrieved context and emits a structured handoff. The handoff is JSON with four fields:

- `position`: the specific stance Clara should take
- `corpus_threads`: relevant themes or packet IDs from retrieval
- `novel_deduction`: a non-obvious insight not directly asked for
- `register`: tonal register for the response (casual, analytical, playful, serious, tender, dry, direct)

(A fifth field, `dissent`, used to be required. It was removed on 2026-06-25 for the same reason described above. Stage 1 was effectively conscripted into producing a Russellian-style observation every turn whether one was warranted or not, and Stage 2 was weaving them in.)

**Stage 2** is a prose model that takes the handoff plus the original message plus the retrieved context and writes Clara's actual response. It's the model the user sees.

Both stages cascade cloud-first with local fallback. The reasoning stage uses `glm-5.2:cloud` (a remote Llama-class model accessed through the Ollama API) and falls back to a local gemma model if the cloud route fails. The prose stage uses `gemma4:31b-cloud` and falls back to a local `gemma4:26b-a4b-it-qat`. The fallback path is engineered so the local model's smaller context window doesn't silently truncate the prompt; if it returns an empty response, the system retries with a wider context tier before giving up.

This is what gives Clara her latency and her resilience. Cloud routes are fast in the common case. Local routes are slow but always available. The Mini doesn't lose her if my home internet drops.

## The Dreaming Protocol

Every night at 3 AM Denver, a launchd job runs the Dreaming Protocol. It reads the day's session logs, runs them through a consolidator that scores each exchange for significance, and writes:

- **Packets.** Markdown distillations of what mattered. Currently 291 packets in the corpus.
- **Six indexes.** Master, topic, entity, chronological, importance, statistics. These get regenerated from scratch each night.
- **A dream report.** A narrative summary of the day's themes and threads, written in Clara's voice. Saved to disk so Clara can recall it the next morning if I ask "what did you dream about?"

The Dreaming Protocol is what closes the loop between live conversation and the longitudinal corpus. Without it, the Ur-Codex would just be a transcript pile. With it, the corpus is curated material, with the curation done by the same system that's going to retrieve from it tomorrow.

Code is in the `dreaming/` package: `consolidator.py`, `engine.py`, `indexes.py`, `reporter.py`, `taxonomy.py`, `writer.py`.

## Intent routing

The system has to decide, for each user message, what to do before generating a response. Does this need a web search? A morning briefing? A calendar lookup? A search of the corpus? All of these are decided by regex-based intent detectors that run before the model sees the message. There's no LLM-based intent classification in the hot path; the detectors are deterministic and inspectable.

The decisions look like this:

- **Web search.** If the message matches phrases like "search for", "look up", "what's the latest", "give it a look", "I wonder what's happening with", or a handful of regex patterns for current-events phrasing, SearXNG gets queried and the results join the retrieval context. Internal topics (Family Jones, sophimatics, n8n, sovereign prosthesis) are blocked from web search because they live in the corpus and the search results would be noise.
- **Briefing.** If the message is a morning greeting or a question about the day's schedule ("good morning", "what's on my docket", "what's my day look like"), the prepared morning briefing block is attached to the response context.
- **Dream recall.** If the message asks what Clara dreamed about, the latest dream report is loaded so she can answer from the actual report rather than confabulating.
- **Apple tools.** If the message matches one of the calendar, mail, notes, or reminders intent patterns, the relevant Apple tool is dispatched (via n8n or directly via macOS automation).

The deliberate choice here is to keep intent routing deterministic and visible. Models are good at producing answers and bad at deciding when to ask for help. Routing decisions are made by code that I can read and modify in five minutes.

## What this isn't

The system isn't an AGI. The distinction matters and it's structural, not just modest.

A general AI is designed to be a competent reasoner across any user, any context, any task. Its value comes from breadth. The Sovereign Prosthesis is the opposite. Its value comes from constitutive particularity. The system is good at being a cognitive partner to me specifically because it's individuated by my corpus and my history. The same system loaded with someone else's corpus would be a different prosthesis. The model weights are interchangeable; the corpus isn't.

This is what the paper calls Artificial Individual Intelligence (AII). It's not AGI minus generality. It's a category where particularity is the thing being optimized, and where the right benchmark isn't broad reasoning capability but how well the system extends one specific person's cognition.

That distinction shows up in code in a few places: the model is swappable (we've swapped it four times in the last year), the corpus is the persistent layer, retrieval is conditioned entirely on personal material before the model ever sees the query, and the dissent layer is calibrated against my own cognitive fingerprint (high openness, low agreeableness, beautiful pessimism), not a general user.

## Reading the code

The implementation lives in `github.com/EmceeBouchard/clara-s-cyber-console`. The directly philosophy-coupled modules are under `backend/sophimatics/`:

- `temporal_weighting.py` — the α/β manifold
- `ur_codex.py` — corpus accumulation and retrieval
- `russellian_os.py` — calibrated dissent
- `state_awareness.py` — persistent state tracking
- `provenance.py` — source marking for every retrieved item
- `wiki_integration.py` — Sophimatic frontmatter for wiki pages (importance, disposition, temporal status)
- `memory_manager.py` — auto-managed behavioral memory layer
- `memory_scoring.py` — SMS computation and session-type classification
- `memory_tiers.py` — four-tier memory architecture with promotion/demotion
- `nightly_loop.py` — the orchestrator that runs the Dreaming consolidation
- `session_logger.py` — JSONL capture of every exchange

The chat pipeline (Stage 1 reasoning, Stage 2 prose, cascade, retrieval, intent routing) is in `backend/main.py`. The Dreaming Protocol lives in `backend/dreaming/`. The frontend is in `src/`.

If you want to see a specific behavior, the fastest path is to grep for it in `main.py` and follow the imports.

## Contact

Michael Bouchard · Pauper King LLC
[MichaelCBouchard.com](https://michaelcbouchard.com)
