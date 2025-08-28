"""
Main job orchestrator for the Halara product infringement monitoring system.

This module contains the ProductionInfringementMonitor class which coordinates all
components of the Halara crawling and analysis system. It manages the complete
workflow from crawling products to analyzing them for infringement and writing
results to Lark spreadsheets.

The job orchestrator handles:
- Loading existing products from the master spreadsheet
- Coordinating the crawling process with duplicate filtering
- Managing the infringement analysis workflow
- Writing results to both new timestamped sheets and the master sheet
- Providing comprehensive logging and error handling
- Supporting incremental crawling to avoid reprocessing existing products

This is the main entry point for the production system and provides a clean
interface for running the complete monitoring workflow.
"""

import sys
import os
import json
import time
import traceback
import argparse
import logging
from datetime import datetime
from typing import Dict, Any, Set, List, Tuple

# Add the project root to sys.path so util is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import the logger from the correct path
try:
    from lark.util.log_util import logger
except ImportError:
    # Fallback to basic logging if the module is not available
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('HALARA_CRAWLER')

# Import local crawler files
from .halara_crawler import HalaraCrawler
from .infringement_detector import InfringementDetector
from .lark_spreadsheet_writer import LarkSpreadsheetWriter
from .crawler_config import CrawlerConfig, normalize_product_url


class ProductionInfringementMonitor:
    """
    Production-ready infringement monitoring system that handles incremental crawling,
    analysis, and spreadsheet writing with image uploads.
    
    This class orchestrates the complete workflow for monitoring Halara products
    for potential brand infringement. It coordinates between the crawler, infringement
    detector, and spreadsheet writer to create a comprehensive monitoring system.
    
    The system is designed for production use with:
    - Incremental crawling to avoid reprocessing existing products
    - Robust error handling and logging
    - Configurable product limits and processing parameters
    - Integration with Lark spreadsheets for data persistence
    - Support for both new sheet creation and master sheet updates
    
    Key features:
    - Loads existing products from Halara_Main to avoid duplicates
    - Crawls new products using the HalaraCrawler
    - Analyzes products for infringement using the InfringementDetector
    - Writes results to both new timestamped sheets and the master sheet
    - Uploads product images to the spreadsheets
    - Provides comprehensive execution reporting
    """
    
    def __init__(self):
        """
        Initialize the monitoring system with all required components.
        
        This method sets up all the necessary components for the monitoring
        system, including the crawler, infringement detector, spreadsheet
        writer, and configuration. It ensures all components are properly
        initialized and ready for production use.
        
        params:
            None
            
        returns:
            None: Initializes the monitoring system instance
        """
        self.config = CrawlerConfig()
        self.crawler = HalaraCrawler()
        self.detector = InfringementDetector()
        self.writer = LarkSpreadsheetWriter()
        
    def load_existing_products(self) -> tuple[Set[str], Dict]:
        """
        Load existing products from Halara_Main only.
        
        This method reads all existing products from the Halara_Main sheet
        to create a set of normalized URLs for duplicate detection. It also
        loads the complete product data for potential merging or reference.
        
        The method uses the centralized URL normalization function to ensure
        consistent duplicate detection across the entire system, handling
        the complex data structures that may be returned by the Lark API.
        
        params:
            None
            
        returns:
            tuple[Set[str], Dict]: A tuple containing:
                - Set of normalized product URLs for duplicate filtering
                - Dictionary of existing product data organized by category
        """
        logger.info("LOADING EXISTING DATA: Reading products from Halara_Main sheet...")
        sheet_data = self.writer.read_existing_data_from_main()
        existing_urls = set()
        existing_data = {}
        
        for category, products in sheet_data.items():
            existing_data[category] = []
            for product in products:
                product_url = product.get('product_url', '')
                normalized_url = normalize_product_url(product_url)
                if normalized_url:
                    existing_urls.add(normalized_url)
                    existing_data[category].append(product)
                    
                    # Debug logging for URL normalization
                    if self.config.ENABLE_DEBUG_LOGGING:
                        logger.info(f"DEBUG: Added URL - Original: {product_url}, Normalized: {normalized_url}")
        
        logger.info(f"EXISTING DATA LOADED: {len(existing_urls)} products from Halara_Main")
        return existing_urls, existing_data
    
    def run_crawler_job(self, max_products: int = None) -> List[Dict]:
        """
        Execute the complete crawling and analysis workflow.
        
        This method orchestrates the entire monitoring workflow, including
        loading existing products, crawling new products, analyzing them
        for infringement, and writing results to spreadsheets. It provides
        comprehensive logging and error handling throughout the process.
        
        The method is designed to be idempotent - running it multiple times
        will only process new products that weren't found in previous runs.
        
        params:
            max_products: Maximum number of new products to process in this run
                         If None, uses the configured max_products_per_run setting
                         
        returns:
            List[Dict]: List of processed products with analysis results
                Each product contains:
                - All original product data (URL, title, image, category)
                - analysis_result: Results from infringement detection
                - risk_level: Calculated risk level (high/medium/low)
                - analysis_timestamp: When the analysis was performed
        """
        start_time = time.time()
        logger.info("PRODUCTION MONITOR: Starting Halara product infringement monitoring system...")
        
        try:
            # Load existing products for duplicate filtering
            existing_urls, existing_data = self.load_existing_products()
            
            # Crawl for new products
            logger.info("CRAWLING PHASE: Starting product discovery and crawling...")
            new_products = self.crawler.crawl_new_products(
                existing_urls=existing_urls,
                max_products=max_products or self.config.MAX_PRODUCTS_PER_RUN
            )
            
            if not new_products:
                logger.info("NO NEW PRODUCTS: No new products found in this run")
                return []
            
            # Flatten the dictionary of products by category into a single list
            all_new_products = []
            for category_products in new_products.values():
                all_new_products.extend(category_products)
            
            logger.info(f"NEW PRODUCTS FOUND: {len(all_new_products)} products across {len(new_products)} categories")
            
            # Analyze products for infringement
            logger.info("ANALYSIS PHASE: Starting infringement detection analysis...")
            analyzed_products = self.crawler.analyze_products_for_infringement(all_new_products)
            
            # Merge with existing data
            logger.info("DATA MERGING: Combining new products with existing data...")
            all_products = self._merge_products(existing_data, analyzed_products)
            
            # Save data to JSON for debugging (if enabled)
            if self.config.PRESERVE_ANALYSIS_JSON:
                self._save_analysis_data(analyzed_products)
            
            # Write results to spreadsheets
            logger.info("SPREADSHEET WRITING: Writing results to new sheet and Halara_Main...")
            
            # Convert flattened list back to category-based dict for spreadsheet writer
            products_by_category = {}
            for product in analyzed_products:
                category = product.get('category', 'unknown')
                if category not in products_by_category:
                    products_by_category[category] = []
                products_by_category[category].append(product)
            
            # Only create sheets and write data if we have new products
            if products_by_category:
                # Write to new timestamped sheet
                self.writer.write_products_to_new_sheet(products_by_category, include_images=True)
                
                # Append to Halara_Main
                self.writer.append_to_halara_main(products_by_category, include_images=True)
                
                logger.info("SPREADSHEET WRITING: New products written to sheets successfully")
            else:
                logger.info("SPREADSHEET WRITING: No new products found - skipping sheet creation")
            
            # Calculate execution statistics
            execution_time = time.time() - start_time
            total_products = len(existing_urls) + len(all_new_products)
            high_risk_count = len([p for p in analyzed_products if p.get('risk_level') == 'high'])
            
            # Log completion summary
            self._log_completion_summary(execution_time, len(all_new_products), total_products, high_risk_count)
            
            return analyzed_products
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR: {e}")
            raise
    
    def _merge_products(self, existing_data: Dict, new_products: List[Dict]) -> Dict:
        """
        Merge new products with existing data organized by category.
        
        This method combines newly crawled and analyzed products with
        existing product data, organizing everything by category for
        consistent data structure and easy access.
        
        params:
            existing_data: Dictionary of existing products organized by category
            new_products: List of newly crawled and analyzed products
                         
        returns:
            Dict: Merged product data organized by category
                Structure: {category: [product1, product2, ...]}
        """
        merged_data = existing_data.copy()
        
        for product in new_products:
            category = product.get('category', 'unknown')
            if category not in merged_data:
                merged_data[category] = []
            merged_data[category].append(product)
        
        return merged_data
    
    def _save_analysis_data(self, products: List[Dict]):
        """
        Save analysis data to JSON file for debugging and reference.
        
        This method creates a timestamped JSON file containing all
        analysis results for debugging purposes. It's only called
        when the PRESERVE_ANALYSIS_JSON configuration is enabled.
        
        params:
            products: List of analyzed products with analysis results
                     
        returns:
            None: Creates a JSON file in the current directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"halara_analysis_{timestamp}.json"
        
        try:
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(products, f, indent=2, ensure_ascii=False)
            logger.info(f"ANALYSIS DATA SAVED: {filename}")
        except Exception as e:
            logger.error(f"ANALYSIS DATA SAVE ERROR: {e}")
    
    def _log_completion_summary(self, execution_time: float, new_products: int, total_products: int, high_risk_count: int):
        """
        Log a comprehensive summary of the job execution.
        
        This method provides a detailed summary of the job execution,
        including timing, product counts, and risk assessment results.
        It helps with monitoring and debugging the system performance.
        
        params:
            execution_time: Total execution time in seconds
            new_products: Number of new products processed
            total_products: Total products in the database after this run
            high_risk_count: Number of high-risk products identified
                            
        returns:
            None: Logs the summary information
        """
        logger.info("=" * 60)
        logger.info("PRODUCTION MONITOR COMPLETE")
        logger.info("=" * 60)
        logger.info(f"EXECUTION TIME: {execution_time:.2f} seconds")
        logger.info(f"NEW PRODUCTS PROCESSED: {new_products}")
        logger.info(f"TOTAL DATABASE SIZE: {total_products}")
        
        if new_products > 0:
            logger.info(f"HIGH RISK PRODUCTS: {high_risk_count}")
            logger.info("SHEETS CREATED: New timestamped sheet and Halara_Main updated")
        else:
            logger.info("SHEETS CREATED: None (no new products found)")
            
        logger.info("=" * 60)


def main():
    """
    Main entry point for the Halara crawler job.
    
    This function parses command line arguments and executes the
    production infringement monitoring job. It provides a command-line
    interface for running the crawler with configurable parameters.
    
    Command line arguments:
    --max-products: Maximum number of products to process (overrides config)
    --debug: Enable debug logging
    --help: Show help information
    
    params:
        None (reads from sys.argv)
        
    returns:
        None: Executes the crawler job and exits
    """
    parser = argparse.ArgumentParser(description='Halara Product Infringement Monitor')
    parser.add_argument('--max-products', type=int, help='Maximum number of products to process')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run the monitor
    monitor = ProductionInfringementMonitor()
    
    try:
        start_time = time.time()
        products = monitor.run_crawler_job(max_products=args.max_products)
        
        # Log final summary
        execution_time = time.time() - start_time
        logger.info(f"JOB COMPLETED: Halara crawler finished successfully")
        logger.info(f"TOTAL DURATION: {execution_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"JOB FAILED: {e}")
        raise


def run_crawler():
    """
    Standalone function for cron job execution.
    
    This function is designed to be called by the cron job scheduler.
    It creates a ProductionInfringementMonitor instance and runs the
    crawler job with default settings. It includes comprehensive error
    handling and logging for automated execution.
    
    params:
        None (uses default configuration)
        
    returns:
        None: Executes the crawler job and logs results
    """
    try:
        logger.info("CRON JOB STARTED: Halara crawler initiated by scheduler")
        
        # Create monitor instance
        monitor = ProductionInfringementMonitor()
        
        # Run the job with default settings (uses config MAX_PRODUCTS_PER_RUN)
        start_time = time.time()
        products = monitor.run_crawler_job()
        
        # Log completion
        execution_time = time.time() - start_time
        logger.info(f"CRON JOB COMPLETED: Successfully processed {len(products)} products in {execution_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"CRON JOB FAILED: {e}")
        logger.error(f"CRON JOB TRACEBACK: {traceback.format_exc()}")
        # Don't raise the exception - let the cron job continue running
        # but log the error for monitoring


def test_new_products_count(max_products: int = 50) -> int:
    """
    Test function to quickly check how many new products the crawler can find.
    
    This function performs a quick crawl to discover new products without doing
    full analysis or writing to sheets. It's useful for determining if a full
    crawl job is necessary before running the complete monitoring workflow.
    
    Args:
        max_products: Maximum number of products to check (default: 50 for quick test)
        
    Returns:
        int: Number of new products found that aren't in the existing Halara_Main data
    """
    try:
        logger.info("TEST FUNCTION: Starting new products count test...")
        
        # Create monitor instance
        monitor = ProductionInfringementMonitor()
        
        # Load existing products for comparison
        existing_urls, _ = monitor.load_existing_products()
        logger.info(f"TEST: Found {len(existing_urls)} existing products in Halara_Main")
        
        # Quick crawl to find new products
        logger.info(f"TEST: Crawling up to {max_products} products to check for new ones...")
        new_products = monitor.crawler.crawl_new_products(
            existing_urls=existing_urls,
            max_products=max_products
        )
        
        # Count total new products found
        total_new_products = 0
        for category_products in new_products.values():
            total_new_products += len(category_products)
        
        logger.info(f"TEST COMPLETE: Found {total_new_products} new products across {len(new_products)} categories")
        
        return total_new_products
        
    except Exception as e:
        logger.error(f"TEST FUNCTION ERROR: {e}")
        logger.error(f"TEST FUNCTION TRACEBACK: {traceback.format_exc()}")
        return -1  # Return -1 to indicate error


if __name__ == '__main__':
    main() 

#cron job: cd /Users/ethanxwong/Desktop/Lark_bot && python -c "from lark.home.crawler.halara_crawler_job import run_crawler; run_crawler()"