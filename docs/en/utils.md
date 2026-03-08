# `utils.py` — Utility Functions

## Module overview

`utils.py` contains small, stateless helper functions shared across the provider implementations. Currently it exposes two functions: `clean_object` and `normalize_args`.

---

## Dependencies

```python
import json
```

Only the standard library `json` module is required.

---

## Functions

### `clean_object(obj)`

```python
def clean_object(obj):
```

Recursively removes `None` values from a nested data structure consisting of `dict` and `list` objects.

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `obj` | `dict`, `list`, or any scalar | The object to clean |

#### Behaviour

- **dict:** Iterates over all keys and deletes any whose value is `None`. For non-`None` values, applies `clean_object` recursively.
- **list:** Filters out `None` elements and applies `clean_object` recursively to the remaining items.
- **Any other type:** Returned unchanged.

#### Returns

The cleaned object (same type as input). Dicts are modified **in place** and also returned.

#### Example

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

Normalises the tool-call argument payload produced by an AI model into a clean Python `dict`, suitable for passing to `client.call_tool()`.

#### Parameters

| Name | Type | Description |
|------|------|-------------|
| `raw_args` | `dict`, `str`, or any | The raw arguments from the model response |

#### Behaviour

1. **`dict`** — Used directly as `obj`.
2. **`str`** — Stripped of leading/trailing whitespace, then parsed as JSON via `json.loads()`. If parsing fails, wrapped in `{"text": raw_args}`.
3. **Any other type** — Used as-is.

After type normalisation, `clean_object(obj)` is called to strip any `None` values before returning.

#### Returns

A `dict` with all `None` values removed.

#### Example

```python
normalize_args('{"key": "value", "empty": null}')
# → {"key": "value"}

normalize_args({"a": 1, "b": None})
# → {"a": 1}

normalize_args("not valid json")
# → {"text": "not valid json"}
```

---

## Notes

- `normalize_args` is used by `OpenAIModel` and `GeminiModel` when extracting tool-call arguments from the API response, as models sometimes return argument payloads as JSON strings rather than pre-parsed dicts.
- `clean_object` removes `None` values because some provider SDKs reject request bodies containing explicit `null` fields.
