# `model_factory.py` — Classe ModelFactory

## Panoramica del modulo

`model_factory.py` fornisce la classe `ModelFactory` — un **builder** che accumula la configurazione tramite un'API fluente di setter e poi costruisce la sottoclasse concreta corretta di `Model` tramite `build()`. Il suo obiettivo è validare tutte le impostazioni richieste al momento della costruzione e nascondere le firme dei costruttori specifici per provider al chiamante.

---

## Dipendenze

```python
from models.openai import OpenAIModel
from models.gemini import GeminiModel
from models.anthropic import AnthropicModel
```

Nessun pacchetto esterno viene importato direttamente; la factory delega la costruzione alle tre classi provider.

---

## Classe `ModelFactory`

### Costruttore

```python
class ModelFactory:
    def __init__(self):
```

Tutti gli attributi di configurazione sono impostati su valori predefiniti sensati o `None`:

| Attributo | Predefinito | Descrizione |
|-----------|-------------|-------------|
| `format` | `None` | Provider — impostato dai metodi `set_*_api_key` |
| `max_tokens` | `None` | Token massimi per risposta |
| `temperature` | `None` | Temperatura di campionamento |
| `name` | `None` | Identificatore del modello |
| `url` | `None` | URL base personalizzato opzionale |
| `api_key` | `None` | Chiave API del provider |
| `system_prompt` | `""` | Prompt di sistema iniziale |
| `max_tries` | `50` | Tentativi in caso di fallimenti API |
| `wait_seconds` | `6` | Secondi tra i tentativi |
| `summarizer_system_prompt` | `None` | Impostato da `set_summarizer_language()` |
| `summarizer_user_prompt` | `None` | Impostato da `set_summarizer_language()` |
| `summarizer_max_tokens` | `None` | Budget di token per il riassunto |
| `summarizer_temperature` | `0.3` | Temperatura per la generazione del riassunto |
| `assistant_print` | `None` | Callback di output per il testo dell'assistente |
| `system_print` | `None` | Callback di output per i messaggi di sistema |
| `error_print` | `None` | Callback di output per gli errori |

---

### Metodi di Configurazione del Provider

#### `set_openai_api_key(self, api_key: str)`

Imposta `format = "openai"`, memorizza `api_key` e cancella `url`. Da usare quando si chiama l'API ufficiale di OpenAI.

#### `set_openai_url(self, url: str)`

Imposta `format = "openai"`, memorizza `url` e cancella `api_key`. Da usare per endpoint locali o di terze parti compatibili con OpenAI che non richiedono una chiave.

#### `set_openai_api_key_and_url(self, api_key: str, url: str)`

Imposta `format = "openai"`, memorizza sia `api_key` che `url`. Da usare per endpoint compatibili con OpenAI che richiedono sia una chiave **che** un URL base personalizzato.

#### `set_gemini_api_key(self, api_key: str)`

Imposta `format = "gemini"`, memorizza `api_key`, cancella `url`.

#### `set_anthropic_api_key(self, api_key: str)`

Imposta `format = "anthropic"`, memorizza `api_key`, cancella `url`.

---

### Impostazioni del Modello

#### `set_name(self, name: str)`

Imposta l'identificatore del modello inviato all'API del provider (es. `"gpt-4o"`, `"claude-3-5-sonnet-20241022"`, `"gemini-1.5-pro"`).

#### `set_max_tokens(self, max_tokens: int)`

Imposta il numero massimo di token di output che il modello può generare per risposta.

#### `set_temperature(self, temperature: float)`

Imposta la temperatura di campionamento (tipicamente `0.0–2.0`).

#### `set_system_prompt(self, system_prompt: str)`

Imposta l'istruzione di sistema iniziale. Di default è `""` se non viene chiamato.

#### `set_max_tries(self, max_tries: int)`

Sovrascrive il valore predefinito di `50` tentativi.

#### `set_wait_seconds(self, wait_seconds: int)`

Sovrascrive il valore predefinito di `6` secondi tra i tentativi.

#### `set_prints(self, assistant_print, system_print, error_print)`

Registra i tre callback di output. Tutti e tre devono essere impostati prima che `build()` venga chiamato.

| Callback | Invocato quando |
|----------|----------------|
| `assistant_print` | L'assistente produce testo visibile |
| `system_print` | Il sistema emette messaggi informativi |
| `error_print` | Si verifica un errore o un evento di retry |

---

### Configurazione del Riassunto

Il riassunto della conversazione comprime la cronologia dei messaggi quando il conteggio dei token supera `max_tokens`, prevenendo il superamento della finestra di contesto.

#### `set_summarizer_max_tokens(self, max_tokens: int)`

Imposta il budget massimo di token per il riassunto generato. **Deve essere chiamato prima** di `set_summarizer_language()`.

#### `set_summarizer_language(self, language: str)`

Imposta i prompt di sistema e utente usati per il riassunto nella lingua specificata. Valori supportati:

| Lingua | `summarizer_system_prompt` (template) | `summarizer_user_prompt` |
|--------|--------------------------------------|--------------------------|
| `"english"` | `"You are an assistant that summarizes conversations …"` | `"Briefly summarize the following conversation:\n"` |
| `"italian"` | `"Sei un assistente che riassume le conversazioni …"` | `"Riassumi brevemente la seguente conversazione:\n"` |

Solleva `ValueError` se:
- `set_summarizer_max_tokens()` non è ancora stato chiamato.
- Viene passata una stringa di lingua non supportata.

---

### `build(self) → Model`

```python
def build(self):
```

Valida tutte le impostazioni richieste e costruisce la sottoclasse concreta appropriata di `Model`.

**Ordine di validazione:**

1. `format` non deve essere `None`.
2. `max_tokens` non deve essere `None`.
3. `temperature` non deve essere `None`.
4. `name` non deve essere `None`.
5. Tutti e tre i callback di print non devono essere `None`.
6. `summarizer_max_tokens` non deve essere `None`.
7. `summarizer_system_prompt` e `summarizer_user_prompt` non devono essere `None`.
8. Specifico per provider: almeno uno tra `api_key` / `url` deve essere impostato (OpenAI), oppure `api_key` deve essere impostato (Gemini, Anthropic).

Tutti i fallimenti sollevano `ValueError` con un messaggio descrittivo.

**Restituisce:** Un'istanza di `OpenAIModel`, `GeminiModel` o `AnthropicModel` con tutti gli attributi pre-popolati.

---

## Esempio d'Uso

```python
from model_factory import ModelFactory

factory = ModelFactory()

# Provider
factory.set_openai_api_key("sk-...")

# Impostazioni del modello
factory.set_name("gpt-4o")
factory.set_max_tokens(4096)
factory.set_temperature(0.7)
factory.set_system_prompt("Sei un assistente utile.")

# Callback di output
factory.set_prints(
    assistant_print=lambda msg: print(f"[AI] {msg}"),
    system_print=lambda msg: print(f"[SYS] {msg}"),
    error_print=lambda msg: print(f"[ERR] {msg}"),
)

# Riassunto
factory.set_summarizer_max_tokens(512)
factory.set_summarizer_language("italian")

# Costruire il modello
model = factory.build()
```

---

## Riferimento Errori

| Messaggio di errore | Causa |
|---------------------|-------|
| `"Model format not set"` | Nessuno dei metodi `set_*_api_key` è stato chiamato |
| `"You must call set_max_tokens before building the model"` | `set_max_tokens()` non è stato chiamato |
| `"You must call set_temperature before building the model"` | `set_temperature()` non è stato chiamato |
| `"You must call set_name before building the model"` | `set_name()` non è stato chiamato |
| `"You must call set_prints before building the model"` | `set_prints()` non è stato chiamato |
| `"You must call set_summarizer_max_tokens before building the model"` | `set_summarizer_max_tokens()` non è stato chiamato |
| `"You must call set_summarizer_language before building the model"` | `set_summarizer_language()` non è stato chiamato |
| `"You must call set_openai_api_key, set_openai_url or set_openai_api_key_and_url …"` | Formato OpenAI ma nessuna chiave API né URL |
| `"You must call set_gemini_api_key before building the model"` | Formato Gemini ma nessuna chiave API |
| `"You must call set_anthropic_api_key before building the model"` | Formato Anthropic ma nessuna chiave API |
| `"Unsupported model format: <format>"` | Valore di `format` sconosciuto (non dovrebbe accadere tramite API pubblica) |
| `"You must call set_summarizer_max_tokens before setting the language"` | `set_summarizer_language()` chiamato prima di `set_summarizer_max_tokens()` |
| `"Unsupported language for summarizer"` | Stringa di lingua diversa da `"english"` o `"italian"` |
