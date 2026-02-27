from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_device_returns_201_and_device(client: AsyncClient):
    payload = {
        "hostname": "switch-01",
        "mgmt_ip": "10.0.0.1",
    }
    response = await client.post("/api/devices", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["hostname"] == "switch-01"
    assert data["mgmt_ip"] == "10.0.0.1"
    assert "id" in data
    assert isinstance(data["id"], int)
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_device_with_optional_fields(client: AsyncClient):
    payload = {
        "hostname": "router-01",
        "mgmt_ip": "10.0.0.2",
        "vendor": "cisco",
        "site_id": "site-1",
        "role": "core",
        "region": "us-east",
        "area": "floor-a",
        "software_version": "17.1",
        "platform": "ios-xe",
    }
    response = await client.post("/api/devices", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["hostname"] == "router-01"
    assert data["mgmt_ip"] == "10.0.0.2"
    assert data["vendor"] == "cisco"
    assert data["site_id"] == "site-1"
    assert data["role"] == "core"
    assert data["region"] == "us-east"
    assert data["area"] == "floor-a"
    assert data["software_version"] == "17.1"
    assert data["platform"] == "ios-xe"


@pytest.mark.asyncio
async def test_create_device_duplicate_hostname_returns_409(client: AsyncClient):
    payload = {"hostname": "dup-host", "mgmt_ip": "10.0.0.10"}
    await client.post("/api/devices", json=payload)
    response = await client.post(
        "/api/devices",
        json={"hostname": "dup-host", "mgmt_ip": "10.0.0.99"},
    )
    assert response.status_code == 409
    detail = response.json().get("detail", "")
    assert "hostname" in detail.lower() or "mgmt_ip" in detail.lower()


@pytest.mark.asyncio
async def test_create_device_duplicate_mgmt_ip_returns_409(client: AsyncClient):
    payload = {"hostname": "first", "mgmt_ip": "10.0.0.20"}
    await client.post("/api/devices", json=payload)
    response = await client.post(
        "/api/devices",
        json={"hostname": "second", "mgmt_ip": "10.0.0.20"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_devices_empty(client: AsyncClient):
    response = await client.get("/api/devices")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_devices_returns_created_devices(client: AsyncClient):
    await client.post("/api/devices", json={"hostname": "a", "mgmt_ip": "10.0.0.1"})
    await client.post("/api/devices", json={"hostname": "b", "mgmt_ip": "10.0.0.2"})
    response = await client.get("/api/devices")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    hostnames = {d["hostname"] for d in items}
    assert hostnames == {"a", "b"}


@pytest.mark.asyncio
async def test_get_device_by_id_returns_200(client: AsyncClient):
    create_resp = await client.post(
        "/api/devices",
        json={"hostname": "get-me", "mgmt_ip": "10.0.0.30"},
    )
    assert create_resp.status_code == 201
    device_id = create_resp.json()["id"]

    response = await client.get(f"/api/devices/{device_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == device_id
    assert data["hostname"] == "get-me"
    assert data["mgmt_ip"] == "10.0.0.30"


@pytest.mark.asyncio
async def test_get_device_not_found_returns_404(client: AsyncClient):
    response = await client.get("/api/devices/99999")
    assert response.status_code == 404
    assert "not found" in response.json().get("detail", "").lower()
