# `models/openai.py` — Provider OpenAI

## Panoramica del modulo

`models/openai.py` implementa `OpenAIModel`, l'integrazione del provider per l'[API di chat completion di OpenAI](https://platform.openai.com/docs/api-reference/chat). Estende la classe base `Model` e aggiunge:

- Conversione dei descrittori di strumenti MCP nel schema di function-calling di OpenAI.
- Un ciclo di retry per le chiamate API.
- Un ciclo `process_query` multi-turno che gestisce le finish reason `stop` (risposta finale) e `tool_calls` (invocazione strumento).
- Un metodo di riassunto che comprime la cronologia della conversazione.

---

## Dipendenze

```python
from model import Model
from utils import normalize_args

import logging
import asyncio
from openai import OpenAI
```

---

## Funzione a Livello di Modulo

### `mcp_tools_to_openai_tools(mcp_tools)`

```python
def mcp_tools_to_openai_tools(mcp_tools):
```

Converte la lista degli strumenti FastMCP nel formato previsto dal parametro `tools` di OpenAI.

#### Parametri

| Nome | Descrizione |
|------|-------------|
| `mcp_tools` | Lista di oggetti descrittori di strumenti FastMCP restituiti da `client.list_tools()` |

#### Restituisce

Una lista di dict con la seguente struttura:

```json
[
  {
    "type": "function",
    "function": {
      "name": "<nome strumento>",
      "description": "<descrizione strumento>",
      "parameters": { /* JSON Schema */ }
    }
  }
]
```

Se un descrittore di strumento non ha l'attributo `input_schema`, viene usato `{"type": "object", "properties": {}}` come fallback.

---

## Classe `OpenAIModel`

Eredita da `Model`.

### Costruttore

```python
class OpenAIModel(Model):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
```

Oltre all'inizializzazione della classe base:

- Crea il client SDK `openai.OpenAI`:
  - Se `url` è `None` o vuoto: `OpenAI(api_key=self.api_key)`
  - Altrimenti: `OpenAI(api_key=self.api_key, base_url=self.url)`
- Inizializza `self.messages` con un singolo messaggio di sistema:
  ```python
  [{"role": "system", "content": self.system}]
  ```

---

### Metodi

#### `init(self)`

Chiama `super().init()`. Può essere esteso per ulteriore configurazione lazy.

---

#### `init_tools(self, tools)`

```python
def init_tools(self, tools):
    super().init_tools(tools)
    self.available_tools = mcp_tools_to_openai_tools(tools)
```

Converte la lista degli strumenti MCP nel formato OpenAI e la memorizza in `self.available_tools`.

---

#### `set_system(self, system_prompt)`

```python
def set_system(self, system_prompt):
    super().set_system(system_prompt)
    self.messages[0] = {"role": "system", "content": system_prompt}
```

Aggiorna il messaggio di sistema all'indice 0 di `self.messages` oltre ad aggiornare `self.system`.

---

#### `create_message(self)` *(async)*

```python
async def create_message(self):
```

Invia la cronologia dei messaggi corrente all'API OpenAI e restituisce la prima scelta.

**Ciclo di retry:**

- Tenta fino a `self.max_tries` volte.
- In caso di successo, restituisce `response.choices[0]` (un oggetto `Choice`).
- In caso di fallimento, registra il messaggio di errore tramite `self.error_print` e attende `self.wait_seconds` prima di riprovare.
- Dopo aver esaurito tutti i tentativi, chiama `self.error_print("Maximum number of attempts reached …")` e restituisce `None`.

**Parametri della chiamata API:**

| Parametro | Valore |
|-----------|--------|
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

Gestisce un turno conversazionale completo, incluse tutte le chiamate agli strumenti necessarie per produrre la risposta finale.

**Flusso:**

1. Chiama `await self._examine_query(query)` per aggiungere il messaggio utente (o i messaggi del prompt MCP) a `self.messages`.
2. Entra in un ciclo finché `tool_use_detected` non è `False`:
   a. Chiama `self.check_summarize_needed(...)` e, se necessario, chiama `await self.summarize()`.
   b. Chiama `await self.create_message()` per ottenere la risposta del modello.
   c. Se `finish_reason == "stop"`: aggiunge il messaggio dell'assistente a `self.messages`, chiama `self.assistant_print` ed esce dal ciclo.
   d. Se `finish_reason == "tool_calls"`: itera su ogni chiamata agli strumenti, normalizza gli argomenti con `normalize_args`, chiama lo strumento tramite `self.client.call_tool(tool_name, tool_args)` e aggiunge il risultato come messaggio di ruolo `"tool"`. Imposta `tool_use_detected = True` per continuare il ciclo.

---

#### `summarize(self)` *(async)*

```python
async def summarize(self):
```

Comprime la cronologia della conversazione.

**Passi:**

1. Costruisce una cronologia temporanea con il prompt di sistema del riassunto e un messaggio utente contenente `self.messages[1:-2]` (escludendo il primo messaggio di sistema e gli ultimi due messaggi per preservare il contesto recente).
2. Chiama l'API OpenAI in modo sincrono (senza ciclo di retry) con `summarizer_max_tokens` e `summarizer_temperature`.
3. Sostituisce `self.messages` con:
   - Il messaggio di sistema originale.
   - Un secondo messaggio di sistema contenente il riassunto.
   - Gli ultimi due messaggi originali (preservati come contesto).

---

## Formato dei Messaggi

OpenAI usa una lista di dict. Ruoli usati in `self.messages`:

| Ruolo | Prodotto da |
|-------|-------------|
| `"system"` | Costruttore / `set_system()` / `summarize()` |
| `"user"` | `_examine_query()` |
| `"assistant"` | `process_query()` — risposta testuale finale |
| `"tool"` | `process_query()` — risultato della chiamata allo strumento |
| Oggetto `ChatCompletionMessage` | `process_query()` — messaggio grezzo dell'assistente quando vengono chiamati strumenti |
