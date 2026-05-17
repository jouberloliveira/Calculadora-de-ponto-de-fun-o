"""Prompt construction for Ollama.

Strips obvious prompt-injection vectors from extracted source text. The LLM
is instructed to respond ONLY with JSON matching the contract; the response
is then re-validated by Pydantic in the caller.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from app.ingest import ExtractedFile

SYSTEM_PROMPT = """You are an IFPUG-certified Function Point counter.
Analyze the provided project files and produce a Function Point analysis.

Rules:
- Identify each transactional function (EI/EO/EQ) and data function (ILF/EIF).
- Classify each function's complexity as "low", "medium", or "high".
- Provide all 14 IFPUG General System Characteristics with values 0..5.
- Respond with a SINGLE JSON OBJECT. No prose, no markdown fences.
- The JSON object MUST match this schema:

{
  "functions": [
    {
      "type": "EI" | "EO" | "EQ" | "ILF" | "EIF",
      "name": "string",
      "complexity": "low" | "medium" | "high",
      "justification": "string"
    }
  ],
  "vafFactors": [
    { "name": "string", "value": 0..5, "rationale": "string" }
  ]
}

Do not include any other top-level keys."""

# Lines that look like a user-injected instruction targeting the LLM.
_INJECTION_PATTERNS = [
    re.compile(r"(?im)^\s*(ignore|disregard).{0,40}(previous|prior|above)\b.*$"),
    re.compile(r"(?im)^\s*system\s*:.*$"),
    re.compile(r"(?im)^\s*assistant\s*:.*$"),
    re.compile(r"(?im)^\s*you are now\b.*$"),
]


def _sanitize(text: str) -> str:
    out = text
    for pat in _INJECTION_PATTERNS:
        out = pat.sub("[stripped]", out)
    return out


def _safe_filename(name: str) -> str:
    """Strip Unicode control characters from a filename.

    Archive member filenames and HTTP multipart filenames are attacker-controlled
    and embedded directly in the LLM prompt header. A name containing embedded
    newlines or other control chars could break out of the header and inject
    instructions. ``unicodedata.category`` starts with ``C`` for all control
    categories (Cc, Cf, Cn, Co, Cs).
    """
    return "".join(ch for ch in name if not unicodedata.category(ch).startswith("C"))


def build_prompt(
    files: Iterable[ExtractedFile],
    *,
    max_total_chars: int = 60_000,
) -> str:
    """Concatenate sanitized file contents into a single user message."""
    blocks: list[str] = []
    used = 0
    for f in files:
        header = f"\n--- FILE: {_safe_filename(f.name)} ---\n"
        budget = max_total_chars - used - len(header)
        if budget <= 0:
            break
        body = _sanitize(f.content)[:budget]
        blocks.append(header + body)
        used += len(header) + len(body)
    joined = "".join(blocks) if blocks else "(no readable files)"
    return (
        "Analyze the following project files and return the JSON object as "
        "specified by the system instructions.\n"
        f"{joined}\n"
    )
