"""
Simple test script to verify authentication system
"""
import asyncio
import sys
import os
import requests
from datetime import datetime

# Add server directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_BASE = "http://localhost:8001"

def test_backend_health():
    """Test if backend is running"""
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            print("✅ Backend is running")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return False

def test_user_registration():
    """Test user registration"""
    print("\n📝 Testing user registration...")
    
    # Generate unique test data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_user = {
        "username": f"testuser_{timestamp}",
        "name": f"Test User {timestamp}",
        "email": f"test_{timestamp}@example.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/api/auth/register",
            json=test_user,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Registration response status: {response.status_code}")
        print(f"Registration response: {response.text}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Registration successful for user: {data['username']}")
            return test_user, data
        else:
            print(f"❌ Registration failed: {response.text}")
            return None, None
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return None, None

def test_user_login(credentials):
    """Test user login"""
    print("\n🔑 Testing user login...")
    
    try:
        # Prepare OAuth2 form data
        form_data = {
            "username": credentials["username"],  # Can be username or email
            "password": credentials["password"]
        }
        
        response = requests.post(
            f"{API_BASE}/api/auth/token",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"Login response status: {response.status_code}")
        print(f"Login response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Login successful, token received")
            return data["access_token"]
        else:
            print(f"❌ Login failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_get_profile(token):
    """Test getting user profile"""
    print("\n👤 Testing get user profile...")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{API_BASE}/api/auth/me",
            headers=headers
        )
        
        print(f"Profile response status: {response.status_code}")
        print(f"Profile response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Profile fetch successful for: {data['name']} ({data['email']})")
            return data
        else:
            print(f"❌ Profile fetch failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Profile fetch error: {e}")
        return None

def main():
    """Run all tests"""
    print("🔐 Starting Authentication System Tests\n")
    
    # Test 1: Backend Health
    if not test_backend_health():
        print("\n❌ Cannot proceed with tests - backend is not accessible")
        return
    
    # Test 2: User Registration
    test_user, registration_data = test_user_registration()
    if not test_user:
        print("\n❌ Cannot proceed with login tests - registration failed")
        return
    
    # Test 3: User Login
    token = test_user_login(test_user)
    if not token:
        print("\n❌ Cannot proceed with profile tests - login failed")
        return
    
    # Test 4: Get Profile
    profile_data = test_get_profile(token)
    if not profile_data:
        print("\n❌ Profile test failed")
        return
    
    print(f"\n🎉 All tests passed successfully!")
    print(f"Test user created: {test_user['username']} ({test_user['email']})")
    print(f"Token: {token[:50]}...")

if __name__ == "__main__":
    main()