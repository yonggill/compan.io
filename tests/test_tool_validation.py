import pytest

from companio.tools.base import Tool
from companio.tools.registry import ToolRegistry


class EchoTool(Tool):
    @property
    def name(self):
        return "echo"

    @property
    def description(self):
        return "Echo back the input"

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to echo"},
            },
            "required": ["text"],
        }

    async def execute(self, text: str = "", **kwargs) -> str:
        return text


class TestToolValidation:
    def test_validate_missing_required(self):
        tool = EchoTool()
        errors = tool.validate_params({})
        assert any("missing" in e.lower() or "required" in e.lower() for e in errors)

    def test_validate_valid_params(self):
        tool = EchoTool()
        errors = tool.validate_params({"text": "hello"})
        assert errors == []

    def test_to_schema(self):
        tool = EchoTool()
        schema = tool.to_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "echo"


class TestToolRegistry:
    @pytest.mark.asyncio
    async def test_register_and_execute(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        result = await registry.execute("echo", {"text": "hello"})
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        registry = ToolRegistry()
        result = await registry.execute("nonexistent", {})
        assert "not found" in result.lower() or "error" in result.lower()

    def test_get_definitions(self):
        registry = ToolRegistry()
        registry.register(EchoTool())
        defs = registry.get_definitions()
        assert len(defs) == 1
        assert defs[0]["function"]["name"] == "echo"
