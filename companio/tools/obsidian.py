"""Obsidian vault tool via obsidian-cli."""

import asyncio
from pathlib import Path
from typing import Any

from companio.tools.base import Tool


class ObsidianTool(Tool):
    """Tool to interact with Obsidian vaults via obsidian-cli."""

    def __init__(self, vault_path: str):
        self._vault_path = vault_path

    @property
    def name(self) -> str:
        return "obsidian"

    @property
    def description(self) -> str:
        return "Interact with Obsidian vault: search, read, create, and list notes."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "read", "create", "write", "list", "tags"],
                    "description": "Action to perform on the vault",
                },
                "query": {
                    "type": "string",
                    "description": "Search query (for 'search' action)",
                },
                "path": {
                    "type": "string",
                    "description": "Note path relative to vault root (e.g. 'Projects/myproject.md')",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write (for 'create' and 'write' actions)",
                },
                "folder": {
                    "type": "string",
                    "description": "Folder to list (for 'list' action, defaults to vault root)",
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        vault = self._vault_path
        if not vault:
            return "Error: Obsidian vault path not configured. Set tools.obsidian.vaultPath in config.json"

        vault_path = Path(vault).expanduser()
        if not vault_path.exists():
            return f"Error: Vault path does not exist: {vault_path}"

        try:
            if action == "search":
                return await self._search(vault_path, kwargs.get("query", ""))
            elif action == "read":
                return await self._read(vault_path, kwargs.get("path", ""))
            elif action == "create":
                return await self._create(vault_path, kwargs.get("path", ""), kwargs.get("content", ""))
            elif action == "write":
                return await self._write(vault_path, kwargs.get("path", ""), kwargs.get("content", ""))
            elif action == "list":
                return await self._list(vault_path, kwargs.get("folder", ""))
            elif action == "tags":
                return await self._tags(vault_path)
            else:
                return f"Error: Unknown action '{action}'"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    async def _search(self, vault: Path, query: str) -> str:
        if not query:
            return "Error: 'query' is required for search action"
        # Use grep-based search across vault markdown files
        proc = await asyncio.create_subprocess_exec(
            "grep", "-ril", "--include=*.md", query, str(vault),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode == 1:  # grep returns 1 for no matches
            return "No matching notes found."
        if proc.returncode != 0:
            return f"Search error: {stderr.decode('utf-8', errors='replace')}"

        files = stdout.decode("utf-8", errors="replace").strip().split("\n")
        # Make paths relative to vault
        results = []
        for f in files[:50]:  # Limit results
            try:
                rel = Path(f).relative_to(vault)
                results.append(str(rel))
            except ValueError:
                results.append(f)
        return f"Found {len(results)} notes:\n" + "\n".join(f"- {r}" for r in results)

    async def _read(self, vault: Path, path: str) -> str:
        if not path:
            return "Error: 'path' is required for read action"
        note = vault / path
        if not note.exists():
            return f"Error: Note not found: {path}"
        try:
            content = note.read_text(encoding="utf-8")
            if len(content) > 10000:
                content = content[:10000] + f"\n... (truncated, {len(content) - 10000} more chars)"
            return content
        except Exception as e:
            return f"Error reading note: {e}"

    async def _create(self, vault: Path, path: str, content: str) -> str:
        if not path:
            return "Error: 'path' is required for create action"
        note = vault / path
        if note.exists():
            return f"Error: Note already exists: {path}. Use 'write' action to overwrite."
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(content, encoding="utf-8")
        return f"Created note: {path}"

    async def _write(self, vault: Path, path: str, content: str) -> str:
        if not path:
            return "Error: 'path' is required for write action"
        note = vault / path
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(content, encoding="utf-8")
        return f"Written to note: {path}"

    async def _list(self, vault: Path, folder: str) -> str:
        target = vault / folder if folder else vault
        if not target.exists():
            return f"Error: Folder not found: {folder or '(vault root)'}"

        items = []
        for item in sorted(target.iterdir()):
            if item.name.startswith("."):
                continue
            if item.is_dir():
                items.append(f"📁 {item.name}/")
            elif item.suffix == ".md":
                items.append(f"📄 {item.name}")

        if not items:
            return "Empty folder."
        label = folder or "(vault root)"
        return f"Contents of {label}:\n" + "\n".join(items)

    async def _tags(self, vault: Path) -> str:
        """Extract all tags from vault markdown files."""
        proc = await asyncio.create_subprocess_exec(
            "grep", "-roh", "--include=*.md", r"#[a-zA-Z][a-zA-Z0-9_/-]*", str(vault),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        if not stdout:
            return "No tags found."

        tags = {}
        for tag in stdout.decode("utf-8", errors="replace").strip().split("\n"):
            tag = tag.strip()
            if tag:
                tags[tag] = tags.get(tag, 0) + 1

        sorted_tags = sorted(tags.items(), key=lambda x: -x[1])[:100]
        lines = [f"- {tag} ({count})" for tag, count in sorted_tags]
        return f"Tags ({len(sorted_tags)}):\n" + "\n".join(lines)
