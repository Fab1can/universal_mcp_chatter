# `mcp_client.py` — MCPClient Class

## Module overview

`mcp_client.py` defines `MCPClient`, the top-level coordinator that:

1. Manages the lifecycle of the FastMCP `Client` connection to an MCP server.
2. Discovers and registers available tools and prompt commands.
3. Delegates query processing to the underlying `Model` instance.

---

## Dependencies

```python
from fastmcp import Client
from fastmcp.client.logging import LogMessage
```

| Import | Purpose |
|--------|---------|
| `fastmcp.Client` | Asynchronous MCP client used to connect to an MCP tool server |
| `fastmcp.client.logging.LogMessage` | Typed log message object emitted by the FastMCP log handler |

---

## Class `MCPClient`

### Constructor

```python
class MCPClient:
    def __init__(self, model):
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | `Model` | A fully constructed model instance produced by `ModelFactory.build()` |

#### Attributes initialised

| Attribute | Initial value | Description |
|-----------|---------------|-------------|
| `self.client` | `None` | The lazy-created `fastmcp.Client` instance |
| `self.model` | `model` | Reference to the underlying model |
| `self.assistant_print` | `model.assistant_print` | Shortcut to the assistant output callback |
| `self.system_print` | `model.system_print` | Shortcut to the system message callback |
| `self.error_print` | `model.error_print` | Shortcut to the error callback |

---

### Methods

#### `get_client(self) → fastmcp.Client`

```python
def get_client(self):
```

Returns the `fastmcp.Client` instance, creating it on the first call (lazy initialisation).

**Behaviour:**

1. If `self.client` is `None`, a new `Client` is created:
   - Target URL: `self.model.url` (set by the factory).
   - Log handler: an inner async function `_log_handler` that routes `"error"`-level messages to `error_print` and all other levels to `system_print`.
2. The newly created client is stored on both `self.client` and `self.model.client` so that the model can call tools through the same connection.
3. On subsequent calls, the existing client is returned immediately.

**Returns:** The `fastmcp.Client` instance.

**Note:** The returned client is designed to be used as an async context manager:

```python
async with client.get_client():
    ...
```

---

#### `init(self)` *(async)*

```python
async def init(self):
```

Performs the one-time setup after a connection to the MCP server has been established. Must be called inside an `async with client.get_client():` block.

**Steps:**

1. Calls `list_tools()` on the FastMCP client and logs the tool names via `system_print`.
2. Calls `list_prompts()` on the FastMCP client and logs the prompt names via `system_print`.
3. Calls `self.model.init_tools(tools)` so the model can convert the tool descriptors to its provider-specific format.
4. Builds `self.available_prompts` — a list of `{"name": ..., "description": ...}` dicts.
5. If any prompts were found, appends a formatted list of slash-commands to the model's system prompt using `self.model.set_system(...)`. The format is:
   ```
   /prompt_name - prompt description
   ```

---

#### `process_query(self, query)` *(async)*

```python
async def process_query(self, query):
    await self.model.process_query(query)
```

Thin wrapper that delegates the query to the underlying model's `process_query` method. Must be called inside an active `async with client.get_client():` block after `init()` has completed.

---

## Full Usage Example

```python
import asyncio
from model_factory import ModelFactory
from mcp_client import MCPClient

async def main():
    # 1. Build the model
    factory = ModelFactory()
    factory.set_openai_api_key("sk-...")
    factory.set_name("gpt-4o")
    factory.set_max_tokens(4096)
    factory.set_temperature(0.7)
    factory.set_prints(print, print, print)
    factory.set_summarizer_max_tokens(512)
    factory.set_summarizer_language("english")
    model = factory.build()

    # 2. Create the MCP client
    client = MCPClient(model)

    # 3. Connect, initialise and chat
    async with client.get_client():
        await client.init()
        await client.process_query("List all available databases.")
        await client.process_query("/summarize")   # MCP prompt command

asyncio.run(main())
```

---

## Design Notes

- **Lazy client creation:** The FastMCP `Client` is not instantiated until `get_client()` is first called. This makes the `MCPClient` object cheap to create and allows the URL to be changed before the connection is opened.
- **Shared client reference:** Setting `self.model.client = self.client` is essential — it gives the model direct access to `call_tool()` so tool results can be fetched inside `process_query()` without any additional routing through `MCPClient`.
- **Prompt commands:** Any query beginning with `/` is treated as an MCP prompt command by the base `Model._examine_query()` method. `MCPClient.init()` ensures the user is aware of available commands by appending them to the system prompt.
