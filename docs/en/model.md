# `model.py` — Base Model Class

## Module overview

`model.py` defines the abstract base class `Model`, which every provider-specific implementation (OpenAI, Anthropic, Gemini) must extend. It captures all configuration shared across providers and supplies the message-history bookkeeping, token-based summarisation trigger, and MCP prompt-command handling.

---

## Dependencies

| Import | Purpose |
|--------|---------|
| `logging` | Standard Python logging |
| `fastmcp.McpError` | Exception raised when an MCP operation fails |
| `tiktoken` | Used to count tokens in the current message history |

```python
import logging
from fastmcp import McpError
import tiktoken
TIKTOKEN = tiktoken.get_encoding("o200k_base")
```

`TIKTOKEN` is a module-level singleton; encoding is initialised once to keep instantiation cost low.

---

## Class `Model`

### Constructor

```python
class Model:
    def __init__(
        self,
        format: str,
        max_tokens: int,
        temperature: float,
        name: str,
        url: str,
        api_key: str,
        system_prompt: str,
        max_tries: int,
        wait_seconds: int,
        summarizer_system_prompt: str,
        summarizer_user_prompt: str,
        summarizer_max_tokens: int,
        summarizer_temperature: float,
        assistant_print,
        system_print,
        error_print,
    ):
```

All arguments are stored as instance attributes. The constructor is called exclusively by `ModelFactory.build()`.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `format` | `str` | Provider identifier — `"openai"`, `"anthropic"`, or `"gemini"` |
| `max_tokens` | `int` | Maximum number of tokens the model may generate per response |
| `temperature` | `float` | Sampling temperature (creativity vs. determinism) |
| `name` | `str` | Model identifier sent to the provider API (e.g., `"gpt-4o"`) |
| `url` | `str` | Optional custom base URL for OpenAI-compatible endpoints |
| `api_key` | `str` | Provider API key |
| `system_prompt` | `str` | Initial system instruction for the assistant |
| `max_tries` | `int` | Maximum number of retry attempts on API errors before giving up |
| `wait_seconds` | `int` | Seconds to wait between retries |
| `summarizer_system_prompt` | `str` | System prompt used when summarising the conversation |
| `summarizer_user_prompt` | `str` | User prompt prefix used when summarising |
| `summarizer_max_tokens` | `int` | Token budget for the generated summary |
| `summarizer_temperature` | `float` | Temperature used for the summariser call |
| `assistant_print` | `callable` | Callback invoked with the assistant's visible text output |
| `system_print` | `callable` | Callback invoked for informational system messages |
| `error_print` | `callable` | Callback invoked for error messages |

#### Notable attributes initialised to `None`

| Attribute | Set by |
|-----------|--------|
| `self.client` | `MCPClient.get_client()` |
| `self.response` | `process_query()` |
| `self.available_tools` | `init_tools()` |
| `self.available_prompts` | `MCPClient.init()` |

---

### Methods

#### `init(self)`

```python
def init(self):
    pass
```

Hook called after construction. Subclasses override this to perform lazy initialisation (e.g., creating the provider SDK client and the initial message list).

---

#### `init_tools(self, tools)`

```python
def init_tools(self, tools):
    pass
```

Called by `MCPClient.init()` after the MCP server's tool list is fetched. Subclasses override this to convert MCP tool descriptors into the format required by their provider SDK.

**Parameters**

| Name | Description |
|------|-------------|
| `tools` | List of `fastmcp` tool descriptors returned by `client.list_tools()` |

---

#### `set_system(self, system_prompt: str)`

```python
def set_system(self, system_prompt: str):
    self.system = system_prompt
```

Replaces the active system prompt. `MCPClient.init()` calls this to append available MCP prompt commands to the original system instruction. Subclasses that store the system prompt inside the message list (e.g., `OpenAIModel`) must override this to keep the stored message consistent.

---

#### `get_user_message(self, query: str) → dict`

```python
def get_user_message(self, query: str):
    return self.get_role_message("user", query)
```

Convenience wrapper that creates a `{"role": "user", "content": query}` message dict.

---

#### `get_role_message(self, role: str, content: str) → dict`

```python
def get_role_message(self, role: str, content: str):
    return {"role": role, "content": content}
```

Returns a standard message dict. Subclasses that use a different message type (e.g., `GeminiModel` uses `types.Content`) override this.

---

#### `check_summarize_needed(self, next_message) → bool`

```python
def check_summarize_needed(self, next_message):
```

Returns `True` when the token count of the entire conversation history plus `next_message` reaches or exceeds `self.max_tokens`, **and** all three summariser configuration fields are set.

**Logic**

1. If any summariser configuration value is `None`, return `False` immediately.
2. Build a snapshot: `list(self.get_messages()) + next_message`.
3. Encode the snapshot as a UTF-8 string using `tiktoken` and count the resulting tokens.
4. Return `True` if `token_count >= self.max_tokens`.

---

#### `_examine_query(self, query)` *(async)*

```python
async def _examine_query(self, query):
```

Inspects the incoming query string. If the query starts with `/`, it is treated as an MCP prompt command:

- The method calls `self.client.get_prompt(query[1:])` to retrieve the prompt messages from the MCP server.
- Each retrieved message is appended to `self.messages` via `get_role_message`.
- If the MCP call raises `McpError` (prompt not found, server error), the raw query is appended as a normal user message instead.

If the query does not start with `/`, it is appended to `self.messages` as a plain user message.

---

#### `process_query(self, query)` *(async)*

```python
async def process_query(self, query):
    pass
```

Entry point for a single conversational turn. Must be overridden by every concrete subclass. Called by `MCPClient.process_query()`.

---

#### `summarize(self)` *(async)*

```python
async def summarize(self):
    pass
```

Produces a compressed summary of the conversation history and replaces `self.messages` with a shorter representation. Must be overridden by every concrete subclass.

---

#### `get_messages(self)`

```python
def get_messages(self):
    for msg in self.messages:
        yield msg
```

Generator that yields every message in `self.messages`. Subclasses that use typed message objects (e.g., `GeminiModel`) override this to normalise the yielded values.

---

#### `set_messages(self, messages)`

```python
def set_messages(self, messages):
    self.messages = [{"role": "system", "content": self.system}]
    for message in messages:
        self.messages.append({"role": message["role"], "content": message["content"]})
```

Replaces the full message history. Prepends the current system prompt as the first element.

---

## Design Notes

- `Model` is designed as an abstract base class; it is never instantiated directly. `ModelFactory.build()` always returns a concrete subclass.
- The three `*_print` callbacks decouple output formatting from the model logic, allowing the caller to use rich terminals, logging frameworks, or GUI widgets without changing the model code.
- The `client` attribute is set by `MCPClient` after construction and before the first call to `process_query`. This late injection avoids a circular dependency between `Model` and `MCPClient`.
