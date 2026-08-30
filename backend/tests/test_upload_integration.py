import sys
import os
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

import models.user
import models.products
import models.invoice
import models.ai
import models.auth

from app import app
from db.database import get_async_db
from middlewares.auth import auth, current_user

def mock_current_user():
    return 10

app.dependency_overrides[current_user] = mock_current_user

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_overrides():
    app.dependency_overrides[current_user] = mock_current_user
    yield
    app.dependency_overrides.clear()

@patch("routes.upload._save_file")
def test_integration_upload_avatar_success(mock_save):
    mock_save.return_value = "/uploads/avatars/test_avatar.png"
    
    file_payload = {"file": ("avatar.png", b"fake binary data", "image/png")}
    response = client.post("/upload/avatar", files=file_payload)
    
    assert response.status_code == 200
    assert response.json() == {"url": "/uploads/avatars/test_avatar.png"}
    mock_save.assert_called_once()

@patch("routes.upload._save_file")
def test_integration_upload_logo_success(mock_save):
    mock_save.return_value = "/uploads/logos/test_logo.png"
    
    file_payload = {"file": ("logo.png", b"fake binary data", "image/png")}
    response = client.post("/upload/logo", files=file_payload)
    
    assert response.status_code == 200
    assert response.json() == {"url": "/uploads/logos/test_logo.png"}
    mock_save.assert_called_once()
