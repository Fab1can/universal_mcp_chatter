# `mcp_client.py` — Classe MCPClient

## Panoramica del modulo

`mcp_client.py` definisce `MCPClient`, il coordinatore di alto livello che:

1. Gestisce il ciclo di vita della connessione FastMCP `Client` a un server MCP.
2. Scopre e registra gli strumenti e i comandi prompt disponibili.
3. Delega l'elaborazione delle query all'istanza sottostante di `Model`.

---

## Dipendenze

```python
from fastmcp import Client
from fastmcp.client.logging import LogMessage
```

| Import | Scopo |
|--------|-------|
| `fastmcp.Client` | Client MCP asincrono usato per connettersi a un server di strumenti MCP |
| `fastmcp.client.logging.LogMessage` | Oggetto messaggio di log tipizzato emesso dal gestore di log FastMCP |

---

## Classe `MCPClient`

### Costruttore

```python
class MCPClient:
    def __init__(self, model):
```

#### Parametri

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `model` | `Model` | Un'istanza del modello completamente costruita prodotta da `ModelFactory.build()` |

#### Attributi inizializzati

| Attributo | Valore iniziale | Descrizione |
|-----------|-----------------|-------------|
| `self.client` | `None` | L'istanza `fastmcp.Client` creata lazy |
| `self.model` | `model` | Riferimento al modello sottostante |
| `self.assistant_print` | `model.assistant_print` | Scorciatoia al callback di output dell'assistente |
| `self.system_print` | `model.system_print` | Scorciatoia al callback dei messaggi di sistema |
| `self.error_print` | `model.error_print` | Scorciatoia al callback degli errori |

---

### Metodi

#### `get_client(self) → fastmcp.Client`

```python
def get_client(self):
```

Restituisce l'istanza `fastmcp.Client`, creandola alla prima chiamata (inizializzazione lazy).

**Comportamento:**

1. Se `self.client` è `None`, viene creato un nuovo `Client`:
   - URL di destinazione: `self.model.url` (impostato dalla factory).
   - Gestore di log: una funzione asincrona interna `_log_handler` che instrada i messaggi di livello `"error"` a `error_print` e tutti gli altri livelli a `system_print`.
2. Il client appena creato viene memorizzato sia in `self.client` che in `self.model.client` in modo che il modello possa chiamare gli strumenti attraverso la stessa connessione.
3. Alle chiamate successive, il client esistente viene restituito immediatamente.

**Restituisce:** L'istanza `fastmcp.Client`.

**Nota:** Il client restituito è progettato per essere usato come context manager asincrono:

```python
async with client.get_client():
    ...
```

---

#### `init(self)` *(async)*

```python
async def init(self):
```

Esegue la configurazione una tantum dopo che è stata stabilita una connessione al server MCP. Deve essere chiamato all'interno di un blocco `async with client.get_client():`.

**Passi:**

1. Chiama `list_tools()` sul client FastMCP e registra i nomi degli strumenti tramite `system_print`.
2. Chiama `list_prompts()` sul client FastMCP e registra i nomi dei prompt tramite `system_print`.
3. Chiama `self.model.init_tools(tools)` in modo che il modello possa convertire i descrittori degli strumenti nel formato specifico del provider.
4. Costruisce `self.available_prompts` — una lista di dict `{"name": ..., "description": ...}`.
5. Se vengono trovati dei prompt, aggiunge una lista formattata di comandi slash al prompt di sistema del modello usando `self.model.set_system(...)`. Il formato è:
   ```
   /nome_prompt - descrizione del prompt
   ```

---

#### `process_query(self, query)` *(async)*

```python
async def process_query(self, query):
    await self.model.process_query(query)
```

Wrapper sottile che delega la query al metodo `process_query` del modello sottostante. Deve essere chiamato all'interno di un blocco `async with client.get_client():` attivo dopo che `init()` è stato completato.

---

## Esempio d'Uso Completo

```python
import asyncio
from model_factory import ModelFactory
from mcp_client import MCPClient

async def main():
    # 1. Costruire il modello
    factory = ModelFactory()
    factory.set_openai_api_key("sk-...")
    factory.set_name("gpt-4o")
    factory.set_max_tokens(4096)
    factory.set_temperature(0.7)
    factory.set_prints(print, print, print)
    factory.set_summarizer_max_tokens(512)
    factory.set_summarizer_language("italian")
    model = factory.build()

    # 2. Creare il client MCP
    client = MCPClient(model)

    # 3. Connettersi, inizializzare e chattare
    async with client.get_client():
        await client.init()
        await client.process_query("Elenca tutti i database disponibili.")
        await client.process_query("/riassumi")   # Comando prompt MCP

asyncio.run(main())
```

---

## Note di Progettazione

- **Creazione lazy del client:** Il `Client` FastMCP non viene istanziato fino alla prima chiamata di `get_client()`. Questo rende l'oggetto `MCPClient` economico da creare e consente di modificare l'URL prima che la connessione venga aperta.
- **Riferimento condiviso al client:** Impostare `self.model.client = self.client` è essenziale — fornisce al modello accesso diretto a `call_tool()` in modo che i risultati degli strumenti possano essere recuperati all'interno di `process_query()` senza alcun instradamento aggiuntivo tramite `MCPClient`.
- **Comandi prompt:** Qualsiasi query che inizia con `/` viene trattata come un comando prompt MCP dal metodo base `Model._examine_query()`. `MCPClient.init()` assicura che l'utente sia a conoscenza dei comandi disponibili aggiungendoli al prompt di sistema.
