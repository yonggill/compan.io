import os

import pytest

from companio.tools.shell import ExecTool


class TestSecretFiltering:
    @pytest.mark.asyncio
    async def test_filters_api_key(self):
        os.environ["ANTHROPIC_API_KEY"] = "sk-test-secret-12345"
        try:
            tool = ExecTool(timeout=10)
            result = await tool.execute(command="env")
            assert "sk-test-secret-12345" not in result
        finally:
            del os.environ["ANTHROPIC_API_KEY"]

    @pytest.mark.asyncio
    async def test_filters_token(self):
        os.environ["TELEGRAM_BOT_TOKEN"] = "123456:ABC-DEF-test"
        try:
            tool = ExecTool(timeout=10)
            result = await tool.execute(command="env")
            assert "123456:ABC-DEF-test" not in result
        finally:
            del os.environ["TELEGRAM_BOT_TOKEN"]

    @pytest.mark.asyncio
    async def test_keeps_safe_vars(self):
        tool = ExecTool(timeout=10)
        result = await tool.execute(command="echo $HOME")
        assert result.strip() != ""
