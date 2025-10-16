#!/usr/bin/env python3
"""
Telegram Notification Test Runner

This script demonstrates how to run the Telegram notification tests
and provides sample test data for the VIGILANTEye surveillance system.

Usage:
    python tests/run_telegram_tests.py

Requirements:
    - pytest
    - Flask test client
    - Mock library for external API calls
"""

import sys
import os
import pytest
import requests
import json
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_telegram_tests():
    """Run all Telegram notification tests"""
    print("🚀 Running Telegram Notification Tests...")
    print("=" * 50)
    
    # Run pytest for the telegram test file
    test_file = os.path.join(os.path.dirname(__file__), 'test_telegram.py')
    exit_code = pytest.main([
        test_file,
        '-v',  # verbose output
        '--tb=short',  # shorter traceback format
        '--color=yes'  # colored output
    ])
    
    return exit_code == 0

def test_api_endpoints_directly():
    """Test Telegram API endpoints directly (requires running server)"""
    print("\n🔧 Testing API Endpoints Directly...")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # Sample test data
    test_cases = [
        {
            "name": "Intrusion Alert",
            "data": {
                "type": "text",
                "content": "🚨 INTRUSION ALERT 🚨\nLocation: Building A - Main Entrance\nTime: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "channel_id": "-1001234567890"
            }
        },
        {
            "name": "Motion Detection",
            "data": {
                "type": "text",
                "content": "⚠️ Motion detected in restricted area\nCamera: CAM-03 (Parking Lot)\nDuration: 2 minutes",
                "channel_id": "-1001234567890"
            }
        },
        {
            "name": "Surveillance Image",
            "data": {
                "type": "image",
                "content": "https://example.com/surveillance/alert_20240115_143025.jpg",
                "channel_id": "-1001234567890"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📤 Testing: {test_case['name']}")
        try:
            response = requests.post(
                f"{base_url}/api/telegram/ingest",
                json=test_case['data'],
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Success - Message ID: {result.get('id')}")
                print(f"   📊 Status: {result.get('status')}")
            else:
                print(f"   ❌ Failed - Status: {response.status_code}")
                print(f"   📝 Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ⚠️  Connection Error - Make sure the server is running on {base_url}")
            break
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

def show_sample_data():
    """Display sample test data for manual testing"""
    print("\n📋 Sample Test Data for Manual Testing")
    print("=" * 50)
    
    sample_data = {
        "surveillance_alerts": [
            {
                "type": "text",
                "content": "🚨 INTRUSION ALERT 🚨\nLocation: Building A - Main Entrance\nTime: 2024-01-15 14:30:25\nConfidence: 95%",
                "channel_id": "-1001234567890"
            },
            {
                "type": "text",
                "content": "⚠️ MOTION DETECTED\nArea: Parking Lot - Zone B\nTime: 2024-01-15 14:32:10\nDuration: 2 minutes\nCamera: CAM-03",
                "channel_id": "-1001234567890"
            },
            {
                "type": "image",
                "content": "https://example.com/surveillance/alert_20240115_143025.jpg",
                "channel_id": "-1001234567890"
            }
        ],
        "webhook_callback": {
            "callback_query": {
                "id": "callback123456",
                "data": "ack:message-id-here",
                "from": {
                    "id": 12345,
                    "first_name": "Security",
                    "username": "security_operator"
                },
                "date": 1640995200
            }
        },
        "curl_examples": {
            "send_text_message": """
curl -X POST http://localhost:5000/api/telegram/ingest \\
  -H "Content-Type: application/json" \\
  -d '{
    "type": "text",
    "content": "🚨 INTRUSION ALERT 🚨\\nLocation: Building A\\nTime: 2024-01-15 14:30:25",
    "channel_id": "-1001234567890"
  }'
            """,
            "send_image_message": """
curl -X POST http://localhost:5000/api/telegram/ingest \\
  -H "Content-Type: application/json" \\
  -d '{
    "type": "image",
    "content": "https://example.com/surveillance/alert.jpg",
    "channel_id": "-1001234567890"
  }'
            """,
            "test_webhook": """
curl -X POST http://localhost:5000/webhook/telegram/test-secret \\
  -H "Content-Type: application/json" \\
  -d '{
    "callback_query": {
      "id": "callback123",
      "data": "ack:message-id-here",
      "from": {"id": 12345, "first_name": "Test"},
      "date": 1640995200
    }
  }'
            """
        }
    }
    
    print("📤 Surveillance Alert Examples:")
    for i, alert in enumerate(sample_data["surveillance_alerts"], 1):
        print(f"\n{i}. {alert['type'].upper()} Message:")
        print(json.dumps(alert, indent=2))
    
    print("\n🔄 Webhook Callback Example:")
    print(json.dumps(sample_data["webhook_callback"], indent=2))
    
    print("\n🌐 cURL Examples:")
    for name, example in sample_data["curl_examples"].items():
        print(f"\n{name.replace('_', ' ').title()}:")
        print(example)

def main():
    """Main test runner function"""
    print("🔍 VIGILANTEye Telegram Notification Test Suite")
    print("=" * 60)
    
    # Show sample data first
    show_sample_data()
    
    # Ask user what they want to do
    print("\n" + "=" * 60)
    print("Choose an option:")
    print("1. Run unit tests (pytest)")
    print("2. Test API endpoints directly (requires running server)")
    print("3. Show sample data only")
    print("4. Run all tests")
    
    try:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            success = run_telegram_tests()
            if success:
                print("\n✅ All unit tests passed!")
            else:
                print("\n❌ Some unit tests failed!")
                
        elif choice == "2":
            test_api_endpoints_directly()
            
        elif choice == "3":
            print("Sample data displayed above.")
            
        elif choice == "4":
            print("\n🔄 Running all tests...")
            success = run_telegram_tests()
            if success:
                print("\n✅ Unit tests passed!")
            else:
                print("\n❌ Unit tests failed!")
            
            print("\n🔧 Testing API endpoints...")
            test_api_endpoints_directly()
            
        else:
            print("Invalid choice. Please run the script again.")
            
    except KeyboardInterrupt:
        print("\n\n👋 Test run cancelled by user.")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
