import asyncio
import types as pytypes

import pytest

from models.anthropic import AnthropicModel


class FakeBlockText:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class FakeBlockToolUse:
    def __init__(self, name, input, id):
        self.type = "tool_use"
        self.name = name
        self.input = input
        self.id = id


class FakeResponse:
    def __init__(self, content):
        self.content = content


def make_model(**overrides):
    defaults = dict(
        format="anthropic",
        max_tokens=1000,
        temperature=0.1,
        name="claude-test",
        url=None,
        api_key="key",
        system_prompt="system",
        max_tries=1,
        wait_seconds=0,
        summarizer_system_prompt="sum sys",
        summarizer_user_prompt="sum user",
        summarizer_max_tokens=64,
        summarizer_temperature=0.1,
        assistant_print=lambda *_: None,
        system_print=lambda *_: None,
        error_print=lambda *_: None,
    )
    defaults.update(overrides)
    m = AnthropicModel(**defaults)
    m.init()
    m.init_tools([])
    return m


@pytest.mark.asyncio
async def test_anthropic_process_query_text_only():
    model = make_model()
    model.check_summarize_needed = lambda *_: False

    async def fake_create_message():
        return FakeResponse([FakeBlockText("hello")])

    model.create_message = fake_create_message

    await asyncio.wait_for(model.process_query("hi"), timeout=2.0)

    # Final assistant message appended
    assert model.messages[-1]["role"] == "assistant"
    assert model.messages[-1]["content"][0].type == "text"


@pytest.mark.asyncio
async def test_anthropic_process_query_tool_use_then_text():
    model = make_model()
    model.check_summarize_needed = lambda *_: False

    calls = {"n": 0}

    async def seq_create_message():
        if calls["n"] == 0:
            calls["n"] += 1
            return FakeResponse([
                FakeBlockText("go"),
                FakeBlockToolUse("echo", {"x": 1}, "id1"),
            ])
        return FakeResponse([FakeBlockText("final")])

    model.create_message = seq_create_message

    class FakeClient:
        async def call_tool(self, name, args):
            class R:
                def __init__(self):
                    self.content = [pytypes.SimpleNamespace(text=f"called {name} with {args}")]
            return R()

    model.client = FakeClient()

    await asyncio.wait_for(model.process_query("hi"), timeout=2.0)

    # A user tool_result message should be present
    user_tool_msgs = [m for m in model.messages if isinstance(m, dict) and m.get("role") == "user"]
    assert user_tool_msgs
    tr = user_tool_msgs[-1]["content"][0]
    assert tr["type"] == "tool_result" and tr["tool_use_id"] == "id1"

    # Final assistant message appended
    assert model.messages[-1]["role"] == "assistant"
    assert model.messages[-1]["content"][0].type == "text"
