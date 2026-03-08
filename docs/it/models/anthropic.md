# `models/anthropic.py` — Provider Anthropic

## Panoramica del modulo

`models/anthropic.py` implementa `AnthropicModel`, l'integrazione del provider per l'[API Messages di Anthropic](https://docs.anthropic.com/en/api/messages) (modelli Claude). Estende la classe base `Model` e aggiunge:

- Conversione dei descrittori di strumenti MCP nel schema degli strumenti di Anthropic.
- Un ciclo di retry per le chiamate API con gestione dei messaggi di errore specifici di Anthropic.
- Un ciclo `process_query` multi-turno che gestisce i blocchi di contenuto `text` (risposta diretta) e `tool_use` (invocazione strumento).
- Un metodo di riassunto che comprime la cronologia della conversazione.

---

## Dipendenze

```python
from model import Model

from anthropic import Anthropic
from fastmcp import McpError
import asyncio
import logging
```

---

## Funzione a Livello di Modulo

### `mcp_tools_to_anthropic_tools(mcp_tools)`

```python
def mcp_tools_to_anthropic_tools(mcp_tools):
```

Converte la lista degli strumenti FastMCP nel formato previsto dal parametro `tools` di Anthropic.

#### Parametri

| Nome | Descrizione |
|------|-------------|
| `mcp_tools` | Lista di oggetti descrittori di strumenti FastMCP restituiti da `client.list_tools()` |

#### Restituisce

Una lista di dict con la seguente struttura:

```json
[
  {
    "name": "<nome strumento>",
    "description": "<descrizione strumento>",
    "input_schema": { /* JSON Schema */ }
  }
]
```

Usa `tool.inputSchema` (camelCase) come schema di input, che è il nome dell'attributo esposto da FastMCP per lo schema compatibile con Anthropic.

---

## Classe `AnthropicModel`

Eredita da `Model`.

### Costruttore

```python
class AnthropicModel(Model):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = None
```

Il client SDK Anthropic (`self.anthropic`) e la lista dei messaggi (`self.messages`) **non** vengono inizializzati nel costruttore; vengono creati in `init()`.

---

### Metodi

#### `init(self)`

```python
def init(self):
    self.anthropic = Anthropic(api_key=self.api_key)
    self.messages = []
```

Crea il client SDK Anthropic e imposta la lista iniziale dei messaggi come lista vuota. Nota: a differenza di OpenAI, l'API Messages di Anthropic passa il prompt di sistema come parametro separato di primo livello in ogni chiamata API (`system=self.system`), quindi non viene memorizzato in `self.messages`.

---

#### `init_tools(self, tools)`

```python
def init_tools(self, tools):
    super().init_tools(tools)
    self.available_tools = mcp_tools_to_anthropic_tools(tools)
```

Converte la lista degli strumenti MCP nel formato Anthropic.

---

#### `set_system(self, system_prompt)`

```python
def set_system(self, system_prompt):
    super().set_system(system_prompt)
```

Delega a `super().set_system()`. Poiché l'API Anthropic riceve il prompt di sistema come campo separato, non è necessario alcun aggiornamento aggiuntivo a `self.messages`.

---

#### `create_message(self)` *(async)*

```python
async def create_message(self):
```

Invia la cronologia dei messaggi corrente all'API Messages di Anthropic e restituisce l'oggetto risposta completo.

**Ciclo di retry:**

- Tenta fino a `self.max_tries` volte.
- Gestisce le seguenti condizioni di errore specifiche di Anthropic con messaggi utente personalizzati:
  - Crediti insufficienti.
  - Server sovraccarico.
  - Limite di richieste per minuto superato.
  - Qualsiasi altro valore di `e.body["error"]["message"]`.
  - Eccezioni generiche senza attributo `e.body`.
- Attende `self.wait_seconds` tra i tentativi.

**Parametri della chiamata API:**

| Parametro | Valore |
|-----------|--------|
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

Gestisce un turno conversazionale completo.

**Flusso:**

1. Chiama `await self._examine_query(query)`.
2. Entra in un ciclo finché `tool_use_detected` non è `False`:
   a. Opzionalmente chiama `await self.summarize()`.
   b. Chiama `await self.create_message()`.
   c. Estrae i blocchi di contenuto da `response.content` uno per uno:
      - **Blocco `text`:** Chiama `self.assistant_print(content.text)` e aggiunge a `assistant_parts`.
      - **Blocco `tool_use`:**
        1. Imposta `tool_use_detected = True`.
        2. Aggiunge un messaggio `"assistant"` contenente `assistant_parts + [content]` (blocchi di testo visti finora in questo turno **più** il blocco `tool_use`).
        3. Chiama `self.client.call_tool(tool_name, tool_args)` in un ciclo di retry interno che cattura `McpError`.
        4. Aggiunge un messaggio `"user"` contenente un blocco `tool_result` con `tool_use_id` e il contenuto restituito.
   d. Se non vengono trovati blocchi `tool_use`, aggiunge un messaggio finale `"assistant"` con `assistant_parts`.

---

#### `summarize(self)` *(async)*

```python
async def summarize(self):
```

Comprime la cronologia della conversazione.

**Passi:**

1. Costruisce una cronologia temporanea con i prompt di sistema e utente del riassunto più `self.messages[1:-2]`.
2. Chiama l'API Messages di Anthropic senza lista di strumenti.
3. Sostituisce `self.messages` con:
   - Un messaggio di sistema contenente `self.system`.
   - Un messaggio di sistema contenente il riassunto.
   - Gli ultimi due messaggi originali.

---

## Formato dei Messaggi

Anthropic usa una lista di dict in `self.messages`. Il prompt `system` viene passato separatamente.

| Ruolo | Tipo di contenuto | Prodotto da |
|-------|-------------------|-------------|
| `"user"` | Stringa semplice | `_examine_query()` |
| `"assistant"` | Lista di blocchi di contenuto | `process_query()` — blocchi testo + tool_use |
| `"user"` | Lista con blocco `tool_result` | `process_query()` — risultato dello strumento |
| `"system"` | Stringa | Solo `summarize()` |
