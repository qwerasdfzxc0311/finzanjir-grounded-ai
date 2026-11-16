"""Bounded extraction of user-selected Gmail message bodies."""
from __future__ import annotations

import base64
from email.header import decode_header, make_header
from html.parser import HTMLParser
from typing import Any

MAX_MESSAGE_BYTES = 2 * 1024 * 1024


class _TextOnlyHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "head"}:
            self.hidden_depth += 1
        elif tag.lower() in {"p", "div", "br", "li", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "head"} and self.hidden_depth:
            self.hidden_depth -= 1
        elif tag.lower() in {"p", "div", "li", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden_depth:
            self.parts.append(data)


def _decode_header(value: str) -> str:
    try:
        return str(make_header(decode_header(value)))
    except (ValueError, TypeError):
        return value


def _decode_body(data: str) -> bytes:
    try:
        decoded = base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
    except (ValueError, TypeError) as exc:
        raise ValueError("Gmail body is not valid base64url") from exc
    if len(decoded) > MAX_MESSAGE_BYTES:
        raise ValueError("Gmail message body exceeds the 2 MB limit")
    return decoded


def extract_gmail_message(message: dict[str, Any]) -> dict[str, Any]:
    payload = message.get("payload") or {}
    headers = {}
    for item in payload.get("headers", []):
        if isinstance(item, dict) and item.get("name"):
            headers[str(item["name"]).lower()] = _decode_header(str(item.get("value", "")))
    plain: list[str] = []
    html: list[str] = []
    total = 0

    def visit(part: dict[str, Any]):
        nonlocal total
        mime = str(part.get("mimeType") or "").lower()
        body = part.get("body") or {}
        data = body.get("data")
        if data and mime in {"text/plain", "text/html"}:
            decoded = _decode_body(str(data))
            total += len(decoded)
            if total > MAX_MESSAGE_BYTES:
                raise ValueError("Gmail message body exceeds the 2 MB limit")
            text = decoded.decode("utf-8", errors="replace")
            if mime == "text/plain":
                plain.append(text)
            else:
                html.append(text)
        for child in part.get("parts", []) or []:
            if isinstance(child, dict):
                visit(child)

    visit(payload)
    if plain:
        body_text = "\n".join(plain)
        extractor = "gmail-mime-text-v1"
    elif html:
        parser = _TextOnlyHTML()
        for fragment in html:
            parser.feed(fragment)
        body_text = "".join(parser.parts)
        extractor = "gmail-html-text-v1"
    else:
        body_text = str(message.get("snippet") or "")
        extractor = "gmail-snippet-v1"
    body_text = "\n".join(line.rstrip() for line in body_text.replace("\x00", "").splitlines()).strip()
    if not body_text:
        raise ValueError("Gmail message contains no readable body text")
    if len(body_text.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise ValueError("Gmail message body exceeds the 2 MB limit")
    header_text = "\n".join(
        f"{name}: {headers[name]}" for name in ("from", "to", "cc", "subject", "date")
        if headers.get(name)
    )
    full_text = (header_text + "\n\n" + body_text).strip()
    return {
        "text": full_text,
        "extractor": extractor,
        "headers": {key: headers[key] for key in ("from", "to", "cc", "subject", "date") if key in headers},
    }
