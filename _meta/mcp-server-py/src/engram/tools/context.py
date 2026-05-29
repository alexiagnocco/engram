"""vault_context tool — pre-session context loader."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from engram.scoring.relevance import match_score

if TYPE_CHECKING:
    from engram.config import Settings
    from engram.state.manifest_cache import ManifestCache


def build_context_response(
    cache: ManifestCache,
    settings: Settings,
    *,
    project: str = "",
    domain: str = "",
    query: str = "",
    max_results: int = 10,
    slim: bool = True,
) -> str:
    manifest = cache.load()
    if manifest.error:
        return manifest.error

    seen: set[str] = set()
    context_notes: list[Any] = []

    def add_note(n: Any) -> None:
        if n.path not in seen:
            seen.add(n.path)
            context_notes.append(n)

    project_memory: dict[str, Any] | None = None
    if project:
        mem_path = f"memory/projects/{project}.md"
        full_mem = (settings.vault_path / mem_path).resolve()
        if not full_mem.is_relative_to(settings.vault_path.resolve()):
            return json.dumps({"error": "Invalid project slug"})
        if full_mem.exists():
            try:
                content = full_mem.read_text(encoding="utf-8")
                excerpt = 2000 if slim else 10000
                project_memory = {
                    "path": mem_path,
                    "exists": True,
                    "recent_content": content[-excerpt:],
                }
            except Exception:
                project_memory = {"path": mem_path, "exists": False}
        else:
            project_memory = {"path": mem_path, "exists": False}

        for n in manifest.notes:
            if match_score(n, "", project) > 0:
                add_note(n)

    if domain:
        for n in manifest.notes:
            if n.domain == domain:
                add_note(n)

    if query:
        for n in manifest.notes:
            if match_score(n, query, "") > 0:
                add_note(n)

    context_notes.sort(key=lambda n: n.updated or "", reverse=True)
    capped = context_notes[:max_results]

    cutoff_7d = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%d")
    recent_count = len([n for n in manifest.notes if (n.updated or "") >= cutoff_7d])
    inbox_count = len([n for n in manifest.notes if n.path.startswith("00-inbox/")])

    if slim:
        context_output = [
            {"path": n.path, "title": n.title, "updated": n.updated, "status": n.status}
            for n in capped
        ]
    else:
        from engram.model.note import note_to_dict

        context_output = [note_to_dict(n) for n in capped]

    result: dict[str, Any] = {
        "project_memory": project_memory,
        "context_notes": context_output,
        "context_count": len(capped),
        "recent_activity_7d": recent_count,
        "inbox_count": inbox_count,
        "nudge": f"Inbox has {inbox_count} items — consider /process-inbox"
        if inbox_count > 5
        else None,
    }

    return json.dumps(result, indent=2)
