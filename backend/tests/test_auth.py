import sys
import os
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

import pytest
import jwt
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
import models.user
import models.products
import models.invoice
import models.ai
import models.auth

from services.auth import (
    hash_password,
    verify_password,
    register_user,
    login_user,
    forgot_password,
    reset_password,
)
from schemas.auth import EmailModel, ResetPasswordModel
from middlewares.auth import verify_token, access_token, refresh_token
from exceptions.user import EmailAlreadyRegisteredException, UserNotFoundException, InvalidOTP
from schemas.auth import RegisterModel, LoginModel
from models.user import User as UserModel

def test_password_hashing():
    pwd = "MySecretPassword123"
    hashed = hash_password(pwd)
    
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_token_creation_and_verification():
    payload = {"user_id": 42, "sub": "test@example.com"}
    token = access_token(payload)
    
    decoded = verify_token(token)
    assert decoded["user_id"] == 42
    assert decoded["sub"] == "test@example.com"

def test_token_verification_invalid():
    with pytest.raises(HTTPException) as excinfo:
        verify_token("invalid-token-string")
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid token" in excinfo.value.detail

def mock_db_result(value=None):
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = value
    return mock_res

@pytest.mark.asyncio
async def test_register_user_success():
    db = AsyncMock()
    db.add = MagicMock() 
    db.execute.return_value = mock_db_result(None)
    
    def mock_refresh(instance):
        instance.id = 99
        instance.created_at = datetime.now()
    db.refresh.side_effect = mock_refresh
    
    payload = RegisterModel(
        name="Test User",
        email="newuser@example.com",
        password="SecurePassword123"
    )
    
    response = await register_user(db, payload)
    
    assert response["name"] == "Test User"
    assert response["email"] == "newuser@example.com"
    assert response["id"] == 99
    
    assert db.add.call_count >= 1
    assert db.commit.call_count >= 1

@pytest.mark.asyncio
async def test_register_user_already_exists():
    db = AsyncMock()
    existing_user = UserModel(id=1, email="existing@example.com", name="Existing")
    db.execute.return_value = mock_db_result(existing_user)
    
    payload = RegisterModel(
        name="New User",
        email="existing@example.com",
        password="Password123"
    )
    
    with pytest.raises(EmailAlreadyRegisteredException):
        await register_user(db, payload)

@pytest.mark.asyncio
async def test_login_user_invalid_credentials():
    db = AsyncMock()
    db.execute.return_value = mock_db_result(None)
    
    payload = LoginModel(
        email="notfound@example.com",
        password="Password123"
    )
    
    response = MagicMock()
    with pytest.raises(HTTPException) as excinfo:
        await login_user(db, payload, response)
        
    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert excinfo.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_forgot_password_user_not_found():
    db = AsyncMock()
    db.execute.return_value = mock_db_result(None)
    payload = EmailModel(email="notfound@example.com")
    with pytest.raises(UserNotFoundException):
        await forgot_password(db, payload)


@pytest.mark.asyncio
async def test_reset_password_user_not_found():
    db = AsyncMock()
    db.execute.return_value = mock_db_result(None)
    payload = ResetPasswordModel(email="notfound@example.com", otp=123456, new_password="NewPassword123")
    with pytest.raises(UserNotFoundException):
        await reset_password(db, payload)


@pytest.mark.asyncio
@patch("services.auth.redisClient")
async def test_forgot_password_success(mock_redis):
    db = AsyncMock()
    user = UserModel(id=1, email="test@example.com", name="Test")
    db.execute.return_value = mock_db_result(user)
    
    payload = EmailModel(email="test@example.com")
    res = await forgot_password(db, payload)
    
    assert res["success"] is True
    assert res["Message"] == "OTP sent to your email successfully"
    mock_redis.set.assert_called_once()


@pytest.mark.asyncio
@patch("services.auth.redisClient")
async def test_reset_password_success_redis(mock_redis):
    db = AsyncMock()
    user = UserModel(id=1, email="test@example.com", name="Test")
    db.execute.return_value = mock_db_result(user)
    
    mock_redis.get.return_value = b"123456"
    
    payload = ResetPasswordModel(email="test@example.com", otp=123456, new_password="NewPassword123")
    res = await reset_password(db, payload)
    
    assert res["success"] is True
    assert res["Message"] == "Password reset successfully"
    mock_redis.get.assert_called_once_with("reset_otp:test@example.com")
    mock_redis.delete.assert_called_once_with("reset_otp:test@example.com")


@pytest.mark.asyncio
@patch("services.auth.redisClient")
async def test_reset_password_success_fallback(mock_redis):
    db = AsyncMock()
    from datetime import datetime, timezone
    user = UserModel(
        id=1,
        email="test@example.com",
        name="Test",
        otp=123456,
        otp_timestamp=datetime.now(timezone.utc)
    )
    db.execute.return_value = mock_db_result(user)
    
    mock_redis.get.return_value = None
    
    payload = ResetPasswordModel(email="test@example.com", otp=123456, new_password="NewPassword123")
    res = await reset_password(db, payload)
    
    assert res["success"] is True
    assert res["Message"] == "Password reset successfully"
    assert db.commit.call_count >= 1
    assert user.otp is None
