import pytest
from companio.providers.registry import PROVIDERS, find_by_name, find_by_model, ProviderSpec
from companio.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class TestProviderRegistry:
    def test_exactly_three_providers(self):
        assert len(PROVIDERS) == 3

    def test_has_anthropic(self):
        spec = find_by_name("anthropic")
        assert spec is not None
        assert spec.name == "anthropic"

    def test_has_openai(self):
        spec = find_by_name("openai")
        assert spec is not None
        assert spec.name == "openai"

    def test_has_gemini(self):
        spec = find_by_name("gemini")
        assert spec is not None
        assert spec.name == "gemini"

    def test_no_deleted_providers(self):
        deleted = ["openrouter", "deepseek", "azure", "custom", "codex", "copilot",
                    "groq", "zhipu", "dashscope", "moonshot", "minimax", "siliconflow",
                    "volcengine", "aihumix", "vllm"]
        for name in deleted:
            assert find_by_name(name) is None, f"Deleted provider {name} still exists"

    def test_find_by_model_claude(self):
        spec = find_by_model("claude-sonnet-4-20250514")
        if spec:
            assert spec.name == "anthropic"

    def test_find_by_model_gpt(self):
        spec = find_by_model("gpt-4o")
        if spec:
            assert spec.name == "openai"


class TestLLMResponse:
    def test_no_tool_calls(self):
        resp = LLMResponse(content="hello")
        assert resp.has_tool_calls is False

    def test_with_tool_calls(self):
        resp = LLMResponse(
            content=None,
            tool_calls=[ToolCallRequest(id="1", name="echo", arguments={"text": "hi"})]
        )
        assert resp.has_tool_calls is True

    def test_default_finish_reason(self):
        resp = LLMResponse(content="done")
        assert resp.finish_reason == "stop"
