# `models/anthropic.py` — Anthropic Provider

## Module overview

`models/anthropic.py` implements `AnthropicModel`, the provider integration for the [Anthropic Messages API](https://docs.anthropic.com/en/api/messages) (Claude models). It extends the base `Model` class and adds:

- Conversion of MCP tool descriptors to the Anthropic tool schema.
- A retry loop for API calls with Anthropic-specific error message handling.
- A multi-turn `process_query` loop that handles `text` (direct answer) and `tool_use` (tool invocation) content blocks.
- A summarisation method that compresses the conversation history.

---

## Dependencies

```python
from model import Model

from anthropic import Anthropic
from fastmcp import McpError
import asyncio
import logging
```

---

## Module-level Function

### `mcp_tools_to_anthropic_tools(mcp_tools)`

```python
def mcp_tools_to_anthropic_tools(mcp_tools):
```

Converts the FastMCP tool list to the format expected by the Anthropic `tools` parameter.

#### Parameters

| Name | Description |
|------|-------------|
| `mcp_tools` | List of FastMCP tool descriptor objects returned by `client.list_tools()` |

#### Returns

A list of dicts with the following structure:

```json
[
  {
    "name": "<tool name>",
    "description": "<tool description>",
    "input_schema": { /* JSON Schema */ }
  }
]
```

Uses `tool.inputSchema` (camelCase) as the input schema, which is the attribute name exposed by FastMCP for the Anthropic-compatible schema.

---

## Class `AnthropicModel`

Inherits from `Model`.

### Constructor

```python
class AnthropicModel(Model):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = None
```

The Anthropic SDK client (`self.anthropic`) and the message list (`self.messages`) are **not** initialised in the constructor; they are created in `init()`.

---

### Methods

#### `init(self)`

```python
def init(self):
    self.anthropic = Anthropic(api_key=self.api_key)
    self.messages = []
```

Creates the Anthropic SDK client and sets the initial message list to an empty list. Note: unlike OpenAI, the Anthropic Messages API passes the system prompt as a separate top-level parameter in each API call (`system=self.system`), so it is not stored in `self.messages`.

---

#### `init_tools(self, tools)`

```python
def init_tools(self, tools):
    super().init_tools(tools)
    self.available_tools = mcp_tools_to_anthropic_tools(tools)
```

Converts the MCP tool list to the Anthropic tools format.

---

#### `set_system(self, system_prompt)`

```python
def set_system(self, system_prompt):
    super().set_system(system_prompt)
```

Delegates to `super().set_system()`. Because the Anthropic API receives the system prompt as a separate field, no additional update to `self.messages` is needed.

---

#### `create_message(self)` *(async)*

```python
async def create_message(self):
```

Sends the current message history to the Anthropic Messages API and returns the full response object.

**Retry loop:**

- Tries up to `self.max_tries` times.
- Handles the following specific Anthropic error conditions with tailored user-facing messages:
  - Insufficient credits.
  - Server overload.
  - Requests-per-minute rate limit exceeded.
  - Any other `e.body["error"]["message"]` value.
  - Generic exceptions without an `e.body` attribute.
- Waits `self.wait_seconds` between retries.

**API call parameters:**

| Parameter | Value |
|-----------|-------|
| `model` | `self.name` |
| `max_tokens` | `self.max_tokens` |
| `messages` | `self.messages` |
| `tools` | `self.available_tools` |
| `system` | `self.system` |

---

#### `process_query(self, query)` *(async)*

```python
async def process_query(self, query):
    """Process a query using Claude and the available tools"""
```

Drives a complete conversational turn.

**Flow:**

1. Calls `await self._examine_query(query)`.
2. Enters a loop until `tool_use_detected` is `False`:
   a. Optionally calls `await self.summarize()`.
   b. Calls `await self.create_message()`.
   c. Pops content blocks from `response.content` one by one:
      - **`text` block:** Calls `self.assistant_print(content.text)` and appends to `assistant_parts`.
      - **`tool_use` block:**
        1. Sets `tool_use_detected = True`.
        2. Appends an `"assistant"` message containing `assistant_parts + [content]` (text blocks seen so far in this turn **plus** the `tool_use` block).
        3. Calls `self.client.call_tool(tool_name, tool_args)` in an inner retry loop that catches `McpError`.
        4. Appends a `"user"` message containing a `tool_result` content block with `tool_use_id` and the returned content.
   d. If no `tool_use` blocks were found, appends a final `"assistant"` message with `assistant_parts`.

---

#### `summarize(self)` *(async)*

```python
async def summarize(self):
```

Compresses the conversation history.

**Steps:**

1. Builds a temporary history with the summariser system and user prompts plus `self.messages[1:-2]`.
2. Calls the Anthropic Messages API without a tool list.
3. Replaces `self.messages` with:
   - A system message containing `self.system`.
   - A system message containing the summary.
   - The last two original messages.

---

## Message Format

Anthropic uses a list of dicts in `self.messages`. The `system` prompt is passed separately.

| Role | Content type | Produced by |
|------|-------------|-------------|
| `"user"` | Plain string | `_examine_query()` |
| `"assistant"` | List of content blocks | `process_query()` — text + tool_use blocks |
| `"user"` | List with `tool_result` block | `process_query()` — tool result |
| `"system"` | String | `summarize()` only |
