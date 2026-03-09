# `model.py` — Classe Base Model

## Panoramica del modulo

`model.py` definisce la classe base astratta `Model`, che ogni implementazione specifica per provider (OpenAI, Anthropic, Gemini) deve estendere. Raccoglie tutta la configurazione condivisa tra i provider e fornisce la gestione della cronologia dei messaggi, il meccanismo di riassunto basato sui token e la gestione dei comandi prompt MCP.

---

## Dipendenze

| Import | Scopo |
|--------|-------|
| `logging` | Logging standard di Python |
| `fastmcp.McpError` | Eccezione sollevata quando un'operazione MCP fallisce |
| `tiktoken` | Usato per contare i token nella cronologia dei messaggi corrente |

```python
import logging
from fastmcp import McpError
import tiktoken
TIKTOKEN = tiktoken.get_encoding("o200k_base")
```

`TIKTOKEN` è un singleton a livello di modulo; la codifica viene inizializzata una sola volta per ridurre il costo di istanziazione.

---

## Classe `Model`

### Costruttore

```python
class Model:
    def __init__(
        self,
        format: str,
        max_tokens: int,
        temperature: float,
        name: str,
        url: str,
        api_key: str,
        system_prompt: str,
        max_tries: int,
        wait_seconds: int,
        summarizer_system_prompt: str,
        summarizer_user_prompt: str,
        summarizer_max_tokens: int,
        summarizer_temperature: float,
        assistant_print,
        system_print,
        error_print,
    ):
```

Tutti gli argomenti vengono memorizzati come attributi di istanza. Il costruttore viene chiamato esclusivamente da `ModelFactory.build()`.

#### Parametri

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `format` | `str` | Identificatore del provider — `"openai"`, `"anthropic"` o `"gemini"` |
| `max_tokens` | `int` | Numero massimo di token che il modello può generare per risposta |
| `temperature` | `float` | Temperatura di campionamento (creatività vs. determinismo) |
| `name` | `str` | Identificatore del modello inviato all'API del provider (es. `"gpt-4o"`) |
| `url` | `str` | URL base personalizzato opzionale per endpoint compatibili OpenAI |
| `api_key` | `str` | Chiave API del provider |
| `system_prompt` | `str` | Istruzione di sistema iniziale per l'assistente |
| `max_tries` | `int` | Numero massimo di tentativi in caso di errori API prima di rinunciare |
| `wait_seconds` | `int` | Secondi di attesa tra i tentativi |
| `summarizer_system_prompt` | `str` | Prompt di sistema usato per riassumere la conversazione |
| `summarizer_user_prompt` | `str` | Prefisso del prompt utente usato per il riassunto |
| `summarizer_max_tokens` | `int` | Budget di token per il riassunto generato |
| `summarizer_temperature` | `float` | Temperatura usata per la chiamata di riassunto |
| `assistant_print` | `callable` | Callback invocato con l'output testuale visibile dell'assistente |
| `system_print` | `callable` | Callback invocato per messaggi di sistema informativi |
| `error_print` | `callable` | Callback invocato per messaggi di errore |

#### Attributi inizializzati a `None`

| Attributo | Impostato da |
|-----------|-------------|
| `self.client` | `MCPClient.get_client()` |
| `self.response` | `process_query()` |
| `self.available_tools` | `init_tools()` |
| `self.available_prompts` | `MCPClient.init()` |

---

### Metodi

#### `init(self)`

```python
def init(self):
    pass
```

Hook chiamato dopo la costruzione. Le sottoclassi sovrascrivono questo metodo per eseguire l'inizializzazione lazy (es. creazione del client SDK del provider e della lista iniziale dei messaggi).

---

#### `init_tools(self, tools)`

```python
def init_tools(self, tools):
    pass
```

Chiamato da `MCPClient.init()` dopo che la lista degli strumenti del server MCP è stata recuperata. Le sottoclassi sovrascrivono questo metodo per convertire i descrittori degli strumenti MCP nel formato richiesto dal loro SDK del provider.

**Parametri**

| Nome | Descrizione |
|------|-------------|
| `tools` | Lista di descrittori di strumenti `fastmcp` restituiti da `client.list_tools()` |

---

#### `set_system(self, system_prompt: str)`

```python
def set_system(self, system_prompt: str):
    self.system = system_prompt
```

Sostituisce il prompt di sistema attivo. `MCPClient.init()` chiama questo metodo per aggiungere i comandi prompt MCP disponibili all'istruzione di sistema originale. Le sottoclassi che memorizzano il prompt di sistema all'interno della lista dei messaggi (es. `OpenAIModel`) devono sovrascrivere questo metodo per mantenere coerente il messaggio memorizzato.

---

#### `get_user_message(self, query: str) → dict`

```python
def get_user_message(self, query: str):
    return self.get_role_message("user", query)
```

Wrapper di convenienza che crea un dict-messaggio `{"role": "user", "content": query}`.

---

#### `get_role_message(self, role: str, content: str) → dict`

```python
def get_role_message(self, role: str, content: str):
    return {"role": role, "content": content}
```

Restituisce un dict-messaggio standard. Le sottoclassi che usano un tipo di messaggio diverso (es. `GeminiModel` usa `types.Content`) sovrascrivono questo metodo.

---

#### `check_summarize_needed(self, next_message) → bool`

```python
def check_summarize_needed(self, next_message):
```

Restituisce `True` quando il conteggio dei token dell'intera cronologia della conversazione più `next_message` raggiunge o supera `self.max_tokens`, **e** tutti e tre i campi di configurazione del riassunto sono impostati.

**Logica**

1. Se uno qualsiasi dei valori di configurazione del riassunto è `None`, restituisce `False` immediatamente.
2. Costruisce uno snapshot: `list(self.get_messages()) + next_message`.
3. Codifica lo snapshot come stringa UTF-8 usando `tiktoken` e conta i token risultanti.
4. Restituisce `True` se `token_count >= self.max_tokens`.

---

#### `_examine_query(self, query)` *(async)*

```python
async def _examine_query(self, query):
```

Esamina la stringa di query in ingresso. Se la query inizia con `/`, viene trattata come un comando prompt MCP:

- Il metodo chiama `self.client.get_prompt(query[1:])` per recuperare i messaggi del prompt dal server MCP.
- Ogni messaggio recuperato viene aggiunto a `self.messages` tramite `get_role_message`.
- Se la chiamata MCP solleva `McpError` (prompt non trovato, errore del server), la query grezza viene aggiunta come normale messaggio utente.

Se la query non inizia con `/`, viene aggiunta a `self.messages` come normale messaggio utente.

---

#### `process_query(self, query)` *(async)*

```python
async def process_query(self, query):
    pass
```

Punto di ingresso per un singolo turno conversazionale. Deve essere sovrascritta da ogni sottoclasse concreta. Chiamata da `MCPClient.process_query()`.

---

#### `summarize(self)` *(async)*

```python
async def summarize(self):
    pass
```

Produce un riassunto compresso della cronologia della conversazione e sostituisce `self.messages` con una rappresentazione più breve. Deve essere sovrascritta da ogni sottoclasse concreta.

---

#### `get_messages(self)`

```python
def get_messages(self):
    for msg in self.messages:
        yield msg
```

Generatore che produce ogni messaggio in `self.messages`. Le sottoclassi che usano oggetti messaggio tipizzati (es. `GeminiModel`) sovrascrivono questo metodo per normalizzare i valori restituiti.

---

#### `set_messages(self, messages)`

```python
def set_messages(self, messages):
    self.messages = [{"role": "system", "content": self.system}]
    for message in messages:
        self.messages.append({"role": message["role"], "content": message["content"]})
```

Sostituisce l'intera cronologia dei messaggi. Inserisce il prompt di sistema corrente come primo elemento.

---

## Note di Progettazione

- `Model` è progettata come classe base astratta; non viene mai istanziata direttamente. `ModelFactory.build()` restituisce sempre una sottoclasse concreta.
- I tre callback `*_print` disaccoppiano la formattazione dell'output dalla logica del modello, consentendo al chiamante di usare terminali ricchi, framework di logging o widget GUI senza modificare il codice del modello.
- L'attributo `client` viene impostato da `MCPClient` dopo la costruzione e prima della prima chiamata a `process_query`. Questa iniezione tardiva evita una dipendenza circolare tra `Model` e `MCPClient`.
