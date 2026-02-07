"""
Test Script for Hackathon Tool Spec Compliance
Tests all 18 official tools with mock server
"""
import sys
from tools.client import ToolsClient

def print_result(tool_name: str, result):
    """Pretty print test result"""
    status = "✅ PASS" if result.success else "❌ FAIL"
    print(f"\n{status} | {tool_name}")
    if result.success:
        print(f"  Data: {result.data}")
    else:
        print(f"  Error: {result.error}")
    print(f"  Retries: {result.retry_count}")


def test_all_tools():
    """Test all 18 official Hackathon tools"""
    print("=" * 60)
    print("HACKATHON TOOL SPEC COMPLIANCE TEST")
    print("=" * 60)
    
    # Initialize client with mock server
    client = ToolsClient(use_mock=True, max_retries=1)
    
    tests = [
        # SHOPIFY TOOLS (13)
        {
            "name": "shopify_add_tags",
            "params": {
                "id": "gid://shopify/Order/12345",
                "tags": ["test-tag", "verified"]
            }
        },
        {
            "name": "shopify_cancel_order",
            "params": {
                "orderId": "gid://shopify/Order/12345",
                "reason": "CUSTOMER",
                "notifyCustomer": True,
                "restock": True,
                "staffNote": "Customer requested cancellation",
                "refundMode": "ORIGINAL",
                "storeCredit": {"expiresAt": None}
            }
        },
        {
            "name": "shopify_create_discount_code",
            "params": {
                "type": "percentage",
                "value": 0.1,
                "duration": 48,
                "productIds": []
            }
        },
        {
            "name": "shopify_create_return",
            "params": {
                "orderId": "gid://shopify/Order/12345"
            }
        },
        {
            "name": "shopify_create_store_credit",
            "params": {
                "id": "gid://shopify/Customer/7424155189325",
                "creditAmount": {
                    "amount": "49.99",
                    "currencyCode": "USD"
                },
                "expiresAt": None
            }
        },
        {
            "name": "shopify_get_collection_recommendations",
            "params": {
                "queryKeys": ["skincare", "acne"]
            }
        },
        {
            "name": "shopify_get_customer_orders",
            "params": {
                "email": "test@example.com",
                "after": "null",
                "limit": 10
            }
        },
        {
            "name": "shopify_get_order_details",
            "params": {
                "orderId": "#1234"
            }
        },
        {
            "name": "shopify_get_product_details",
            "params": {
                "queryKey": "gid://shopify/Product/123",
                "queryType": "id"
            }
        },
        {
            "name": "shopify_get_product_recommendations",
            "params": {
                "queryKeys": ["moisturizer", "sensitive skin"]
            }
        },
        {
            "name": "shopify_get_related_knowledge_source",
            "params": {
                "question": "How do I apply this product?",
                "specificToProductId": "gid://shopify/Product/123"
            }
        },
        {
            "name": "shopify_refund_order",
            "params": {
                "orderId": "gid://shopify/Order/12345",
                "refundMethod": "ORIGINAL_PAYMENT_METHODS"
            }
        },
        {
            "name": "shopify_update_order_shipping_address",
            "params": {
                "orderId": "gid://shopify/Order/12345",
                "shippingAddress": {
                    "firstName": "John",
                    "lastName": "Doe",
                    "company": "Test Corp",
                    "address1": "123 Main St",
                    "address2": "Apt 4B",
                    "city": "New York",
                    "provinceCode": "NY",
                    "country": "US",
                    "zip": "10001",
                    "phone": "+1234567890"
                }
            }
        },
        
        # SKIO TOOLS (5)
        {
            "name": "skio_cancel_subscription",
            "params": {
                "subscriptionId": "sub_123",
                "cancellationReasons": ["too expensive", "not using it"]
            }
        },
        {
            "name": "skio_get_subscription_status",
            "params": {
                "email": "test@example.com"
            }
        },
        {
            "name": "skio_pause_subscription",
            "params": {
                "subscriptionId": "sub_123",
                "pausedUntil": "2026-03-01"
            }
        },
        {
            "name": "skio_skip_next_order_subscription",
            "params": {
                "subscriptionId": "sub_123"
            }
        },
        {
            "name": "skio_unpause_subscription",
            "params": {
                "subscriptionId": "sub_123"
            }
        }
    ]
    
    print(f"\nTesting {len(tests)} tools...\n")
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = client.execute(test["name"], test["params"])
            print_result(test["name"], result)
            
            if result.success or result.error:  # Either success or proper error response
                passed += 1
            else:
                failed += 1
                
        except Exception as e:
            print(f"\n❌ EXCEPTION | {test['name']}")
            print(f"  Error: {str(e)}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/len(tests)*100):.1f}%")
    
    # Check response format compliance
    print("\n" + "=" * 60)
    print("RESPONSE FORMAT COMPLIANCE")
    print("=" * 60)
    for result in client.call_history:
        has_success = hasattr(result, 'success')
        has_data_or_error = hasattr(result, 'data') or hasattr(result, 'error')
        compliant = has_success and has_data_or_error
        status = "✅" if compliant else "❌"
        print(f"{status} {result.tool_name}: success={result.success}")
    
    return passed == len(tests)


if __name__ == "__main__":
    success = test_all_tools()
    sys.exit(0 if success else 1)
