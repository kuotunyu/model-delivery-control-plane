from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping, Sequence
from typing import Any

_SENSITIVE_KEY = re.compile(r"token|secret|password|private", re.IGNORECASE)


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [redact_sensitive(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    """Format structured messages as deterministic, redacted JSON."""

    def format(self, record: logging.LogRecord) -> str:
        message = (
            record.msg if isinstance(record.msg, Mapping) else {"message": record.getMessage()}
        )
        payload = dict(redact_sensitive(message))
        payload["level"] = record.levelname
        payload["logger"] = record.name
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
