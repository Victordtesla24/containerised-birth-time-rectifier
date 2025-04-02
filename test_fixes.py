#!/usr/bin/env python3
"""
Test script to verify the fixes made to the server code.
"""

import os
import sys
import time
import subprocess
import signal
import requests
import json

def start_servers():
    """Start the AI service and API Gateway servers."""
    print("Starting AI Service...")
    ai_service = subprocess.Popen(
        ["python", "-m", "ai_service.unified_main"],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    print("Starting API Gateway...")
    api_gateway = subprocess.Popen(
        ["python", "-m", "api_gateway.main"],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    return ai_service, api_gateway

def check_servers_health(max_attempts=10, delay=2):
    """Check if the servers are running and healthy."""
    print("Checking server health...")

    for attempt in range(max_attempts):
        print(f"Attempt {attempt + 1}/{max_attempts}...")

        # Check AI Service
        try:
            ai_response = requests.get("http://localhost:8001/", timeout=5)
            if ai_response.status_code == 200:
                print("✅ AI Service is running")
                ai_healthy = True
            else:
                print(f"❌ AI Service returned status code {ai_response.status_code}")
                ai_healthy = False
        except requests.RequestException as e:
            print(f"❌ AI Service check failed: {e}")
            ai_healthy = False

        # Check API Gateway
        try:
            gw_response = requests.get("http://localhost:3001/", timeout=5)
            if gw_response.status_code == 200:
                print("✅ API Gateway is running")
                gw_healthy = True
            else:
                print(f"❌ API Gateway returned status code {gw_response.status_code}")
                gw_healthy = False
        except requests.RequestException as e:
            print(f"❌ API Gateway check failed: {e}")
            gw_healthy = False

        if ai_healthy and gw_healthy:
            return True

        print(f"Waiting {delay} seconds before next attempt...")
        time.sleep(delay)

    return False

def stop_servers(ai_service, api_gateway):
    """Stop the servers cleanly."""
    print("Stopping servers...")

    # Send SIGTERM to processes
    if ai_service:
        ai_service.terminate()

    if api_gateway:
        api_gateway.terminate()

    # Wait for processes to terminate
    try:
        ai_service.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print("Forcibly killing AI Service...")
        ai_service.kill()

    try:
        api_gateway.wait(timeout=5)
    except subprocess.TimeoutExpired:
        print("Forcibly killing API Gateway...")
        api_gateway.kill()

def main():
    """Run the test script."""
    print("===== Server Fixes Test =====")

    # Start the servers
    ai_service, api_gateway = start_servers()

    try:
        # Wait for servers to start
        print("Waiting for servers to start...")
        time.sleep(10)

        # Check server health
        servers_healthy = check_servers_health()

        if servers_healthy:
            print("\n✅ All servers are running correctly!")
            print("The fixes have been successfully applied.")
            return 0
        else:
            print("\n❌ Servers did not start correctly.")
            print("There may still be issues with the code.")
            return 1
    finally:
        # Always stop the servers
        stop_servers(ai_service, api_gateway)

if __name__ == "__main__":
    sys.exit(main())
