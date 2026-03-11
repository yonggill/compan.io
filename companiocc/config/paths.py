"""Runtime path helpers derived from the active config context."""

from __future__ import annotations

from pathlib import Path

from companiocc.config.loader import get_config_path
from companiocc.helpers import ensure_dir


def get_data_dir() -> Path:
    """Return the instance-level runtime data directory."""
    return ensure_dir(get_config_path().parent)


def get_runtime_subdir(name: str) -> Path:
    """Return a named runtime subdirectory under the instance data dir."""
    return ensure_dir(get_data_dir() / name)


def get_media_dir(channel: str | None = None) -> Path:
    """Return the media directory, optionally namespaced per channel."""
    base = get_runtime_subdir("media")
    return ensure_dir(base / channel) if channel else base


def get_cron_dir() -> Path:
    """Return the cron storage directory."""
    return get_runtime_subdir("cron")


def get_logs_dir() -> Path:
    """Return the logs directory."""
    return get_runtime_subdir("logs")


def get_workspace_path(workspace: str | None = None) -> Path:
    """Resolve and ensure the agent workspace path."""
    path = Path(workspace).expanduser() if workspace else Path.home() / ".companiocc" / "workspace"
    return ensure_dir(path)


def get_cli_history_path() -> Path:
    """Return the shared CLI history file path."""
    return Path.home() / ".companiocc" / "history" / "cli_history"



def get_claude_project_dir() -> Path:
    """Return the Claude CLI project directory for companiocc.

    This directory holds CLAUDE.md (system prompt) and is used as cwd
    when spawning Claude CLI, keeping sessions isolated from the user's
    own Claude Code usage.
    """
    return ensure_dir(Path.home() / ".companiocc" / "project")


def get_legacy_sessions_dir() -> Path:
    """Return the legacy global session directory used for migration fallback."""
    return Path.home() / ".companiocc" / "sessions"


def sync_user_mcp_servers() -> bool:
    """Sync user-scope MCP servers from ~/.claude.json to the project directory.

    Claude CLI stores user-scope MCP servers in ~/.claude.json under
    ``mcpServers``.  When companiocc runs ``claude -p`` from its own project
    directory, only project-level ``.mcp.json`` is loaded.  This function
    bridges the gap by copying user-scope servers into the project dir.

    Returns:
        True if .mcp.json was written/updated, False otherwise.
    """
    import json

    claude_json = Path.home() / ".claude.json"
    if not claude_json.exists():
        return False

    try:
        data = json.loads(claude_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    mcp_servers = data.get("mcpServers")
    if not mcp_servers:
        return False

    project_dir = get_claude_project_dir()
    mcp_json_path = project_dir / ".mcp.json"

    # Merge with existing project .mcp.json if present
    existing: dict = {}
    if mcp_json_path.exists():
        try:
            existing = json.loads(mcp_json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    existing_servers = existing.get("mcpServers", {})
    # User-scope servers are added but don't overwrite project-level ones
    merged = {**mcp_servers, **existing_servers}

    new_content = json.dumps({"mcpServers": merged}, indent=2, ensure_ascii=False) + "\n"
    mcp_json_path.write_text(new_content, encoding="utf-8")
    return True
