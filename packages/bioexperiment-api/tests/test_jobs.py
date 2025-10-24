"""Test job management routes."""

import pytest
import time


def create_test_job(client):
    """Helper to create a test job."""
    # Get a spectrophotometer device
    response = client.get("/devices")
    devices = response.json()
    
    spectro_id = None
    for device in devices:
        if device["type"] == "spectrophotometer":
            spectro_id = device["device_id"]
            break
    
    if not spectro_id:
        pytest.skip("No spectrophotometer device found")
    
    # Create a measurement job
    response = client.post(
        f"/devices/{spectro_id}/spectro/measure",
        json={"timeout": 30}
    )
    assert response.status_code == 202
    
    return response.json()["job_id"]


def test_get_job(client):
    """Test getting job details."""
    job_id = create_test_job(client)
    
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 200
    
    job = response.json()
    assert job["job_id"] == str(job_id)
    assert job["status"] in ["pending", "running", "succeeded", "failed"]
    assert "submitted_at" in job
    assert "device_id" in job
    assert "action" in job
    assert "params" in job


def test_get_nonexistent_job(client):
    """Test getting nonexistent job."""
    response = client.get("/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_list_jobs(client):
    """Test listing jobs."""
    # Create a test job
    job_id = create_test_job(client)
    
    response = client.get("/jobs")
    assert response.status_code == 200
    
    jobs = response.json()
    assert isinstance(jobs, list)
    assert len(jobs) > 0
    
    # Check if our job is in the list
    job_ids = [job["job_id"] for job in jobs]
    assert str(job_id) in job_ids


def test_list_jobs_pagination(client):
    """Test job listing with pagination."""
    # Create multiple test jobs
    job_ids = []
    for _ in range(3):
        job_id = create_test_job(client)
        job_ids.append(job_id)
    
    # Test with limit
    response = client.get("/jobs?limit=2")
    assert response.status_code == 200
    
    jobs = response.json()
    assert len(jobs) <= 2
    
    # Test with offset
    response = client.get("/jobs?limit=1&offset=1")
    assert response.status_code == 200
    
    jobs = response.json()
    assert len(jobs) <= 1


def test_delete_job(client):
    """Test deleting a completed job."""
    job_id = create_test_job(client)
    
    # Wait for job to complete (in emulation mode it should be quick)
    max_wait = 10  # seconds
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = client.get(f"/jobs/{job_id}")
        job = response.json()
        
        if job["status"] in ["succeeded", "failed"]:
            break
        
        time.sleep(0.5)
    
    # Now try to delete it
    response = client.delete(f"/jobs/{job_id}")
    assert response.status_code == 200
    
    result = response.json()
    assert "message" in result
    assert str(job_id) in result["message"]
    
    # Verify job is deleted
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 404


def test_delete_nonexistent_job(client):
    """Test deleting nonexistent job."""
    response = client.delete("/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_delete_running_job(client):
    """Test deleting a running job (should fail)."""
    # Create a long-running job
    response = client.get("/devices")
    devices = response.json()
    
    pump_id = None
    for device in devices:
        if device["type"] == "pump":
            pump_id = device["device_id"]
            break
    
    if not pump_id:
        pytest.skip("No pump device found")
    
    # Create a long-running pour operation
    response = client.post(
        f"/devices/{pump_id}/pump/pour-volume",
        json={
            "volume": 100.0,  # Large volume
            "flow_rate": 1.0,  # Slow flow rate
            "direction": "left",
            "blocking_mode": False
        }
    )
    
    if response.status_code == 202:  # If it's async
        job_id = response.json()["job_id"]
        
        # Try to delete while running
        response = client.delete(f"/jobs/{job_id}")
        # Should either be 409 (cannot delete running) or 404 (already completed in emulation)
        assert response.status_code in [404, 409]
