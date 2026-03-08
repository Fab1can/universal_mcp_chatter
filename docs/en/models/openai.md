# `models/openai.py` — OpenAI Provider

## Module overview

`models/openai.py` implements `OpenAIModel`, the provider integration for [OpenAI's chat completion API](https://platform.openai.com/docs/api-reference/chat). It extends the base `Model` class and adds:

- Conversion of MCP tool descriptors to the OpenAI function-calling schema.
- A retry loop for API calls.
- A multi-turn `process_query` loop that handles `stop` (final answer) and `tool_calls` (tool invocation) finish reasons.
- A summarisation method that compresses the conversation history.

---

## Dependencies

```python
from model import Model
from utils import normalize_args

import logging
import asyncio
from openai import OpenAI
```

---

## Module-level Function

### `mcp_tools_to_openai_tools(mcp_tools)`

```python
def mcp_tools_to_openai_tools(mcp_tools):
```

Converts the FastMCP tool list to the format expected by the OpenAI `tools` parameter.

#### Parameters

| Name | Description |
|------|-------------|
| `mcp_tools` | List of FastMCP tool descriptor objects returned by `client.list_tools()` |

#### Returns

A list of dicts with the following structure:

```json
[
  {
    "type": "function",
    "function": {
      "name": "<tool name>",
      "description": "<tool description>",
      "parameters": { /* JSON Schema */ }
    }
  }
]
```

If a tool descriptor has no `input_schema` attribute, `{"type": "object", "properties": {}}` is used as a fallback.

---

## Class `OpenAIModel`

Inherits from `Model`.

### Constructor

```python
class OpenAIModel(Model):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
```

In addition to the base class initialisation:

- Creates the `openai.OpenAI` SDK client:
  - If `url` is `None` or empty: `OpenAI(api_key=self.api_key)`
  - Otherwise: `OpenAI(api_key=self.api_key, base_url=self.url)`
- Initialises `self.messages` with a single system message:
  ```python
  [{"role": "system", "content": self.system}]
  ```

---

### Methods

#### `init(self)`

Calls `super().init()`. Can be extended for further lazy setup.

---

#### `init_tools(self, tools)`

```python
def init_tools(self, tools):
    super().init_tools(tools)
    self.available_tools = mcp_tools_to_openai_tools(tools)
```

Converts the MCP tool list to the OpenAI tools format and stores it in `self.available_tools`.

---

#### `set_system(self, system_prompt)`

```python
def set_system(self, system_prompt):
    super().set_system(system_prompt)
    self.messages[0] = {"role": "system", "content": system_prompt}
```

Updates the system message at index 0 of `self.messages` in addition to updating `self.system`.

---

#### `create_message(self)` *(async)*

```python
async def create_message(self):
```

Sends the current message history to the OpenAI API and returns the first choice.

**Retry loop:**

- Tries up to `self.max_tries` times.
- On success, returns `response.choices[0]` (a `Choice` object).
- On failure, logs the error message via `self.error_print` and waits `self.wait_seconds` before retrying.
- After exhausting all retries, calls `self.error_print("Maximum number of attempts reached …")` and returns `None`.

**API call parameters:**

| Parameter | Value |
|-----------|-------|
| `model` | `self.name` |
| `messages` | `self.messages` |
| `max_tokens` | `self.max_tokens` |
| `temperature` | `self.temperature` |
| `tools` | `self.available_tools` |

---

#### `process_query(self, query)` *(async)*

```python
async def process_query(self, query):
    """Process a query using a model and the available tools"""
```

Drives a complete conversational turn, including all tool calls needed to produce the final answer.

**Flow:**

1. Calls `await self._examine_query(query)` to append the user message (or MCP prompt messages) to `self.messages`.
2. Enters a loop until `tool_use_detected` is `False`:
   a. Calls `self.check_summarize_needed(...)` and, if needed, calls `await self.summarize()`.
   b. Calls `await self.create_message()` to get the model's response.
   c. If `finish_reason == "stop"`: appends the assistant message to `self.messages`, calls `self.assistant_print`, and exits the loop.
   d. If `finish_reason == "tool_calls"`: iterates over each tool call, normalises arguments with `normalize_args`, calls the tool via `self.client.call_tool(tool_name, tool_args)`, and appends the result as a `"tool"` role message. Sets `tool_use_detected = True` to continue the loop.

---

#### `summarize(self)` *(async)*

```python
async def summarize(self):
```

Compresses the conversation history.

**Steps:**

1. Builds a temporary history with the summariser system prompt and a user message containing `self.messages[1:-2]` (excluding the first system message and the last two messages to preserve recent context).
2. Calls the OpenAI API synchronously (no retry loop) with `summarizer_max_tokens` and `summarizer_temperature`.
3. Replaces `self.messages` with:
   - The original system message.
   - A second system message containing the summary.
   - The last two original messages (preserved as context).

---

## Message Format

OpenAI uses a list of dicts. Roles used in `self.messages`:

| Role | Produced by |
|------|-------------|
| `"system"` | Constructor / `set_system()` / `summarize()` |
| `"user"` | `_examine_query()` |
| `"assistant"` | `process_query()` — final text response |
| `"tool"` | `process_query()` — tool call result |
| `ChatCompletionMessage` object | `process_query()` — raw assistant message when tools are called |
