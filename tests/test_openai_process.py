import asyncio
import pytest

from model_factory import ModelFactory


class StubClient:
    def __init__(self):
        self.called = []

    async def call_tool(self, name, args):
        self.called.append((name, args))

        class _Result:
            class _Content:
                def __init__(self):
                    self.text = "result-text"

            def __init__(self):
                self.content = [self._Content()]

        return _Result()


def make_model():
    mf = ModelFactory()
    mf.set_openai_api_key("k")
    mf.set_name("gpt-test")
    mf.set_max_tokens(10000)
    mf.set_temperature(0.1)
    logs = []

    def aprint(x):
        logs.append(("assistant", x))

    def sprint(x):
        logs.append(("system", x))

    def eprint(x):
        logs.append(("error", x))

    mf.set_prints(aprint, sprint, eprint)
    model = mf.build()
    model.client = StubClient()
    return model, logs


class ChoiceMsg:
    def __init__(self, content="", tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


class Choice:
    def __init__(self, finish_reason, message):
        self.finish_reason = finish_reason
        self.message = message


@pytest.mark.asyncio
async def test_openai_process_query_stop():
    model, logs = make_model()

    async def fake_create_message():
        return Choice("stop", ChoiceMsg(content="ciao"))

    model.create_message = fake_create_message

    await asyncio.wait_for(model.process_query("salve"), timeout=2.0)

    # Assistant printed final content
    assert ("assistant", "ciao") in logs
    # Messages contain assistant reply at the end
    assert model.messages[-1]["role"] == "assistant"
    assert model.messages[-1]["content"] == "ciao"


class ToolCall:
    class Function:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

    def __init__(self, name, arguments):
        self.function = ToolCall.Function(name, arguments)


@pytest.mark.asyncio
async def test_openai_process_query_tool_calls_then_stop():
    model, logs = make_model()

    calls = {
        "count": 0
    }

    async def seq_create_message():
        if calls["count"] == 0:
            calls["count"] += 1
            # First response asks to call a tool
            tc = ToolCall("tool1", '{"x": 1}')
            return Choice("tool_calls", ChoiceMsg(content="use tool", tool_calls=[tc]))
        else:
            # Second response ends the loop
            return Choice("stop", ChoiceMsg(content="final"))

    model.create_message = seq_create_message

    await asyncio.wait_for(model.process_query("esegui"), timeout=2.0)

    # Tool was invoked once
    assert model.client.called and model.client.called[0][0] == "tool1"
    assert model.client.called[0][1] == {"x": 1}

    # Assistant printed final content
    assert ("assistant", "final") in logs
    # Final assistant message appended
    assert model.messages[-1]["role"] == "assistant"
    assert model.messages[-1]["content"] == "final"
