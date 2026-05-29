# engram

**A knowledge-compounding engine for engineering work, built as a set of Claude Code customization layers.**

Engram turns an AI coding agent's transient context into a durable, self-improving knowledge base. It pairs a Python MCP server that does **hybrid retrieval with a reinforcement-learning feedback loop** with a layered stack of skills, hooks, rules, and subagents that make an agent *retrieve before it acts, persist as it works, and learn what was actually useful*.

The thesis in one line:

> A knowledge base compounds only when it surfaces the right things faster than it forgets them: **σ · ρ > δ / 100**.

- **σ** — retrieval *coverage*: how much of what you know you actually surface.
- **ρ** — retrieval *precision*: how useful what you surface turns out to be.
- **δ** — *decay*: how fast unused knowledge goes stale.

When `σ·ρ` exceeds `δ/100`, the system is above *escape velocity* — it accumulates useful, retrievable knowledge faster than it loses it. Every layer in engram exists to push one of those terms in the right direction.

---

## The engineering centerpiece

The retrieval engine (`vault_retrieve`) is a **two-stage hybrid ranker with a learned utility signal**:

1. **Fusion / candidacy.** Every eligible note is scored two ways at once — a keyword composite (`match·3 + freshness·2 + connectivity·1`) and dense-vector cosine similarity against a query embedding — then ranked by `zNorm(keyword) + W_DENSE · zNorm(dense)`. Because candidacy no longer requires a keyword hit, a *conceptually* relevant note with zero shared keywords still surfaces.
2. **MemRL re-ranking.** The top pool is re-ranked by a **reinforcement-learning utility signal**: `+ LAMBDA_UTILITY · zNorm(utility)`. Every time a retrieved note is later *cited* in the work, its utility is rewarded; when it's surfaced but ignored, it isn't. Utility is tracked as an exponential moving average (`α = 0.3`) per note, so the ranker continuously learns which notes are actually worth surfacing — not just which ones match the words.

This is the loop that makes the system *compound*: retrieval feeds work, work emits a feedback signal, and the signal sharpens the next retrieval. `vault_feedback` records the reward; `vault_sigma_rho` reads the accumulated feedback back out as measured coverage/precision; `vault_health` reports whether the whole system is above escape velocity.

Embeddings are pluggable: a dependency-free **hashing** backend (deterministic SHA-1 feature hashing, always available) or a **semantic ONNX** backend (a real sentence-transformer via `onnxruntime`). Per-note vectors are cached incrementally and keyed by content hash, so only changed notes re-embed.

---

## Architecture

Four composable customization layers, plus the data substrate they operate on.

```text
┌─────────────────────────────────────────────────────────────┐
│  Skills (21)   slash-command workflows: /boot /recall /wrap … │
│  Hooks (14)    deterministic lifecycle automation             │
│  Rules (8)     always-on behavioral conventions               │
│  Agents (2)    subagent orchestration (plan, research)        │
└───────────────┬─────────────────────────────────────────────┘
                │ all read/write through
        ┌───────▼────────┐
        │  engram MCP     │   23 tools — Python / FastMCP
        │  server         │   hybrid retrieval · MemRL · health
        └───────┬────────┘
                │ operates on
        ┌───────▼────────┐
        │  the vault      │   a PARA-organized store of Markdown notes
        └────────────────┘
```

| Layer | What it is | Why it's separate |
|---|---|---|
| **MCP server** (`_meta/mcp-server-py/`) | A 23-tool Python [FastMCP](https://github.com/jlowin/fastmcp) server: retrieval, link-graph, knowledge-health, and read/write tools. | Access + computation. Portable across any MCP client. |
| **Skills** (`.claude/skills/`) | Slash-command workflows (`/boot`, `/recall`, `/evolve`, `/wrap`, …) that compose the MCP tools into runbooks. | Teach the agent *how* to use the tools consistently. |
| **Hooks** (`.claude/hooks/`) | Shell scripts wired to lifecycle events (`PreToolUse`, `PostToolUse`, `Stop`, …). | Enforcement that happens *regardless* of what the model decides — e.g. blocking `rm` of an active note. |
| **Rules** (`.claude/rules/`) | Always-loaded behavioral conventions (retrieval order, frontmatter schema, nudge system). | Shape default behavior without a slash command. |
| **Agents** (`.claude/agents/`) | Subagent definitions for context-isolated fan-out (planning, research). | Keep large sub-tasks out of the main context window. |

The MCP server itself is cleanly layered: a **dispatcher** routes each call to a filesystem implementation or the optional Obsidian Local REST API and degrades gracefully when REST is unavailable; a **connection monitor** tracks REST health on a background poll; a **manifest builder** maintains a metadata + link-graph index; a **scoring** package holds the retrieval math, embedding backends, MemRL utility, and the health equation; and a **state** layer handles incremental embedding/utility caches with atomic writes. See [`_meta/mcp-server-py/README.md`](_meta/mcp-server-py/README.md) for the module-level tour.

---

## The MCP tools (23)

```text
Read / search   vault_status  vault_search  vault_read  vault_recent
                vault_related  vault_manifest  vault_rebuild
                vault_document_map  vault_tags  vault_active
Retrieval +     vault_retrieve  vault_health  vault_context
knowledge       vault_session_check  vault_feedback  vault_sigma_rho
health          vault_prune_dryrun  vault_unmined_sessions
Write           vault_checkpoint  vault_patch  vault_periodic
                vault_command  vault_open
```

## The skills (21)

| Group | Skills |
|---|---|
| Session lifecycle | `boot` · `wrap` · `handoff` |
| Retrieval & feedback | `recall` · `retrieve` · `feedback` · `sigma-rho` |
| Knowledge health | `health` · `health-check` · `prune` · `link-repair` |
| Intelligence & evolution | `evolve` · `connect` · `think-deep` · `weekly-review` |
| Capture | `new-note` · `retro` · `mine-sessions` |
| Engineering | `frame` · `execute` · `readme` |

`evolve` is the self-improving core: it audits whether learnings captured in memory have actually propagated into the operational surfaces (skills, rules, hooks) that govern behavior — closing the loop between "we learned this" and "the agent now does this."

---

## Quick start

```bash
# 1. Install the MCP server (Python 3.12 + uv)
cd _meta/mcp-server-py
uv sync --extra dev
uv run pytest -q          # 68 tests

# 2. Point engram at your knowledge vault (defaults to ~/vault)
export VAULT_PATH="$(git rev-parse --show-toplevel)"   # e.g. this repo

# 3. Register the server with Claude Code
#    .mcp.json in the repo root already declares the `engram` server.
#    Open the repo in Claude Code and the 23 tools load automatically.
```

The server runs **filesystem-first** — no external services required. To enable live two-way sync with Obsidian, install the [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) plugin and set `OBSIDIAN_API_KEY` (or store it in the OS keyring under service `engram`). To enable the semantic embedding backend:

```bash
cd _meta/mcp-server-py
uv sync --extra embeddings
uv run --extra embeddings python scripts/fetch-embedding-model.py
export ENGRAM_EMBEDDINGS_BACKEND=onnx
export ENGRAM_EMBEDDINGS_MODEL_DIR=$PWD/models/all-MiniLM-L6-v2
```

---

## Repository layout

```text
engram/
├── .claude/
│   ├── skills/        21 slash-command workflows (+ an eval harness)
│   ├── hooks/         14 lifecycle automation scripts
│   ├── rules/         8 always-on behavioral rules
│   ├── agents/        2 subagent definitions
│   └── settings.json  wires hooks to lifecycle events
├── _meta/
│   ├── mcp-server-py/ the engram MCP server (Python / FastMCP, 68 tests)
│   └── scripts/       standalone vault utilities
├── 00-inbox/ … 50-maps/   the PARA knowledge vault (empty scaffold here)
├── memory/            project memory, glossary, contacts (empty scaffold)
├── .mcp.json          MCP server registration
├── CLAUDE.md          operating instructions for the agent
├── STRUCTURE.md       the vault layout + customization layers, explained
└── EXAMPLES.md        end-to-end session walkthroughs
```

This repository is the **foundation scaffold** — the engine and the customization layers, with the PARA folders empty. Point engram at a vault that has real notes and the retrieval, feedback, and health loops come alive.

## Skill evaluation

Skills are tuned against graded before/after benchmarks, not vibes. [`.claude/skills/execute-workspace/`](.claude/skills/execute-workspace/) contains a runnable harness that scores the `/execute` skill across three scenarios (ambiguous scope, over-engineering bait, a security refactor) with and without the skill loaded, so regressions in skill quality are measurable.

## License

[MIT](LICENSE).
