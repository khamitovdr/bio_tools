"""Test pump routes."""

import pytest
import time


def get_pump_device_id(client):
    """Helper to get a pump device ID."""
    response = client.get("/devices")
    devices = response.json()
    
    for device in devices:
        if device["type"] == "pump":
            return device["device_id"]
    
    pytest.skip("No pump device found")


def test_set_default_flow(client):
    """Test setting default flow rate."""
    device_id = get_pump_device_id(client)
    
    response = client.post(
        f"/devices/{device_id}/pump/set-default-flow",
        json={"flow_rate": 5.0}
    )
    assert response.status_code == 200
    
    result = response.json()
    assert "message" in result
    assert "5.0" in result["message"]


def test_set_default_flow_invalid_device(client):
    """Test setting flow rate on invalid device."""
    response = client.post(
        "/devices/nonexistent/pump/set-default-flow",
        json={"flow_rate": 5.0}
    )
    assert response.status_code == 404


def test_pour_volume_sync(client):
    """Test synchronous pour volume."""
    device_id = get_pump_device_id(client)
    
    # Set default flow rate first
    client.post(
        f"/devices/{device_id}/pump/set-default-flow",
        json={"flow_rate": 10.0}
    )
    
    # Pour small volume synchronously (should complete quickly)
    response = client.post(
        f"/devices/{device_id}/pump/pour-volume",
        json={
            "volume": 1.0,
            "flow_rate": 10.0,
            "direction": "left",
            "blocking_mode": True
        }
    )
    assert response.status_code == 200
    
    result = response.json()
    assert "message" in result
    assert "Poured" in result["message"]


def test_pour_volume_async(client):
    """Test asynchronous pour volume."""
    device_id = get_pump_device_id(client)
    
    # Pour larger volume asynchronously
    response = client.post(
        f"/devices/{device_id}/pump/pour-volume",
        json={
            "volume": 10.0,
            "flow_rate": 1.0,  # Slow flow rate to ensure async execution
            "direction": "right",
            "blocking_mode": False
        }
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
    assert job["action"] == "pour_volume"


def test_start_pump(client):
    """Test starting pump."""
    device_id = get_pump_device_id(client)
    
    response = client.post(
        f"/devices/{device_id}/pump/start",
        json={
            "flow_rate": 5.0,
            "direction": "left"
        }
    )
    assert response.status_code == 200
    
    result = response.json()
    assert "message" in result
    assert "started" in result["message"].lower()


def test_stop_pump(client):
    """Test stopping pump."""
    device_id = get_pump_device_id(client)
    
    response = client.post(f"/devices/{device_id}/pump/stop")
    assert response.status_code == 200
    
    result = response.json()
    assert "message" in result
    assert "stopped" in result["message"].lower()


def test_pump_operations_on_spectro(client):
    """Test pump operations on spectrophotometer device."""
    # Get spectrophotometer device
    response = client.get("/devices")
    devices = response.json()
    
    spectro_id = None
    for device in devices:
        if device["type"] == "spectrophotometer":
            spectro_id = device["device_id"]
            break
    
    if not spectro_id:
        pytest.skip("No spectrophotometer device found")
    
    # Try pump operation on spectrophotometer
    response = client.post(
        f"/devices/{spectro_id}/pump/set-default-flow",
        json={"flow_rate": 5.0}
    )
    assert response.status_code == 409  # Conflict
