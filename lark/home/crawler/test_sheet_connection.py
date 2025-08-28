"""
NOTE: This file has been sanitized for portfolio display.
Replace placeholder values with actual credentials for production use.
"""

#!/usr/bin/env python3
"""
Test script for Lark sheet connection and management.
This script demonstrates the new flexible sheet management features.
"""

import os
from lark_spreadsheet_writer import LarkSpreadsheetWriter

def test_sheet_management():
    """Test the new sheet management features"""
    print("🧪 Testing Lark Sheet Management")
    print("=" * 50)
    
    try:
        # Initialize writer
        writer = LarkSpreadsheetWriter()
        
        # Test 1: List all sheets
        print("\n1. Listing all sheets in spreadsheet:")
        sheets = writer.list_sheets()
        
        # Test 2: Find specific sheet
        print("\n2. Testing sheet search:")
        test_sheet_name = "Halara_Main"
        found_sheet_id = writer.find_sheet_by_name(test_sheet_name)
        
        if found_sheet_id:
            print(f"   ✅ Found sheet '{test_sheet_name}'")
        else:
            print(f"   ❌ Sheet '{test_sheet_name}' not found")
        
        # Test 3: Get or create sheet
        print("\n3. Testing get_or_create_sheet:")
        sheet_id = writer.get_or_create_sheet("Test_Sheet")
        print(f"   📊 Using sheet ID: {sheet_id}")
        
        # Test 4: Connection test
        print("\n4. Testing connection:")
        if writer.test_connection():
            print("   ✅ Connection successful")
        else:
            print("   ❌ Connection failed")
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")

def test_environment_variables():
    """Test environment variable configuration"""
    print("\n🔧 Environment Variables Check")
    print("=" * 50)
    
    required_vars = ['LARK_SHEET_TOKEN', 'LARK_APP_ID', 'LARK_APP_SECRET']
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Show first few characters for security
            masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"❌ {var}: Not set")
    
    # Optional variables
    optional_vars = {
        'HALARA_SHEET_STRATEGY': 'new_sheet',
        'HALARA_TARGET_SHEET': 'Halara_Analysis',
        'PRESERVE_CRAWLER_JSON': 'false'
    }
    
    print("\nOptional variables:")
    for var, default in optional_vars.items():
        value = os.getenv(var, default)
        print(f"   {var}: {value}")

if __name__ == '__main__':
    test_environment_variables()
    test_sheet_management() 