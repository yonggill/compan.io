"""Tests for the Obsidian vault tool."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from companio.tools.obsidian import ObsidianTool


@pytest.fixture
def vault(tmp_path):
    """Create a temporary vault with sample notes."""
    (tmp_path / "Projects").mkdir()
    (tmp_path / "Daily").mkdir()
    (tmp_path / "Projects" / "companio.md").write_text(
        "# Companio\n\nAI assistant framework.\n\n#project #ai", encoding="utf-8"
    )
    (tmp_path / "Daily" / "2026-03-09.md").write_text(
        "# 2026-03-09\n\n## Tasks\n- Review code\n- Write tests\n\n#daily", encoding="utf-8"
    )
    (tmp_path / "notes.md").write_text("# Quick Notes\n\nSome quick notes here.", encoding="utf-8")
    return tmp_path


@pytest.fixture
def tool(vault):
    return ObsidianTool(vault_path=str(vault))


class TestObsidianTool:
    def test_name(self, tool):
        assert tool.name == "obsidian"

    def test_parameters_has_action(self, tool):
        params = tool.parameters
        assert "action" in params["properties"]
        assert "action" in params["required"]

    @pytest.mark.asyncio
    async def test_search_finds_notes(self, tool):
        result = await tool.execute(action="search", query="companio")
        assert "companio.md" in result.lower()

    @pytest.mark.asyncio
    async def test_search_no_results(self, tool):
        result = await tool.execute(action="search", query="nonexistent_xyz_123")
        assert "no matching" in result.lower()

    @pytest.mark.asyncio
    async def test_search_requires_query(self, tool):
        result = await tool.execute(action="search")
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_read_note(self, tool):
        result = await tool.execute(action="read", path="Projects/companio.md")
        assert "AI assistant framework" in result

    @pytest.mark.asyncio
    async def test_read_missing_note(self, tool):
        result = await tool.execute(action="read", path="nonexistent.md")
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_create_note(self, tool, vault):
        result = await tool.execute(
            action="create", path="new-note.md", content="# New Note\n\nHello!"
        )
        assert "created" in result.lower()
        assert (vault / "new-note.md").read_text(encoding="utf-8") == "# New Note\n\nHello!"

    @pytest.mark.asyncio
    async def test_create_existing_note_fails(self, tool):
        result = await tool.execute(action="create", path="notes.md", content="overwrite")
        assert "already exists" in result.lower()

    @pytest.mark.asyncio
    async def test_write_overwrites(self, tool, vault):
        result = await tool.execute(action="write", path="notes.md", content="Updated content")
        assert "written" in result.lower()
        assert (vault / "notes.md").read_text(encoding="utf-8") == "Updated content"

    @pytest.mark.asyncio
    async def test_list_vault_root(self, tool):
        result = await tool.execute(action="list")
        assert "Daily" in result
        assert "Projects" in result
        assert "notes.md" in result

    @pytest.mark.asyncio
    async def test_list_subfolder(self, tool):
        result = await tool.execute(action="list", folder="Projects")
        assert "companio.md" in result

    @pytest.mark.asyncio
    async def test_list_missing_folder(self, tool):
        result = await tool.execute(action="list", folder="nonexistent")
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_tags(self, tool):
        result = await tool.execute(action="tags")
        assert "#project" in result
        assert "#daily" in result

    @pytest.mark.asyncio
    async def test_unknown_action(self, tool):
        result = await tool.execute(action="unknown")
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_invalid_vault_path(self):
        tool = ObsidianTool(vault_path="/nonexistent/vault/path")
        result = await tool.execute(action="list")
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_create_nested_folder(self, tool, vault):
        result = await tool.execute(
            action="create", path="New/Nested/Folder/note.md", content="Deep note"
        )
        assert "created" in result.lower()
        assert (vault / "New" / "Nested" / "Folder" / "note.md").exists()


class TestObsidianConfig:
    def test_obsidian_config_defaults(self):
        from companio.config.schema import Config

        config = Config()
        assert config.tools.obsidian.enabled is False
        assert config.tools.obsidian.vault_path == ""
