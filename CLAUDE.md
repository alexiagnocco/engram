# Operating Instructions — engram

This file governs how Claude Code operates inside an engram knowledge vault. It is methodology only — no metrics, scan outputs, or data that goes stale (those come from the `engram` MCP tools at run time).

## What this is

A knowledge-compounding system for engineering work. The vault is a PARA-organized store of Markdown notes; the `engram` MCP server gives structured, scored access to it; skills, hooks, and rules make the agent retrieve before acting, persist as it works, and learn what was useful. The goal is *escape velocity* — surfacing the right knowledge faster than it decays (`σ·ρ > δ/100`). *(This compounding model is adapted from [AgentOps · The Science](https://boshu2.github.io/agentops/the-science/); see [CREDITS.md](CREDITS.md).)*

## Non-negotiables

1. **Retrieve before you create.** Before writing a note, making a decision, or starting non-trivial work, search the vault (`vault_retrieve` / `vault_search` or `/recall`). Never start from a blank slate when the vault already knows something.
2. **Persist as you work.** Significant decisions, rationale, rejected alternatives, blockers, and non-obvious fixes go into the vault *as they happen* — not only at the end.
3. **Capture the feedback signal.** When retrieved notes are used, record it (`vault_feedback`). This is the training signal that sharpens future retrieval; skipping it lets the ranker go stale.
4. **Verify before asserting.** Don't compute dates mentally, guess an API's shape, or claim what a tool does without checking the source. A ten-second verification beats a confident error.

## Session protocol

- **Start:** `/boot` — date, health pulse, project context, and a recall pass in one command.
- **End:** `/wrap` — retro, feedback, session-check, handoff, and commit in one command.

## Response conventions

- Reference other notes with Obsidian `[[wikilinks]]`.
- Every substantive piece of knowledge lands in a vault `.md` file, not just the chat.
- End task responses with a short **Recommended Next Steps** section.

## Where knowledge goes

| Knowledge type | Destination |
|---|---|
| Reusable pattern / technique | `30-resources/<domain>/` |
| Project-specific decision | `memory/projects/<project>.md` |
| Cross-domain insight | `30-resources/synthesis/` |
| Bug fix / non-obvious workaround | `30-resources/<domain>/` or the project note |
| Raw capture to triage later | `00-inbox/` |

## The engram MCP tools

Prefer these over raw file reads:

| Tool | Purpose |
|---|---|
| `vault_retrieve` | Hybrid keyword + dense retrieval, re-ranked by MemRL utility |
| `vault_search` | Metadata + text query |
| `vault_read` | Read full note content by path |
| `vault_related` | Bidirectional link-graph neighbors |
| `vault_context` | Pre-session context load for a project/domain |
| `vault_feedback` | Record retrieval helpfulness (the MemRL signal) |
| `vault_health` / `vault_sigma_rho` | Knowledge-health metrics; measured σ/ρ |
| `vault_rebuild` | Rebuild the manifest index |

## Modular rules

Detailed conventions live in `.claude/rules/` and load automatically:

- `vault-architecture.md` — folder structure, naming, linking
- `frontmatter-schema.md` — YAML frontmatter + tag policy
- `knowledge-workflow.md` — the retrieve → persist → extract lifecycle
- `retrieval-order.md` — how to traverse the vault for context
- `nudge-system.md` — proactive maintenance suggestions
- `skills.md` — the slash-command reference
- `subagent-patterns.md` — when and how to fan out to subagents
- `vault-integration.md` — auto read/write protocol from any project directory

## Operating rules

1. Never delete notes — archive to `40-archive/` to preserve the link graph.
2. Always bump the `updated:` field when editing a note.
3. Append to logs and project memory; never overwrite.
4. No orphans — every note should have at least one inbound link.
5. CLAUDE.md holds methodology, never data — data comes from tools at run time.
