# `models/gemini.py` — Gemini Provider

## Module overview

`models/gemini.py` implements `GeminiModel`, the provider integration for [Google's Generative AI (Gemini) API](https://ai.google.dev/). It extends the base `Model` class and adds:

- Conversion of MCP tool descriptors to Gemini's `function_declarations` schema.
- An async retry loop for API calls.
- A multi-turn `process_query` loop that handles `STOP` (final answer) and `CALL_FUNCTION` (tool invocation) finish reasons.
- A summarisation method.
- Overridden `get_messages` and `set_messages` to work with `types.Content` objects.

---

## Dependencies

```python
from model import Model
from utils import normalize_args

from google import genai
from google.genai import types
import asyncio
import logging
```

---

## Module-level Function

### `mcp_tools_to_gemini_tools(mcp_tools)`

```python
def mcp_tools_to_gemini_tools(mcp_tools):
    """
    Convert the MCP tools obtained from list_tools() of a FastMCP client
    into the format required by Gemini (function_declarations).
    """
```

Converts the FastMCP tool list to the Gemini `tools` format (a list containing one dict with a `function_declarations` key).

#### Parameters

| Name | Description |
|------|-------------|
| `mcp_tools` | List of FastMCP tool descriptor objects returned by `client.list_tools()` |

#### Returns

```json
[
  {
    "function_declarations": [
      {
        "name": "<tool name>",
        "description": "<tool description>",
        "parameters": { /* JSON Schema */ }
      }
    ]
  }
]
```

Uses `getattr(t, "description", "")` and `getattr(t, "input_schema", {...})` with safe defaults.

---

## Class `GeminiModel`

Inherits from `Model`.

### Constructor

```python
class GeminiModel(Model):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
```

Only calls `super().__init__()`. The SDK client and message list are created in `init()`.

---

### Methods

#### `init(self)`

```python
def init(self):
    self.gemini = genai.client.Client(api_key=self.api_key)
    self.messages = [
        types.Content(role="user", parts=[types.Part(text=self.system)])
    ]
```

Creates the Gemini SDK client and initialises `self.messages` with the system prompt as the first `user` message. **Note:** Gemini does not natively support a `system` role in the conversation history; the system prompt is injected as a `user` message at position 0.

---

#### `init_tools(self, tools)`

Converts the MCP tool list to the Gemini `function_declarations` format and stores it in `self.available_tools`.

---

#### `set_system(self, system_prompt)`

```python
def set_system(self, system_prompt):
    super().set_system(system_prompt)
    self.messages[0] = types.Content(role="user", parts=[types.Part(text=system_prompt)])
```

Updates `self.system` and replaces the first message in `self.messages` with the new system prompt.

---

#### `create_message(self)` *(async)*

```python
async def create_message(self):
```

Sends the current message history to the Gemini API via the async client.

**Retry loop:**

- Tries up to `self.max_tries` times.
- On failure, calls `self.error_print(str(e))` and waits `self.wait_seconds`.

**API call parameters:**

| Parameter | Value |
|-----------|-------|
| `model` | `self.name` |
| `contents` | `self.messages` |
| `config.temperature` | `self.temperature` |
| `config.max_output_tokens` | `self.max_tokens` |
| `config.tools` | `[self.client.session]` |

**Note:** `tools=[self.client.session]` passes the FastMCP session directly to Gemini, which uses native function-calling routing. This is a different approach from OpenAI/Anthropic, where a converted tool list is passed.

---

#### `get_role_message(self, role, content)`

```python
def get_role_message(self, role, content):
    return types.Content(role=role, parts=[types.Part(text=content)])
```

Overrides the base class to return a `types.Content` object instead of a plain dict.

---

#### `process_query(self, query)` *(async)*

```python
async def process_query(self, query):
    """Process a query using a model and the available tools"""
```

Drives a complete conversational turn.

**Flow:**

1. Calls `await self._examine_query(query)`.
2. Enters a loop until `tool_use_detected` is `False`:
   a. Optionally calls `await self.summarize()`.
   b. Calls `await self.create_message()`.
   c. Reads `candidate.finish_reason`:
      - **`"STOP"`:** Reads `candidate.content.parts[0].text`, appends a `"model"` role `Content` to `self.messages`, calls `self.assistant_print`, and exits the loop.
      - **`"CALL_FUNCTION"`:** Sets `tool_use_detected = True`. Collects all `function_call` parts from `candidate.content`. Appends a `"model"` message for the intent. For each function call: normalises args with `normalize_args`, calls `self.client.call_tool`, appends the result as a `"user"` message.

---

#### `summarize(self)` *(async)*

```python
async def summarize(self):
```

Compresses the conversation history.

**Steps:**

1. Builds a temporary history using `types.Content` objects with `"system"` and `"user"` roles.
2. Calls the Gemini API asynchronously.
3. Reads the summary from `summarizer.candidates[0].parts[0].text`.
4. Replaces `self.messages` with a system user message, a system summary message, and the last two original messages.

---

#### `get_messages(self)`

```python
def get_messages(self):
    for msg in self.messages:
        if isinstance(msg, dict):
            yield types.Content(role=msg["role"], content=[types.Part(text=msg["content"])])
        else:
            yield msg
```

Overrides the base class to handle mixed message lists (dicts from `set_messages` and `types.Content` objects from native operations).

---

#### `set_messages(self, messages)`

```python
def set_messages(self, messages):
    self.messages = [
        types.Content(role="user", parts=[types.Part(text=self.system)])
    ]
    for message in messages:
        self.messages.append(
            types.Content(role=message["role"], parts=[types.Part(text=message["content"])])
        )
```

Replaces the full message history, converting dict-style messages to `types.Content` objects.

---

## Message Format

Gemini uses `types.Content` objects in `self.messages`.

| Role | Produced by |
|------|-------------|
| `"user"` | Constructor (system prompt), `_examine_query()`, tool results |
| `"model"` | `process_query()` — assistant responses |
| `"system"` | `summarize()` — temporary summariser history |
