"""
Configuration file for the Halara crawler system.
This file centralizes all configurable settings, environment variables, and utility functions
for the Halara product crawling and infringement detection system. It provides a single
source for all crawler settings and includes a URL normalization function
for consistent duplicate detection across the entire system.

The file contains:
- Environment variable loading and configuration
- URL normalization utility function
- CrawlerConfig class with all system settings
- Documentation for all environment variables
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def normalize_product_url(url):
    """
    Centralized function to normalize product URLs for consistent duplicate detection.
    
    This function handles various URL formats that may be encountered during crawling
    and from the Lark API. It extracts the actual product URL from complex data structures
    (like lists containing dictionaries) and normalizes them to a consistent relative
    format for reliable duplicate detection across the entire system.
    
    params:
        url: Product URL in various formats (string, dict, list, or None)
            - Can be a simple string URL
            - Can be a dictionary with 'link' or 'text' keys (Lark API format)
            - Can be a list containing a dictionary (complex Lark API format)
            - Can be None or empty
            
    returns:
        str: Normalized relative URL starting with /, or empty string if invalid
        Examples:
        - "/products/high-waisted-leggings" 
        - "/products/dress-with-pockets?currentSkc=123456"
        - "" (empty string for invalid URLs)
    """
    if not url:
        return ''
    
    # Handle Lark API data structure: list containing dictionary
    if isinstance(url, list) and len(url) > 0:
        url_item = url[0]
        if isinstance(url_item, dict):
            if 'link' in url_item:
                url = url_item['link']
            elif 'text' in url_item:
                url = url_item['text']
            else:
                return ''
        else:
            url = url_item
    
    # Handle different data types
    if isinstance(url, dict):
        if 'link' in url:
            url = url['link']
        elif 'text' in url:
            url = url['text']
        else:
            return ''
    
    if not isinstance(url, str):
        url = str(url) if url else ''
    
    # Remove domain if present to match crawler's relative URL format
    if url.startswith('https://thehalara.com'):
        url = url.replace('https://thehalara.com', '')
    elif url.startswith('http://thehalara.com'):
        url = url.replace('http://thehalara.com', '')
    
    # Ensure it starts with / for relative URLs
    if not url.startswith('/'):
        url = '/' + url
        
    return url

class CrawlerConfig:
    """
    Configuration class for the Halara crawler system.
    
    This class provides centralized access to all configurable settings for the
    Halara product crawling and infringement detection system. It loads settings
    from environment variables with sensible defaults and provides methods to
    access configuration data in various formats for different components of
    the system.
    
    The class handles:
    - Crawler behavior settings (product limits, delays, pagination)
    - Category management (default categories, single-page categories)
    - Sheet management strategies
    - Logging and debugging configuration
    - Data persistence settings
    """
    
    # Crawler settings
    MAX_PRODUCTS_PER_RUN = int(os.getenv('HALARA_MAX_PRODUCTS_PER_RUN', '100'))
    PRODUCTS_PER_CATEGORY = int(os.getenv('HALARA_PRODUCTS_PER_CATEGORY', '20'))
    PAGES_PER_CATEGORY = int(os.getenv('HALARA_PAGES_PER_CATEGORY', '2'))
    
    # Timing settings
    DELAY_BETWEEN_PAGES = int(os.getenv('HALARA_DELAY_BETWEEN_PAGES', '1'))
    DELAY_BETWEEN_CATEGORIES = int(os.getenv('HALARA_DELAY_BETWEEN_CATEGORIES', '2'))
    DELAY_BETWEEN_ANALYSIS = int(os.getenv('HALARA_DELAY_BETWEEN_ANALYSIS', '1'))
    
    # Sheet management
    DEFAULT_SHEET_STRATEGY = os.getenv('HALARA_SHEET_STRATEGY', 'new_sheet')
    DEFAULT_TARGET_SHEET = os.getenv('HALARA_TARGET_SHEET', 'Halara_Main')
    
    # Data persistence
    PRESERVE_ANALYSIS_JSON = os.getenv('PRESERVE_CRAWLER_JSON', 'false').lower() == 'true'
    
    # Categories that don't support pagination (single page only)
    SINGLE_PAGE_CATEGORIES = [
        '/collections/the-halara-circle',
        '/collections/sales'
    ]
    
    # Default categories (fallback if dynamic discovery fails)
    DEFAULT_CATEGORIES = [
        '/collections/best-sellers',
        '/collections/new-arrivals',
        '/collections/clothing',
        '/collections/the-halara-circle',
        '/collections/sales',
        '/collections/dresses',
        '/collections/shorts-bikers',
        '/collections/pants',
        '/collections/tops',
        '/collections/skirts',
        '/collections/denim',
        '/collections/leggings',
        '/collections/plus-size'
    ]
    
    # User agent for web requests
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    
    # Base URL
    BASE_URL = 'https://thehalara.com'
    
    # Logging settings
    LOG_LEVEL = os.getenv('HALARA_LOG_LEVEL', 'INFO')
    ENABLE_DEBUG_LOGGING = os.getenv('HALARA_DEBUG', 'false').lower() == 'true'
    
    @classmethod
    def get_crawler_settings(cls) -> Dict[str, Any]:
        """
        Get all crawler settings as a dictionary for easy access by crawler components.
        
        This method provides a clean interface for the HalaraCrawler class to access
        all relevant configuration settings without needing to reference individual
        class attributes directly.
        
        params:
            None (class method)
            
        returns:
            Dict[str, Any]: Dictionary containing all crawler-related settings
            Keys include: max_products_per_run, products_per_category, pages_per_category,
            delay_between_pages, delay_between_categories, delay_between_analysis,
            single_page_categories, default_categories, user_agent, base_url
        """
        return {
            'max_products_per_run': cls.MAX_PRODUCTS_PER_RUN,
            'products_per_category': cls.PRODUCTS_PER_CATEGORY,
            'pages_per_category': cls.PAGES_PER_CATEGORY,
            'delay_between_pages': cls.DELAY_BETWEEN_PAGES,
            'delay_between_categories': cls.DELAY_BETWEEN_CATEGORIES,
            'delay_between_analysis': cls.DELAY_BETWEEN_ANALYSIS,
            'single_page_categories': cls.SINGLE_PAGE_CATEGORIES,
            'default_categories': cls.DEFAULT_CATEGORIES,
            'user_agent': cls.USER_AGENT,
            'base_url': cls.BASE_URL
        }
    
    @classmethod
    def get_sheet_settings(cls) -> Dict[str, Any]:
        """
        Get all sheet-related settings as a dictionary for spreadsheet operations.
        
        This method provides a clean interface for the LarkSpreadsheetWriter class
        to access all relevant sheet management settings without needing to reference
        individual class attributes directly.
        
        params:
            None (class method)
            
        returns:
            Dict[str, Any]: Dictionary containing all sheet-related settings
            Keys include: default_strategy, default_target_sheet, preserve_analysis_json
        """
        return {
            'default_strategy': cls.DEFAULT_SHEET_STRATEGY,
            'default_target_sheet': cls.DEFAULT_TARGET_SHEET,
            'preserve_analysis_json': cls.PRESERVE_ANALYSIS_JSON
        }
    
    @classmethod
    def print_configuration(cls):
        """
        Print current configuration for debugging and verification purposes.
        
        This method displays all current configuration settings in a formatted
        output, making it easy to verify that environment variables are being
        loaded correctly and to debug configuration-related issues.
        
        params:
            None (class method)
            
        returns:
            None: Prints configuration to stdout
        """
        print("=" * 60)
        print("HALARA CRAWLER CONFIGURATION")
        print("=" * 60)
        
        print(f"Max products per run: {cls.MAX_PRODUCTS_PER_RUN}")
        print(f"Products per category: {cls.PRODUCTS_PER_CATEGORY}")
        print(f"Pages per category: {cls.PAGES_PER_CATEGORY}")
        print(f"Delay between pages: {cls.DELAY_BETWEEN_PAGES}s")
        print(f"Delay between categories: {cls.DELAY_BETWEEN_CATEGORIES}s")
        print(f"Delay between analysis: {cls.DELAY_BETWEEN_ANALYSIS}s")
        print(f"Sheet strategy: {cls.DEFAULT_SHEET_STRATEGY}")
        print(f"Target sheet: {cls.DEFAULT_TARGET_SHEET}")
        print(f"Preserve analysis JSON: {cls.PRESERVE_ANALYSIS_JSON}")
        print(f"Debug logging: {cls.ENABLE_DEBUG_LOGGING}")
        print(f"Log level: {cls.LOG_LEVEL}")
        
        print(f"\nSingle page categories ({len(cls.SINGLE_PAGE_CATEGORIES)}):")
        for category in cls.SINGLE_PAGE_CATEGORIES:
            print(f"  - {category}")
        
        print(f"\nDefault categories ({len(cls.DEFAULT_CATEGORIES)}):")
        for category in cls.DEFAULT_CATEGORIES:
            print(f"  - {category}")
        
        print("=" * 60)


# Environment variable documentation
ENV_VARS_DOC = """
Environment Variables for Halara Crawler:

HALARA_MAX_PRODUCTS_PER_RUN (default: 100)
    Maximum number of products to process per job run

HALARA_PRODUCTS_PER_CATEGORY (default: 20)
    Maximum number of products to crawl per category page

HALARA_PAGES_PER_CATEGORY (default: 2)
    Number of pages to crawl per category (if pagination is supported)

HALARA_DELAY_BETWEEN_PAGES (default: 1)
    Delay in seconds between crawling different pages

HALARA_DELAY_BETWEEN_CATEGORIES (default: 2)
    Delay in seconds between crawling different categories

HALARA_DELAY_BETWEEN_ANALYSIS (default: 1)
    Delay in seconds between analyzing different products

HALARA_SHEET_STRATEGY (default: new_sheet)
    Sheet management strategy: 'new_sheet', 'append_to_main', or 'specific_sheet'

HALARA_TARGET_SHEET (default: Halara_Main)
    Target sheet name when using 'specific_sheet' strategy

PRESERVE_CRAWLER_JSON (default: false)
    Whether to preserve analysis JSON files for debugging

HALARA_LOG_LEVEL (default: INFO)
    Logging level: DEBUG, INFO, WARNING, ERROR

HALARA_DEBUG (default: false)
    Enable debug logging and additional output
"""

if __name__ == '__main__':
    # Print configuration when run directly
    CrawlerConfig.print_configuration()
    print("\n" + ENV_VARS_DOC) 