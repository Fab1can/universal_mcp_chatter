# Universal MCP Chatter — Project Documentation

## Overview

**Universal MCP Chatter** is a lightweight Python library that provides a unified interface for interacting with multiple AI model providers (OpenAI, Anthropic, Google Gemini) via the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol). It allows any application to connect to an MCP server, discover available tools and prompts, and drive a multi-turn conversation with any supported AI backend without changing the application code.

---

## Project Structure

```
universal_mcp_chatter/
├── mcp_client.py          # MCP client wrapper and conversation entry point
├── model.py               # Abstract base class for all AI model integrations
├── model_factory.py       # Builder (factory) for constructing configured model instances
├── utils.py               # Shared utility helpers
├── models/
│   ├── openai.py          # OpenAI chat completion provider
│   ├── anthropic.py       # Anthropic (Claude) provider
│   └── gemini.py          # Google Gemini provider
├── tests/
│   ├── conftest.py        # Pytest fixtures and third-party stubs
│   ├── test_utils.py      # Tests for utility functions
│   ├── test_model_factory.py      # Tests for ModelFactory
│   ├── test_openai_process.py     # Tests for the OpenAI provider
│   ├── test_anthropic_process.py  # Tests for the Anthropic provider
│   ├── test_gemini_process.py     # Tests for the Gemini provider
│   └── test_process_openai.py     # Additional OpenAI processing tests
├── requirements.txt       # Runtime dependencies
├── requirements-test.txt  # Test-only dependencies
└── pytest.ini             # Pytest configuration
```

---

## Dependencies

### Runtime (`requirements.txt`)

| Package | Purpose |
|---------|---------|
| `fastmcp` | MCP client/server framework used to connect to tool servers |
| `tiktoken` | Token counting for OpenAI-compatible tokenisation |
| `openai>=1.0` | OpenAI Python SDK |
| `anthropic` | Anthropic Python SDK |
| `google-genai` | Google Generative AI Python SDK |

### Test (`requirements-test.txt`)

| Package | Purpose |
|---------|---------|
| `pytest>=7.0` | Test runner |
| `pytest-asyncio>=0.21` | `async`/`await` support in pytest |

---

## Quick Start

### 1 — Install dependencies

```bash
pip install -r requirements.txt
```

### 2 — Build a model

Use `ModelFactory` to configure and build a model instance:

```python
from model_factory import ModelFactory

factory = ModelFactory()
factory.set_openai_api_key("sk-...")
factory.set_name("gpt-4o")
factory.set_max_tokens(4096)
factory.set_temperature(0.7)
factory.set_summarizer_max_tokens(512)
factory.set_summarizer_language("english")
factory.set_prints(
    assistant_print=print,
    system_print=print,
    error_print=print,
)
model = factory.build()
```

### 3 — Connect to an MCP server and chat

```python
import asyncio
from mcp_client import MCPClient

async def main():
    client = MCPClient(model)
    async with client.get_client():
        await client.init()
        await client.process_query("Hello, what tools do you have?")

asyncio.run(main())
```

---

## Component Documentation

| File | Description |
|------|-------------|
| [model.md](model.md) | Base `Model` abstract class |
| [model_factory.md](model_factory.md) | `ModelFactory` builder |
| [mcp_client.md](mcp_client.md) | `MCPClient` wrapper |
| [utils.md](utils.md) | Utility functions |
| [models/openai.md](models/openai.md) | OpenAI provider |
| [models/anthropic.md](models/anthropic.md) | Anthropic provider |
| [models/gemini.md](models/gemini.md) | Gemini provider |

---

## Running Tests

```bash
# Install test dependencies first
pip install -r requirements-test.txt

# Run all tests
pytest -q
```

The test suite uses in-memory stubs for all third-party SDKs (OpenAI, Anthropic, Google GenAI, FastMCP, tiktoken) so no real API keys are needed.
