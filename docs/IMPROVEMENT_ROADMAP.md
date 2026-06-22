# Improvement Roadmap — Ontology-Driven GraphRAG for Vietnamese Law

**Date:** 2026-06-20
**Scope:** Engineering and research improvements for the Đất đai (land-law) pipeline, ordered by return on effort. Cost control of the Claude API is treated as a first-class constraint throughout.

---

## 0. Cost Model (why this ordering)

Per-million-token pricing for the models in use:

| Role | Model | Input $/1M | Output $/1M |
|---|---|---:|---:|
| Answer Generator | `claude-sonnet-4-6` | 3.00 | 15.00 |
| Query Planner / Faithfulness judge / Ontology mapper | `claude-haiku-4-5` | 1.00 | 5.00 |

The dominant cost is **answer generation** (Sonnet, large context + long output), multiplied by every evaluation run (N runs × 26+ questions). The optimizations below attack that multiplier directly before anything else.

Two cost mechanisms are already in place and should be preserved: the local prompt-hash cache (`.llm_cache/`, $0 on exact replays) and Anthropic prompt caching of the system prompt (D-15).

---

## Tier A — Low effort, high impact (do first)

### A1. Route evaluation through the Message Batches API (−50% on every eval run)
The Batches API processes standard Messages requests asynchronously at **50% of list price**, supports all features (prompt caching included), and typically completes within an hour. Evaluation is the ideal workload: it is offline, not latency-sensitive, and already a fixed set of independent requests.

- **Plan:** run all local retrieval first (Neo4j/Qdrant, no API), collect every `(system, user)` generation request, submit one batch keyed by `custom_id = question_id`, then reassemble results. The planner (Haiku) calls can be batched the same way, but generation is the 80/20.
- **Impact:** halves the API cost of every full run with no change to outputs.
- **Effort:** ~0.5–1 day. Keep the synchronous path for the demo and single-question debugging.
- **Caveat:** results return unordered — key by `custom_id`, never by position.

### A2. Make caching verifiable and trim-proof
The system prompt is cached via `cache_control: ephemeral`. The real minimum cacheable prefix on Sonnet 4.6 is **2048 tokens, not 1024** (the figure recorded in D-15 was wrong; corrected). If a future prompt edit pushes the system prompt below 2048 tokens, caching stops **silently** — no error, just full-price input.

- Add a startup/CI check that token-counts the system prompt (via `client.messages.count_tokens`, which is free) and warns below ~2200 tokens.
- Log `usage.cache_read_input_tokens` per call; if it is zero across a batch, a silent cache invalidator is present.
- **Effort:** ~1 hour. **Impact:** protects the ~90% input-cost saving the project already depends on.

### A3. Tiered faithfulness by default
Faithfulness Tier 2 invokes the Haiku judge and adds cost to every run. Tier 1 (existence check) is deterministic and $0.

- Default routine runs to `--faithfulness-tier 1`; reserve Tier 2 for the final report run only.
- If Tier 2 currently issues one judge call per citation, consolidate to **one call per question** (judge all of a question's citations together) and cache the rubric. Fewer requests, lower cost, same signal.
- **Effort:** ~0.5 day. **Impact:** removes Haiku judge cost from the inner development loop.

### A4. Formalize an N=1 development cadence vs N=3 reporting cadence
LLM stochasticity (P-09) justifies N=3 only for the numbers that go into the thesis. Paying 3× the API cost on every exploratory iteration is wasteful.

- Add a `--quick` profile (N=1, local cache on) for iteration and a `--report` profile (N=3, `--no-llm-cache`) for publishable figures.
- **Effort:** a small flag. **Impact:** ~3× cost reduction on routine iterations.

---

## Tier B — Medium effort, high impact

### B1. Local cross-encoder re-ranking for the documented retrieval limitation
Q022 (and its class) is the one unresolved failure: BGE-M3 cannot disambiguate articles that share a label prefix (P-08, D-12). A cross-encoder re-ranker (e.g. `BAAI/bge-reranker-v2-m3`) scores `(question, candidate)` pairs jointly and resolves exactly this case.

- Run it **locally** (same MPS path as BGE-M3) over the dense candidate pool, before the 4-pass allocation. **Inference cost is $0** — no Claude API involved.
- The rejected label-keyword helpers (kept inactive in `semantic_filter.py`) can be removed once this lands.
- **Effort:** ~1–2 days. **Impact:** targets the single worst failure case and a concrete thesis "future work → done" story, at no API cost.

### B2. Close the multi-domain gap (Hộ tịch + Nuôi con nuôi)
Gap 1 ("multi-domain") is currently argued on Đất đai alone. The thesis claim is only fully supported once the pipeline is evaluated across the other two domains.

- Extend the test set and `data/raw/` coverage once teammate B's data lands; re-run the same metrics cross-domain.
- **Effort:** depends on upstream data (teammate B). **Impact:** converts the headline scientific claim from partially to fully evidenced. This is the largest *research* gap, distinct from the *engineering* items above.

### B3. Context-size sweep for the generator
Context is capped at 6000 tokens and output at 3000 — together the dominant Sonnet cost. The 4-pass allocation already caps per-norm/per-tier, so much of the tail context may not change the answer.

- Sweep context cap (e.g. 3000 / 4500 / 6000) against F1 to find the knee. If F1 is flat below 6000, the smaller cap is a permanent per-call input saving with no quality loss.
- **Effort:** one parameterized run set (use the A1 batch path to keep it cheap). **Impact:** recurring input-token reduction on every generation.

---

## Tier C — Creative / higher-effort (later)

### C1. Replace the Query Planner LLM with a local classifier
The planner emits a constrained JSON object (theme/procedure/jurisdiction/temporal/response_mode). It already has a regex backfill ("Cách C") and a disk cache. A small local model — or a rules-plus-embedding classifier — could remove the Haiku dependency from the hot path entirely ($0 planner cost, no 529 exposure).

- **Effort:** medium. **Impact:** eliminates one API dependency; modest direct cost saving (Haiku is cheap) but improves robustness and offline reproducibility.

### C2. Embedding pre-filter ahead of the LLM faithfulness judge
Before calling the Haiku judge (Tier 2), score each citation's text against its supporting chunk with BGE similarity (local, $0). Auto-pass high-similarity citations and only send genuinely borderline ones to the judge — a cheap "Tier 1.5" that shrinks the judge's request volume.

### C3. Cache pre-warming for the live demo
For weekly demos, send a `max_tokens: 0` request at startup to write the system-prompt cache, so the first real question does not pay the cold-cache latency. Negligible cost, smoother demo.

### C4. Temporal versioning depth (Gap 4 showcase)
Per D-03, only current CTV snapshots exist. Adding 2–3 historical CTV versions for a few articles would let the demo show genuine point-in-time evolution rather than amendment metadata alone — strengthening the Gap 4 narrative that is already the strongest differentiator.

---

## Suggested sequence

1. **A2 + A4** (hours): make caching safe and stop overpaying on iterations.
2. **A1** (half-day): the headline 50% cost cut on evaluation.
3. **A3** (half-day): take the judge out of the inner loop.
4. **B1** (1–2 days): fix the documented retrieval limitation at $0 inference.
5. **B3** (one run set): trim generation tokens with evidence.
6. **B2** when teammate B's data is ready: close the multi-domain research gap.
7. **Tier C** opportunistically.

Items A1–A4 and B1/B3 require no additional Claude spend to *implement* and reduce ongoing spend; B2 is the principal research deliverable; Tier C is exploratory.
