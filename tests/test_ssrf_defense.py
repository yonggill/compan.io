import pytest

from companio.tools.web import WebFetchTool


@pytest.fixture
def fetch_tool():
    return WebFetchTool()


class TestSSRFDefense:
    @pytest.mark.asyncio
    async def test_blocks_localhost(self, fetch_tool):
        result = await fetch_tool.execute(url="http://127.0.0.1/admin")
        assert (
            "error" in result.lower() or "blocked" in result.lower() or "internal" in result.lower()
        )

    @pytest.mark.asyncio
    async def test_blocks_private_10(self, fetch_tool):
        result = await fetch_tool.execute(url="http://10.0.0.1/secret")
        assert (
            "error" in result.lower() or "blocked" in result.lower() or "internal" in result.lower()
        )

    @pytest.mark.asyncio
    async def test_blocks_metadata(self, fetch_tool):
        result = await fetch_tool.execute(url="http://169.254.169.254/latest/meta-data/")
        assert (
            "error" in result.lower() or "blocked" in result.lower() or "internal" in result.lower()
        )
