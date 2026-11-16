"""Conservative media type and container validation before private storage."""
from __future__ import annotations

import io
import wave
import warnings

from PIL import Image, UnidentifiedImageError


MAX_IMAGE_PIXELS = 40_000_000


class UnsupportedMedia(ValueError):
    pass


def validate_media_content(mime_type: str, content: bytes) -> dict:
    if not content or len(content) > 100 * 1024 * 1024:
        raise ValueError("media must be between 1 byte and 100 MB")
    mime = mime_type.split(";", 1)[0].strip().lower()
    if mime.startswith("image/"):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(content)) as image:
                    if image.width * image.height > MAX_IMAGE_PIXELS:
                        raise ValueError("image exceeds the 40 megapixel safety limit")
                    detected = Image.MIME.get(image.format)
                    image.verify()
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
                Image.DecompressionBombWarning) as exc:
            raise UnsupportedMedia("image bytes failed format or safety validation") from exc
        if detected != mime and not (detected == "image/jpeg" and mime == "image/jpg"):
            raise UnsupportedMedia("image MIME type does not match its content")
        return {"media_type": "photo", "width_checked": True}

    if mime in {"image/heic", "image/heif", "image/avif"}:
        if len(content) < 16 or content[4:8] != b"ftyp":
            raise UnsupportedMedia("HEIC/HEIF/AVIF bytes failed ISO-BMFF validation")
        brand = content[8:12]
        accepted = {
            "image/heic": {b"heic", b"heix", b"hevc", b"hevx", b"mif1"},
            "image/heif": {b"heic", b"heix", b"mif1", b"msf1"},
            "image/avif": {b"avif", b"avis", b"mif1"},
        }
        if brand not in accepted[mime]:
            raise UnsupportedMedia("HEIC/HEIF/AVIF brand does not match MIME type")
        return {"media_type": "photo", "container_checked": True}

    if mime in {"audio/wav", "audio/x-wav"}:
        try:
            with wave.open(io.BytesIO(content), "rb") as audio:
                if audio.getnchannels() not in {1, 2} or audio.getframerate() > 192000:
                    raise ValueError("WAV audio parameters exceed supported bounds")
        except (wave.Error, EOFError) as exc:
            raise UnsupportedMedia("WAV bytes failed format validation") from exc
        return {"media_type": "audio"}

    if mime in {"audio/aac", "audio/aacp"}:
        if len(content) < 7 or content[0] != 0xFF or content[1] & 0xF6 != 0xF0:
            raise UnsupportedMedia("AAC bytes failed ADTS validation")
        return {"media_type": "audio"}
    if mime in {"audio/mpeg", "audio/mp3"}:
        if not (content.startswith(b"ID3") or
                (len(content) > 1 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0)):
            raise UnsupportedMedia("MP3 bytes failed format validation")
        return {"media_type": "audio"}
    if mime == "audio/flac":
        if not content.startswith(b"fLaC"):
            raise UnsupportedMedia("FLAC bytes failed format validation")
        return {"media_type": "audio"}
    if mime in {"audio/ogg", "application/ogg"}:
        if not content.startswith(b"OggS"):
            raise UnsupportedMedia("OGG bytes failed format validation")
        return {"media_type": "audio"}

    if mime in {"video/mp4", "video/quicktime", "audio/mp4", "audio/x-m4a"}:
        if len(content) < 12 or content[4:8] != b"ftyp":
            raise UnsupportedMedia("MP4/MOV bytes failed container validation")
        return {"media_type": "video" if mime.startswith("video/") else "audio"}
    if mime in {"video/3gpp", "video/3gpp2"}:
        if len(content) < 12 or content[4:8] != b"ftyp":
            raise UnsupportedMedia("3GPP video bytes failed container validation")
        return {"media_type": "video"}

    if mime in {"video/x-matroska", "video/webm"}:
        if not content.startswith(bytes.fromhex("1A45DFA3")):
            raise UnsupportedMedia("Matroska/WebM bytes failed container validation")
        return {"media_type": "video"}
    if mime == "video/x-msvideo":
        if len(content) < 12 or content[:4] != b"RIFF" or content[8:12] != b"AVI ":
            raise UnsupportedMedia("AVI bytes failed container validation")
        return {"media_type": "video"}
    raise UnsupportedMedia("media MIME type is not in the supported safe-format list")
