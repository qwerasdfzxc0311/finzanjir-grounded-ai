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


def test_heic_avif_aac_and_3gpp_are_checked_by_container_brand():
    heic = bytes.fromhex("000000186674797068656963") + bytes(20)
    avif = bytes.fromhex("000000186674797061766966") + bytes(20)
    aac = bytes.fromhex("fff1") + bytes(12)
    video = bytes.fromhex("000000186674797033677034") + bytes(20)
    assert validate_media_content("image/heic", heic)["media_type"] == "photo"
    assert validate_media_content("image/avif", avif)["media_type"] == "photo"
    assert validate_media_content("audio/aac", aac)["media_type"] == "audio"
    assert validate_media_content("video/3gpp", video)["media_type"] == "video"
