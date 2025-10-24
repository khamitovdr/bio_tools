#!/usr/bin/env python3
"""Demo script for bioexperiment API."""

import os
import time
from fastapi.testclient import TestClient

# Set up emulation environment
os.environ["EMULATE_DEVICES"] = "true"
os.environ["N_VIRTUAL_PUMPS"] = "2"
os.environ["N_VIRTUAL_SPECTROPHOTOMETERS"] = "1"

from bioexperiment_api.app import create_app

def main():
    """Run API demo."""
    print("🧪 Bioexperiment API Demo")
    print("=" * 50)
    
    # Create app and client
    app = create_app()
    client = TestClient(app)
    
    # 1. Health check
    print("1️⃣  Health Check")
    health = client.get("/healthz")
    print(f"   Status: {health.json()}")
    
    # 2. List devices
    print("\n2️⃣  Discovering Devices")
    devices_response = client.get("/devices")
    devices = devices_response.json()
    print(f"   Found {len(devices)} devices:")
    
    pumps = []
    spectros = []
    
    for device in devices:
        device_type = device["type"]
        device_id = device["device_id"]
        port = device["port"]
        print(f"   - {device_type.capitalize()} ({device_id}) on {port}")
        
        if device_type == "pump":
            pumps.append(device_id)
        else:
            spectros.append(device_id)
    
    # 3. Pump operations
    if pumps:
        print(f"\n3️⃣  Pump Operations (using {pumps[0]})")
        pump_id = pumps[0]
        
        # Set flow rate
        print("   Setting default flow rate...")
        flow_response = client.post(
            f"/devices/{pump_id}/pump/set-default-flow",
            json={"flow_rate": 5.0}
        )
        print(f"   {flow_response.json()['message']}")
        
        # Pour volume (async)
        print("   Starting async pour operation...")
        pour_response = client.post(
            f"/devices/{pump_id}/pump/pour-volume",
            json={
                "volume": 10.0,
                "flow_rate": 2.0,
                "direction": "left",
                "blocking_mode": False
            }
        )
        
        if pour_response.status_code == 202:
            job_id = pour_response.json()["job_id"]
            print(f"   Job submitted: {job_id}")
            
            # Check job status
            for i in range(3):
                time.sleep(1)
                job_response = client.get(f"/jobs/{job_id}")
                job = job_response.json()
                print(f"   Job status: {job['status']}")
                
                if job["status"] in ["succeeded", "failed"]:
                    if job["status"] == "succeeded":
                        print("   ✅ Pour operation completed!")
                    else:
                        print(f"   ❌ Pour operation failed: {job.get('error')}")
                    break
        
        # Start continuous rotation
        print("   Starting continuous rotation...")
        start_response = client.post(
            f"/devices/{pump_id}/pump/start",
            json={"flow_rate": 3.0, "direction": "right"}
        )
        print(f"   {start_response.json()['message']}")
        
        # Stop pump
        print("   Stopping pump...")
        stop_response = client.post(f"/devices/{pump_id}/pump/stop")
        print(f"   {stop_response.json()['message']}")
    
    # 4. Spectrophotometer operations
    if spectros:
        print(f"\n4️⃣  Spectrophotometer Operations (using {spectros[0]})")
        spectro_id = spectros[0]
        
        # Get temperature
        print("   Getting temperature...")
        temp_response = client.get(f"/devices/{spectro_id}/spectro/temperature")
        temperature = temp_response.json()["temperature"]
        print(f"   Temperature: {temperature:.2f}°C")
        
        # Measure optical density (async)
        print("   Starting optical density measurement...")
        measure_response = client.post(
            f"/devices/{spectro_id}/spectro/measure",
            json={"timeout": 30}
        )
        
        if measure_response.status_code == 202:
            job_id = measure_response.json()["job_id"]
            print(f"   Job submitted: {job_id}")
            
            # Check job status
            for i in range(5):
                time.sleep(1)
                job_response = client.get(f"/jobs/{job_id}")
                job = job_response.json()
                print(f"   Job status: {job['status']}")
                
                if job["status"] in ["succeeded", "failed"]:
                    if job["status"] == "succeeded":
                        od = job["result"]
                        print(f"   ✅ Optical density: {od:.5f}")
                    else:
                        print(f"   ❌ Measurement failed: {job.get('error')}")
                    break
    
    # 5. Job management
    print("\n5️⃣  Job Management")
    jobs_response = client.get("/jobs?limit=5")
    jobs = jobs_response.json()
    print(f"   Recent jobs: {len(jobs)}")
    
    for job in jobs:
        action = job["action"]
        status = job["status"]
        device_id = job["device_id"]
        print(f"   - {action} on {device_id}: {status}")
    
    print("\n🎉 Demo completed!")
    print("   The API is working correctly with emulated devices.")
    print("   To run with real devices, set EMULATE_DEVICES=false")


if __name__ == "__main__":
    main()
