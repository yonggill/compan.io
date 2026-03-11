---
name: obsidian
description: Manage Obsidian vault notes — search, read, create, and organize documents.
---

# Obsidian Vault Tool

## Overview

The `obsidian` tool provides direct access to an Obsidian vault for searching, reading, creating, and organizing markdown notes. It requires `tools.obsidian.vaultPath` to be configured in `config.json`.

## Setup

Add the following to your `config.json`:

```json
{
  "tools": {
    "obsidian": {
      "enabled": true,
      "vaultPath": "~/Documents/Obsidian/MyVault"
    }
  }
}
```

## Actions

### `search` — Full-text search across all notes
Searches all `.md` files in the vault for the given query string (case-insensitive). Returns a list of matching note paths.
- **Requires:** `query`

### `read` — Read a note's content
Reads and returns the full content of a note. Truncates at 10,000 characters for very large notes.
- **Requires:** `path`

### `create` — Create a new note
Creates a new note at the specified path. Fails if the note already exists (use `write` to overwrite).
- **Requires:** `path`
- **Optional:** `content`

### `write` — Create or overwrite a note
Writes content to a note, creating it if it doesn't exist or overwriting if it does.
- **Requires:** `path`
- **Optional:** `content`

### `list` — List files in a folder
Lists all markdown files and subdirectories in a folder. Hidden files (starting with `.`) are excluded.
- **Optional:** `folder` (defaults to vault root)

### `tags` — List all tags with counts
Scans all markdown files and extracts tags (e.g., `#project`, `#todo`), returning them sorted by frequency.

## Examples

```
obsidian(action="search", query="meeting notes")
obsidian(action="read", path="Projects/companio.md")
obsidian(action="create", path="Daily/2026-03-09.md", content="# 2026-03-09\n\n## Tasks\n- ...")
obsidian(action="write", path="Projects/companio.md", content="# Companio\n\nUpdated content...")
obsidian(action="list", folder="Projects")
obsidian(action="tags")
```

## Best Practices

- Use `search` before creating notes to avoid duplicates.
- Use meaningful folder structure (e.g., `Daily/`, `Projects/`, `References/`).
- Include YAML frontmatter in notes for metadata (e.g., tags, date, status).
- Use tags (`#tag`) for cross-cutting categorization across folders.
- Paths are always relative to the vault root and should include the `.md` extension.
