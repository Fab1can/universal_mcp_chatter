import asyncio
import types

import pytest

from models.openai import OpenAIModel


class FakeChoiceMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeChoice:
    def __init__(self, finish_reason="stop", message=None):
        self.finish_reason = finish_reason
        self.message = message or FakeChoiceMessage("")


async def _noop(*args, **kwargs):
    return None


def make_model(**overrides):
    defaults = dict(
        format="openai",
        max_tokens=1000,
        temperature=0.1,
        name="gpt-test",
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
    m = OpenAIModel(**defaults)
    # Avoid external client usage during tests
    m.init_tools([])
    return m


@pytest.mark.asyncio
async def test_process_query_stop_appends_assistant_message():
    model = make_model()
    # Ensure we don't trigger summarization during test
    model.check_summarize_needed = lambda *_: False

    async def fake_create_message():
        return FakeChoice(finish_reason="stop", message=FakeChoiceMessage(content="ciao"))

    model.create_message = fake_create_message

    await model.process_query("hello")

    # Last assistant message content should be "ciao"
    assert model.messages[-1]["role"] == "assistant"
    assert model.messages[-1]["content"] == "ciao"


@pytest.mark.asyncio
async def test_process_query_tool_calls_invokes_client_and_appends_tool_result():
    model = make_model()
    # Ensure we don't trigger summarization during test
    model.check_summarize_needed = lambda *_: False

    # Prepare a fake tool call structure mimicking OpenAI's shape
    ToolFunc = types.SimpleNamespace
    ToolCall = types.SimpleNamespace

    tool_call = ToolCall(function=ToolFunc(name="echo", arguments="{\"text\": \"hi\"}"))

    calls = {"n": 0}

    async def fake_create_message():
        if calls["n"] == 0:
            calls["n"] += 1
            return FakeChoice(
                finish_reason="tool_calls",
                message=FakeChoiceMessage(content="", tool_calls=[tool_call]),
            )
        return FakeChoice(finish_reason="stop", message=FakeChoiceMessage(content="done"))

    model.create_message = fake_create_message

    class FakeClient:
        async def call_tool(self, name, args):
            class R:
                content = [types.SimpleNamespace(text=f"called {name} with {args}")]
            return R()

    model.client = FakeClient()

    await asyncio.wait_for(model.process_query("hello"), timeout=2.0)

    # There should be a tool message with the output
    tool_msgs = [m for m in model.messages if isinstance(m, dict) and m.get("role") == "tool" and m.get("name") == "echo"]
    assert tool_msgs and "called echo" in tool_msgs[-1]["content"]
    # Final assistant message appended
    assert model.messages[-1]["role"] == "assistant"
    assert model.messages[-1]["content"] == "done"
