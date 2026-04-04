import httpx
import os
import sys

# Test configuration
BASE_URL = "http://localhost:8000"
DEV_TOKEN = "dev-token-test-user"

def test_auth_enforcement():
    print(f"Testing auth enforcement at {BASE_URL}...")
    
    # Try to access a protected route (e.g. /auth/me) with dev token
    headers = {"Authorization": f"Bearer {DEV_TOKEN}"}
    try:
        response = httpx.get(f"{BASE_URL}/auth/me", headers=headers, timeout=5)
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("SUCCESS: Dev auth correctly blocked.")
        elif response.status_code == 200:
            print("FAILURE: Dev auth still allowed!")
        else:
            print(f"UNEXPECTED: Got status code {response.status_code}. Details: {response.text}")
            
    except httpx.ConnectError:
        print("ERROR: Backend server not running at http://localhost:8000")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_auth_enforcement()
