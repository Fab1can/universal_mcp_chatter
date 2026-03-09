# `utils.py` — Funzioni di Utilità

## Panoramica del modulo

`utils.py` contiene piccole funzioni helper stateless condivise tra le implementazioni dei provider. Attualmente espone due funzioni: `clean_object` e `normalize_args`.

---

## Dipendenze

```python
import json
```

È richiesto solo il modulo `json` della libreria standard.

---

## Funzioni

### `clean_object(obj)`

```python
def clean_object(obj):
```

Rimuove ricorsivamente i valori `None` da una struttura dati annidata composta da oggetti `dict` e `list`.

#### Parametri

| Nome | Tipo | Descrizione |
|------|------|-------------|
| `obj` | `dict`, `list` o qualsiasi scalare | L'oggetto da pulire |

#### Comportamento

- **dict:** Itera su tutte le chiavi ed elimina quelle il cui valore è `None`. Per i valori non `None`, applica `clean_object` ricorsivamente.
- **list:** Filtra gli elementi `None` e applica `clean_object` ricorsivamente agli elementi rimanenti.
- **Qualsiasi altro tipo:** Restituito invariato.

#### Restituisce

L'oggetto pulito (stesso tipo dell'input). I dict vengono modificati **in place** e restituiti.

#### Esempio

```python
clean_object({"a": 1, "b": None, "c": {"d": None, "e": 2}})
# → {"a": 1, "c": {"e": 2}}

clean_object([1, None, {"x": None, "y": 3}])
# → [1, {"y": 3}]
```

---

### `normalize_args(raw_args)`

```python
def normalize_args(raw_args):
```

Normalizza il payload degli argomenti delle chiamate agli strumenti prodotto da un modello AI in un `dict` Python pulito, adatto per essere passato a `client.call_tool()`.

#### Parametri

| Nome | Tipo | Descrizione |
|------|------|-------------|
| `raw_args` | `dict`, `str` o qualsiasi | Gli argomenti grezzi dalla risposta del modello |

#### Comportamento

1. **`dict`** — Usato direttamente come `obj`.
2. **`str`** — Ripulito degli spazi iniziali/finali, poi analizzato come JSON tramite `json.loads()`. Se l'analisi fallisce, viene racchiuso in `{"text": raw_args}`.
3. **Qualsiasi altro tipo** — Usato così com'è.

Dopo la normalizzazione del tipo, viene chiamato `clean_object(obj)` per rimuovere eventuali valori `None` prima di restituire.

#### Restituisce

Un `dict` con tutti i valori `None` rimossi.

#### Esempio

```python
normalize_args('{"key": "value", "empty": null}')
# → {"key": "value"}

normalize_args({"a": 1, "b": None})
# → {"a": 1}

normalize_args("json non valido")
# → {"text": "json non valido"}
```

---

## Note

- `normalize_args` è usata da `OpenAIModel` e `GeminiModel` quando si estraggono gli argomenti delle chiamate agli strumenti dalla risposta dell'API, poiché i modelli a volte restituiscono i payload degli argomenti come stringhe JSON anziché come dict già analizzati.
- `clean_object` rimuove i valori `None` perché alcuni SDK del provider rifiutano i corpi delle richieste contenenti campi `null` espliciti.
