from __future__ import annotations

import io
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_device_returns_201_and_device(client: AsyncClient, auth_headers: dict[str, str]):
    payload = {
        "hostname": "switch-01",
        "mgmt_ip": "10.0.0.1",
    }
    response = await client.post("/api/devices", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["hostname"] == "switch-01"
    assert data["mgmt_ip"] == "10.0.0.1"
    assert "id" in data
    assert isinstance(data["id"], int)
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_device_with_optional_fields(client: AsyncClient, auth_headers: dict[str, str]):
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
    response = await client.post("/api/devices", json=payload, headers=auth_headers)
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
async def test_create_device_duplicate_hostname_returns_409(client: AsyncClient, auth_headers: dict[str, str]):
    payload = {"hostname": "dup-host", "mgmt_ip": "10.0.0.10"}
    await client.post("/api/devices", json=payload, headers=auth_headers)
    response = await client.post(
        "/api/devices",
        json={"hostname": "dup-host", "mgmt_ip": "10.0.0.99"},
        headers=auth_headers
    )
    assert response.status_code == 409
    detail = response.json().get("detail", "")
    assert "hostname" in detail.lower() or "mgmt_ip" in detail.lower()


@pytest.mark.asyncio
async def test_create_device_duplicate_mgmt_ip_returns_409(client: AsyncClient, auth_headers: dict[str, str]):
    payload = {"hostname": "first", "mgmt_ip": "10.0.0.20"}
    await client.post("/api/devices", json=payload, headers=auth_headers)
    response = await client.post(
        "/api/devices",
        json={"hostname": "second", "mgmt_ip": "10.0.0.20"},
        headers=auth_headers
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_list_devices_empty(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.get("/api/devices", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_devices_returns_created_devices(client: AsyncClient, auth_headers: dict[str, str]):
    await client.post("/api/devices", json={"hostname": "a", "mgmt_ip": "10.0.0.1"}, headers=auth_headers)
    await client.post("/api/devices", json={"hostname": "b", "mgmt_ip": "10.0.0.2"}, headers=auth_headers)
    response = await client.get("/api/devices", headers=auth_headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    hostnames = {d["hostname"] for d in items}
    assert hostnames == {"a", "b"}


@pytest.mark.asyncio
async def test_get_device_by_id_returns_200(client: AsyncClient, auth_headers: dict[str, str]):
    create_resp = await client.post(
        "/api/devices",
        json={"hostname": "get-me", "mgmt_ip": "10.0.0.30"},
        headers=auth_headers
    )
    assert create_resp.status_code == 201
    device_id = create_resp.json()["id"]

    response = await client.get(f"/api/devices/{device_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == device_id
    assert data["hostname"] == "get-me"
    assert data["mgmt_ip"] == "10.0.0.30"


@pytest.mark.asyncio
async def test_get_device_not_found_returns_404(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.get("/api/devices/99999", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json().get("detail", "").lower()


@pytest.mark.asyncio
async def test_update_device_returns_200_and_updated_device(client: AsyncClient, auth_headers: dict[str, str]):
    create_resp = await client.post(
        "/api/devices",
        json={"hostname": "original", "mgmt_ip": "10.0.0.40"},
        headers=auth_headers
    )
    assert create_resp.status_code == 201
    device_id = create_resp.json()["id"]

    update_payload = {"hostname": "updated", "vendor": "cisco"}
    response = await client.put(f"/api/devices/{device_id}", json=update_payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == device_id
    assert data["hostname"] == "updated"
    assert data["mgmt_ip"] == "10.0.0.40"
    assert data["vendor"] == "cisco"


@pytest.mark.asyncio
async def test_update_device_partial_update(client: AsyncClient, auth_headers: dict[str, str]):
    create_resp = await client.post(
        "/api/devices",
        json={"hostname": "partial", "mgmt_ip": "10.0.0.50", "vendor": "juniper"},
        headers=auth_headers
    )
    assert create_resp.status_code == 201
    device_id = create_resp.json()["id"]

    update_payload = {"role": "edge"}
    response = await client.put(f"/api/devices/{device_id}", json=update_payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["hostname"] == "partial"
    assert data["mgmt_ip"] == "10.0.0.50"
    assert data["vendor"] == "juniper"
    assert data["role"] == "edge"


@pytest.mark.asyncio
async def test_update_device_not_found_returns_404(client: AsyncClient, auth_headers: dict[str, str]):
    response = await client.put(
        "/api/devices/99999",
        json={"hostname": "nonexistent"},
        headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_device_duplicate_hostname_returns_409(client: AsyncClient, auth_headers: dict[str, str]):
    await client.post("/api/devices", json={"hostname": "first", "mgmt_ip": "10.0.0.60"}, headers=auth_headers)
    create_resp = await client.post(
        "/api/devices",
        json={"hostname": "second", "mgmt_ip": "10.0.0.61"},
        headers=auth_headers
    )
    device_id = create_resp.json()["id"]

    response = await client.put(f"/api/devices/{device_id}", json={"hostname": "first"}, headers=auth_headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_delete_device_returns_204(client: AsyncClient, admin_headers: dict[str, str]):
    create_resp = await client.post(
        "/api/devices",
        json={"hostname": "to-delete", "mgmt_ip": "10.0.0.70"},
        headers=admin_headers
    )
    assert create_resp.status_code == 201
    device_id = create_resp.json()["id"]

    response = await client.delete(f"/api/devices/{device_id}", headers=admin_headers)
    assert response.status_code == 204

    get_response = await client.get(f"/api/devices/{device_id}", headers=admin_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_device_not_found_returns_404(client: AsyncClient, admin_headers: dict[str, str]):
    response = await client.delete("/api/devices/99999", headers=admin_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_device_requires_admin(client: AsyncClient, auth_headers: dict[str, str], admin_headers: dict[str, str]):
    create_resp = await client.post(
        "/api/devices",
        json={"hostname": "test-delete-perm", "mgmt_ip": "10.0.0.71"},
        headers=admin_headers
    )
    device_id = create_resp.json()["id"]
    
    response = await client.delete(f"/api/devices/{device_id}", headers=auth_headers)
    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_csv_import_creates_new_devices(client: AsyncClient, admin_headers: dict[str, str]):
    csv_content = """hostname,mgmt_ip,vendor,site_id,role,region,area,software_version,platform
router1,10.0.1.1,cisco,site1,core,us-east,dc1,17.1,ios-xe
switch1,10.0.1.2,juniper,site1,access,us-east,dc1,21.2,junos
fw1,10.0.1.3,palo-alto,site2,firewall,us-west,dc2,10.1,panos"""
    
    files = {"file": ("devices.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    response = await client.post("/api/devices/import", files=files, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 3
    assert data["created"] == 3
    assert data["updated"] == 0
    assert data["skipped"] == 0
    assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_csv_import_updates_existing_devices(client: AsyncClient, admin_headers: dict[str, str]):
    await client.post("/api/devices", json={"hostname": "existing", "mgmt_ip": "10.0.2.1"}, headers=admin_headers)
    
    csv_content = """hostname,mgmt_ip,vendor,site_id,role
existing,10.0.2.1,cisco,site-updated,core"""
    
    files = {"file": ("devices.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    response = await client.post("/api/devices/import", files=files, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 1
    assert data["created"] == 0
    assert data["updated"] == 1
    
    device_resp = await client.get("/api/devices", headers=admin_headers)
    devices = [d for d in device_resp.json() if d["hostname"] == "existing"]
    assert len(devices) == 1
    assert devices[0]["vendor"] == "cisco"
    assert devices[0]["site_id"] == "site-updated"


@pytest.mark.asyncio
async def test_csv_import_mixed_create_and_update(client: AsyncClient, admin_headers: dict[str, str]):
    await client.post("/api/devices", json={"hostname": "old-device", "mgmt_ip": "10.0.3.1"}, headers=admin_headers)
    
    csv_content = """hostname,mgmt_ip,vendor
old-device,10.0.3.1,updated-vendor
new-device,10.0.3.2,new-vendor"""
    
    files = {"file": ("devices.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    response = await client.post("/api/devices/import", files=files, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2
    assert data["created"] == 1
    assert data["updated"] == 1


@pytest.mark.asyncio
async def test_csv_import_handles_validation_errors(client: AsyncClient, admin_headers: dict[str, str]):
    csv_content = """hostname,mgmt_ip,vendor
valid-device,10.0.4.1,cisco
,10.0.4.2,juniper
invalid-device,,palo-alto"""
    
    files = {"file": ("devices.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    response = await client.post("/api/devices/import", files=files, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 3
    assert data["created"] == 1
    assert data["skipped"] == 2
    assert len(data["errors"]) == 2


@pytest.mark.asyncio
async def test_csv_import_handles_empty_file(client: AsyncClient, admin_headers: dict[str, str]):
    csv_content = """hostname,mgmt_ip,vendor"""
    
    files = {"file": ("devices.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    response = await client.post("/api/devices/import", files=files, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 0
    assert data["created"] == 0


@pytest.mark.asyncio
async def test_csv_import_reports_duplicate_errors(client: AsyncClient, admin_headers: dict[str, str]):
    csv_content = """hostname,mgmt_ip,vendor
dup-device,10.0.5.1,cisco
dup-device,10.0.5.2,juniper"""
    
    files = {"file": ("devices.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    response = await client.post("/api/devices/import", files=files, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2
    assert data["created"] == 1
    assert data["skipped"] == 1
    assert len(data["errors"]) == 1
    assert "Duplicate" in data["errors"][0]["error"]


@pytest.mark.asyncio
async def test_csv_import_requires_admin(client: AsyncClient, auth_headers: dict[str, str]):
    csv_content = """hostname,mgmt_ip,vendor
test,10.0.6.1,cisco"""
    
    files = {"file": ("devices.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    response = await client.post("/api/devices/import", files=files, headers=auth_headers)
    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_device_endpoints_require_authentication(client: AsyncClient):
    response = await client.get("/api/devices")
    assert response.status_code == 401
    
    response = await client.post("/api/devices", json={"hostname": "test", "mgmt_ip": "10.0.0.1"})
    assert response.status_code == 401
