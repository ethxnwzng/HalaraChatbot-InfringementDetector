"""
Goods-based infringement detector that uses the goods database instead of web crawling.

This module integrates the image_ai goods database access with the existing infringement
detection system to provide faster, more reliable product monitoring. It can detect
products that may not even be in the online store yet.

Key features:
- Direct database access to goods_center
- Retrieves products by date range
- Gets all product images from database
- Integrates with existing infringement detection
- Outputs to new Lark sheet for goods-based scanning
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from home.image_ai.goods import get_goods, get_goods_mall_all_picture
from home.crawler.infringement_detector import InfringementDetector
from home.crawler.lark_spreadsheet_writer import LarkSpreadsheetWriter
from home.crawler.crawler_config import CrawlerConfig

logger = logging.getLogger('GOODS_INFRINGEMENT_DETECTOR')


class GoodsBasedInfringementDetector:
    """
    Infringement detector that uses the goods database instead of web crawling.
    
    This class provides a more efficient and reliable way to monitor products
    for infringement by directly accessing the goods database. It can detect
    products that may not be visible on the website yet, providing earlier
    infringement detection.
    
    Key advantages over web crawling:
    - Faster access to product data
    - More reliable (no website changes affecting crawling)
    - Access to products not yet published online
    - Direct access to high-quality product images
    - No rate limiting or anti-bot measures
    """
    
    def __init__(self):
        """Initialize the goods-based infringement detector."""
        self.config = CrawlerConfig()
        self.detector = InfringementDetector()
        self.writer = LarkSpreadsheetWriter()
        
        # Set logging to INFO level to reduce verbosity
        logging.basicConfig(level=logging.INFO)
        logger.setLevel(logging.INFO)
    
    def get_products_from_database(self, days_back: int = 7) -> List[Dict]:
        """
        Retrieve products from the goods database for the specified date range.
        
        Args:
            days_back: Number of days to look back for products
            
        Returns:
            List[Dict]: List of products with database information
        """
        try:
            #calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            #format dates for database query
            online_from = start_date.strftime('%Y-%m-%d')
            online_to = end_date.strftime('%Y-%m-%d')
            
            logger.info(f"Retrieving products from {online_from} to {online_to}")
            
            #get products from database
            goods_list = get_goods(online_from, online_to)
            
            if not goods_list:
                logger.info("No products found in specified date range")
                return []
            
            logger.info(f"Retrieved {len(goods_list)} products from database")
            return goods_list
            
        except Exception as e:
            logger.error(f"Database error: Failed to retrieve products - {e}")
            return []
    
    def get_product_images(self, style_code: str) -> List[str]:
        """
        Get all image URLs for a specific product style code, sorted by preference.
        Prioritizes accessible regions and filters out China region URLs that cause timeouts.
        """
        try:
            images_data = get_goods_mall_all_picture(style_code)
            if not images_data:
                return []
            
            # Collect all image URLs from all SKC groups
            all_image_urls = []
            for skc_id, images in images_data.items():
                for image in images:
                    all_image_urls.append(image['url'])
            
            # Filter and prioritize URLs by accessibility
            accessible_urls = []
            china_region_urls = []
            other_urls = []
            
            for url in all_image_urls:
                if 'ap-southeast-1.amazonaws.com' in url:
                    # Most accessible region for OpenAI
                    accessible_urls.append(url)
                elif 'cn-northwest-1.amazonaws.com.cn' in url or 'cn-north-1.amazonaws.com.cn' in url:
                    # China region URLs that cause timeouts - skip these
                    china_region_urls.append(url)
                else:
                    # Other regions - try these as fallback
                    other_urls.append(url)
            
            # Return accessible URLs first, then others, skip China region entirely
            prioritized_urls = accessible_urls + other_urls
            
            if not prioritized_urls:
                logger.warning(f"NO ACCESSIBLE IMAGES: All images for {style_code} are from China region (timeout-prone)")
                return []
            
            logger.info(f"IMAGE FILTERING: {style_code} - {len(accessible_urls)} accessible, {len(other_urls)} other, {len(china_region_urls)} China region (skipped)")
            return prioritized_urls
            
        except Exception as e:
            logger.error(f"IMAGE RETRIEVAL ERROR: Failed to get images for {style_code} - {e}")
            return []

    def analyze_product_for_infringement(self, product: Dict) -> Dict:
        """
        Analyze a single product for infringement using multiple images if needed.
        """
        try:
            style_code = product.get('style_code')
            if not style_code:
                logger.warning(f"NO STYLE CODE: Skipping product without style code")
                return product
            
            # Get all available images
            image_urls = self.get_product_images(style_code)
            if not image_urls:
                logger.warning(f"NO IMAGES: No images found for product {style_code}")
                product['infringement_analysis'] = {
                    'detected_brands': [],
                    'risk_level': 'Unknown',
                    'detection_details': 'No images available for analysis'
                }
                product['risk_level'] = 'Unknown'
                product['analyzed_images'] = 0
                return product
            
            # Try each image until one works
            for i, image_url in enumerate(image_urls):
                logger.info(f"Trying image {i+1}/{len(image_urls)} for product {style_code}")
                
                analysis = self.detector.analyze_image(image_url)
                if analysis:
                    product['infringement_analysis'] = analysis
                    product['risk_level'] = analysis.get('risk_level', 'Unknown')
                    product['analyzed_images'] = i + 1
                    product['image_url'] = image_url
                    logger.info(f"ANALYSIS SUCCESS: Product {style_code} - {analysis.get('risk_level', 'Unknown')}")
                    return product
                else:
                    logger.warning(f"Image {i+1} failed for product {style_code}, trying next...")
            
            # If all images failed
            product['infringement_analysis'] = {
                'detected_brands': [],
                'risk_level': 'Unknown',
                'detection_details': 'Analysis failed for all images (OpenAI timeout or error)'
            }
            product['risk_level'] = 'Unknown'
            product['analyzed_images'] = len(image_urls)
            product['image_url'] = image_urls[0] if image_urls else ''
            logger.warning(f"ANALYSIS FAILED: Product {style_code} - All images failed")
            
            return product
            
        except Exception as e:
            logger.error(f"ANALYSIS ERROR: Failed to analyze product {product.get('style_code', 'unknown')} - {e}")
            product['infringement_analysis'] = {
                'detected_brands': [],
                'risk_level': 'Error',
                'detection_details': f'Analysis error: {str(e)}'
            }
            product['risk_level'] = 'Error'
            product['analyzed_images'] = 0
            return product
    
    def get_existing_products_from_main_sheet(self) -> Dict:
        """
        Read existing products from the 'Goods_DB Main' sheet to avoid duplicates.
        
        Returns:
            Dict: Existing products data organized by category
        """
        try:
            #find the Goods_DB Main sheet
            sheet_id = self.writer.find_sheet_by_name('Goods_DB Main')
            if not sheet_id:
                logger.info("GOODS_DB_MAIN: Sheet 'Goods_DB Main' not found, will create new products")
                return {}
            
            #read existing data from the sheet
            existing_data = self.writer.read_existing_data(sheet_id)
            logger.info(f"GOODS_DB_MAIN: Found {sum(len(products) for products in existing_data.values())} existing products")
            return existing_data
            
        except Exception as e:
            logger.error(f"GOODS_DB_MAIN ERROR: Failed to read existing data - {e}")
            return {}
    
    def filter_already_analyzed_products(self, new_products: List[Dict], existing_data: Dict) -> List[Dict]:
        """
        Filter out products that have already been analyzed in the main sheet.
        
        Args:
            new_products: List of products from database
            existing_data: Existing products from main sheet
            
        Returns:
            List[Dict]: Filtered list of products that haven't been analyzed
        """
        if not existing_data:
            logger.info("FILTER: No existing data, processing all products")
            return new_products
        
        #extract existing product URLs from main sheet
        existing_urls = set()
        for category, products in existing_data.items():
            for product in products:
                if 'product_url' in product:
                    existing_urls.add(product['product_url'])
        
        #filter out products that already exist
        filtered_products = []
        for product in new_products:
            product_url = product.get('global_mall_url', '')
            if product_url not in existing_urls:
                filtered_products.append(product)
            else:
                logger.info(f"FILTER: Skipping already analyzed product - {product.get('style_code', 'unknown')}")
        
        logger.info(f"FILTER: {len(new_products)} total products, {len(filtered_products)} new products to analyze")
        return filtered_products

    def run_goods_based_detection(self, days_back: int = 7, max_products: int = None, check_existing: bool = True) -> List[Dict]:
        """
        Run the complete goods-based infringement detection workflow.
        
        Args:
            days_back: Number of days to look back for products
            max_products: Maximum number of products to process
            check_existing: Whether to check for existing products in main sheet
            
        Returns:
            List[Dict]: List of analyzed products with infringement results
        """
        start_time = time.time()
        logger.info("Starting goods-based infringement detection...")
        
        try:
            #get products from database
            products = self.get_products_from_database(days_back)
            
            if not products:
                logger.info("No products found in database")
                return []
            
            #check for existing products if requested
            if check_existing:
                existing_data = self.get_existing_products_from_main_sheet()
                products = self.filter_already_analyzed_products(products, existing_data)
                
                if not products:
                    logger.info("All products have already been analyzed")
                    return []
            
            # Limit products if specified
            if max_products and len(products) > max_products:
                products = products[:max_products]
                logger.info(f"Limited to {max_products} products")
            
            #analyze products for infringement
            logger.info(f"Analyzing {len(products)} products for infringement...")
            analyzed_products = []
            
            for i, product in enumerate(products, 1):
                #only log every 10 products or the last one
                if i % 10 == 0 or i == len(products):
                    logger.info(f"Progress: {i}/{len(products)} products processed")
                
                analyzed_product = self.analyze_product_for_infringement(product)
                analyzed_products.append(analyzed_product)
                
                #rate limiting between analyses
                time.sleep(self.config.DELAY_BETWEEN_ANALYSIS)
            
            #calculate statistics
            execution_time = time.time() - start_time
            high_risk_count = len([p for p in analyzed_products if p.get('risk_level') == 'High Risk'])
            medium_risk_count = len([p for p in analyzed_products if p.get('risk_level') == 'Medium Risk'])
            
            logger.info(f"Analysis complete: {len(analyzed_products)} products analyzed in {execution_time:.2f} seconds")
            logger.info(f"Risk summary: {high_risk_count} high-risk, {medium_risk_count} medium-risk products")
            
            return analyzed_products
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            raise
    
    def write_results_to_sheet(self, products: List[Dict], sheet_name: str = None) -> bool:
        """
        Write analysis results to a new Lark sheet.
        
        Args:
            products: List of analyzed products
            sheet_name: Name for the new sheet (defaults to timestamped name)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not products:
                logger.info("NO PRODUCTS: No products to write to sheet")
                return True
            
            #generate sheet name if not provided
            if not sheet_name:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                sheet_name = f"Goods_Infringement_Scan_{timestamp}"
            
            #convert products to category-based format for spreadsheet writer
            products_by_category = {'Database Products': products}
            
            #write to new sheet
            self.writer.write_products_to_new_sheet(products_by_category, include_images=True)
            
            logger.info(f"SHEET WRITTEN: Results written to {sheet_name}")
            return True
            
        except Exception as e:
            logger.error(f"SHEET WRITING ERROR: {e}")
            return False
    
    def run_complete_workflow(self, days_back: int = 7, max_products: int = None, check_existing: bool = True) -> List[Dict]:
        """
        Run the complete workflow: database retrieval, analysis, and sheet writing.
        
        Args:
            days_back: Number of days to look back for products
            max_products: Maximum number of products to process
            check_existing: Whether to check for existing products in main sheet
            
        Returns:
            List[Dict]: List of analyzed products
        """
        logger.info("COMPLETE WORKFLOW: Starting goods-based infringement detection workflow...")
        
        products = self.run_goods_based_detection(days_back, max_products, check_existing)
        
        if products:
            # Write results to sheet
            success = self.write_results_to_sheet(products)
            if success:
                logger.info("WORKFLOW COMPLETE: Detection and sheet writing completed successfully")
            else:
                logger.error("WORKFLOW ERROR: Detection completed but sheet writing failed")
        else:
            logger.info("WORKFLOW COMPLETE: No products found to analyze")
        
        return products


def main():
    """Main entry point for goods-based infringement detection."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Goods-based Infringement Detector')
    parser.add_argument('--days-back', type=int, default=30, help='Number of days to look back for products (default: 30)')
    parser.add_argument('--max-products', type=int, help='Maximum number of products to process')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--skip-existing-check', action='store_true', help='Skip checking for existing products in main sheet')
    
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run detector
    detector = GoodsBasedInfringementDetector()
    
    try:
        start_time = time.time()
        products = detector.run_complete_workflow(
            days_back=args.days_back,
            max_products=args.max_products,
            check_existing=not args.skip_existing_check
        )
        
        # Log final summary
        execution_time = time.time() - start_time
        logger.info(f"JOB COMPLETED: Goods-based detection finished successfully")
        logger.info(f"TOTAL DURATION: {execution_time:.2f} seconds")
        logger.info(f"PRODUCTS PROCESSED: {len(products)} products")
        
    except Exception as e:
        logger.error(f"JOB FAILED: {e}")
        raise


if __name__ == '__main__':
    main() 