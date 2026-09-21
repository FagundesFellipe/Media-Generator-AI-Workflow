# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project state

Greenfield. The spec is closed (`docs/spec/v1.md`, 2026-09-16) and the design is documented, but `src/`, `tests/` and `db/` are empty and `main.py` is a stub. **Read `docs/` before implementing anything** — the docs are the source of truth and contain non-obvious constraints:

- `docs/spec/v1.md` — what the product is, deliverables per platform, HITL decision points, memory layers, build order.
- `docs/ARCHITECTURE.md` — C4 views, `core/` component layout, `ContextPack`, Postgres data model, API routes, CLI commands, ADRs.
- `docs/LANGGRAPH_BUILD_REFERENCE/LANGGRAPH_NODES_V1.md` + `.mermaid` — graph topology, state schema with reducers, and the LangGraph rules the design assumes.
- `docs/dev-workflow.md` — step-by-step development workflow, testing patterns, and common tasks during implementation.

Docs are in Portuguese; code identifiers are in English.

## Commands

Toolchain: Python 3.13, `uv` (lockfile committed). Dev deps are in the `dev` dependency group.

```bash
uv sync                          # install (incl. dev group)
uv run python main.py            # run entrypoint
uv run pytest                    # all tests (pytest-asyncio installed)
uv run pytest tests/path/test_x.py::test_name   # single test
uv run ruff check . && uv run ruff format .     # lint / format
uv run pyright                   # type check
uv run langgraph dev             # LangGraph Studio (langgraph-cli); needs a langgraph.json — not yet created
```

Pinned versions matter: `langgraph==1.2.11`, `langchain==1.4.1`, `langchain-openai==1.6.2`, `langgraph-checkpoint-postgres==3.1.2`, `psycopg==3.3.5`. Check Context7 for these versions' APIs rather than assuming older LangGraph/LangChain idioms.

## What this project actually is

Content generation (YouTube / LinkedIn / X from a transcript or `.md`) is only the **example domain**. The real product is: full observability per node, explicit context engineering (per-agent allowlist), and procedural memory that learns from human review and post-publication feedback. Single-user, local, no auth.

**Build order is a hard rule: UI is last.** Sequence: (1) foundation + one linear LI agent end-to-end via CLI, with the real regen loop → (2) `learning_graph` with rule HITL → (3) other platforms/agents + parallel fan-out → (4) web research subgraph → (5) React UI → (6) phase 2. Don't build ahead of this order.

## Architecture essentials

Two LangGraph graphs that **never call each other**; Postgres is the only link:

- `generation_graph` — `ingest_context → memory_loader → [research?] → platform_dispatch → {yt,li,x}_graph (parallel) → review_gate (interrupt) → regen or finalize`. 1 run = 1 `thread_id` in `PostgresSaver`; regen reuses the same thread.
- `learning_graph` — `write_episodic → learning_agent → hitl_rules (interrupt) → apply_rules → resolve_contradictions`. Writes `procedural_rules`; contradictions set the old rule to `contested` (never delete), which triggers a research refresh on the next generation run.

Planned `core/` layout: `graphs/`, `agents/`, `prompts/<agent>/<vN>.md` (versioned, frontmatter with `model_tier`), `context/` (`ContentBrief`, `ContextPack`, per-agent allowlist `policies.py`), `memory/` (procedural / semantic / episodic / store), `observability/` (`@traced` tracer → `steps` table, cost table, event bus → SSE), `tools/` (OpenRouter is the single LLM gateway; Tavily, Firecrawl, Playwright renderer), `config.py` (model tiers `cheap | image` → model via env).

Invariants that flow from the ADRs:

- **No agent receives the whole state.** Every agent is an `Agent(name, prompt_version, model_tier, output_schema, context_policy)`; it gets only the `ContextPack` keys in its allowlist, and the tracer serializes exactly that pack into `steps.context_pack`.
- **One LLM node = exactly one model call** via `init_chat_model().with_structured_output()`. `create_agent` (tool loop) is only for the `research_*` nodes. This is what makes 1 row per node in `steps` (tokens, cost, latency, prompt hash) meaningful.
- **No procedural rule enters memory without human approval.** `learning_agent` proposes; `interrupt()` decides.
- Code blocks from `.md` are never rewritten by an LLM — they go verbatim into HTML templates rendered to PNG by Playwright.

## LangGraph rules the graph design depends on

From `docs/LANGGRAPH_BUILD_REFERENCE/LANGGRAPH_NODES_V1.md` §4 — violating these causes deadlock, double execution, or a regen that regenerates nothing:

- Platform fan-out is **static** (max 3): three `add_edge("platform_dispatch", "<p>_graph")` calls, **not** `Send`.
- `add_edge([list], target)` is a **barrier** (`NamedBarrierValue`); `add_edge("a", "b")` is an individual edge. Barrier only where every branch always runs in the same wave (`review_gate`, `yt_join`, `r_synth`). Never put a barrier on a branch that may not run.
- Because `review_gate` is a barrier over all three subgraphs, `platform_dispatch` and `regen_dispatch` always route into **all three**; subgraphs that have nothing to do exit through a no-op entry router so the barrier is still satisfied.
- Regen is a **cycle** driven by `regen_targets` in state (the subgraph entry router jumps straight to the rejected artifact's node). Raise `recursion_limit` (~100). `regen_dispatch` rewrites `regen_targets` from scratch; clear `wave="fresh"` and `regen_targets={}` at the end of each regen wave.
- Keys written by parallel subgraphs (`artifacts`, `review`, `regen_targets`) must use a `merge_dict` reducer; `semantic_refresh` uses `operator.or_`. Otherwise `InvalidUpdateError`.
- Multiple concurrent interrupts (LI format, X format, YT face) are resumed with a map: `Command(resume={interrupt_id: decision})`. The API contract `POST /runs/{id}/resume {interrupt_id, decision}` exists because of this — keep it.
- Use explicit `interrupt()` inside nodes, never `HumanInTheLoopMiddleware`. A node that interrupts **re-runs from the top on resume**: call `interrupt()` first, side effects after.
- Subgraphs are compiled `StateGraph`s added as nodes with `checkpointer=False`; parent edges point at the subgraph id, never at internal nodes.
- Every node declares `node`, `model_tier`, `reads`, `writes`, `interrupt`, `idempotente` in its file header and in `@traced(node_name)`.
