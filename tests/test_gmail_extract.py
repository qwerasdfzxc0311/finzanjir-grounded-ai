import base64

from finzanjir_ai.integrations.gmail_extract import extract_gmail_message


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
