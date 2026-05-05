"""
NHS Classifications Browser tool for the clinical coding agent.

Provides a direct REST API client for classbrowser.nhs.uk — no browser required.
Exposes a Claude tool definition so the agent can search ICD-10 and OPCS-4 live.
"""

from __future__ import annotations

import base64
import ctypes
import re
import urllib.parse
from typing import Any

import requests

_BOOKS = {
    "ICD-10": "ICD-10-5TH-Edition",
    "OPCS-4": "OPCS-4.11",
}

_BASE_URL = "https://classbrowser.nhs.uk"

_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
            ),
            "Referer": _BASE_URL + "/",
            "Accept": "*/*",
        })
        s.get(_BASE_URL + "/", timeout=10)
        _session = s
    return _session


def _encode_uri(s: str) -> str:
    """Equivalent to JavaScript's encodeURI — does not encode standard URI chars."""
    return urllib.parse.quote(s, safe=";,/?:@&=+$-_.!~*'()#[]")


def _js_hash(s: str) -> int:
    """Replicates the stringToHash() function from classbrowser search.js."""
    h = 0
    for c in s:
        h = ctypes.c_int32(ctypes.c_int32(h << 5).value - h + ord(c)).value
    return h


def _build_request_args(search_term: str, book_id: str) -> tuple[str, int]:
    """Return (base64_arg, hash) for the given search term and book."""
    search_json = (
        '{  '
        '    "branches": []'
        '  , "releaseVersions": [       "' + book_id + '"     ]'
        '  ,  "searchContent": "' + search_term + '"  }'
    )
    b64 = base64.b64encode(_encode_uri(search_json).encode()).decode()
    return b64, _js_hash(b64)


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    return (
        text.replace("&#10148;", "→")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .strip()
    )


def _flatten_results(node: dict, depth: int = 0) -> list[str]:
    """Recursively flatten the jstree response into labelled text lines."""
    lines: list[str] = []
    text = _strip_html(node.get("text", ""))
    if depth == 0:
        lines.append(text)
    elif depth == 1:
        lines.append(f"\n[{text}]")
    elif text:
        lines.append(f"  • {text}")
    for child in node.get("children", []):
        lines.extend(_flatten_results(child, depth + 1))
    return lines


def search_classbrowser(search_term: str, classification: str) -> str:
    """
    Search the NHS Classifications Browser and return a formatted text summary.

    Args:
        search_term: Clinical term to search (e.g. 'appendicitis', 'polypectomy').
        classification: 'ICD-10' for diagnoses or 'OPCS-4' for procedures.

    Returns:
        Formatted text summary of matching entries from the alphabetical index
        and tabular list, suitable for inclusion in a Claude conversation.
    """
    book_id = _BOOKS.get(classification.upper().replace(" ", "-"))
    if not book_id:
        return f"Unknown classification '{classification}'. Use 'ICD-10' or 'OPCS-4'."

    try:
        session = _get_session()
        b64, h = _build_request_args(search_term, book_id)
        url = f"{_BASE_URL}/bookdoc/search/{book_id}/{h}"
        response = session.get(url, headers={"searchArg-base64": b64}, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return f"NHS Classifications Browser lookup failed: {exc}"

    summary_line = _strip_html(data.get("text", "No results"))
    if "0 matches" in summary_line or not data.get("children"):
        return f"{summary_line} for '{search_term}' in {classification}."

    lines = [f"{summary_line} for '{search_term}' in {classification} 5th Edition:\n"]
    for group in data.get("children", []):
        group_lines = _flatten_results(group)
        # Cap each volume at 20 entries to keep context concise
        cap = 20
        if len(group_lines) > cap:
            group_lines = group_lines[:cap] + [f"  … ({len(group_lines) - cap} more entries)"]
        lines.extend(group_lines)

    return "\n".join(lines)


# ── Claude tool definition ────────────────────────────────────────────────────

TOOL_DEFINITION: dict[str, Any] = {
    "name": "search_classbrowser",
    "description": (
        "Search the official NHS Classifications Browser (classbrowser.nhs.uk) "
        "for ICD-10 5th Edition diagnosis codes or OPCS-4.11 procedure codes. "
        "Use this to verify a proposed code is correct, find the right code for "
        "a clinical condition or procedure, or resolve ambiguity between similar codes. "
        "Always search before finalising codes for the primary diagnosis and primary procedure."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "search_term": {
                "type": "string",
                "description": (
                    "The clinical term to search for. Use the medical/clinical name "
                    "rather than abbreviations (e.g. 'colonoscopy' not 'OGD', "
                    "'haemorrhoids' not 'piles')."
                ),
            },
            "classification": {
                "type": "string",
                "enum": ["ICD-10", "OPCS-4"],
                "description": "ICD-10 for diagnosis codes, OPCS-4 for procedure codes.",
            },
        },
        "required": ["search_term", "classification"],
    },
}


def handle_tool_call(tool_name: str, tool_input: dict) -> str:
    """Dispatch a Claude tool_use block to the correct function."""
    if tool_name == "search_classbrowser":
        return search_classbrowser(
            search_term=tool_input["search_term"],
            classification=tool_input["classification"],
        )
    return f"Unknown tool: {tool_name}"
