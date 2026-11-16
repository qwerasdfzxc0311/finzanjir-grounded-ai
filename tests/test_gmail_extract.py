import base64

from finzanjir_ai.integrations.gmail_extract import (
    collect_gmail_attachments, decode_gmail_attachment_data, extract_gmail_message,
)


def b64(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_extract_selected_gmail_plain_text_and_headers():
    message = {
        "id": "message-123",
        "threadId": "thread-1",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "sender@example.com"},
                {"name": "Subject", "value": "Research notes"},
                {"name": "Date", "value": "Mon, 16 Nov 2026 10:00:00 +0000"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": b64("FINZANJIR research body")}},
                {"mimeType": "text/html", "body": {"data": b64("<p>HTML fallback</p>")}},
            ],
        },
    }
    result = extract_gmail_message(message)
    assert result["extractor"] == "gmail-mime-text-v1"
    assert "Subject: Research notes" in result["text"]
    assert "FINZANJIR research body" in result["text"]


def test_extract_gmail_html_strips_scripts_and_markup():
    message = {
        "payload": {
            "mimeType": "text/html",
            "headers": [{"name": "Subject", "value": "HTML message"}],
            "body": {"data": b64("<html><script>steal()</script><p>Hello <b>FINZANJIR</b></p></html>")},
        }
    }
    result = extract_gmail_message(message)
    assert result["extractor"] == "gmail-html-text-v1"
    assert "Hello FINZANJIR" in result["text"]
    assert "steal()" not in result["text"]
    assert "<b>" not in result["text"]


def test_gmail_snippet_fallback_and_empty_rejection():
    result = extract_gmail_message({"snippet": "Short message preview", "payload": {}})
    assert result["extractor"] == "gmail-snippet-v1"
    assert result["text"] == "Short message preview"
    try:
        extract_gmail_message({"snippet": "", "payload": {}})
    except ValueError:
        pass
    else:
        raise AssertionError("empty message was accepted")


def test_collect_named_gmail_attachments_and_decode_inline_content():
    message = {
        "payload": {
            "mimeType": "multipart/mixed",
            "parts": [
                {
                    "filename": "notes.txt", "mimeType": "text/plain",
                    "body": {"attachmentId": "attachment-1", "size": 5},
                },
                {
                    "filename": "photo.jpg", "mimeType": "image/jpeg",
                    "body": {"data": b64("image-bytes"), "size": 10},
                },
                {"mimeType": "text/plain", "body": {"data": b64("email body")}},
            ],
        }
    }
    attachments = collect_gmail_attachments(message)
    assert [item["filename"] for item in attachments] == ["notes.txt", "photo.jpg"]
    assert attachments[0]["attachment_id"] == "attachment-1"
    assert decode_gmail_attachment_data(attachments[1]["inline_data"]) == b"image-bytes"
    body = extract_gmail_message(message)
    assert "email body" in body["text"]
    assert "image-bytes" not in body["text"]


def test_gmail_attachment_decode_has_separate_ten_megabyte_limit():
    import pytest
    huge = b64("x" * (10 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="10 MB"):
        decode_gmail_attachment_data(huge)
