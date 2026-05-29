---
description: Automatic vault integration protocol for reading and writing vault context from any project directory
---

# Vault Integration Protocol

The vault at `~/vault/` (override with the `VAULT_PATH` env var) is a persistent knowledge layer. When working in any project directory, Claude automatically consults and updates the vault without being asked.

## Automatic Vault Reads

### On Session Start

1. **Project memory**: Read ~/vault/memory/projects/<project-name>.md where <project-name> matches the current project directory name. Use `vault_read` or Read tool.
2. **Glossary**: Use `vault_search` for terms relevant to the project's domain.
3. **Context load**: Use `vault_context` MCP tool for composite pre-session loading (project memory + domain search + recent activity + inbox nudge).
4. **Recall**: The `/recall` skill orchestrates this — prefer it over manual steps.

### During Work

- **Unfamiliar term/acronym**: vault_search for the term
- **Architectural decision needed**: Search for prior ADRs, patterns, decisions
- **Before creating anything**: Check vault for existing notes on the topic
- **Before citing facts about tools, APIs, or dates**: Verify against the actual source (read the file, call the API, use a date tool). Never compute day-of-week mentally. Never assert what tools a team "uses" without checking the vault or project memory.

### Project-to-Vault Mapping

Convention: directory name maps to vault memory file.
- `~/projects/acme-api/` → `~/vault/memory/projects/acme-api.md`
- `~/projects/data-pipeline/` → `~/vault/memory/projects/data-pipeline.md`
- Fallback: vault_search by project name

### MCP Tools (engram)

The engram MCP server provides structured vault access. Prefer these over raw file reads:

| Tool | Purpose |
|------|---------|
| `vault_search` | Find notes by metadata and/or text query |
| `vault_read` | Read full content of specific notes by path |
| `vault_retrieve` | Hybrid retrieval: keyword composite (match + freshness + connectivity) fused with dense-vector cosine, then re-ranked by MemRL utility |
| `vault_recent` | Notes modified in last N days, optional domain filter |
| `vault_related` | Bidirectional link graph neighbors for a note |
| `vault_context` | Pre-session context loader (project memory + domain + recent + inbox) |
| `vault_health` | Knowledge health metrics (sigma, rho, delta, phi, escape velocity) |
| `vault_session_check` | Post-session validation (new notes, orphans, frontmatter, project memory) |
| `vault_feedback` | Record helpful/not-helpful feedback for MemRL utility scoring |
| `vault_sigma_rho` | Compute true sigma/rho from accumulated feedback data |
| `vault_rebuild` | Trigger manifest rebuild |
| `vault_unmined_sessions` | Find sessions not yet mined for knowledge |

### Token Efficiency

- Use targeted `vault_search`, not `vault_manifest`
- Never load the full manifest for project sessions
- Read frontmatter + first section, not full notes
- Lazy loading: don't fetch until needed

## Automatic Vault Writes

### When to Write

| Trigger | What to Write | Where |
|---------|--------------|-------|
| Significant decision made | Decision + rationale | ~/vault/memory/projects/<project>.md |
| Milestone completed | Status/progress update | ~/vault/memory/projects/<project>.md |
| Measurable accomplishment | Win + context + metrics | ~/vault/20-areas/accomplishments-log.md |
| New term/acronym learned | Definition | ~/vault/memory/glossary.md |
| New person encountered | Profile | ~/vault/memory/people/<name>.md |
| Reusable pattern discovered | Resource note | ~/vault/30-resources/<domain>/ or 00-inbox/ |
| Non-obvious bug root cause | Documentation | ~/vault/30-resources/<domain>/ |
| Session ending (substantive work done) | Session handoff | Use `/handoff` skill |
| Rate limit / context overflow | Session handoff | ~/vault/00-inbox/session-handoff.md |

### Write Rules

- All vault paths MUST be absolute (~/vault/...)
- Always update updated: frontmatter when modifying existing notes
- Append to existing notes for logs and project memory (never overwrite)
- Batch writes: update when something meaningful happens, not after every response

### Scope Guard

| Context | Write Behavior |
|---------|---------------|
| Working in the vault (~/vault/) | Write per vault operating rules |
| Working in a project | Decisions, milestones, learnings, new terms, accomplishments |
| Debugging / exploring | Only non-obvious patterns or root causes |
| Routine code changes | No vault write needed |

## Frontmatter for New Vault Notes

When creating vault notes from outside the vault:

```yaml
---
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []           # From: backend, data, devops, scripting, git, testing,
                   #   retrieval, mcp, obsidian, ai, meta, synthesis,
                   #   architecture, optimization, automation
status: active     # draft | active | review | done | archived
type: note         # note | project | meeting | decision | reference
domain: work       # work | meta
---
```

When appending to existing notes, update only the updated: field.

## Conflict Avoidance

- Write using absolute paths
- Writes are append-only for logs/memory
- If a vault file has uncommitted changes, append rather than overwrite