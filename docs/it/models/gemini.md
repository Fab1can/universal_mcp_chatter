# `models/gemini.py` — Provider Gemini

## Panoramica del modulo

`models/gemini.py` implementa `GeminiModel`, l'integrazione del provider per l'[API Google Generative AI (Gemini)](https://ai.google.dev/). Estende la classe base `Model` e aggiunge:

- Conversione dei descrittori di strumenti MCP nel schema `function_declarations` di Gemini.
- Un ciclo di retry asincrono per le chiamate API.
- Un ciclo `process_query` multi-turno che gestisce le finish reason `STOP` (risposta finale) e `CALL_FUNCTION` (invocazione strumento).
- Un metodo di riassunto.
- Override di `get_messages` e `set_messages` per lavorare con oggetti `types.Content`.

---

## Dipendenze

```python
from model import Model
from utils import normalize_args

from google import genai
from google.genai import types
import asyncio
import logging
```

---

## Funzione a Livello di Modulo

### `mcp_tools_to_gemini_tools(mcp_tools)`

```python
def mcp_tools_to_gemini_tools(mcp_tools):
    """
    Convert the MCP tools obtained from list_tools() of a FastMCP client
    into the format required by Gemini (function_declarations).
    """
```

Converte la lista degli strumenti FastMCP nel formato `tools` di Gemini (una lista contenente un dict con la chiave `function_declarations`).

#### Parametri

| Nome | Descrizione |
|------|-------------|
| `mcp_tools` | Lista di oggetti descrittori di strumenti FastMCP restituiti da `client.list_tools()` |

#### Restituisce

```json
[
  {
    "function_declarations": [
      {
        "name": "<nome strumento>",
        "description": "<descrizione strumento>",
        "parameters": { /* JSON Schema */ }
      }
    ]
  }
]
```

Usa `getattr(t, "description", "")` e `getattr(t, "input_schema", {...})` con valori predefiniti sicuri.

---

## Classe `GeminiModel`

Eredita da `Model`.

### Costruttore

```python
class GeminiModel(Model):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
```

Chiama solo `super().__init__()`. Il client SDK e la lista dei messaggi vengono creati in `init()`.

---

### Metodi

#### `init(self)`

```python
def init(self):
    self.gemini = genai.client.Client(api_key=self.api_key)
    self.messages = [
        types.Content(role="user", parts=[types.Part(text=self.system)])
    ]
```

Crea il client SDK Gemini e inizializza `self.messages` con il prompt di sistema come primo messaggio `user`. **Nota:** Gemini non supporta nativamente un ruolo `system` nella cronologia della conversazione; il prompt di sistema viene iniettato come messaggio `user` alla posizione 0.

---

#### `init_tools(self, tools)`

Converte la lista degli strumenti MCP nel formato `function_declarations` di Gemini e la memorizza in `self.available_tools`.

---

#### `set_system(self, system_prompt)`

```python
def set_system(self, system_prompt):
    super().set_system(system_prompt)
    self.messages[0] = types.Content(role="user", parts=[types.Part(text=system_prompt)])
```

Aggiorna `self.system` e sostituisce il primo messaggio in `self.messages` con il nuovo prompt di sistema.

---

#### `create_message(self)` *(async)*

```python
async def create_message(self):
```

Invia la cronologia dei messaggi corrente all'API Gemini tramite il client asincrono.

**Ciclo di retry:**

- Tenta fino a `self.max_tries` volte.
- In caso di fallimento, chiama `self.error_print(str(e))` e attende `self.wait_seconds`.

**Parametri della chiamata API:**

| Parametro | Valore |
|-----------|--------|
| `model` | `self.name` |
| `contents` | `self.messages` |
| `config.temperature` | `self.temperature` |
| `config.max_output_tokens` | `self.max_tokens` |
| `config.tools` | `[self.client.session]` |

**Nota:** `tools=[self.client.session]` passa la sessione FastMCP direttamente a Gemini, che usa il routing nativo delle function-calling. Questo approccio è diverso da OpenAI/Anthropic, dove viene passata una lista di strumenti convertita.

---

#### `get_role_message(self, role, content)`

```python
def get_role_message(self, role, content):
    return types.Content(role=role, parts=[types.Part(text=content)])
```

Sovrascrive la classe base per restituire un oggetto `types.Content` invece di un dict semplice.

---

#### `process_query(self, query)` *(async)*

```python
async def process_query(self, query):
    """Process a query using a model and the available tools"""
```

Gestisce un turno conversazionale completo.

**Flusso:**

1. Chiama `await self._examine_query(query)`.
2. Entra in un ciclo finché `tool_use_detected` non è `False`:
   a. Opzionalmente chiama `await self.summarize()`.
   b. Chiama `await self.create_message()`.
   c. Legge `candidate.finish_reason`:
      - **`"STOP"`:** Legge `candidate.content.parts[0].text`, aggiunge un `Content` di ruolo `"model"` a `self.messages`, chiama `self.assistant_print` ed esce dal ciclo.
      - **`"CALL_FUNCTION"`:** Imposta `tool_use_detected = True`. Raccoglie tutte le parti `function_call` da `candidate.content`. Aggiunge un messaggio `"model"` per l'intenzione. Per ogni chiamata di funzione: normalizza gli argomenti con `normalize_args`, chiama `self.client.call_tool`, aggiunge il risultato come messaggio `"user"`.

---

#### `summarize(self)` *(async)*

```python
async def summarize(self):
```

Comprime la cronologia della conversazione.

**Passi:**

1. Costruisce una cronologia temporanea usando oggetti `types.Content` con ruoli `"system"` e `"user"`.
2. Chiama l'API Gemini in modo asincrono.
3. Legge il riassunto da `summarizer.candidates[0].parts[0].text`.
4. Sostituisce `self.messages` con un messaggio utente di sistema, un messaggio di sistema con il riassunto e gli ultimi due messaggi originali.

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

Sovrascrive la classe base per gestire liste di messaggi miste (dict da `set_messages` e oggetti `types.Content` dalle operazioni native).

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

Sostituisce l'intera cronologia dei messaggi, convertendo i messaggi in stile dict in oggetti `types.Content`.

---

## Formato dei Messaggi

Gemini usa oggetti `types.Content` in `self.messages`.

| Ruolo | Prodotto da |
|-------|-------------|
| `"user"` | Costruttore (prompt di sistema), `_examine_query()`, risultati degli strumenti |
| `"model"` | `process_query()` — risposte dell'assistente |
| `"system"` | `summarize()` — cronologia temporanea del riassunto |
