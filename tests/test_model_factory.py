import pytest

from model_factory import ModelFactory
from models.openai import OpenAIModel
from models.gemini import GeminiModel
from models.anthropic import AnthropicModel


def _prints():
    return (lambda *a, **k: None, lambda *a, **k: None, lambda *a, **k: None)


def test_build_without_format_raises():
    mf = ModelFactory()
    mf.set_name("gpt")
    mf.set_max_tokens(128)
    mf.set_temperature(0.1)
    a, s, e = _prints()
    mf.set_prints(a, s, e)
    with pytest.raises(ValueError, match="Model format not set"):
        mf.build()


def test_build_requires_all_mandatory_params():
    mf = ModelFactory()
    mf.set_openai_api_key("k")
    # Missing name
    mf.set_max_tokens(128)
    mf.set_temperature(0.1)
    a, s, e = _prints()
    mf.set_prints(a, s, e)
    with pytest.raises(ValueError, match="You must call set_name"):
        mf.build()


@pytest.mark.parametrize(
    "setter, expected_cls",
    [
        (lambda mf: mf.set_openai_api_key("k"), OpenAIModel),
        (lambda mf: mf.set_gemini_api_key("k"), GeminiModel),
        (lambda mf: mf.set_anthropic_api_key("k"), AnthropicModel),
    ],
)
def test_build_for_each_provider(setter, expected_cls):
    mf = ModelFactory()
    setter(mf)
    mf.set_name("test-model")
    mf.set_max_tokens(64)
    mf.set_temperature(0.2)
    a, s, e = _prints()
    mf.set_prints(a, s, e)
    model = mf.build()
    assert isinstance(model, expected_cls)
