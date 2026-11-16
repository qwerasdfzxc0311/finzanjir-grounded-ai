import pytest
from cryptography.fernet import Fernet

from finzanjir_ai.integrations.drive_extract import (
    MAX_DOWNLOAD_BYTES,
    UnsupportedDriveFormat,
    extract_drive_text,
)
from finzanjir_ai.integrations.personal_memory import PersonalMemoryStore


def test_extract_utf8_text_and_csv():
    text = extract_drive_text("notes.txt", "text/plain", "Salom\nFINZANJIR".encode())
    assert text["text"] == "Salom\nFINZANJIR"
    assert text["extractor"] == "utf8-text-v1"
    csv = extract_drive_text("table.csv", "text/csv", b"name,value\nA,10\nB,20")
    assert "name\tvalue" in csv["text"]
    assert "A\t10" in csv["text"]


def test_reject_unsupported_and_oversized_content():
    with pytest.raises(UnsupportedDriveFormat):
        extract_drive_text("photo.png", "image/png", b"fake-image")
    with pytest.raises(ValueError):
        extract_drive_text("large.txt", "text/plain", b"x" * (MAX_DOWNLOAD_BYTES + 1))


def test_reject_invalid_utf8_in_text_file():
    with pytest.raises(UnicodeDecodeError):
        extract_drive_text("broken.txt", "text/plain", b"\xff\xfe")


def test_docx_text_and_table_extraction():
    from docx import Document
    import io

    doc = Document()
    doc.add_paragraph("FINZANJIR hujjati")
    table = doc.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Nomi"
    table.cell(0, 1).text = "Qiymati"
    output = io.BytesIO()
    doc.save(output)
    extracted = extract_drive_text(
        "concept.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        output.getvalue(),
    )
    assert "FINZANJIR hujjati" in extracted["text"]
    assert "Nomi\tQiymati" in extracted["text"]


def test_pdf_text_extraction():
    from reportlab.pdfgen import canvas
    import io

    output = io.BytesIO()
    pdf = canvas.Canvas(output)
    pdf.drawString(72, 720, "FINZANJIR PDF source")
    pdf.save()
    extracted = extract_drive_text("source.pdf", "application/pdf", output.getvalue())
    assert "FINZANJIR PDF source" in extracted["text"]


def test_personal_memory_is_encrypted_owner_scoped_and_quarantined(tmp_path):
    key = Fernet.generate_key().decode()
    path = tmp_path / "memory.sqlite"
    store = PersonalMemoryStore(str(path), key)
    saved = store.quarantine(
        owner_email="owner@example.com", account_id="acc-1",
        remote_file_id="drive-file-1", file_name="notes.txt",
        mime_type="text/plain", modified_time="2026-11-16T10:00:00Z",
        extracted_text="My private notes",
        metadata={"extractor": "utf8-text-v1"},
    )
    assert saved["status"] == "quarantined"
    raw = path.read_bytes()
    assert b"My private notes" not in raw
    assert store.read_source("owner@example.com", saved["source_id"])["text"] == "My private notes"
    assert store.read_source("other@example.com", saved["source_id"]) is None
    assert store.list_sources("owner@example.com")[0]["file_name"] == "notes.txt"
    assert store.list_sources("other@example.com") == []


def test_same_remote_file_updates_one_quarantine_record(tmp_path):
    store = PersonalMemoryStore(str(tmp_path / "memory.sqlite"), Fernet.generate_key().decode())
    args = dict(
        owner_email="owner@example.com", account_id="acc-1",
        remote_file_id="drive-file-1", file_name="notes.txt",
        mime_type="text/plain", modified_time=None,
    )
    first = store.quarantine(**args, extracted_text="Version 1")
    second = store.quarantine(**args, extracted_text="Version 2")
    assert first["source_id"] == second["source_id"]
    assert len(store.list_sources("owner@example.com")) == 1
    assert store.read_source("owner@example.com", first["source_id"])["text"] == "Version 2"


def test_personal_memory_rejects_oversized_extracted_text(tmp_path):
    store = PersonalMemoryStore(str(tmp_path / "memory.sqlite"), Fernet.generate_key().decode())
    with pytest.raises(ValueError):
        store.quarantine(
            owner_email="owner@example.com", account_id="acc-1",
            remote_file_id="drive-file-1", file_name="huge.txt",
            mime_type="text/plain", modified_time=None,
            extracted_text="x" * 2_000_001,
        )
