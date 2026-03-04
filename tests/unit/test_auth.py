from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user_returns_201(client: AsyncClient):
    payload = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword123"
    }
    response = await client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_username_returns_409(client: AsyncClient):
    payload = {"username": "duplicate", "email": "user1@example.com", "password": "password123"}
    await client.post("/api/auth/register", json=payload)
    
    response = await client.post(
        "/api/auth/register",
        json={"username": "duplicate", "email": "user2@example.com", "password": "password123"}
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_with_valid_credentials_returns_token(client: AsyncClient):
    register_payload = {"username": "loginuser", "email": "login@example.com", "password": "mypassword123"}
    await client.post("/api/auth/register", json=register_payload)
    
    login_payload = {"username": "loginuser", "password": "mypassword123"}
    response = await client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_with_invalid_password_returns_401(client: AsyncClient):
    register_payload = {"username": "badpassuser", "email": "badpass@example.com", "password": "correctpass"}
    await client.post("/api/auth/register", json=register_payload)
    
    login_payload = {"username": "badpassuser", "password": "wrongpassword"}
    response = await client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_with_nonexistent_user_returns_401(client: AsyncClient):
    login_payload = {"username": "nonexistent", "password": "anypassword"}
    response = await client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_valid_token_returns_user(client: AsyncClient):
    register_payload = {"username": "meuser", "email": "me@example.com", "password": "password123"}
    await client.post("/api/auth/register", json=register_payload)
    
    login_response = await client.post("/api/auth/login", json={"username": "meuser", "password": "password123"})
    token = login_response.json()["access_token"]
    
    response = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "meuser"
    assert data["email"] == "me@example.com"


@pytest.mark.asyncio
async def test_get_me_without_token_returns_401(client: AsyncClient):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_invalid_token_returns_401(client: AsyncClient):
    response = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == 401
