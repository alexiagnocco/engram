from __future__ import annotations

import json
from typing import Any

from engram.config import FallbackMode, Settings
from engram.rest.client import _version_lt
from engram.rest.connection import ConnectionMonitor, ConnectionState


def build_status_response(settings: Settings, monitor: ConnectionMonitor) -> str:
    state = monitor.current_state
    if settings.obsidian_fallback_mode == FallbackMode.FS_ONLY:
        state_label = "DISABLED"
    else:
        state_label = state.value

    result: dict[str, Any] = {
        "state": state_label,
        "plugin_version": monitor.plugin_version or None,
        "obsidian_version": monitor.obsidian_version or None,
        "last_check": monitor.last_check_iso or None,
        "recheck_interval_sec": settings.obsidian_recheck_interval_sec,
        "fallback_mode": settings.obsidian_fallback_mode.value,
        "rest_url": settings.obsidian_rest_url,
        "vault_path": str(settings.vault_path),
        "server_version": "4.0.0",
    }

    if monitor.error_message:
        result["error"] = monitor.error_message

    if state == ConnectionState.CONNECTED:
        min_ver = settings.obsidian_rest_api_version_min
        if monitor.plugin_version and _version_lt(monitor.plugin_version, min_ver):
            result["warning"] = (
                f"Plugin version {monitor.plugin_version} is below minimum {min_ver}"
            )

    return json.dumps(result, indent=2)
