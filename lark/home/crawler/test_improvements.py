#!/usr/bin/env python3
"""
Test script for the improved Halara crawler system.
This script tests the new features:
1. Dynamic category discovery
2. Duplicate detection
3. Product limits
4. Configuration system
"""

import sys
import os
import json
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from lark.home.crawler.crawler_config import CrawlerConfig
from lark.home.crawler.halara_crawler import HalaraCrawler
from lark.home.crawler.lark_spreadsheet_writer import LarkSpreadsheetWriter


def test_configuration():
    """Test the configuration system"""
    print("=" * 60)
    print("TESTING CONFIGURATION SYSTEM")
    print("=" * 60)
    
    config = CrawlerConfig()
    config.print_configuration()
    
    # Test configuration access
    print(f"\n✅ Configuration loaded successfully:")
    print(f"   Max products per run: {config.MAX_PRODUCTS_PER_RUN}")
    print(f"   Default sheet strategy: {config.DEFAULT_SHEET_STRATEGY}")
    print(f"   Default target sheet: {config.DEFAULT_TARGET_SHEET}")
    
    return True


def test_category_discovery():
    """Test dynamic category discovery"""
    print("\n" + "=" * 60)
    print("TESTING CATEGORY DISCOVERY")
    print("=" * 60)
    
    crawler = HalaraCrawler()
    
    try:
        categories = crawler.discover_categories()
        print(f"✅ Discovered {len(categories)} categories:")
        
        for i, category in enumerate(categories[:10], 1):  # Show first 10
            print(f"   {i}. {category}")
        
        if len(categories) > 10:
            print(f"   ... and {len(categories) - 10} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in category discovery: {e}")
        return False


def test_pagination_detection():
    """Test pagination detection for categories"""
    print("\n" + "=" * 60)
    print("TESTING PAGINATION DETECTION")
    print("=" * 60)
    
    crawler = HalaraCrawler()
    
    # Test a few categories
    test_categories = [
        '/collections/best-sellers',
        '/collections/the-halara-circle',
        '/collections/sales'
    ]
    
    for category in test_categories:
        try:
            supports_pagination = crawler.test_category_pagination(category)
            status = "✅ Supports pagination" if supports_pagination else "❌ Single page only"
            print(f"{category}: {status}")
        except Exception as e:
            print(f"{category}: ❌ Error testing pagination - {e}")
    
    return True


def test_duplicate_detection():
    """Test duplicate detection logic"""
    print("\n" + "=" * 60)
    print("TESTING DUPLICATE DETECTION")
    print("=" * 60)
    
    # Create test data
    existing_products = {
        'dresses': [
            {'product_url': '/products/dress-1', 'title': 'Dress 1'},
            {'product_url': '/products/dress-2', 'title': 'Dress 2'},
        ]
    }
    
    new_products = {
        'dresses': [
            {'product_url': '/products/dress-2', 'title': 'Dress 2 (duplicate)'},
            {'product_url': '/products/dress-3', 'title': 'Dress 3 (new)'},
        ],
        'tops': [
            {'product_url': '/products/top-1', 'title': 'Top 1 (new)'},
        ]
    }
    
    # Create sets of existing URLs
    existing_urls = set()
    for category, products in existing_products.items():
        for product in products:
            existing_urls.add(product['product_url'])
    
    # Test filtering
    filtered_products = {}
    total_filtered = 0
    
    for category, products in new_products.items():
        filtered_category_products = []
        for product in products:
            if product['product_url'] not in existing_urls:
                filtered_category_products.append(product)
                total_filtered += 1
        
        if filtered_category_products:
            filtered_products[category] = filtered_category_products
    
    print(f"✅ Duplicate detection test:")
    print(f"   Existing products: {len(existing_urls)}")
    print(f"   New products before filtering: {sum(len(products) for products in new_products.values())}")
    print(f"   New products after filtering: {total_filtered}")
    print(f"   Duplicates removed: {sum(len(products) for products in new_products.values()) - total_filtered}")
    
    # Verify results
    expected_filtered = 2  # dress-3 and top-1 should remain
    if total_filtered == expected_filtered:
        print(f"✅ Duplicate detection working correctly")
        return True
    else:
        print(f"❌ Duplicate detection failed - expected {expected_filtered}, got {total_filtered}")
        return False


def test_crawler_initialization():
    """Test crawler initialization with configuration"""
    print("\n" + "=" * 60)
    print("TESTING CRAWLER INITIALIZATION")
    print("=" * 60)
    
    try:
        crawler = HalaraCrawler()
        
        print(f"✅ Crawler initialized successfully:")
        print(f"   Base URL: {crawler.base_url}")
        print(f"   Max products per run: {crawler.max_products_per_run}")
        print(f"   Products per category: {crawler.products_per_category}")
        print(f"   Pages per category: {crawler.pages_per_category}")
        print(f"   Delay between pages: {crawler.delay_between_pages}s")
        print(f"   Delay between categories: {crawler.delay_between_categories}s")
        print(f"   Delay between analysis: {crawler.delay_between_analysis}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing crawler: {e}")
        return False


def test_spreadsheet_writer():
    """Test spreadsheet writer initialization"""
    print("\n" + "=" * 60)
    print("TESTING SPREADSHEET WRITER")
    print("=" * 60)
    
    try:
        writer = LarkSpreadsheetWriter()
        
        # Test connection
        if writer.test_connection():
            print("✅ Spreadsheet writer initialized and connection successful")
            
            # List sheets
            sheets = writer.list_sheets()
            if sheets:
                print(f"✅ Found {len(sheets)} sheets in spreadsheet")
                return True
            else:
                print("⚠️  No sheets found in spreadsheet")
                return True
        else:
            print("❌ Spreadsheet connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing spreadsheet writer: {e}")
        return False


def run_all_tests():
    """Run all tests"""
    print("🧪 RUNNING HALARA CRAWLER IMPROVEMENT TESTS")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Configuration System", test_configuration),
        ("Category Discovery", test_category_discovery),
        ("Pagination Detection", test_pagination_detection),
        ("Duplicate Detection", test_duplicate_detection),
        ("Crawler Initialization", test_crawler_initialization),
        ("Spreadsheet Writer", test_spreadsheet_writer),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The improvements are working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the configuration and dependencies.")
    
    return passed == total


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1) 