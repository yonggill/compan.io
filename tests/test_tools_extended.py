import pytest
from companio.tools.base import Tool
from companio.tools.registry import ToolRegistry


class NumberTool(Tool):
    @property
    def name(self): return "add"
    @property
    def description(self): return "Add two numbers"
    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        }
    async def execute(self, a: int = 0, b: int = 0, **kwargs) -> str:
        return str(a + b)


class TestToolCasting:
    def test_cast_string_to_int(self):
        tool = NumberTool()
        params = tool.cast_params({"a": "5", "b": "3"})
        assert params["a"] == 5
        assert params["b"] == 3

    def test_cast_preserves_correct_types(self):
        tool = NumberTool()
        params = tool.cast_params({"a": 5, "b": 3})
        assert params["a"] == 5

    def test_validate_wrong_type(self):
        tool = NumberTool()
        errors = tool.validate_params({"a": "not_a_number", "b": 3})
        assert len(errors) > 0


class TestToolRegistryExtended:
    @pytest.mark.asyncio
    async def test_register_unregister(self):
        reg = ToolRegistry()
        reg.register(NumberTool())
        assert reg.has("add")
        assert len(reg) == 1
        reg.unregister("add")
        assert not reg.has("add")
        assert len(reg) == 0

    @pytest.mark.asyncio
    async def test_execute_with_casting(self):
        reg = ToolRegistry()
        reg.register(NumberTool())
        result = await reg.execute("add", {"a": "10", "b": "20"})
        assert result == "30"

    @pytest.mark.asyncio
    async def test_execute_validation_error(self):
        reg = ToolRegistry()
        reg.register(NumberTool())
        result = await reg.execute("add", {"a": 5})  # missing required 'b'
        assert "error" in result.lower()

    def test_contains(self):
        reg = ToolRegistry()
        reg.register(NumberTool())
        assert "add" in reg
        assert "subtract" not in reg
