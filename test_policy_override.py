"""
Quick test for Dynamic MAS Update System

Tests the policy override feature by:
1. Creating an override via API
2. Simulating a workflow evaluation
3. Verifying the override is applied
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_policy_override():
    """Test the policy override system"""
    
    print("=" * 60)
    print("DYNAMIC MAS UPDATE SYSTEM - TEST")
    print("=" * 60)
    
    # Test 1: Create a policy override
    print("\n1. Creating policy override...")
    print("   Prompt: 'If a customer wants to update their address,")
    print("           don't update it directly. Mark as NEEDS_ATTENTION")
    print("           and escalate.'")
    
    override_request = {
        "prompt": "If a customer wants to update their order address, do not update it directly. Mark the order as 'NEEDS_ATTENTION' and escalate the situation.",
        "active": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/admin/policy-override",
            json=override_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Override created: {result['override_id']}")
            print(f"   Parsed: {json.dumps(result['parsed_policy'], indent=2)}")
            override_id = result['override_id']
        else:
            print(f"   ❌ Failed: {response.status_code} - {response.text}")
            return
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print(f"   Note: Make sure server is running at {BASE_URL}")
        return
    
    # Test 2: List all overrides
    print("\n2. Listing all policy overrides...")
    
    try:
        response = requests.get(f"{BASE_URL}/admin/policy-override")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Total overrides: {result['total']}")
            
            for override in result['overrides']:
                print(f"   - {override['override_id']} (active: {override['active']})")
        
        else:
            print(f"   ❌ Failed: {response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Toggle override
    print("\n3. Toggling override...")
    
    try:
        response = requests.post(f"{BASE_URL}/admin/policy-override/{override_id}/toggle")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Override is now: {'active' if result['active'] else 'inactive'}")
        
        else:
            print(f"   ❌ Failed: {response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Toggle back
    print("\n4. Toggling back to active...")
    
    try:
        response = requests.post(f"{BASE_URL}/admin/policy-override/{override_id}/toggle")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Override is now: {'active' if result['active'] else 'inactive'}")
        
        else:
            print(f"   ❌ Failed: {response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Try creating a session with address update request")
    print("2. Verify that system escalates instead of updating")
    print("3. Check trace for 'policy_override_applied' event")
    print("4. Test with: POST /session/start")
    print("   Body: {\"customer_query\": \"I want to change my address #1234\"}")


if __name__ == "__main__":
    test_policy_override()
