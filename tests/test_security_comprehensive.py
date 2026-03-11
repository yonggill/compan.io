"""Comprehensive security tests for SSRF defense, secret filtering, and workspace restriction."""

import os
from pathlib import Path

import pytest

from companio.tools.filesystem import ReadFileTool, WriteFileTool
from companio.tools.shell import ExecTool
from companio.tools.web import WebFetchTool


class TestSSRFComprehensive:
    @pytest.fixture
    def fetch_tool(self):
        return WebFetchTool()

    @pytest.mark.asyncio
    async def test_blocks_192_168(self, fetch_tool):
        result = await fetch_tool.execute(url="http://192.168.1.1/admin")
        assert "error" in result.lower() or "blocked" in result.lower() or "internal" in result.lower()

    @pytest.mark.asyncio
    async def test_blocks_172_16(self, fetch_tool):
        result = await fetch_tool.execute(url="http://172.16.0.1/internal")
        assert "error" in result.lower() or "blocked" in result.lower() or "internal" in result.lower()

    @pytest.mark.asyncio
    async def test_blocks_zero_ip(self, fetch_tool):
        result = await fetch_tool.execute(url="http://0.0.0.0/")
        assert "error" in result.lower() or "blocked" in result.lower() or "internal" in result.lower()

    @pytest.mark.asyncio
    async def test_valid_url_required(self, fetch_tool):
        result = await fetch_tool.execute(url="not-a-url")
        assert "error" in result.lower()

    @pytest.mark.asyncio
    async def test_ftp_blocked(self, fetch_tool):
        result = await fetch_tool.execute(url="ftp://files.example.com/secret")
        assert "error" in result.lower()


class TestSecretFilteringComprehensive:
    @pytest.mark.asyncio
    async def test_filters_openai_key(self):
        os.environ["OPENAI_API_KEY"] = "sk-openai-test-key-xyz"
        try:
            tool = ExecTool(timeout=10)
            result = await tool.execute(command="env")
            assert "sk-openai-test-key-xyz" not in result
        finally:
            del os.environ["OPENAI_API_KEY"]

    @pytest.mark.asyncio
    async def test_filters_gemini_key(self):
        os.environ["GEMINI_API_KEY"] = "AIzaSy-test-gemini-key"
        try:
            tool = ExecTool(timeout=10)
            result = await tool.execute(command="env")
            assert "AIzaSy-test-gemini-key" not in result
        finally:
            del os.environ["GEMINI_API_KEY"]

    @pytest.mark.asyncio
    async def test_filters_companio_vars(self):
        os.environ["COMPANIO_SECRET_VALUE"] = "super-secret-123"
        try:
            tool = ExecTool(timeout=10)
            result = await tool.execute(command="env")
            assert "super-secret-123" not in result
        finally:
            del os.environ["COMPANIO_SECRET_VALUE"]

    @pytest.mark.asyncio
    async def test_filters_password_vars(self):
        os.environ["DB_PASSWORD"] = "my-db-pass-456"
        try:
            tool = ExecTool(timeout=10)
            result = await tool.execute(command="env")
            assert "my-db-pass-456" not in result
        finally:
            del os.environ["DB_PASSWORD"]

    @pytest.mark.asyncio
    async def test_filters_credential_vars(self):
        os.environ["AWS_CREDENTIAL"] = "aws-cred-789"
        try:
            tool = ExecTool(timeout=10)
            result = await tool.execute(command="env")
            assert "aws-cred-789" not in result
        finally:
            del os.environ["AWS_CREDENTIAL"]


class TestShellSafetyGuards:
    @pytest.mark.asyncio
    async def test_blocks_rm_rf(self):
        tool = ExecTool(timeout=10)
        result = await tool.execute(command="rm -rf /")
        assert "error" in result.lower() or "blocked" in result.lower() or "denied" in result.lower()

    @pytest.mark.asyncio
    async def test_blocks_fork_bomb(self):
        tool = ExecTool(timeout=10)
        result = await tool.execute(command=":(){ :|:& };:")
        assert "error" in result.lower() or "blocked" in result.lower() or "denied" in result.lower()

    @pytest.mark.asyncio
    async def test_basic_command_works(self):
        tool = ExecTool(timeout=10)
        result = await tool.execute(command="echo hello")
        assert "hello" in result


class TestWorkspaceRestriction:
    @pytest.mark.asyncio
    async def test_read_within_workspace(self, tmp_path):
        # Create a test file in workspace
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        tool = ReadFileTool(allowed_dir=tmp_path)
        result = await tool.execute(path=str(test_file))
        assert "hello" in result

    @pytest.mark.asyncio
    async def test_read_outside_workspace_blocked(self, tmp_path):
        tool = ReadFileTool(allowed_dir=tmp_path)
        result = await tool.execute(path="/etc/passwd")
        assert "error" in result.lower() or "permission" in result.lower() or "denied" in result.lower()

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, tmp_path):
        tool = ReadFileTool(allowed_dir=tmp_path)
        result = await tool.execute(path=str(tmp_path / "../../etc/passwd"))
        assert "error" in result.lower() or "permission" in result.lower() or "denied" in result.lower()
