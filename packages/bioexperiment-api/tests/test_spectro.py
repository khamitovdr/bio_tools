"""Test spectrophotometer routes."""

import pytest


def get_spectro_device_id(client):
    """Helper to get a spectrophotometer device ID."""
    response = client.get("/devices")
    devices = response.json()
    
    for device in devices:
        if device["type"] == "spectrophotometer":
            return device["device_id"]
    
    pytest.skip("No spectrophotometer device found")


def test_get_temperature(client):
    """Test getting temperature."""
    device_id = get_spectro_device_id(client)
    
    response = client.get(f"/devices/{device_id}/spectro/temperature")
    assert response.status_code == 200
    
    result = response.json()
    assert "temperature" in result
    assert isinstance(result["temperature"], (int, float))
    assert 0 <= result["temperature"] <= 100  # Reasonable temperature range


def test_get_temperature_invalid_device(client):
    """Test getting temperature from invalid device."""
    response = client.get("/devices/nonexistent/spectro/temperature")
    assert response.status_code == 404


def test_measure_optical_density(client):
    """Test measuring optical density (async)."""
    device_id = get_spectro_device_id(client)
    
    response = client.post(
        f"/devices/{device_id}/spectro/measure",
        json={"timeout": 30}
    )
    assert response.status_code == 202
    
    result = response.json()
    assert "job_id" in result
    
    # Check job status
    job_id = result["job_id"]
    job_response = client.get(f"/jobs/{job_id}")
    assert job_response.status_code == 200
    
    job = job_response.json()
    assert job["status"] in ["pending", "running", "succeeded"]
    assert job["action"] == "measure_optical_density"
    assert job["device_id"] == device_id


def test_spectro_operations_on_pump(client):
    """Test spectrophotometer operations on pump device."""
    # Get pump device
    response = client.get("/devices")
    devices = response.json()
    
    pump_id = None
    for device in devices:
        if device["type"] == "pump":
            pump_id = device["device_id"]
            break
    
    if not pump_id:
        pytest.skip("No pump device found")
    
    # Try spectro operation on pump
    response = client.get(f"/devices/{pump_id}/spectro/temperature")
    assert response.status_code == 409  # Conflict
