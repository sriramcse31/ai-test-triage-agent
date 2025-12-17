#!/usr/bin/env python3
"""
Generate all sample data for the project
Run from project root: python generate_samples.py
"""

from pathlib import Path

SAMPLE_LOGS = {
    "test_login_timeout.log": """[2024-01-15 10:23:45] INFO: Starting test: test_user_login
[2024-01-15 10:23:45] INFO: Navigating to https://app.example.com/login
[2024-01-15 10:23:46] INFO: Page loaded successfully
[2024-01-15 10:23:46] INFO: Entering username: test@example.com
[2024-01-15 10:23:46] INFO: Entering password: ********
[2024-01-15 10:23:46] INFO: Clicking login button
[2024-01-15 10:23:47] INFO: Waiting for dashboard element: #user-dashboard
[2024-01-15 10:24:17] ERROR: TimeoutError: Timeout 30000ms exceeded.
[2024-01-15 10:24:17] ERROR: waiting for selector "#user-dashboard" to be visible
[2024-01-15 10:24:17] ERROR: selector resolved to hidden <div id="user-dashboard" style="display: none">
[2024-01-15 10:24:17] FAIL: test_user_login - FAILED after 32s
[2024-01-15 10:24:17] INFO: Screenshot saved: login_timeout_20240115.png""",

    "test_selector_changed.log": """[2024-01-15 14:32:11] INFO: Starting test: test_add_to_cart
[2024-01-15 14:32:11] INFO: Navigating to https://shop.example.com/products/123
[2024-01-15 14:32:12] INFO: Product page loaded
[2024-01-15 14:32:12] INFO: Searching for add to cart button: button[data-test-id="add-cart"]
[2024-01-15 14:32:42] ERROR: TimeoutError: Timeout 30000ms exceeded.
[2024-01-15 14:32:42] ERROR: waiting for selector "button[data-test-id='add-cart']"
[2024-01-15 14:32:42] ERROR: Expected element not found on page
[2024-01-15 14:32:42] INFO: Available buttons: [.btn-primary.add-to-cart, .btn-wishlist, .btn-share]
[2024-01-15 14:32:42] FAIL: test_add_to_cart - FAILED after 31s
[2024-01-15 14:32:42] NOTE: Page structure appears to have changed""",

    "test_flaky_network.log": """[2024-01-15 16:45:23] INFO: Starting test: test_api_product_search
[2024-01-15 16:45:23] INFO: Sending GET request to /api/v1/products?q=laptop
[2024-01-15 16:45:28] ERROR: RequestError: connect ETIMEDOUT 10.0.1.42:443
[2024-01-15 16:45:28] ERROR: Failed to establish connection to API server
[2024-01-15 16:45:28] INFO: Retry attempt 1/3
[2024-01-15 16:45:33] ERROR: RequestError: socket hang up
[2024-01-15 16:45:33] INFO: Retry attempt 2/3
[2024-01-15 16:45:38] INFO: Request successful - Status 200
[2024-01-15 16:45:38] PASS: test_api_product_search - PASSED after 15s (with retries)
[2024-01-15 16:45:38] WARNING: Test exhibited flaky behavior - network instability detected""",

    "test_data_issue.log": """[2024-01-15 18:12:05] INFO: Starting test: test_order_checkout
[2024-01-15 18:12:05] INFO: Setting up test data: creating user account
[2024-01-15 18:12:06] INFO: User created: test_user_849201
[2024-01-15 18:12:06] INFO: Adding product to cart: SKU-12345
[2024-01-15 18:12:07] ERROR: DatabaseError: duplicate key value violates unique constraint "products_sku_key"
[2024-01-15 18:12:07] ERROR: DETAIL: Key (sku)=(SKU-12345) already exists.
[2024-01-15 18:12:07] ERROR: Test data setup failed
[2024-01-15 18:12:07] FAIL: test_order_checkout - FAILED after 2s
[2024-01-15 18:12:07] INFO: Data cleanup initiated
[2024-01-15 18:12:07] NOTE: Possible test data pollution from previous run"""
}

def generate_sample_logs():
    """Generate sample CI failure logs"""
    log_dir = Path("demo/sample_ci_failures")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    for filename, content in SAMPLE_LOGS.items():
        filepath = log_dir / filename
        filepath.write_text(content.strip())
        print(f"✓ Created: {filepath}")
    
    print("\n✅ Sample logs generated!")

def generate_sample_historical_data():
    """Generate sample historical failures with resolutions"""
    import json
    
    data = [
        {
            "test_name": "test_user_login",
            "error_message": "TimeoutError: selector '#user-dashboard' not visible",
            "error_type": "TimeoutError",
            "log_snippet": "waiting for selector '#user-dashboard' to be visible. Element is hidden.",
            "timestamp": "2024-01-10T10:00:00",
            "duration_seconds": 32.0,
            "retry_count": 0,
            "artifacts": ["login_fail.png"],
            "resolution": {
                "root_cause": "Dashboard renders with display:none initially, needs animation time",
                "classification": "timeout",
                "fix_applied": "Increased wait timeout to 60s and added waitForLoadState('networkidle')",
                "fixed_by": "engineer@example.com",
                "fixed_at": "2024-01-10T14:00:00",
                "confidence": 0.95
            },
            "flaky_score": 0.2
        }
    ]
    
    filepath = Path("demo/sample_historical_data.json")
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Created: {filepath}")

if __name__ == "__main__":
    print("🔧 Generating sample data...\n")
    generate_sample_logs()
    generate_sample_historical_data()
    print("\n✅ All sample data generated!")