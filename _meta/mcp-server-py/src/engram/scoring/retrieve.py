"""Hybrid composite-score + dense-vector retrieval with re-ranking.

Two retrieval paths share one entry point:

* **Keyword-only** (no query embedding supplied): the original composite scorer
  — ``match*3 + freshness*2 + connectivity*1`` re-ranked by
  ``zNorm(base) + LAMBDA_UTILITY * zNorm(utility)``. Behavior is unchanged from
  the pre-hybrid implementation, so notes with ``match_score == 0`` are skipped.

* **Hybrid** (a ``query_vector`` and per-note ``note_vectors`` are supplied):
  two stages —

  1. *Candidate generation / fusion.* Every non-archived, in-domain note is a
     candidate (not just keyword matches), so a conceptually relevant note that
     shares no keywords with the query is no longer dropped. Each candidate gets
     a fused stage-1 score ``zNorm(base) + W_DENSE * zNorm(dense_cosine)``. The
     top ``pool`` candidates advance.
  2. *Re-ranking.* Within the pool, the learned MemRL utility signal is folded
     in: ``stage1 + LAMBDA_UTILITY * zNorm(utility)``. The top ``max_results``
     are returned.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engram.scoring.embeddings import cosine
from engram.scoring.relevance import (
    LAMBDA_UTILITY,
    POOL_FLOOR,
    POOL_MULTIPLIER,
    W_DENSE,
    connectivity_score,
    freshness_score,
    match_score,
    retrieval_id,
    round_val,
    utility_score,
    z_norm,
)

if TYPE_CHECKING:
    from engram.model.note import Note
    from engram.state.utility import UtilityScores


def retrieve(
    notes: list[Note],
    scores: UtilityScores,
    *,
    query: str = "",
    project: str = "",
    domain: str = "",
    max_results: int = 10,
    include_archived: bool = False,
    note_vectors: dict[str, list[float]] | None = None,
    query_vector: list[float] | None = None,
    dense_weight: float = W_DENSE,
) -> tuple[list[dict[str, Any]], str, list[str]]:
    """Score, rank, and return the top results with a retrieval ID.

    When ``query_vector`` and ``note_vectors`` are provided the hybrid two-stage
    path runs; otherwise the keyword-only composite path runs.

    Returns (results, retrieval_id, gaps).
    """
    hybrid = bool(query_vector) and bool(note_vectors)
    rid = retrieval_id()

    if hybrid:
        top = _retrieve_hybrid(
            notes,
            scores,
            query=query,
            project=project,
            domain=domain,
            max_results=max_results,
            include_archived=include_archived,
            note_vectors=note_vectors or {},
            query_vector=query_vector or [],
            dense_weight=dense_weight,
        )
    else:
        top = _retrieve_keyword(
            notes,
            scores,
            query=query,
            project=project,
            domain=domain,
            max_results=max_results,
            include_archived=include_archived,
        )

    gaps: list[str] = []
    if query and not top:
        gaps.append(f"No vault content found for '{query}'")
    if project and not any("memory/projects" in str(r["path"]) for r in top):
        gaps.append(f"No project memory found for '{project}'")

    return top, rid, gaps


def _candidate(note: Note, scores: UtilityScores, ms: int) -> dict[str, Any]:
    fs = freshness_score(note.updated or "")
    cs = connectivity_score(note)
    base = ms * 3 + fs * 2 + cs * 1
    util = utility_score(note.path, scores)
    return {
        "path": note.path,
        "title": note.title or note.basename or "",
        "baseScore": base,
        "utility": round_val(util, 3),
        "matchScore": ms,
        "freshnessScore": fs,
        "connectivityScore": cs,
        "updated": note.updated or "",
        "status": note.status or "",
        "inboundLinks": note.inboundCount,
        "isArchived": note.path.startswith("40-archive"),
        "domain": note.domain or "",
        "tags": list(note.tags),
    }


def _eligible(note: Note, *, domain: str, include_archived: bool) -> bool:
    if not include_archived and note.path.startswith("40-archive"):
        return False
    return not (domain and note.domain != domain)


def _retrieve_keyword(
    notes: list[Note],
    scores: UtilityScores,
    *,
    query: str,
    project: str,
    domain: str,
    max_results: int,
    include_archived: bool,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for note in notes:
        if not _eligible(note, domain=domain, include_archived=include_archived):
            continue
        ms = match_score(note, query, project)
        if ms == 0 and (query or project):
            continue
        cand = _candidate(note, scores, ms)
        cand["denseScore"] = 0.0
        cand["mode"] = "keyword"
        candidates.append(cand)

    if candidates:
        z_base = z_norm([float(c["baseScore"]) for c in candidates])
        z_util = z_norm([float(c["utility"]) for c in candidates])
        for i, cand in enumerate(candidates):
            cand["score"] = round_val(z_base[i] + LAMBDA_UTILITY * z_util[i], 4)
        candidates.sort(key=lambda c: float(c["score"]), reverse=True)

    return candidates[:max_results]


def _retrieve_hybrid(
    notes: list[Note],
    scores: UtilityScores,
    *,
    query: str,
    project: str,
    domain: str,
    max_results: int,
    include_archived: bool,
    note_vectors: dict[str, list[float]],
    query_vector: list[float],
    dense_weight: float,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for note in notes:
        if not _eligible(note, domain=domain, include_archived=include_archived):
            continue
        ms = match_score(note, query, project)
        vec = note_vectors.get(note.path)
        dense = cosine(query_vector, vec) if vec else 0.0
        # Stage 1 candidate generation: keep keyword matches AND any note with a
        # dense vector, so zero-keyword-but-semantically-relevant notes survive.
        if ms == 0 and dense <= 0.0:
            continue
        cand = _candidate(note, scores, ms)
        cand["denseScore"] = round_val(dense, 4)
        cand["mode"] = "hybrid"
        candidates.append(cand)

    if not candidates:
        return []

    # Stage 1: fuse z-normalized keyword base with z-normalized dense cosine.
    z_base = z_norm([float(c["baseScore"]) for c in candidates])
    z_dense = z_norm([float(c["denseScore"]) for c in candidates])
    for i, cand in enumerate(candidates):
        cand["stage1Score"] = z_base[i] + dense_weight * z_dense[i]
    candidates.sort(key=lambda c: float(c["stage1Score"]), reverse=True)

    pool_size = max(max_results * POOL_MULTIPLIER, POOL_FLOOR)
    pool = candidates[:pool_size]

    # Stage 2: re-rank the pool with the learned MemRL utility signal.
    z_util = z_norm([float(c["utility"]) for c in pool])
    for i, cand in enumerate(pool):
        cand["score"] = round_val(
            float(cand["stage1Score"]) + LAMBDA_UTILITY * z_util[i], 4
        )
        cand.pop("stage1Score", None)
    pool.sort(key=lambda c: float(c["score"]), reverse=True)

    return pool[:max_results]
