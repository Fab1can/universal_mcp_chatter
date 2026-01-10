import pytest

from utils import clean_object, normalize_args


def test_clean_object_removes_nones_nested():
    data = {
        "a": 1,
        "b": None,
        "c": {"d": None, "e": 2},
        "f": [1, None, {"g": None, "h": 3}],
    }
    expected = {
        "a": 1,
        "c": {"e": 2},
        "f": [1, {"h": 3}],
    }
    assert clean_object(data) == expected


def test_normalize_args_with_dict_returns_cleaned():
    raw = {"a": 1, "b": None, "c": [1, None, 2]}
    expected = {"a": 1, "c": [1, 2]}
    assert normalize_args(raw) == expected


def test_normalize_args_with_valid_json_string():
    raw = '{"a": 1, "b": null, "c": [1, null, 2]}'
    expected = {"a": 1, "c": [1, 2]}
    assert normalize_args(raw) == expected


def test_normalize_args_with_non_json_string():
    raw = "ciao mondo"
    expected = {"text": "ciao mondo"}
    assert normalize_args(raw) == expected
