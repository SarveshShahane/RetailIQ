import sys
import os
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, UploadFile
from routes.upload import _validate_image, _save_file
from pathlib import Path

def test_validate_image_allowed():
    file = MagicMock(spec=UploadFile)
    file.filename = "pic.png"
    file.content_type = "image/png"
    _validate_image(file)

def test_validate_image_missing_filename():
    file = MagicMock(spec=UploadFile)
    file.filename = ""
    file.content_type = "image/png"
    with pytest.raises(HTTPException) as excinfo:
        _validate_image(file)
    assert excinfo.value.status_code == 400
    assert "No filename" in excinfo.value.detail

def test_validate_image_disallowed_extension():
    file = MagicMock(spec=UploadFile)
    file.filename = "script.exe"
    file.content_type = "image/png"
    with pytest.raises(HTTPException) as excinfo:
        _validate_image(file)
    assert excinfo.value.status_code == 400
    assert "not allowed" in excinfo.value.detail

def test_validate_image_disallowed_content_type():
    file = MagicMock(spec=UploadFile)
    file.filename = "doc.png"
    file.content_type = "text/plain"
    with pytest.raises(HTTPException) as excinfo:
        _validate_image(file)
    assert excinfo.value.status_code == 400
    assert "Only image files" in excinfo.value.detail

@pytest.mark.asyncio
async def test_save_file_size_exceeded():
    file = MagicMock(spec=UploadFile)
    file.filename = "pic.png"
    file.content_type = "image/png"
    
    large_data = b"0" * (5 * 1024 * 1024 + 1)
    file.read = AsyncMock(return_value=large_data)
    
    with pytest.raises(HTTPException) as excinfo:
        await _save_file(file, Path("/tmp"))
    assert excinfo.value.status_code == 413
    assert "exceeds" in excinfo.value.detail

@pytest.mark.asyncio
@patch("routes.upload.open")
@patch("routes.upload.Path.mkdir")
async def test_save_file_success(mock_mkdir, mock_open):
    file = MagicMock(spec=UploadFile)
    file.filename = "pic.png"
    file.content_type = "image/png"
    file.read = AsyncMock(return_value=b"fake image data")
    
    mock_file_handle = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file_handle
    
    dest_dir = Path("dummy_dest")
    
    with patch("routes.upload.BASE_DIR", Path(".")):
        url_path = await _save_file(file, dest_dir)
        assert url_path.endswith(".png")
        assert "dummy_dest" in url_path
