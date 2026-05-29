"""MemRL EMA update logic.

Handles utility score updates (EMA) and retrieval logging.
Write operations only fire when REST is CONNECTED to avoid
recording feedback against stale manifest snapshots.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from engram.scoring.relevance import ALPHA, round_val
from engram.state.feedback import append_feedback_log

if TYPE_CHECKING:
    from pathlib import Path

    from engram.state.utility import UtilityCache


def log_retrieval(
    vault_path: Path,
    utility_cache: UtilityCache,
    *,
    retrieval_id: str,
    query: str,
    project: str,
    domain: str,
    surfaced_paths: list[str],
) -> None:
    """Log a retrieval event and bump retrieval counts."""
    now = datetime.now(UTC).isoformat()

    append_feedback_log(vault_path, {
        "event": "retrieval",
        "retrievalId": retrieval_id,
        "timestamp": now,
        "query": query,
        "project": project,
        "domain": domain,
        "surfacedPaths": surfaced_paths,
        "surfacedCount": len(surfaced_paths),
    })

    scores = utility_cache.load()
    for path in surfaced_paths:
        entry = scores.get(path)
        if entry is None:
            from engram.state.utility import UtilityEntry as UE

            scores[path] = UE(utility=0.5, retrievals=1, citations=0, lastUpdated=now)
        else:
            entry.retrievals += 1
            entry.lastUpdated = now
    utility_cache.save(scores)


def update_feedback(
    vault_path: Path,
    utility_cache: UtilityCache,
    *,
    paths: list[str],
    helpful: bool,
    retrieval_id: str = "",
) -> list[dict[str, Any]]:
    """Apply EMA update for feedback. Returns list of {path, oldUtility, newUtility}."""
    now = datetime.now(UTC).isoformat()
    reward = 1.0 if helpful else 0.0
    scores = utility_cache.load()
    updated: list[dict[str, Any]] = []

    for path in paths:
        entry = scores.get(path)
        if entry is None:
            from engram.state.utility import UtilityEntry as UE

            entry = UE(utility=0.5, retrievals=0, citations=0, lastUpdated="")
            scores[path] = entry
        old_util = entry.utility
        entry.utility = round_val((1 - ALPHA) * old_util + ALPHA * reward, 4)
        if helpful:
            entry.citations += 1
        entry.lastUpdated = now
        updated.append({"path": path, "oldUtility": old_util, "newUtility": entry.utility})

    utility_cache.save(scores)

    append_feedback_log(vault_path, {
        "event": "feedback",
        "timestamp": now,
        "retrievalId": retrieval_id,
        "helpful": helpful,
        "paths": paths,
    })

    return updated
