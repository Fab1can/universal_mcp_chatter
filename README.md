# Universal MCP Chatter

A lightweight Python workspace to experiment with multiple model providers (OpenAI, Anthropic, Gemini) behind a common interface. Includes tests for core utilities and provider-specific processing.

## Setup

- Ensure Python 3.10+ is available.
- (Optional) Create a virtual environment.
- Install development/test dependencies:

```bash
pip install -r requirements-test.txt
```

## Running Tests

```bash
pytest -q
```

## Project Structure

- `models/`: Provider integrations (`openai.py`, `anthropic.py`, `gemini.py`).
- `model.py`: Core model orchestration.
- `utils.py`: Shared helpers.
- `tests/`: Unit tests for utilities and providers.

## Notes

Environment variables for provider SDKs may be required (e.g., API keys). See each provider’s documentation.