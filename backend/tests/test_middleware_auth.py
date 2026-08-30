import sys
import os
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from middlewares.auth import auth, current_user

@pytest.mark.asyncio
@patch("middlewares.auth.current_user")
async def test_auth_success(mock_current_user):
    mock_current_user.return_value = 10
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")
    
    result = await auth(user_id=10, credentials=credentials)
    assert result == 10
    mock_current_user.assert_called_once_with(credentials)

@pytest.mark.asyncio
@patch("middlewares.auth.current_user")
async def test_auth_forbidden(mock_current_user):
    mock_current_user.return_value = 10
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")
    
    with pytest.raises(HTTPException) as excinfo:
        await auth(user_id=20, credentials=credentials)
    assert excinfo.value.status_code == 403
    assert "not allowed to access" in excinfo.value.detail

@pytest.mark.asyncio
async def test_current_user_no_credentials():
    with pytest.raises(HTTPException) as excinfo:
        await current_user(credentials=None)
    assert excinfo.value.status_code == 401
    assert "Not authenticated" in excinfo.value.detail

@pytest.mark.asyncio
@patch("middlewares.auth.verify_token")
async def test_current_user_missing_claim(mock_verify_token):
    mock_verify_token.return_value = {}
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")
    
    with pytest.raises(HTTPException) as excinfo:
        await current_user(credentials=credentials)
    assert excinfo.value.status_code == 401
    assert "missing user_id" in excinfo.value.detail
