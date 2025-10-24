"""Test device routes."""

import pytest


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_list_devices(client):
    """Test listing devices."""
    response = client.get("/devices")
    assert response.status_code == 200
    
    devices = response.json()
    assert isinstance(devices, list)
    assert len(devices) == 3  # 2 pumps + 1 spectrophotometer
    
    # Check device structure
    for device in devices:
        assert "device_id" in device
        assert "type" in device
        assert "port" in device
        assert "is_available" in device
        assert device["type"] in ["pump", "spectrophotometer"]


def test_get_device_details(client):
    """Test getting device details."""
    # First get list of devices
    response = client.get("/devices")
    devices = response.json()
    
    # Test getting details for first device
    device_id = devices[0]["device_id"]
    response = client.get(f"/devices/{device_id}")
    assert response.status_code == 200
    
    device = response.json()
    assert device["device_id"] == device_id
    assert "type" in device
    assert "port" in device
    assert "is_available" in device


def test_get_nonexistent_device(client):
    """Test getting details for nonexistent device."""
    response = client.get("/devices/nonexistent")
    assert response.status_code == 404


def test_rescan_devices(client):
    """Test device rescan."""
    response = client.post("/devices:rescan")
    assert response.status_code == 200
    
    result = response.json()
    assert "added" in result
    assert "removed" in result
    assert isinstance(result["added"], list)
    assert isinstance(result["removed"], list)
