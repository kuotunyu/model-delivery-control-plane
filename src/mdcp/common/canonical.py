from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

import rfc8785

type JsonScalar = None | bool | int | float | str
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


class CanonicalizationError(ValueError):
    """The input cannot be represented as unambiguous canonical JSON."""


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise CanonicalizationError("non-finite number")
    if isinstance(value, Mapping):
        for nested in value.values():
            _reject_non_finite(nested)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for nested in value:
            _reject_non_finite(nested)


def canonicalize_json(value: JsonValue) -> bytes:
    _reject_non_finite(value)
    try:
        return rfc8785.dumps(value)
    except (TypeError, ValueError, UnicodeError) as error:
        raise CanonicalizationError("value is not RFC 8785 canonicalizable") from error


def parse_json_bytes(raw: bytes) -> JsonValue:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise CanonicalizationError("input is not UTF-8") from error

    def reject_duplicate_keys(pairs: list[tuple[str, JsonValue]]) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {}
        for key, value in pairs:
            if key in result:
                raise CanonicalizationError("duplicate object key")
            result[key] = value
        return result

    def reject_non_standard_number(_value: str) -> None:
        raise CanonicalizationError("non-finite number")

    try:
        parsed = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_standard_number,
        )
    except CanonicalizationError:
        raise
    except (json.JSONDecodeError, UnicodeError) as error:
        raise CanonicalizationError("input is not valid JSON") from error
    _reject_non_finite(parsed)
    return parsed
