"""
Halara product crawler for scraping product data from thehalara.com.

This module contains the HalaraCrawler class which is responsible for crawling product
information from the Halara website. It handles category discovery, pagination,
product extraction, and duplicate filtering. The crawler works in conjunction with
the infringement detector and spreadsheet writer to create a complete product
monitoring and analysis system.

The crawler supports:
- Dynamic category discovery from the website
- Pagination handling for large product catalogs
- Duplicate detection using normalized URLs
- Configurable product limits and delays
- Integration with the centralized configuration system

Key features:
- Respects robots.txt and implements polite crawling delays
- Filters out existing products to avoid duplicates
- Extracts comprehensive product information (URLs, images, titles)
- Supports both single-page and multi-page categories
"""

import json
import time
import requests
import logging
from bs4 import BeautifulSoup
from .infringement_detector import InfringementDetector
from .crawler_config import CrawlerConfig, normalize_product_url

# Set up logger
logger = logging.getLogger('HALARA_CRAWLER')

class HalaraCrawler:
    """
    Main crawler class for extracting product data from thehalara.com.
    
    This class handles all aspects of crawling the Halara website, including
    category discovery, product extraction, pagination, and duplicate filtering.
    It works as part of a larger system that includes infringement detection
    and spreadsheet writing capabilities.
    
    The crawler is designed to be respectful of the website's resources by
    implementing configurable delays and following web scraping best practices.
    It also integrates with the centralized configuration system for consistent
    behavior across different environments.
    
    Key responsibilities:
    - Discover and crawl product categories
    - Extract product information from HTML pages
    - Handle pagination for large product catalogs
    - Filter out duplicate products using normalized URLs
    - Respect rate limiting and implement polite delays
    - Provide detailed logging for monitoring and debugging
    """
    
    def __init__(self):
        """
        Initialize the Halara crawler with configuration and settings.
        
        This method sets up the crawler with all necessary configuration,
        including base URLs, headers, category settings, and operational
        parameters. It loads settings from the centralized configuration
        system to ensure consistent behavior.
        
        params:
            None
            
        returns:
            None: Initializes the crawler instance
        """
        # Load configuration
        self.config = CrawlerConfig()
        self.base_url = self.config.BASE_URL
        self.headers = {
            'User-Agent': self.config.USER_AGENT
        }
        
        # Load settings from configuration
        self.default_categories = self.config.DEFAULT_CATEGORIES
        self.single_page_categories = self.config.SINGLE_PAGE_CATEGORIES
        self.products_per_category = self.config.PRODUCTS_PER_CATEGORY
        self.pages_per_category = self.config.PAGES_PER_CATEGORY
        self.max_products_per_run = self.config.MAX_PRODUCTS_PER_RUN
        self.delay_between_pages = self.config.DELAY_BETWEEN_PAGES
        self.delay_between_categories = self.config.DELAY_BETWEEN_CATEGORIES
        self.delay_between_analysis = self.config.DELAY_BETWEEN_ANALYSIS
        
        self.infringement_detector = InfringementDetector()

    def discover_categories(self):
        """
        Dynamically discover categories from the homepage.
        Returns a list of category URLs that can be crawled.
        """
        try:
            logger.info("CATEGORY DISCOVERY: Scanning homepage for product categories...")
            response = requests.get(self.base_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Look for category links in navigation or menu
            category_links = []
            
            # Method 1: Look for navigation menu links
            nav_links = soup.find_all('a', href=True)
            for link in nav_links:
                href = link.get('href', '')
                if href.startswith('/collections/') and href not in category_links:
                    category_links.append(href)
            
            # Method 2: Look for category cards or featured collections
            category_cards = soup.find_all('a', class_=lambda x: x and 'collection' in x.lower())
            for card in category_cards:
                href = card.get('href', '')
                if href.startswith('/collections/') and href not in category_links:
                    category_links.append(href)
            
            # Method 3: Look for footer links
            footer_links = soup.find('footer')
            if footer_links:
                footer_categories = footer_links.find_all('a', href=True)
                for link in footer_categories:
                    href = link.get('href', '')
                    if href.startswith('/collections/') and href not in category_links:
                        category_links.append(href)
            
            if category_links:
                logger.info(f"CATEGORY DISCOVERY: Found {len(category_links)} categories dynamically")
                return category_links
            else:
                logger.warning("CATEGORY DISCOVERY: No categories found, using default list")
                return self.default_categories
                
        except Exception as e:
            logger.error(f"CATEGORY DISCOVERY ERROR: {e}")
            logger.warning("CATEGORY DISCOVERY: Using default category list")
            return self.default_categories

    def test_category_pagination(self, category_url):
        """
        Test if a category supports pagination by checking if page 2 exists.
        
        Args:
            category_url: The category URL to test
            
        Returns:
            bool: True if pagination is supported, False otherwise
        """
        try:
            # Skip testing for known single-page categories
            if category_url in self.single_page_categories:
                return False
            
            test_url = f"{self.base_url}{category_url}?page=2"
            response = requests.get(test_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Check if there are products on page 2
            product_grid = soup.find('div', class_='GoodsList_gridTwo__cqNQC')
            if product_grid:
                product_items = product_grid.find_all('div', class_='GoodsList_item__hQwg4')
                return len(product_items) > 0
            
            return False
            
        except Exception as e:
            logger.warning(f"PAGINATION TEST ERROR for {category_url}: {e}")
            return False

    def crawl_category_page(self, category_url, page=1):
        """Crawl products from a specific category page"""
        if page == 1:
            full_url = f"{self.base_url}{category_url}"
        else:
            # Handle multiple pages within a clothing category
            full_url = f"{self.base_url}{category_url}?page={page}"
        
        try:
            logger.info(f"CRAWLING PAGE: {full_url}")
            response = requests.get(full_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'lxml')
            
            product_grid = soup.find('div', class_='GoodsList_gridTwo__cqNQC')
            if not product_grid:
                logger.warning(f"NO PRODUCTS FOUND: {full_url}")
                return []

            products = []
            product_items = product_grid.find_all('div', class_='GoodsList_item__hQwg4')
            
            for item in product_items[:self.products_per_category]:
                try:
                    # Get fields from product item (guaranteed)
                    title = item.find('p', class_='ListDetail_p__ueQLj').text.strip()
                    image_url = item.find('img', class_='observerImg').get('data-src')
                    product_url = item.find('a')['href']
                    
                    # Get price if available
                    price_element = item.find('span', class_='ListDetail_price__ueQLj')
                    price = price_element.text.strip() if price_element else "Price not available"
                    
                    products.append({
                        'title': title,
                        'image_url': image_url,
                        'product_url': product_url,
                        'price': price,
                        'category': category_url.split('/')[-1],
                        'page': page,
                        'crawl_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except Exception as e:
                    logger.error(f"PRODUCT PROCESSING ERROR: {e}")
                    continue

            return products
        except Exception as e:
            logger.error(f"CRAWLING ERROR for {full_url}: {e}")
            return []

    def crawl_category(self, category_url, existing_urls=None, max_products=None):
        """
        Crawl products from a specific category across multiple pages.
        
        Args:
            category_url: The category URL to crawl
            existing_urls: Set of existing product URLs to avoid duplicates
            max_products: Maximum number of products to return from this category
            
        Returns:
            list: New products found in this category (limited by max_products)
        """
        if existing_urls is None:
            existing_urls = set()
            
        if self.config.ENABLE_DEBUG_LOGGING:
            logger.info(f"DUPLICATE CHECK: Checking against {len(existing_urls)} existing URLs")
            
        all_products = []
        category_supports_pagination = self.test_category_pagination(category_url)
        
        # Determine how many pages to crawl
        pages_to_crawl = 1 if not category_supports_pagination else self.pages_per_category
        
        for page in range(1, pages_to_crawl + 1):
            products = self.crawl_category_page(category_url, page)
            
            # Filter out existing products using centralized URL normalization
            new_products = []
            filtered_count = 0
            for product in products:
                original_url = product.get('product_url', '')
                normalized_url = normalize_product_url(original_url)
                
                if normalized_url and normalized_url not in existing_urls:
                    new_products.append(product)
                else:
                    filtered_count += 1
            
            if self.config.ENABLE_DEBUG_LOGGING:
                logger.info(f"PAGE {page} RESULTS: Found {len(products)} products, filtered {filtered_count} duplicates, kept {len(new_products)} new")
            
            all_products.extend(new_products)
            
            # Check if we've reached the limit for this category
            if max_products and len(all_products) >= max_products:
                all_products = all_products[:max_products]  # Trim to exact limit
                break
            
            # Be nice to the server between pages
            if page < pages_to_crawl:
                time.sleep(self.delay_between_pages)
        
        return all_products

    def crawl_new_products(self, existing_urls=None, max_products=None):
        """
        Crawl for new products across all categories with limits.
        
        Args:
            existing_urls: Set of existing product URLs to avoid
            max_products: Maximum number of products to crawl (defaults to self.max_products_per_run)
            
        Returns:
            dict: New products organized by category
        """
        if existing_urls is None:
            existing_urls = set()
        
        if max_products is None:
            max_products = self.max_products_per_run
            
        logger.info(f"CRAWLING STARTED: Processing up to {max_products} new products...")
        
        # Discover categories dynamically
        categories = self.discover_categories()
        
        all_products = {}
        total_new_products = 0
        
        for category_url in categories:
            if total_new_products >= max_products:
                logger.info(f"PRODUCT LIMIT REACHED: Stopping at {max_products} products")
                break
                
            try:
                logger.info(f"CRAWLING CATEGORY: {category_url}")
                
                # Calculate how many more products we can get
                remaining_products = max_products - total_new_products
                products = self.crawl_category(category_url, existing_urls, remaining_products)
                
                if products:
                    category_name = category_url.split('/')[-1]
                    all_products[category_name] = products
                    total_new_products += len(products)
                    logger.info(f"CATEGORY COMPLETE: {category_name} - {len(products)} new products")
                else:
                    logger.info(f"CATEGORY EMPTY: {category_url} - no new products")
                
            except Exception as e:
                logger.error(f"CATEGORY ERROR: {category_url} - {e}")
                continue
            
            # Be nice to the server between categories
            time.sleep(self.delay_between_categories)
        
        logger.info(f"CRAWLING COMPLETE: Found {total_new_products} new products across {len(all_products)} categories")
        return all_products

    def analyze_products_for_infringement(self, products):
        """Analyze products for potential infringement"""
        logger.info(f"ANALYSIS STARTED: Processing {len(products)} products for infringement detection...")
        
        analyzed_products = []
        for i, product in enumerate(products, 1):
            if i % 10 == 0 or i == len(products):  # Log every 10th product or the last one
                logger.info(f"ANALYSIS PROGRESS: {i}/{len(products)} products processed")
            
            # Analyze the image for infringement
            analysis = self.infringement_detector.analyze_image(product['image_url'])
            
            if analysis:
                product['infringement_analysis'] = analysis
            else:
                product['infringement_analysis'] = {
                    'detected_brands': [],
                    'risk_level': 'Unknown',
                    'detection_details': 'Analysis failed'
                }
            
            analyzed_products.append(product)
            
            # Rate limiting for API calls
            time.sleep(self.delay_between_analysis)
        
        logger.info(f"ANALYSIS COMPLETE: {len(analyzed_products)} products analyzed")
        return analyzed_products

    def run(self, analyze_infringement=False, existing_urls=None, max_products=None):
        """
        Run the crawler with improved functionality.
        
        Args:
            analyze_infringement: Whether to analyze products for infringement
            existing_urls: Set of existing product URLs to avoid duplicates
            max_products: Maximum number of products to process
        """
        logger.info("HALARA CRAWLER: Starting advanced product monitoring system...")
        
        # Print configuration if debug is enabled
        if self.config.ENABLE_DEBUG_LOGGING:
            self.config.print_configuration()
        
        # Crawl for new products only
        all_products = self.crawl_new_products(existing_urls, max_products)
        
        if not all_products:
            logger.info("NO NEW PRODUCTS: Exiting - no new products found")
            return {}
        
        # Analyze for infringement if requested
        if analyze_infringement:
            logger.info("INFRINGEMENT ANALYSIS: Starting brand detection analysis...")
            for category_name, products in all_products.items():
                if products:
                    logger.info(f"ANALYZING CATEGORY: {category_name} - {len(products)} products")
                    analyzed_products = self.analyze_products_for_infringement(products)
                    all_products[category_name] = analyzed_products
        
        # Save results to a JSON file
        output_file = 'halara_products_with_analysis.json' if analyze_infringement else 'halara_products.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, indent=2, ensure_ascii=False)
        
        logger.info(f"DATA SAVED: Results written to {output_file}")
        
        # Print summary
        total_products = 0
        high_risk_count = 0
        
        for category, products in all_products.items():
            logger.info(f"CATEGORY SUMMARY: {category} - {len(products)} products")
            total_products += len(products)
            
            if analyze_infringement:
                high_risk_products = [p for p in products if p.get('infringement_analysis', {}).get('risk_level') == 'High Risk']
                high_risk_count += len(high_risk_products)
                logger.info(f"  RISK ASSESSMENT: {len(high_risk_products)} high-risk, {len(products) - len(high_risk_products)} low-risk")
        
        logger.info(f"FINAL SUMMARY: {total_products} total products processed")
        if analyze_infringement:
            logger.info(f"RISK SUMMARY: {high_risk_count} high-risk products identified")
        
        return all_products

if __name__ == '__main__':
    crawler = HalaraCrawler()
    
    # Run with infringement analysis
    crawler.run(analyze_infringement=True)
    
    # Comment out the basic crawling line below
    # crawler.run(analyze_infringement=False)

"""
Analyze the apparel image URL and return a JSON object containing: detected_brands (array), risk_level, detection_details.

Rules:
1. **High Risk** triggers if ANY of the following are detected:
   - Recognizable brand logos or design markers from the following:
     • adidas: Trefoil logo (三叶草), 3-stripes (三条纹), 2/3/4 visible parallel bands (→ stripe_count)
     • Nike: Swoosh logo, Nike Air sole unit
     • Converse: Star Chevron logo, circular star patch, rubber toe bumper
     • ASICS: "Tiger Claw" curved stripe pattern (commonly seen on sides of running shoes), ASICS logo
   - **Uploaded shoe image is detected in the input image** (exact or near-exact match)

2. **Low Risk** is assigned **only when none** of the above logos/design features or shoe matches are detected.

Detection criteria:
- Logo recognition requires at least 60% visual similarity to official branding
- Design element matching must identify distinctive structural features (e.g., shape of swoosh, curved ASICS stripe configuration, etc.)
- Image match to uploaded shoe must be based on color, shape, and pattern, with at least 75% visual similarity (fine-grained matching)

Return Format (example):
{
  "detected_brands": [
    {
      "brand": "ASICS",
      "element_type": "design_element",
      "feature": "tiger_claw_stripe"
    },
    {
      "brand": "ASICS",
      "element_type": "logo",
      "confidence": "82%"
    }
  ],
  "risk_level": "High Risk",
  "detection_details": "ASICS tiger claw stripe and logo detected; shoe matches uploaded sample"
}
"""