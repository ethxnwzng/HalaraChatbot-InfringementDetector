#!/usr/bin/env python3
"""
Test script for the goods-based infringement detector.

This script tests the basic functionality of the goods-based detector
to ensure it can retrieve products from the database and analyze them.
"""

import sys
import os
import logging
from datetime import datetime

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from goods_based_infringement_detector import GoodsBasedInfringementDetector


def test_database_connection():
    """Test that we can connect to the database and retrieve products."""
    print("=== TESTING DATABASE CONNECTION ===")
    
    detector = GoodsBasedInfringementDetector()
    
    # Test with a longer date range to find products
    products = detector.get_products_from_database(days_back=7)
    
    if products:
        print(f"✅ SUCCESS: Retrieved {len(products)} products from database")
        print(f"Sample product: {products[0]}")
        return True
    else:
        print("❌ FAILED: No products retrieved from database")
        return False


def test_image_retrieval():
    """Test that we can retrieve images for a product."""
    print("\n=== TESTING IMAGE RETRIEVAL ===")
    
    detector = GoodsBasedInfringementDetector()
    
    # Get a sample product
    products = detector.get_products_from_database(days_back=7)
    
    if not products:
        print("❌ FAILED: No products available for image testing")
        return False
    
    # Test with the first product
    sample_product = products[0]
    style_code = sample_product.get('style_code')
    
    if not style_code:
        print("❌ FAILED: Sample product has no style code")
        return False
    
    print(f"Testing image retrieval for style code: {style_code}")
    
    # Get images
    image_urls = detector.get_product_images(style_code)
    
    if image_urls:
        print(f"✅ SUCCESS: Retrieved {len(image_urls)} images for {style_code}")
        print(f"Sample image URL: {image_urls[0]}")
        return True
    else:
        print(f"❌ FAILED: No images found for {style_code}")
        return False


def test_single_product_analysis():
    """Test analyzing a single product for infringement."""
    print("\n=== TESTING SINGLE PRODUCT ANALYSIS ===")
    
    detector = GoodsBasedInfringementDetector()
    
    # Get a sample product
    products = detector.get_products_from_database(days_back=7)
    
    if not products:
        print("❌ FAILED: No products available for analysis testing")
        return False
    
    # Test with the first product
    sample_product = products[0]
    print(f"Testing analysis for product: {sample_product.get('style_code')}")
    
    # Analyze the product
    analyzed_product = detector.analyze_product_for_infringement(sample_product)
    
    if analyzed_product:
        print("✅ SUCCESS: Product analysis completed")
        print(f"Risk Level: {analyzed_product.get('risk_level')}")
        print(f"Analyzed Images: {analyzed_product.get('analyzed_images')}")
        
        analysis = analyzed_product.get('infringement_analysis', {})
        print(f"Detection Details: {analysis.get('detection_details', 'N/A')}")
        
        return True
    else:
        print("❌ FAILED: Product analysis failed")
        return False


def test_complete_workflow():
    """Test the complete workflow with at least 20 products."""
    print("=== TESTING COMPLETE WORKFLOW (AT LEAST 20 PRODUCTS) ===")
    
    detector = GoodsBasedInfringementDetector()
    
    # Test with a much longer date range to get more products (90 days = 3 months)
    products = detector.get_products_from_database(days_back=90)
    
    if not products:
        print("❌ FAILED: No products retrieved from database")
        return False
    
    # Use all available products, but target at least 20
    target_products = max(20, len(products))
    print(f"✅ Retrieved {len(products)} products, targeting {target_products} products for analysis")
    
    # Test the complete workflow with sheet writing
    try:
        results = detector.run_complete_workflow(days_back=90, max_products=target_products)
        print(f"✅ SUCCESS: Processed {len(results)} products successfully")
        print(f"Results summary: {len(results)} analysis results")
        print("📊 Sheet writing completed - check your Lark sheets for the new analysis")
        return True
    except Exception as e:
        print(f"❌ FAILED: Error in complete workflow: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 GOODS-BASED INFRINGEMENT DETECTOR TESTS")
    print("=" * 50)
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    tests = [
        test_database_connection,
        test_image_retrieval,
        test_single_product_analysis,
        test_complete_workflow
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ TEST FAILED WITH EXCEPTION: {e}")
    
    print("\n" + "=" * 50)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The goods-based detector is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 