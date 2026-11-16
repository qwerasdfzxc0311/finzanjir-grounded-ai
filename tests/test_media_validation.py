import io
import wave

import pytest
from PIL import Image

from finzanjir_ai.integrations.media_validation import (
    UnsupportedMedia,
    validate_media_content,
)


def test_valid_png_is_identified_as_photo():
    output = io.BytesIO()
    Image.new("RGB", (32, 32)).save(output, format="PNG")
    result = validate_media_content("image/png", output.getvalue())
    assert result["media_type"] == "photo"


def test_reject_mismatched_and_invalid_image_bytes():
    with pytest.raises(UnsupportedMedia):
        validate_media_content("image/jpeg", b"not an image")
    output = io.BytesIO()
    Image.new("RGB", (8, 8)).save(output, format="PNG")
    with pytest.raises(UnsupportedMedia):
        validate_media_content("image/jpeg", output.getvalue())


def test_valid_wav_is_identified_as_audio():
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 160)
    assert validate_media_content("audio/wav", output.getvalue())["media_type"] == "audio"


def test_mp4_and_webm_container_headers_are_checked():
    mp4 = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 24
    webm = bytes.fromhex("1A45DFA3") + b"\x00" * 20
    assert validate_media_content("video/mp4", mp4)["media_type"] == "video"
    assert validate_media_content("video/webm", webm)["media_type"] == "video"
    with pytest.raises(UnsupportedMedia):
        validate_media_content("video/mp4", b"fake video")


def test_media_size_is_bounded():
    with pytest.raises(ValueError):
        validate_media_content("audio/mpeg", b"x" * (100 * 1024 * 1024 + 1))
