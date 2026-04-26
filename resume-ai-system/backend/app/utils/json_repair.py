"""Best-effort JSON extraction from LLM responses.

Models occasionally wrap JSON in markdown fences, prepend chatter, or emit
trailing commentary. This module strips that noise and parses the largest
balanced JSON object in the response.
"""
from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> dict[str, Any] | list[Any]:
    """Parse JSON from a possibly-noisy LLM response.

    Strategy:
      1. If the whole string parses, return that.
      2. If wrapped in a ```json ... ``` fence, extract and parse.
      3. Otherwise scan for the first balanced { ... } or [ ... ] block.

    Raises json.JSONDecodeError if no valid JSON is found.
    """
    text = text.strip()

    # Fast path
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Markdown fence
    fence_match = _FENCE_RE.search(text)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Balanced-bracket scan
    for opener, closer in [("{", "}"), ("[", "]")]:
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if c == opener:
                depth += 1
            elif c == closer:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    raise json.JSONDecodeError("No valid JSON found in response", text, 0)
