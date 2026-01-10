import asyncio
import types as pytypes

import pytest

from models.gemini import GeminiModel
from google.genai import types


class FakeResponse:
    def __init__(self, candidates):
        self.candidates = candidates


class FakeCandidateStop:
    def __init__(self, text="ciao"):
        self.finish_reason = "STOP"
        self.content = types.Content(role="model", parts=[types.Part(text=text)])


class FakeCandidateTool:
    def __init__(self, name="echo", args='{"text":"hi"}', text=""):
        self.finish_reason = "CALL_FUNCTION"
        # parts that include a function_call object
        func_call = pytypes.SimpleNamespace(name=name, args=args)
        self.content = [pytypes.SimpleNamespace(function_call=func_call)]
        self.text = text


def make_model(**overrides):
    defaults = dict(
        format="gemini",
        max_tokens=1000,
        temperature=0.1,
        name="gemini-test",
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
    m = GeminiModel(**defaults)
    m.init()
    m.init_tools([])
    return m


@pytest.mark.asyncio
async def test_gemini_process_query_stop():
    model = make_model()
    model.check_summarize_needed = lambda *_: False

    async def fake_create_message():
        return FakeResponse([FakeCandidateStop(text="ciao")])

    model.create_message = fake_create_message

    await asyncio.wait_for(model.process_query("hello"), timeout=2.0)

    # Last message should be a model response content
    last = model.messages[-1]
    assert isinstance(last, types.Content)
    assert last.role == "model"
    assert last.parts[0].text == "ciao"


@pytest.mark.asyncio
async def test_gemini_process_query_tool_call_then_stop():
    model = make_model()
    model.check_summarize_needed = lambda *_: False

    calls = {"n": 0}

    async def seq_create_message():
        if calls["n"] == 0:
            calls["n"] += 1
            return FakeResponse([FakeCandidateTool(name="echo", args='{"text":"hi"}', text="")])
        return FakeResponse([FakeCandidateStop(text="final")])

    model.create_message = seq_create_message

    class FakeClient:
        async def call_tool(self, name, args):
            class R:
                class C:
                    def __init__(self):
                        self.text = f"called {name} with {args}"

                def __init__(self):
                    self.content = [self.C()]

            return R()

    model.client = FakeClient()

    await asyncio.wait_for(model.process_query("hello"), timeout=2.0)

    # A user message carrying tool output should be present
    user_msgs = [m for m in model.messages if isinstance(m, types.Content) and m.role == "user"]
    assert user_msgs and "called echo" in user_msgs[-1].parts[0].text

    # Final model message appended
    assert isinstance(model.messages[-1], types.Content)
    assert model.messages[-1].role == "model"
    assert model.messages[-1].parts[0].text == "final"
