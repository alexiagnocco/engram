---
name: readme
description: >
  Generate a comprehensive, research-backed README.md for any project by analyzing the codebase.
  Adapts structure and emphasis based on project type: library, application, CLI tool, MCP server,
  monorepo, or internal project. Use this skill whenever the user wants to create, generate, write,
  update, or improve a project README -- even if they say "add documentation," "make this repo
  presentable," "document this project," or "help onboard new developers to this codebase."
---

# /readme -- Project README Generator

Analyze the codebase, classify the project, generate a README.md. The output should look professional when rendered on GitHub -- no broken formatting.

```
/readme                      # Analyze pwd, generate README.md
/readme --type library       # Override detected project type
/readme --audience internal  # Force internal-team README
/readme --update             # Update existing README, preserve custom sections
```

## Hard Rules (violating any of these is a bug)

These rules exist because every single one failed in testing. They are not suggestions.

1. **Every fenced code block MUST have a language tag.** No exceptions. Use `bash` for shell commands, `json` for config, `yaml` for frontmatter, `text` for plain output, `markdown` for markdown examples. A bare ` ``` ` with no language is never acceptable. Directory trees get `text`. If you're unsure, use `text`.

2. **The short description (first paragraph after the H1 title) MUST be under 120 characters.** Count them. If it's over 120, shorten it. Move detail to the long description paragraph below. Example of too long (140 chars): "A one-click workspace bootstrap CLI that provisions database connectivity, secret management, and editor extensions for new engineers." Fixed (62 chars): "One-click workspace bootstrap CLI for new engineers."

3. **Heading hierarchy must never skip levels.** H1 -> H2 -> H3 is fine. H1 -> H3 or H2 -> H4 is broken. Every heading level must be used in order.

4. **Internal projects (no LICENSE file) MUST NOT have a License section.** If there's no LICENSE file in the repo, omit the License section entirely. Don't add "Proprietary" or "Internal use only" -- just leave it out.

5. **Mermaid node labels must not use `<br/>` tags.** Many renderers outside GitHub choke on HTML inside Mermaid. Use short single-line labels instead. If a label needs two concepts, split into two nodes connected by an edge.

6. **ASCII only in prose.** Never use em dashes (the long dash, U+2014), right arrows (U+2192), or other non-ASCII punctuation. They render as mojibake on Windows terminals and many viewers. Use `--` for dashes, `->` for arrows. The only exception: box-drawing characters inside `text` code blocks for directory trees are acceptable because they're inside code blocks where encoding is handled.

7. **Never invent features.** Only document what you verify exists in the code. If you can't determine something (URL, screenshot), use `[TODO: description]`.

8. **Use the project's actual commands.** Read package.json scripts, Makefile, pyproject.toml. Don't guess `npm start` -- check what the project actually uses.

## Before You Write: Verify These Formatting Rules

After drafting the README in memory and before writing to disk, mentally audit:
- Count the characters in your short description -- is it under 120?
- Scan every ` ``` ` -- does each one have a language tag?
- Check heading levels -- do they go 1->2->3 in order with no skips?
- Is there a License section? Should there be? (Only if LICENSE file exists)
- Any Mermaid blocks? Do they avoid `<br/>` tags?
- Any non-ASCII characters outside of code blocks? Replace `--` with `--`, `->` with `->`

If any check fails, fix it before writing.

## Codebase Analysis

Read the project to understand what you're documenting. Be targeted -- don't load every file.

**What to check:**

| Signal | What to Read |
|---|---|
| Language & build | `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, file extensions |
| Entry points | `main`, `bin`, `src/index`, CLI entry, `app.py` |
| CI/CD | `.github/workflows/`, `.gitlab-ci.yml` |
| Tests | `test/`, `tests/`, `__tests__/` |
| License | `LICENSE` file -- presence determines audience |
| Existing README | `README.md` -- preserve custom content on `--update` |
| Config | `.env.example`, env var usage in code |

**Classify the project type:**

| Type | Key Signals |
|---|---|
| Library | `main`/`exports` in package.json, `setup.py`, published to registry |
| Application | Server files, routes, database config, Docker |
| CLI Tool | `bin` field, argparse/commander/clap usage |
| MCP Server | MCP SDK imports, tool definitions, stdio transport |
| Monorepo | `workspaces`, `packages/`, Turborepo/Nx |
| Internal | No LICENSE, corporate paths, internal URLs |

## Section Selection

Include these sections in order. Skip any marked "skip if" when the condition is true.

1. **Title** -- H1, matches the repo name
2. **Badges** -- shields.io, max 5. *Skip if: internal project with no CI*
3. **Short description** -- one line, under 120 chars. "With [NAME] you can [VERB] [NOUN]."
4. **Long description** -- 2-4 sentences: problem, audience, differentiator
5. **Table of Contents** -- *skip if: README under ~100 lines*
6. **Features** -- bullet list, lead with verbs
7. **Prerequisites** -- runtime versions, required tools
8. **Installation / Getting Started** -- copy-paste commands
9. **Usage** -- real examples with expected output. MCP servers: show config JSON + tool invocations. CLIs: show subcommands with output.
10. **Configuration** -- env vars table (Variable | Description | Default | Required). *Skip if: none*
11. **API / Tool Reference** -- *skip if: not a library or MCP server*
12. **Project Structure** -- annotated directory tree (use `text` language tag)
13. **Architecture** -- Mermaid diagram with short labels, no `<br/>`. *Skip if: trivial project*
14. **Development** -- clone, install deps, run tests, build
15. **Contributing** -- link to CONTRIBUTING.md or inline basics. *Skip if: internal*
16. **Troubleshooting** -- common issues and fixes. *Skip if: nothing to troubleshoot*
17. **License** -- link to LICENSE. *Skip if: no LICENSE file exists*

**MCP Server specifics:** Section 9 (Usage) must include a copy-paste JSON config block for `mcpServers` / VS Code `mcp.json`. Section 11 (Tool Reference) must use this layout:
- Group tools under H3 headings by category (e.g., `### Scanning (3)`)
- Use simple **2-column tables** (Tool | Description) for each category -- no Key Parameters column
- Add a `### Parameter Quick Reference` H3 section at the end with a flat 2-column table (Tool | Parameters)
- Never put tables inside `<details>` blocks -- rendering is broken in many viewers

**Internal project specifics:** Optimize for "new developer, day one." Clone -> install -> configure -> run in under 5 minutes of reading. Include team contact channels. Skip License, Badges, Contributing.

## Writing Quality

- **Tone**: competent colleague explaining their work -- not a textbook, not a chat message
- **Front-load**: first paragraph answers "what does this do and why should I care?"
- **No condescending language**: never write "simply," "just," "easy," "obviously"
- **Code examples**: copy-paste ready, always show expected output, `$` prefix on commands
- **Short paragraphs**: 3-4 lines max. Lists over prose for scannable content
- **GFM alerts**: use `> [!NOTE]` / `> [!WARNING]` / `> [!IMPORTANT]` for critical callouts
- **Collapsible sections**: `<details>`/`<summary>` for verbose text content only. Never put markdown tables inside `<details>` -- they render inconsistently across viewers. If a table is worth including, give it a regular heading.

## After Writing

Report to the user:
- Sections included and skipped (with reasons)
- Any `[TODO]` placeholders that need human input
- Suggested next steps (fill TODOs, test install instructions on clean machine, add a screenshot/demo)
