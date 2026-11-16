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


def test_personal_memory_keeps_drive_and_gmail_sources_separate(tmp_path):
    store = PersonalMemoryStore(str(tmp_path / "memory.sqlite"), Fernet.generate_key().decode())
    common = dict(
        owner_email="owner@example.com", account_id="acc-1",
        remote_file_id="same-remote-id", file_name="source",
        mime_type="text/plain", modified_time=None,
        extracted_text="Private source text",
    )
    drive = store.quarantine(**common, provider="google_drive")
    gmail = store.quarantine(**common, provider="google_gmail")
    assert drive["source_id"] != gmail["source_id"]
    assert len(store.list_sources("owner@example.com")) == 2


def test_google_photos_picker_session_is_owner_and_account_bound(tmp_path):
    store = PersonalMemoryStore(str(tmp_path / "memory.sqlite"), Fernet.generate_key().decode())
    store.save_picker_session("owner@example.com", "account-a", "session-1",
                              "https://photos.google.com/picker/session-1")
    assert store.get_picker_session("owner@example.com", "account-a", "session-1")["status"] == "created"
    assert store.get_picker_session("other@example.com", "account-a", "session-1") is None
    assert store.get_picker_session("owner@example.com", "account-b", "session-1") is None
    assert store.set_picker_session_status("owner@example.com", "account-a", "session-1", "ready")
    assert store.get_picker_session("owner@example.com", "account-a", "session-1")["status"] == "ready"


def test_selected_photo_video_bytes_are_encrypted_and_owner_scoped(tmp_path):
    key = Fernet.generate_key().decode()
    path = tmp_path / "memory.sqlite"
    store = PersonalMemoryStore(str(path), key)
    photo = store.quarantine_media(
        owner_email="owner@example.com", account_id="photos-account",
        remote_media_id="photo-1", file_name="family.jpg",
        mime_type="image/jpeg", media_type="photo",
        content=b"private-image-bytes",
        metadata={"picker_session_id": "session-1"},
    )
    assert photo["status"] == "quarantined"
    assert b"private-image-bytes" not in path.read_bytes()
    assert store.read_media("owner@example.com", photo["media_id"])["content"] == b"private-image-bytes"
    assert store.read_media("other@example.com", photo["media_id"]) is None
    assert store.list_media("owner@example.com")[0]["file_name"] == "family.jpg"


def test_media_store_rejects_empty_and_unsupported_kind(tmp_path):
    store = PersonalMemoryStore(str(tmp_path / "memory.sqlite"), Fernet.generate_key().decode())
    base = dict(owner_email="owner@example.com", account_id="a", remote_media_id="m",
                file_name="file", mime_type="application/octet-stream")
    with pytest.raises(ValueError):
        store.quarantine_media(**base, media_type="archive", content=b"data")
    with pytest.raises(ValueError):
        store.quarantine_media(**base, media_type="photo", content=b"")


def test_owner_only_local_search_reads_encrypted_sources_without_external_search(tmp_path):
    store = PersonalMemoryStore(str(tmp_path / "memory.sqlite"), Fernet.generate_key().decode())
    store.quarantine(
        owner_email="owner@example.com", account_id="drive-1",
        remote_file_id="doc-1", file_name="research.txt",
        mime_type="text/plain", modified_time=None,
        extracted_text="FINZANJIR astronomy research includes Mars and the solar system.",
    )
    store.quarantine(
        owner_email="other@example.com", account_id="drive-2",
        remote_file_id="doc-2", file_name="private.txt",
        mime_type="text/plain", modified_time=None,
        extracted_text="FINZANJIR secret private material.",
    )
    results = store.search_sources("owner@example.com", "astronomy Mars")
    assert len(results) == 1
    assert results[0]["file_name"] == "research.txt"
    assert "Mars" in results[0]["snippet"]
    assert store.search_sources("other@example.com", "astronomy Mars") == []
    with pytest.raises(ValueError):
        store.search_sources("owner@example.com", " ")


def test_media_from_drive_and_photos_have_separate_source_ids(tmp_path):
    store = PersonalMemoryStore(str(tmp_path / "memory.sqlite"), Fernet.generate_key().decode())
    common = dict(
        owner_email="owner@example.com", account_id="account-1",
        remote_media_id="media-1", file_name="recording.wav",
        mime_type="audio/wav", media_type="audio", content=b"private-audio",
    )
    photos = store.quarantine_media(**common, provider="google_photos")
    drive = store.quarantine_media(**common, provider="google_drive")
    assert photos["media_id"] != drive["media_id"]
    assert len(store.list_media("owner@example.com")) == 2
