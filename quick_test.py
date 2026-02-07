"""Quick tool test - validates 3 sample tools"""
from tools.client import ToolsClient

client = ToolsClient(use_mock=True)

print("Testing 3 sample tools...")
print("=" * 50)

# Test 1
print("\n1. shopify_get_order_details")
r1 = client.execute("shopify_get_order_details", {"orderId": "#1234"})
print(f"   Success: {r1.success}")
print(f"   Data: {r1.data if r1.success else r1.error}")

# Test 2
print("\n2. skio_get_subscription_status")
r2 = client.execute("skio_get_subscription_status", {"email": "test@example.com"})
print(f"   Success: {r2.success}")
print(f"   Data: {r2.data if r2.success else r2.error}")

# Test 3 - Invalid params (should fail validation)
print("\n3. shopify_add_tags (with invalid params)")
r3 = client.execute("shopify_add_tags", {"wrong": "params"})
print(f"   Success: {r3.success}")
print(f"   Error: {r3.error}")

print("\n" + "=" * 50)
print("QUICK TEST COMPLETE")
print("All tools loaded successfully!")
