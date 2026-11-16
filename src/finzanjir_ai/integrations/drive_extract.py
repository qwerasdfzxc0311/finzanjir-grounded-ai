"""Bounded text extraction for explicitly supported Google Drive formats."""
from __future__ import annotations

import csv
import io
from pathlib import PurePosixPath
import re
import zipfile
from typing import Any

MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024
MAX_EXTRACTED_CHARS = 2_000_000

TEXT_MIMES = {
    "text/plain", "text/markdown", "text/csv",
    "application/json", "application/xml",
}
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MIME = "application/pdf"


class UnsupportedDriveFormat(ValueError):
    pass


def _clean(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = text.strip()
    if not text:
        raise ValueError("file contains no extractable text")
    if len(text) > MAX_EXTRACTED_CHARS:
        text = text[:MAX_EXTRACTED_CHARS]
    return text


def _validate_office_archive(content: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            if len(infos) > 2000:
                raise ValueError("Office document exceeds the 2,000-entry archive limit")
            total = 0
            for info in infos:
                name = PurePosixPath(info.filename)
                if name.is_absolute() or ".." in name.parts:
                    raise ValueError("Office archive contains an unsafe path")
                total += info.file_size
                if info.file_size > 50 * 1024 * 1024 or total > 100 * 1024 * 1024:
                    raise ValueError("Office document exceeds the 100 MB expanded-size limit")
                if info.compress_size == 0 and info.file_size > 0:
                    raise ValueError("Office archive has an invalid compression entry")
                if info.compress_size and info.file_size / info.compress_size > 200:
                    raise ValueError("Office archive compression ratio exceeds safety limit")
    except zipfile.BadZipFile as exc:
        raise ValueError("Office document is not a valid ZIP container") from exc


def extract_drive_text(file_name: str, mime_type: str, content: bytes) -> dict[str, Any]:
    if not content or len(content) > MAX_DOWNLOAD_BYTES:
        raise ValueError("file must be between 1 byte and 10 MB")
    mime = mime_type.split(";", 1)[0].strip().lower()
    if mime in TEXT_MIMES:
        decoded = content.decode("utf-8-sig", errors="strict")
        if mime == "text/csv":
            rows = list(csv.reader(io.StringIO(decoded), strict=True))
            decoded = "\n".join("\t".join(cell for cell in row) for row in rows)
        return {"text": _clean(decoded), "extractor": "utf8-text-v1"}
    if mime == PDF_MIME:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content), strict=True)
        if len(reader.pages) > 500:
            raise ValueError("PDF exceeds the 500-page extraction limit")
        pages = []
        for index, page in enumerate(reader.pages, start=1):
            pages.append(f"[Page {index}]\n{page.extract_text() or ''}")
        return {"text": _clean("\n\n".join(pages)), "extractor": "pypdf-text-v1"}
    if mime == XLSX_MIME:
        _validate_office_archive(content)
        from openpyxl import load_workbook
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        if len(workbook.worksheets) > 100:
            raise ValueError("workbook exceeds the 100-sheet extraction limit")
        parts = []
        cells = 0
        try:
            for sheet in workbook.worksheets:
                parts.append(f"[Sheet: {sheet.title[:120]}]")
                for row in sheet.iter_rows(values_only=True):
                    cells += len(row)
                    if cells > 100_000:
                        raise ValueError("workbook exceeds the 100,000-cell extraction limit")
                    values = ["" if value is None else str(value) for value in row]
                    if any(values):
                        parts.append("\t".join(values))
        finally:
            workbook.close()
        return {"text": _clean("\n".join(parts)), "extractor": "openpyxl-xlsx-v1"}
    if mime == DOCX_MIME:
        _validate_office_archive(content)
        from docx import Document
        document = Document(io.BytesIO(content))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        for table_index, table in enumerate(document.tables, start=1):
            paragraphs.append(f"[Table {table_index}]")
            for row in table.rows:
                paragraphs.append("\t".join(cell.text.replace("\n", " ") for cell in row.cells))
        return {"text": _clean("\n".join(paragraphs)), "extractor": "python-docx-v1"}
    raise UnsupportedDriveFormat(f"unsupported Google Drive MIME type: {mime or 'unknown'}")
