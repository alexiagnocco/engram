"""vault_retrieve tool — hybrid composite-score + dense-vector retrieval.

Stage 1 fuses the keyword composite with dense cosine similarity (when an
embedding store is available); stage 2 re-ranks by MemRL utility.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from engram.rest.connection import ConnectionState
from engram.scoring.memrl import log_retrieval
from engram.scoring.retrieve import retrieve

if TYPE_CHECKING:
    from engram.config import Settings
    from engram.rest.connection import ConnectionMonitor
    from engram.state.embedding_store import EmbeddingStore
    from engram.state.manifest_cache import ManifestCache
    from engram.state.utility import UtilityCache

logger = logging.getLogger(__name__)

_MAX_RESULTS_CAP = 100


def build_retrieve_response(
    cache: ManifestCache,
    utility_cache: UtilityCache,
    settings: Settings,
    *,
    monitor: ConnectionMonitor,
    embedding_store: EmbeddingStore | None = None,
    query: str = "",
    project: str = "",
    domain: str = "",
    max_results: int = 10,
    include_archived: bool = False,
) -> str:
    manifest = cache.load()
    if manifest.error:
        return manifest.error

    max_results = min(max_results, _MAX_RESULTS_CAP)

    note_vectors = None
    query_vector = None
    mode = "keyword"
    # Dense retrieval only applies to text queries; project/domain-only browsing
    # stays on the keyword path.
    if embedding_store is not None and query.strip():
        try:
            note_vectors = embedding_store.index(manifest.notes)
            query_vector = embedding_store.embed_query(query)
            mode = "hybrid"
        except Exception as exc:
            logger.warning("Dense retrieval unavailable (%s); keyword-only", exc)
            note_vectors = None
            query_vector = None
            mode = "keyword"

    scores = utility_cache.load()
    top, rid, gaps = retrieve(
        manifest.notes,
        scores,
        query=query,
        project=project,
        domain=domain,
        max_results=max_results,
        include_archived=include_archived,
        note_vectors=note_vectors,
        query_vector=query_vector,
        dense_weight=settings.engram_dense_weight,
    )

    surfaced = [str(c["path"]) for c in top]

    if monitor.current_state == ConnectionState.CONNECTED:
        log_retrieval(
            settings.vault_path,
            utility_cache,
            retrieval_id=rid,
            query=query,
            project=project,
            domain=domain,
            surfaced_paths=surfaced,
        )

    return json.dumps(
        {
            "results": top,
            "count": len(top),
            "mode": mode,
            "gaps": gaps,
            "retrievalId": rid,
        },
        indent=2,
    )
