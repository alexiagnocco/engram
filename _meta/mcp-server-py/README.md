# engram

A [FastMCP](https://github.com/jlowin/fastmcp) MCP server that gives Claude Code
(and any MCP client) structured, persistent access to a local Markdown knowledge
vault. It works directly against the filesystem and can optionally drive the
Obsidian Local REST API for live read/write when Obsidian is running.

- **Stack:** Python 3.12, FastMCP, httpx, pydantic-settings, keyring.
- **Architecture:** REST-first (Obsidian Local REST API) with per-tool FS
  fallback via a `Dispatcher`. A `ConnectionMonitor` tracks REST health.
- **23 tools** spanning search/read, link-graph, knowledge-health (MemRL),
  checkpoints, and REST-only writes (PATCH, periodic notes, commands).

## Install

```bash
uv venv --python 3.12
uv sync --extra dev            # runtime + test/lint/type deps
```

The server is launched via `scripts/launch.sh` (it `unset`s `VIRTUAL_ENV`
before `uv run` to avoid the Claude Code runtime's `/usr` venv warning).

## Configuration

Settings load from environment variables or a `.env` file (see `config.py`).
The API key falls back to the OS keyring (`keyring.get_password("engram",
"obsidian-rest")`).

| Variable | Default | Purpose |
|---|---|---|
| `VAULT_PATH` | `~/vault` | Vault root |
| `OBSIDIAN_REST_URL` | `https://127.0.0.1:27124` | Local REST API base |
| `OBSIDIAN_API_KEY` | — | Bearer token (or via keyring) |
| `OBSIDIAN_FALLBACK_MODE` | `auto` | `auto` \| `rest_only` \| `fs_only` |
| `ENGRAM_EMBEDDINGS_BACKEND` | `auto` | `auto` \| `onnx` \| `hashing` \| `none` |
| `ENGRAM_EMBEDDINGS_MODEL_DIR` | — | Dir with `model.onnx` + `tokenizer.json` |
| `ENGRAM_EMBEDDINGS_DIM` | `256` | Hashing-backend vector dimension |
| `ENGRAM_DENSE_WEIGHT` | `1.0` | Weight of dense vs keyword in fusion |

## Tools

`vault_status`, `vault_search`, `vault_read`, `vault_recent`, `vault_related`,
`vault_manifest`, `vault_rebuild`, `vault_document_map`, `vault_tags`,
`vault_active`, `vault_retrieve`, `vault_health`, `vault_context`,
`vault_session_check`, `vault_feedback`, `vault_sigma_rho`, `vault_prune_dryrun`,
`vault_unmined_sessions`, `vault_checkpoint`, `vault_patch`, `vault_periodic`,
`vault_command`, `vault_open`.

## Hybrid retrieval (`vault_retrieve`)

`vault_retrieve` performs **hybrid composite + dense-vector retrieval with
two-stage re-ranking**:

1. **Fusion / candidate generation.** Every eligible note is scored by both the
   keyword composite (`match·3 + freshness·2 + connectivity·1`) and dense cosine
   similarity, then ranked by `zNorm(keyword) + W_DENSE·zNorm(dense)`. Because
   candidacy no longer requires a keyword match, a conceptually relevant note
   with no shared keywords still surfaces.
2. **Re-ranking.** The top pool is re-ranked with the learned MemRL utility
   signal: `+ LAMBDA_UTILITY·zNorm(utility)`.

The response includes `"mode": "hybrid" | "keyword"`. With no embedding backend
configured (or an empty query) it falls back to the original keyword-only path.

### Embedding backends

| Backend | Dependencies | Notes |
|---|---|---|
| Hashing (default fallback) | none | Deterministic SHA-1 feature hashing. Always available. **Lexical, not semantic.** |
| ONNX | `embeddings` extra | Real sentence-transformer (e.g. all-MiniLM-L6-v2) via onnxruntime. **Semantic.** |

Per-note vectors are cached incrementally in `_meta/vault-embeddings.json`
(gitignored); only changed notes re-embed.

### Enabling the semantic (ONNX) backend

```bash
uv sync --extra embeddings
uv run --extra embeddings python scripts/fetch-embedding-model.py   # downloads MiniLM ONNX
export ENGRAM_EMBEDDINGS_BACKEND=onnx
export ENGRAM_EMBEDDINGS_MODEL_DIR=$PWD/models/all-MiniLM-L6-v2
# restart the server
```

Model weights are provisioned on demand and never committed.

## Development

```bash
uv run ruff check src tests     # lint
uv run mypy                     # strict type check
uv run pytest -q                # tests
```

Tests live in `tests/`. The ONNX backend test runs against a tiny committed
fixture (`tests/fixtures/tiny-onnx/`) and skips when the `embeddings` extra is
not installed.
