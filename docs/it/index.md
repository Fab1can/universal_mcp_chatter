# Universal MCP Chatter — Documentazione del Progetto

## Panoramica

**Universal MCP Chatter** è una libreria Python leggera che fornisce un'interfaccia unificata per interagire con più provider di modelli AI (OpenAI, Anthropic, Google Gemini) tramite il [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol). Consente a qualsiasi applicazione di connettersi a un server MCP, scoprire gli strumenti e i prompt disponibili, e condurre una conversazione multi-turno con qualsiasi backend AI supportato senza modificare il codice applicativo.

---

## Struttura del Progetto

```
universal_mcp_chatter/
├── mcp_client.py          # Wrapper del client MCP e punto di ingresso per le conversazioni
├── model.py               # Classe base astratta per tutte le integrazioni AI
├── model_factory.py       # Builder (factory) per costruire istanze del modello configurate
├── utils.py               # Helper condivisi
├── models/
│   ├── openai.py          # Provider OpenAI (chat completion)
│   ├── anthropic.py       # Provider Anthropic (Claude)
│   └── gemini.py          # Provider Google Gemini
├── tests/
│   ├── conftest.py        # Fixture pytest e stub di terze parti
│   ├── test_utils.py      # Test per le funzioni di utilità
│   ├── test_model_factory.py      # Test per ModelFactory
│   ├── test_openai_process.py     # Test per il provider OpenAI
│   ├── test_anthropic_process.py  # Test per il provider Anthropic
│   ├── test_gemini_process.py     # Test per il provider Gemini
│   └── test_process_openai.py     # Test aggiuntivi per OpenAI
├── requirements.txt       # Dipendenze di runtime
├── requirements-test.txt  # Dipendenze solo per i test
└── pytest.ini             # Configurazione di pytest
```

---

## Dipendenze

### Runtime (`requirements.txt`)

| Pacchetto | Scopo |
|-----------|-------|
| `fastmcp` | Framework client/server MCP per connettersi ai server di strumenti |
| `tiktoken` | Conteggio dei token per la tokenizzazione compatibile con OpenAI |
| `openai>=1.0` | SDK Python di OpenAI |
| `anthropic` | SDK Python di Anthropic |
| `google-genai` | SDK Python di Google Generative AI |

### Test (`requirements-test.txt`)

| Pacchetto | Scopo |
|-----------|-------|
| `pytest>=7.0` | Test runner |
| `pytest-asyncio>=0.21` | Supporto `async`/`await` in pytest |

---

## Avvio Rapido

### 1 — Installare le dipendenze

```bash
pip install -r requirements.txt
```

### 2 — Costruire un modello

Usare `ModelFactory` per configurare e costruire un'istanza del modello:

```python
from model_factory import ModelFactory

factory = ModelFactory()
factory.set_openai_api_key("sk-...")
factory.set_name("gpt-4o")
factory.set_max_tokens(4096)
factory.set_temperature(0.7)
factory.set_summarizer_max_tokens(512)
factory.set_summarizer_language("italian")
factory.set_prints(
    assistant_print=print,
    system_print=print,
    error_print=print,
)
model = factory.build()
```

### 3 — Connettersi a un server MCP e chattare

```python
import asyncio
from mcp_client import MCPClient

async def main():
    client = MCPClient(model)
    async with client.get_client():
        await client.init()
        await client.process_query("Ciao, quali strumenti hai?")

asyncio.run(main())
```

---

## Documentazione dei Componenti

| File | Descrizione |
|------|-------------|
| [model.md](model.md) | Classe base astratta `Model` |
| [model_factory.md](model_factory.md) | Builder `ModelFactory` |
| [mcp_client.md](mcp_client.md) | Wrapper `MCPClient` |
| [utils.md](utils.md) | Funzioni di utilità |
| [models/openai.md](models/openai.md) | Provider OpenAI |
| [models/anthropic.md](models/anthropic.md) | Provider Anthropic |
| [models/gemini.md](models/gemini.md) | Provider Gemini |

---

## Esecuzione dei Test

```bash
# Installare prima le dipendenze di test
pip install -r requirements-test.txt

# Eseguire tutti i test
pytest -q
```

La suite di test usa stub in-memory per tutti gli SDK di terze parti (OpenAI, Anthropic, Google GenAI, FastMCP, tiktoken), quindi non sono necessarie chiavi API reali.
