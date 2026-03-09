# `model_factory.py` — ModelFactory Class

## Module overview

`model_factory.py` provides the `ModelFactory` class — a **builder** that accumulates configuration through a fluent setter API and then constructs the correct concrete `Model` subclass via `build()`. Its goal is to validate all required settings at construction time and to hide the provider-specific constructor signatures from the caller.

---

## Dependencies

```python
from models.openai import OpenAIModel
from models.gemini import GeminiModel
from models.anthropic import AnthropicModel
```

No external packages are imported directly; the factory delegates construction to the three provider classes.

---

## Class `ModelFactory`

### Constructor

```python
class ModelFactory:
    def __init__(self):
```

All configuration attributes are set to sensible defaults or `None`:

| Attribute | Default | Description |
|-----------|---------|-------------|
| `format` | `None` | Provider — set by `set_*_api_key` methods |
| `max_tokens` | `None` | Maximum tokens per response |
| `temperature` | `None` | Sampling temperature |
| `name` | `None` | Model identifier |
| `url` | `None` | Optional custom base URL |
| `api_key` | `None` | Provider API key |
| `system_prompt` | `""` | Initial system prompt |
| `max_tries` | `50` | Retry attempts on API failures |
| `wait_seconds` | `6` | Seconds between retries |
| `summarizer_system_prompt` | `None` | Set by `set_summarizer_language()` |
| `summarizer_user_prompt` | `None` | Set by `set_summarizer_language()` |
| `summarizer_max_tokens` | `None` | Token budget for the summary |
| `summarizer_temperature` | `0.3` | Temperature for summary generation |
| `assistant_print` | `None` | Output callback for assistant text |
| `system_print` | `None` | Output callback for system messages |
| `error_print` | `None` | Output callback for errors |

---

### Provider Configuration Methods

#### `set_openai_api_key(self, api_key: str)`

Sets `format = "openai"`, stores `api_key`, and clears `url`. Use when calling the official OpenAI API.

#### `set_openai_url(self, url: str)`

Sets `format = "openai"`, stores `url`, and clears `api_key`. Use for OpenAI-compatible local or third-party endpoints that do not require a key.

#### `set_openai_api_key_and_url(self, api_key: str, url: str)`

Sets `format = "openai"`, stores both `api_key` and `url`. Use for OpenAI-compatible endpoints that require a key **and** a custom base URL.

#### `set_gemini_api_key(self, api_key: str)`

Sets `format = "gemini"`, stores `api_key`, clears `url`.

#### `set_anthropic_api_key(self, api_key: str)`

Sets `format = "anthropic"`, stores `api_key`, clears `url`.

---

### Model Settings

#### `set_name(self, name: str)`

Sets the model identifier forwarded to the provider API (e.g., `"gpt-4o"`, `"claude-3-5-sonnet-20241022"`, `"gemini-1.5-pro"`).

#### `set_max_tokens(self, max_tokens: int)`

Sets the maximum number of output tokens the model may generate per response.

#### `set_temperature(self, temperature: float)`

Sets the sampling temperature (typically `0.0–2.0`).

#### `set_system_prompt(self, system_prompt: str)`

Sets the initial system instruction. Defaults to `""` if not called.

#### `set_max_tries(self, max_tries: int)`

Overrides the default of `50` retry attempts.

#### `set_wait_seconds(self, wait_seconds: int)`

Overrides the default of `6` seconds between retries.

#### `set_prints(self, assistant_print, system_print, error_print)`

Registers the three output callbacks. All three must be set before `build()` is called.

| Callback | Invoked when |
|----------|-------------|
| `assistant_print` | The assistant produces visible text |
| `system_print` | The system emits informational messages |
| `error_print` | An error or retry event occurs |

---

### Summariser Configuration

The conversation summariser compresses the message history when the token count exceeds `max_tokens`, preventing context-window overflows.

#### `set_summarizer_max_tokens(self, max_tokens: int)`

Sets the maximum token budget for the generated summary. **Must be called before** `set_summarizer_language()`.

#### `set_summarizer_language(self, language: str)`

Sets the system and user prompts used for summarisation in the specified language. Supported values:

| Language | `summarizer_system_prompt` (template) | `summarizer_user_prompt` |
|----------|--------------------------------------|--------------------------|
| `"english"` | `"You are an assistant that summarizes conversations …"` | `"Briefly summarize the following conversation:\n"` |
| `"italian"` | `"Sei un assistente che riassume le conversazioni …"` | `"Riassumi brevemente la seguente conversazione:\n"` |

Raises `ValueError` if:
- `set_summarizer_max_tokens()` has not been called yet.
- An unsupported language string is passed.

---

### `build(self) → Model`

```python
def build(self):
```

Validates all required settings and constructs the appropriate concrete `Model` subclass.

**Validation order:**

1. `format` must not be `None`.
2. `max_tokens` must not be `None`.
3. `temperature` must not be `None`.
4. `name` must not be `None`.
5. All three print callbacks must not be `None`.
6. `summarizer_max_tokens` must not be `None`.
7. `summarizer_system_prompt` and `summarizer_user_prompt` must not be `None`.
8. Provider-specific: at least one of `api_key` / `url` must be set (OpenAI), or `api_key` must be set (Gemini, Anthropic).

All failures raise `ValueError` with a descriptive message.

**Returns:** An instance of `OpenAIModel`, `GeminiModel`, or `AnthropicModel` with all attributes pre-populated.

---

## Usage Example

```python
from model_factory import ModelFactory

factory = ModelFactory()

# Provider
factory.set_openai_api_key("sk-...")

# Model settings
factory.set_name("gpt-4o")
factory.set_max_tokens(4096)
factory.set_temperature(0.7)
factory.set_system_prompt("You are a helpful assistant.")

# Output callbacks
factory.set_prints(
    assistant_print=lambda msg: print(f"[AI] {msg}"),
    system_print=lambda msg: print(f"[SYS] {msg}"),
    error_print=lambda msg: print(f"[ERR] {msg}"),
)

# Summariser
factory.set_summarizer_max_tokens(512)
factory.set_summarizer_language("english")

# Build the model
model = factory.build()
```

---

## Error Reference

| Error message | Root cause |
|---------------|-----------|
| `"Model format not set"` | None of the `set_*_api_key` methods was called |
| `"You must call set_max_tokens before building the model"` | `set_max_tokens()` was not called |
| `"You must call set_temperature before building the model"` | `set_temperature()` was not called |
| `"You must call set_name before building the model"` | `set_name()` was not called |
| `"You must call set_prints before building the model"` | `set_prints()` was not called |
| `"You must call set_summarizer_max_tokens before building the model"` | `set_summarizer_max_tokens()` was not called |
| `"You must call set_summarizer_language before building the model"` | `set_summarizer_language()` was not called |
| `"You must call set_openai_api_key, set_openai_url or set_openai_api_key_and_url …"` | OpenAI format but no API key or URL |
| `"You must call set_gemini_api_key before building the model"` | Gemini format but no API key |
| `"You must call set_anthropic_api_key before building the model"` | Anthropic format but no API key |
| `"Unsupported model format: <format>"` | An unknown `format` value was produced (should not occur via public API) |
| `"You must call set_summarizer_max_tokens before setting the language"` | `set_summarizer_language()` called before `set_summarizer_max_tokens()` |
| `"Unsupported language for summarizer"` | Language string other than `"english"` or `"italian"` passed |
