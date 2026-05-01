"""Tests for temp file save and cleanup utilities."""
from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.core.temp_files import save_upload, temp_upload


@pytest.fixture
def mock_upload(tmp_path):
    """UploadFile mock that yields content then EOF."""
    upload = AsyncMock()
    upload.filename = "audio.wav"
    upload.read = AsyncMock(side_effect=[b"fake audio content", b""])
    return upload


async def test_save_upload_creates_file(mock_upload, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "temp_dir", str(tmp_path))
    path = await save_upload(mock_upload)
    assert path.exists()
    assert path.read_bytes() == b"fake audio content"


async def test_save_upload_preserves_extension(mock_upload, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "temp_dir", str(tmp_path))
    path = await save_upload(mock_upload)
    assert path.suffix == ".wav"


async def test_save_upload_uses_unique_name(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "temp_dir", str(tmp_path))

    def make_upload():
        u = AsyncMock()
        u.filename = "audio.mp3"
        u.read = AsyncMock(side_effect=[b"data", b""])
        return u

    path1 = await save_upload(make_upload())
    path2 = await save_upload(make_upload())
    assert path1 != path2


async def test_temp_upload_deletes_file_on_exit(mock_upload, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "temp_dir", str(tmp_path))
    async with temp_upload(mock_upload) as path:
        assert path.exists()
    assert not path.exists()


async def test_temp_upload_deletes_file_on_exception(
    mock_upload, monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "temp_dir", str(tmp_path))
    captured_path = None
    with pytest.raises(ValueError):
        async with temp_upload(mock_upload) as path:
            captured_path = path
            raise ValueError("something broke")
    assert captured_path is not None
    assert not captured_path.exists()
