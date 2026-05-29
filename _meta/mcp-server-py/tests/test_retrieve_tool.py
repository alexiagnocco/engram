"""Integration test for build_retrieve_response — the vault_retrieve tool surface.

Exercises the full path: ManifestCache → EmbeddingStore (hashing) → hybrid
retrieve → JSON response, with a disconnected monitor so no MemRL log is written.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from engram.config import Settings
from engram.rest.connection import ConnectionState
from engram.scoring.embeddings import HashingEmbeddingBackend
from engram.state.embedding_store import EmbeddingStore
from engram.state.manifest_cache import ManifestCache
from engram.state.utility import UtilityCache
from engram.tools.retrieve import build_retrieve_response

_MANIFEST = {
    "version": "2.0",
    "generated": "2026-05-28T00:00:00",
    "vault_path": "/tmp/vault",
    "note_count": 3,
    "stats": {},
    "notes": [
        {"path": "git-guide.md", "title": "Git rebase guide", "basename": "git-guide",
         "summary": "how to rebase branches", "updated": "2026-05-20", "inboundCount": 2},
        {"path": "sql-notes.md", "title": "SQL notes", "basename": "sql-notes",
         "summary": "query patterns", "updated": "2026-05-20", "inboundCount": 2},
        {"path": "memory/projects/p.md", "title": "Project P", "basename": "p",
         "summary": "git workflow decisions", "updated": "2026-05-20", "inboundCount": 1},
    ],
}


def _write_manifest(vault_path) -> None:
    meta = vault_path / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "vault-manifest.json").write_text(json.dumps(_MANIFEST), encoding="utf-8")


def _settings(vault_path) -> Settings:
    return Settings(
        obsidian_api_key="k",
        vault_path=vault_path,
        engram_embeddings_backend="hashing",
        engram_embeddings_dim=64,
    )


def _disconnected():
    return SimpleNamespace(current_state=ConnectionState.DISCONNECTED)


def test_hybrid_mode_reported(tmp_path) -> None:
    _write_manifest(tmp_path)
    store = EmbeddingStore(tmp_path, HashingEmbeddingBackend(dim=64))
    resp = json.loads(
        build_retrieve_response(
            ManifestCache(tmp_path),
            UtilityCache(tmp_path),
            _settings(tmp_path),
            monitor=_disconnected(),
            embedding_store=store,
            query="git",
            max_results=5,
        )
    )
    assert resp["mode"] == "hybrid"
    assert resp["count"] >= 1
    assert "retrievalId" in resp
    paths = [r["path"] for r in resp["results"]]
    assert "git-guide.md" in paths
    # Embedding cache was written as a side effect.
    assert (tmp_path / "_meta" / "vault-embeddings.json").is_file()


def test_keyword_mode_without_store(tmp_path) -> None:
    _write_manifest(tmp_path)
    resp = json.loads(
        build_retrieve_response(
            ManifestCache(tmp_path),
            UtilityCache(tmp_path),
            _settings(tmp_path),
            monitor=_disconnected(),
            embedding_store=None,
            query="git",
            max_results=5,
        )
    )
    assert resp["mode"] == "keyword"
    assert all(r["mode"] == "keyword" for r in resp["results"])


def test_empty_query_stays_keyword_even_with_store(tmp_path) -> None:
    _write_manifest(tmp_path)
    store = EmbeddingStore(tmp_path, HashingEmbeddingBackend(dim=64))
    resp = json.loads(
        build_retrieve_response(
            ManifestCache(tmp_path),
            UtilityCache(tmp_path),
            _settings(tmp_path),
            monitor=_disconnected(),
            embedding_store=store,
            query="",
            project="p",
            max_results=5,
        )
    )
    # Dense path only activates for text queries.
    assert resp["mode"] == "keyword"
