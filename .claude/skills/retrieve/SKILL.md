---
name: retrieve
description: "Composite-scored vault retrieval with MemRL utility weighting. Use when the user says 'retrieve', 'smart search', or 'scored retrieval'. For general vault lookups, prefer /recall instead."
---

# /retrieve — Smart Retrieval

Retrieve vault notes ranked by composite score: text match, freshness, link connectivity, and MemRL utility. This is the scoring engine behind `/recall`, exposed as a standalone tool.

## Usage

`/retrieve <query>` · `/retrieve --project <slug> <query>` · `/retrieve --domain work <query>` · `/retrieve --include-archived`

## Behavior

1. **Query** — Call `vault_retrieve` with the query, optional project/domain filters, and max_results (default 10, respecting the 40% context rule).
2. **Display** — Show results with their composite scores:
   - Path, title, domain, status
   - **Match score**: how well text matches the query
   - **Freshness**: how recently the note was modified
   - **Connectivity**: how well-linked the note is in the graph
   - **Utility**: MemRL learned helpfulness from past feedback
   - **Composite**: final weighted score
3. **Interpret** — Flag interesting patterns:
   - High utility notes = frequently helpful in past sessions
   - High match but low utility = matches text but rarely used (possible tagging issue)
   - High utility but low match = tangentially related but historically valuable

## vs /recall

| Feature | /retrieve | /recall |
|---|---|---|
| Scoring | Composite + MemRL | Full workflow |
| Graph walk | No | Yes (vault_related) |
| Context load | No | Yes (vault_context) |
| Feedback | Ranked by past feedback | Records new feedback |

## MCP Tool

Primary: `vault_retrieve`
