"""
NOTE: This file has been sanitized for portfolio display.
Replace placeholder values with actual credentials for production use.
"""

#!/usr/bin/env python3

import os
import json
import time
import requests
import math
import re
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from .crawler_config import normalize_product_url

# Load environment variables
load_dotenv()

class LarkSpreadsheetWriter:
    def __init__(self):
        # Get sheet token and app credentials from .env
        self.sheet_token = os.getenv("LARK_SHEET_TOKEN")
        self.app_id = os.getenv("LARK_APP_ID")
        self.app_secret = os.getenv("LARK_APP_SECRET")
        
        if not self.sheet_token or not self.app_id or not self.app_secret:
            raise ValueError("LARK_SHEET_TOKEN, LARK_APP_ID, and LARK_APP_SECRET must be set in your .env file.")
        
        # Get app access token
        self.app_access_token = self.get_app_access_token()
        if not self.app_access_token:
            raise ValueError("Failed to get app access token. Check your LARK_APP_ID and LARK_APP_SECRET.")
        
        # Define headers for API calls
        self.headers = {
            "Authorization": f"Bearer {self.app_access_token}",
            "Content-Type": "application/json"
        }
        
        # Define column headers (updated for new structure)
        self.headers_list = [
            'Product Title',
            'Category', 
            'Image URL',
            'Image',
            'Product URL',
            'Risk Level',
            'Detected Brands',
            'Detection Details',
            'Analysis Timestamp'
        ]
        
        # Current sheet ID (can be updated for new sheets)
        self.current_sheet_id = "f611fa"

    def get_app_access_token(self):
        """Get app access token using app_id and app_secret"""
        url = "https://your-feishu-instance.com"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("app_access_token")
        else:
            print(f"ERROR: Failed to get app access token: {resp.text}")
            return None

    def create_new_sheet(self, sheet_name: str) -> Optional[str]:
        """
        Create a new sheet in the spreadsheet.
        
        Args:
            sheet_name: Name for the new sheet
            
        Returns:
            str: New sheet ID if successful, None otherwise
        """
        try:
            url = f'https://your-feishu-instance.com'
            
            payload = {
                "requests": [
                    {
                        "addSheet": {
                            "properties": {
                                "title": sheet_name,
                                "index": 0  # Add as first sheet
                            }
                        }
                    }
                ]
            }
            
            resp = requests.post(url, headers=self.headers, json=payload)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    new_sheet_id = data['data']['replies'][0]['addSheet']['properties']['sheetId']
                    print(f"SHEET CREATED: {sheet_name} (ID: {new_sheet_id})")
                    return new_sheet_id
                else:
                    print(f"SHEET CREATION FAILED: {data.get('msg', 'Unknown error')}")
                    return None
            else:
                print(f"SHEET CREATION HTTP ERROR: {resp.status_code}")
                return None
                
        except Exception as e:
            print(f"SHEET CREATION ERROR: {str(e)}")
            return None

    def read_existing_data(self, sheet_id: str = None) -> Dict:
        """
        Read existing data from a sheet to avoid duplicates.
        
        Args:
            sheet_id: Sheet ID to read from (defaults to current sheet)
            
        Returns:
            Dict: Existing products data
        """
        if sheet_id is None:
            sheet_id = self.current_sheet_id
            
        try:
            url = f'https://your-feishu-instance.com'
            
            resp = requests.get(url, headers=self.headers)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    values = data['data']['valueRange']['values']
                    
                    if len(values) <= 1:  # Only headers or empty
                        print("SHEET DATA: No existing data found in sheet")
                        return {}
                    
                    # Parse existing data
                    existing_products = {}
                    for row in values[1:]:  # Skip header row
                        if len(row) >= 5:  # Ensure we have enough columns
                            product_url = row[4] if len(row) > 4 else ''  # Column E
                            
                            # Use centralized URL normalization
                            normalized_url = normalize_product_url(product_url)
                            if normalized_url:
                                category = row[1] if len(row) > 1 else 'Unknown'
                                # Handle category data type
                                if isinstance(category, list):
                                    category = category[0] if category else 'Unknown'
                                elif not isinstance(category, str):
                                    category = str(category) if category else 'Unknown'
                                
                                if category not in existing_products:
                                    existing_products[category] = []
                                
                                # Handle title and image_url data types
                                title = row[0] if len(row) > 0 else ''
                                if isinstance(title, list):
                                    title = title[0] if title else ''
                                elif not isinstance(title, str):
                                    title = str(title) if title else ''
                                
                                image_url = row[2] if len(row) > 2 else ''
                                if isinstance(image_url, list):
                                    image_url = image_url[0] if image_url else ''
                                elif not isinstance(image_url, str):
                                    image_url = str(image_url) if image_url else ''
                                
                                existing_products[category].append({
                                    'product_url': normalized_url,  # Store normalized URL
                                    'title': title,
                                    'image_url': image_url
                                })
                    
                    print(f"SHEET DATA LOADED: {sum(len(products) for products in existing_products.values())} existing products")
                    return existing_products
                else:
                    print(f"SHEET READ ERROR: {data.get('msg', 'Unknown error')}")
                    return {}
            else:
                print(f"SHEET READ HTTP ERROR: {resp.status_code}")
                return {}
                
        except Exception as e:
            print(f"SHEET READ ERROR: {str(e)}")
            return {}

    def write_to_sheet(self, loc, values, retry_max=3):
        """Write data to sheet using official Feishu API"""
        url = f'https://your-feishu-instance.com'
        
        # Auto-batch insertion, max 4k rows per batch
        max_row = 4020
        loop = math.ceil(len(values) / max_row)
        begin_row = int(re.sub(r'^[a-zA-Z]*|[a-zA-Z]*$', '', loc.split('!')[-1].split(':')[0]))
        
        for i in range(loop):
            each_values = values[i*max_row:(i+1)*max_row]
            each_loc = loc.replace('{}:'.format(begin_row), '{}:'.format(begin_row+i*max_row))
            data = {"valueRange": {"range": each_loc, "values": each_values}}
            
            retry, ok = 0, False
            while retry < retry_max:
                retry += 1
                resp = requests.put(url, headers=self.headers, data=json.dumps(data))
                print(f'SHEET WRITE: Batch {i+1}/{loop}, Response: {resp.text}')
                
                if resp.ok and resp.json()['code'] == 0:
                    ok = True
                    break
                else:
                    # Refresh token if needed
                    if resp.json().get('code') == 99991663:  # Token expired
                        self.app_access_token = self.get_app_access_token()
                        self.headers["Authorization"] = f"Bearer {self.app_access_token}"
            
            if not ok:
                msg = f'[sheet_token] {self.sheet_token}\n[loc] {loc}\n[values] {values}'
                print(f'SHEET WRITE FAILED: {msg}')
                return False
        
        return True

    def write_image_to_sheet(self, loc, image_url, retry_max=3):
        """Write image to sheet cell using team lead's approach"""
        retry = 0
        while retry < retry_max:
            retry += 1
            try:
                if not image_url or image_url == '':
                    print(f"IMAGE SKIP: Empty image URL for {loc}")
                    return None
                
                # Handle image_url that might be a dictionary (from Lark's data format)
                if isinstance(image_url, dict):
                    # Extract URL from dictionary format
                    if 'link' in image_url:
                        image_url = image_url['link']
                    elif 'text' in image_url:
                        image_url = image_url['text']
                    else:
                        print(f"IMAGE SKIP: Invalid image URL format for {loc}: {image_url}")
                        return None
                
                # Ensure image_url is a string
                if not isinstance(image_url, str):
                    print(f"IMAGE SKIP: Non-string image URL for {loc}: {image_url}")
                    return None
                
                url = f'https://your-feishu-instance.com'
                name = str(image_url).split('/')[-1].split('?')[0]
                if '.' not in name:
                    name += '.jpeg'
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
                }
                
                print(f'IMAGE DOWNLOAD: {image_url}')
                img_resp = requests.get(image_url, headers=headers, timeout=30)
                
                img_bytes = None
                if img_resp.ok and img_resp.content is not None:
                    img_bytes = bytearray(img_resp.content)
                    print(f'IMAGE DOWNLOADED: {len(img_bytes)} bytes')
                else:
                    print(f'IMAGE DOWNLOAD FAILED: {img_resp.status_code}')
                    continue
                
                img_array = []
                if img_bytes is not None:
                    for each in img_bytes:
                        img_array.append(each)
                
                data = {'range': loc, 'image': img_array, 'name': name}
                print(f'IMAGE UPLOAD: Uploading to {loc}...')
                resp = requests.post(url, headers=self.headers, data=json.dumps(data))
                print(f'IMAGE UPLOAD RESPONSE: {resp.text}')
                
                if resp.ok and resp.json()['code'] == 0:
                    print(f'IMAGE UPLOAD SUCCESS: {loc}')
                    return json.loads(resp.text)
                else:
                    print(f'IMAGE UPLOAD FAILED: {resp.text}')
                    
            except Exception as e:
                print(f'IMAGE UPLOAD ERROR for {loc}: {e}')
            
            # Refresh token if needed
            if retry < retry_max:
                print(f'IMAGE UPLOAD RETRY: {retry}/{retry_max}')
                self.app_access_token = self.get_app_access_token()
                self.headers["Authorization"] = f"Bearer {self.app_access_token}"
        
        print(f'IMAGE UPLOAD FAILED: {retry_max} retries exhausted')
        return None

    def build_data_matrix(self, products_data: Dict) -> list:
        """Build a 2D array: first row is headers, rest is data"""
        rows = [self.headers_list]
        for category_name, products in products_data.items():
            for product in products:
                analysis = product.get('infringement_analysis', {})
                detected_brands = analysis.get('detected_brands', [])
                brands_text = ""
                if detected_brands:
                    brand_list = []
                    for brand in detected_brands:
                        brand_info = f"{brand.get('brand', 'Unknown')} ({brand.get('element_type', 'Unknown')})"
                        if 'confidence' in brand:
                            brand_info += f" - {brand['confidence']}"
                        brand_list.append(brand_info)
                    brands_text = "; ".join(brand_list)
                
                # Updated row structure with empty cell for image
                row = [
                    product.get('title', ''),
                    category_name,
                    product.get('image_url', ''),
                    '',  # Empty cell for image (column D)
                    f"https://thehalara.com{product.get('product_url', '')}",
                    analysis.get('risk_level', 'Unknown'),
                    brands_text,
                    analysis.get('detection_details', ''),
                    time.strftime('%Y-%m-%d %H:%M:%S')
                ]
                rows.append(row)
        return rows

    def write_products(self, products_data: Dict, include_images=False, create_new_sheet=False, sheet_name=None, target_sheet_name=None):
        """
        Write products data to sheet with optional image uploads.
        
        Args:
            products_data: Products data to write
            include_images: Whether to upload images
            create_new_sheet: Whether to create a new sheet for this run
            sheet_name: Name for new sheet (if creating new sheet)
            target_sheet_name: Name of existing sheet to write to (if not creating new)
        """
        # Determine which sheet to use
        if create_new_sheet:
            if sheet_name is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                sheet_name = f"Halara_Analysis_{timestamp}"
            
            # Create new sheet
            new_sheet_id = self.create_new_sheet(sheet_name)
            if new_sheet_id:
                self.current_sheet_id = new_sheet_id
                print(f"WRITING TO NEW SHEET: {sheet_name}")
            else:
                print("SHEET CREATION FAILED: Using existing sheet")
        elif target_sheet_name:
            # Use specific existing sheet
            sheet_id = self.get_or_create_sheet(target_sheet_name)
            self.current_sheet_id = sheet_id
            print(f"WRITING TO EXISTING SHEET: {target_sheet_name}")
        else:
            # Use default sheet (first sheet or create one)
            sheets = self.list_sheets()
            if sheets:
                # Use the first sheet as default
                self.current_sheet_id = sheets[0]['properties']['sheetId']
                default_name = sheets[0]['properties']['title']
                print(f"WRITING TO DEFAULT SHEET: {default_name}")
            else:
                # Create a default sheet if none exist
                default_sheet_id = self.create_new_sheet("Halara_Default")
                if default_sheet_id:
                    self.current_sheet_id = default_sheet_id
                    print("WRITING TO NEW DEFAULT SHEET")
        
        print(f"WRITING DATA: Feishu sheet ID {self.current_sheet_id}")
        
        # Check if we should append to existing data or write fresh
        if not create_new_sheet:
            # Read existing data to avoid duplicates
            existing_data = self.read_existing_data(self.current_sheet_id)
            if existing_data:
                print(f"EXISTING DATA FOUND: {sum(len(products) for products in existing_data.values())} products")
                
                # Filter out products that already exist
                filtered_products = self.filter_existing_products(products_data, existing_data)
                
                if not filtered_products:
                    print("DUPLICATE FILTER: All products already exist, nothing to add")
                    return
                
                # Append only new products
                self.append_new_products(filtered_products, include_images)
                return
        
        # Write main data (updated range for 9 columns A-I)
        data_matrix = self.build_data_matrix(products_data)
        success = self.write_to_sheet(f"{self.current_sheet_id}!A1:I", data_matrix)
        
        if success:
            print(f"DATA WRITE SUCCESS: Feishu sheet updated")
            print(f"SHEET URL: https://your-feishu-instance.com")
            
            # Optionally upload images
            if include_images:
                print("IMAGE UPLOAD: Starting product image uploads...")
                self.upload_product_images(products_data)
        else:
            print("DATA WRITE FAILED: Could not write to sheet")

    def write_products_with_existing_data(self, products_data: Dict, existing_data: Dict, include_images=False, create_new_sheet=False, sheet_name=None, target_sheet_name=None):
        """
        Write products data to sheet with optional image uploads, using provided existing data.
        
        Args:
            products_data: Products data to write
            existing_data: Existing products data (to avoid duplicate reads)
            include_images: Whether to upload images
            create_new_sheet: Whether to create a new sheet for this run
            sheet_name: Name for new sheet (if creating new sheet)
            target_sheet_name: Name of existing sheet to write to (if not creating new)
        """
        # Determine which sheet to use
        if create_new_sheet:
            if sheet_name is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                sheet_name = f"Halara_Analysis_{timestamp}"
            
            # Create new sheet
            new_sheet_id = self.create_new_sheet(sheet_name)
            if new_sheet_id:
                self.current_sheet_id = new_sheet_id
                print(f"WRITING TO NEW SHEET: {sheet_name}")
            else:
                print("SHEET CREATION FAILED: Using existing sheet")
        elif target_sheet_name:
            # Use specific existing sheet
            sheet_id = self.get_or_create_sheet(target_sheet_name)
            self.current_sheet_id = sheet_id
            print(f"WRITING TO EXISTING SHEET: {target_sheet_name}")
        else:
            # Use default sheet (first sheet or create one)
            sheets = self.list_sheets()
            if sheets:
                # Use the first sheet as default
                self.current_sheet_id = sheets[0]['properties']['sheetId']
                default_name = sheets[0]['properties']['title']
                print(f"WRITING TO DEFAULT SHEET: {default_name}")
            else:
                # Create a default sheet if none exist
                default_sheet_id = self.create_new_sheet("Halara_Default")
                if default_sheet_id:
                    self.current_sheet_id = default_sheet_id
                    print("WRITING TO NEW DEFAULT SHEET")
        
        print(f"WRITING DATA: Feishu sheet ID {self.current_sheet_id}")
        
        # Check if we should append to existing data or write fresh
        if not create_new_sheet and existing_data:
            print(f"USING EXISTING DATA: {sum(len(products) for products in existing_data.values())} products")
            
            # Filter out products that already exist
            filtered_products = self.filter_existing_products(products_data, existing_data)
            
            if not filtered_products:
                print("DUPLICATE FILTER: All products already exist, nothing to add")
                return
            
            # Append only new products
            self.append_new_products(filtered_products, include_images)
            return
        
        # Write main data (updated range for 9 columns A-I)
        data_matrix = self.build_data_matrix(products_data)
        success = self.write_to_sheet(f"{self.current_sheet_id}!A1:I", data_matrix)
        
        if success:
            print(f"DATA WRITE SUCCESS: Feishu sheet updated")
            print(f"SHEET URL: https://your-feishu-instance.com")
            
            # Optionally upload images
            if include_images:
                print("IMAGE UPLOAD: Starting product image uploads...")
                self.upload_product_images(products_data)
        else:
            print("DATA WRITE FAILED: Could not write to sheet")

    def filter_existing_products(self, new_products: Dict, existing_data: Dict) -> Dict:
        """
        Filter out products that already exist in the sheet.
        Args:
            new_products: New products to check
            existing_data: Existing products in the sheet
        Returns:
            Dict: Only products that don't already exist
        """
        existing_urls = set()
        for category, products in existing_data.items():
            for product in products:
                product_url = normalize_product_url(product.get('product_url', ''))
                if product_url:
                    existing_urls.add(product_url)

        filtered_products = {}
        total_filtered = 0
        for category, products in new_products.items():
            filtered_category_products = []
            for product in products:
                product_url = normalize_product_url(product.get('product_url', ''))
                if product_url and product_url not in existing_urls:
                    filtered_category_products.append(product)
                    total_filtered += 1
            if filtered_category_products:
                filtered_products[category] = filtered_category_products
        print(f"DUPLICATE FILTER: {total_filtered} new products (removed {sum(len(products) for products in new_products.values()) - total_filtered} duplicates)")
        return filtered_products

    def append_new_products(self, new_products: Dict, include_images=False):
        """
        Append new products to the existing sheet.
        
        Args:
            new_products: New products to append
            include_images: Whether to upload images
        """
        try:
            # Get current row count to know where to append
            current_data = self.read_existing_data(self.current_sheet_id)
            if current_data:
                # Count existing rows (including header)
                existing_row_count = 1  # Start with header row
                for category, products in current_data.items():
                    existing_row_count += len(products)
                
                print(f"APPENDING DATA: Starting from row {existing_row_count + 1}")
                
                # Build data matrix for new products only
                data_matrix = self.build_data_matrix(new_products)
                
                # Remove header row since we're appending
                if data_matrix and len(data_matrix) > 1:
                    data_matrix = data_matrix[1:]  # Remove header
                    
                    # Append data starting from the next row
                    success = self.write_to_sheet(f"{self.current_sheet_id}!A{existing_row_count + 1}:I", data_matrix)
                    
                    if success:
                        print(f"DATA APPEND SUCCESS: {len(data_matrix)} new product rows added")
                        
                        # Upload images for new products if requested
                        if include_images:
                            print("IMAGE UPLOAD: Starting uploads for new products...")
                            self.upload_product_images_from_row(new_products, existing_row_count + 1)
                    else:
                        print("DATA APPEND FAILED: Could not append to sheet")
                else:
                    print("NO NEW PRODUCTS: Nothing to append")
            else:
                print("NO EXISTING DATA: Writing fresh data")
                # Fallback to writing fresh data
                data_matrix = self.build_data_matrix(new_products)
                success = self.write_to_sheet(f"{self.current_sheet_id}!A1:I", data_matrix)
                
                if success:
                    print(f"FRESH DATA WRITE: {len(data_matrix) - 1} product rows written")
                    
                    if include_images:
                        print("IMAGE UPLOAD: Starting uploads...")
                        self.upload_product_images(new_products)
                else:
                    print("FRESH DATA WRITE FAILED: Could not write to sheet")
                    
        except Exception as e:
            print(f"APPEND ERROR: {str(e)}")
            raise

    def upload_product_images_from_row(self, products_data: Dict, start_row: int):
        """
        Upload product images starting from a specific row.
        
        Args:
            products_data: Products data to upload images for
            start_row: Starting row number for image uploads
        """
        row = start_row
        total_products = sum(len(products) for products in products_data.values())
        uploaded_count = 0
        
        print(f"IMAGE UPLOAD: {total_products} new products from row {start_row}")
        
        for category_name, products in products_data.items():
            for product in products:
                image_url = product.get('image_url', '')
                if image_url:
                    if uploaded_count % 10 == 0 or uploaded_count == total_products - 1:  # Log every 10th or last
                        print(f"IMAGE UPLOAD PROGRESS: {uploaded_count + 1}/{total_products} (row {row})")
                    result = self.write_image_to_sheet(f"{self.current_sheet_id}!D{row}:D{row}", image_url)
                    if result:
                        uploaded_count += 1
                else:
                    print(f"IMAGE SKIP: No image URL for row {row}")
                row += 1
        
        print(f"IMAGE UPLOAD COMPLETE: {uploaded_count}/{total_products} images uploaded")

    def upload_product_images(self, products_data: Dict):
        """Upload product images to sheet column D"""
        row = 2  # Start from row 2 (after headers)
        total_products = sum(len(products) for products in products_data.values())
        uploaded_count = 0
        
        print(f"IMAGE UPLOAD: {total_products} products")
        
        for category_name, products in products_data.items():
            for product in products:
                image_url = product.get('image_url', '')
                if image_url:
                    if uploaded_count % 10 == 0 or uploaded_count == total_products - 1:  # Log every 10th or last
                        print(f"IMAGE UPLOAD PROGRESS: {uploaded_count + 1}/{total_products} (row {row})")
                    result = self.write_image_to_sheet(f"{self.current_sheet_id}!D{row}:D{row}", image_url)
                    if result:
                        uploaded_count += 1
                else:
                    print(f"IMAGE SKIP: No image URL for row {row}")
                row += 1
        
        print(f"IMAGE UPLOAD COMPLETE: {uploaded_count}/{total_products} images uploaded")

    def test_connection(self) -> bool:
        """Test the connection to Feishu API"""
        try:
            print("CONNECTION TEST: Testing Feishu API connection...")
            print(f"CONNECTION INFO: Sheet Token: {self.sheet_token}")
            print(f"CONNECTION INFO: App ID: {self.app_id}")
            
            if not self.app_access_token:
                print("CONNECTION ERROR: No app access token available")
                return False
            
            # Try to get sheet metadata
            url = f'https://your-feishu-instance.com'
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    print("CONNECTION SUCCESS: Feishu API connected")
                    return True
                else:
                    print(f"CONNECTION ERROR: API Error - {data.get('msg', 'Unknown error')}")
                    return False
            else:
                print(f"CONNECTION ERROR: HTTP Error {response.status_code}")
                print(f"CONNECTION ERROR: Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"CONNECTION ERROR: {e}")
            return False

    def list_sheets(self) -> List[Dict]:
        """
        List all sheets in the spreadsheet.
        
        Returns:
            List[Dict]: List of sheet information with id, title, etc.
        """
        try:
            url = f'https://your-feishu-instance.com'
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    sheets = data['data']['sheets']
                    print(f"SHEET LIST: Found {len(sheets)} sheets in spreadsheet")
                    
                    # Debug: Print the structure of first sheet
                    if sheets:
                        print(f"SHEET STRUCTURE: {list(sheets[0].keys())}")
                    
                    for sheet in sheets:
                        # Handle different possible structures
                        if 'properties' in sheet:
                            title = sheet['properties'].get('title', 'Unknown')
                            sheet_id = sheet['properties'].get('sheetId', 'Unknown')
                        elif 'title' in sheet:
                            title = sheet.get('title', 'Unknown')
                            sheet_id = sheet.get('sheetId', 'Unknown')
                        else:
                            # Fallback: try to extract from any available fields
                            title = str(sheet.get('title', sheet.get('name', 'Unknown')))
                            sheet_id = str(sheet.get('sheetId', sheet.get('id', 'Unknown')))
                        
                        print(f"SHEET: {title} (ID: {sheet_id})")
                    
                    return sheets
                else:
                    print(f"SHEET LIST ERROR: {data.get('msg', 'Unknown error')}")
                    print(f"SHEET LIST DEBUG: {data}")
                    return []
            else:
                print(f"SHEET LIST HTTP ERROR: {response.status_code}")
                print(f"SHEET LIST DEBUG: {response.text}")
                return []
                
        except Exception as e:
            print(f"SHEET LIST ERROR: {str(e)}")
            print(f"SHEET LIST DEBUG: {e}")
            return []

    def find_sheet_by_name(self, sheet_name: str) -> Optional[str]:
        """
        Find a sheet by name and return its ID.
        
        Args:
            sheet_name: Name of the sheet to find
            
        Returns:
            str: Sheet ID if found, None otherwise
        """
        sheets = self.list_sheets()
        for sheet in sheets:
            # Handle different possible structures
            if 'properties' in sheet:
                title = sheet['properties'].get('title', '')
                sheet_id = sheet['properties'].get('sheetId', '')
            elif 'title' in sheet:
                title = sheet.get('title', '')
                sheet_id = sheet.get('sheetId', '')
            else:
                # Fallback: try to extract from any available fields
                title = str(sheet.get('title', sheet.get('name', '')))
                sheet_id = str(sheet.get('sheetId', sheet.get('id', '')))
            
            # Case-insensitive comparison
            if title.lower() == sheet_name.lower():
                print(f"SHEET FOUND: '{title}' matches '{sheet_name}' (ID: {sheet_id})")
                return sheet_id
        
        print(f"SHEET NOT FOUND: '{sheet_name}'")
        return None

    def get_or_create_sheet(self, sheet_name: str) -> str:
        """
        Get existing sheet or create new one if it doesn't exist.
        
        Args:
            sheet_name: Name of the sheet
            
        Returns:
            str: Sheet ID
        """
        # Try to find existing sheet
        existing_sheet_id = self.find_sheet_by_name(sheet_name)
        if existing_sheet_id:
            self.current_sheet_id = existing_sheet_id
            return existing_sheet_id
        
        # Create new sheet if not found
        print(f"SHEET CREATION: Creating new sheet '{sheet_name}'")
        new_sheet_id = self.create_new_sheet(sheet_name)
        if new_sheet_id:
            self.current_sheet_id = new_sheet_id
            return new_sheet_id
        else:
            # Fallback to default sheet
            print("SHEET CREATION FAILED: Using default sheet")
            return self.current_sheet_id

    def read_existing_data_from_main(self) -> Dict:
        """
        Read existing data from the 'Halara_Main' sheet only. Error if not found.
        Returns:
            Dict: Existing products data
        """
        sheet_id = self.find_sheet_by_name('Halara_Main')
        if not sheet_id:
            raise Exception("Halara_Main sheet not found. Please create it and add your master data.")
        return self.read_existing_data(sheet_id)

    def write_products_to_new_sheet(self, products_data: Dict, include_images=False):
        """
        Write products data to a new timestamped sheet.
        Args:
            products_data: Products data to write
            include_images: Whether to upload images
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        sheet_name = f"Halara_Analysis_{timestamp}"
        self.write_products(products_data, include_images=include_images, create_new_sheet=True, sheet_name=sheet_name)
        print(f"NEW SHEET CREATED: {sheet_name}")

    def append_to_halara_main(self, products_data: Dict, include_images=False):
        """
        Append new products to Halara_Main sheet (master database).
        Args:
            products_data: Products data to append
            include_images: Whether to upload images
        """
        sheet_id = self.find_sheet_by_name('Halara_Main')
        if not sheet_id:
            raise Exception("Halara_Main sheet not found. Cannot append new products.")
        
        # Set current sheet ID to Halara_Main
        self.current_sheet_id = sheet_id
        
        # Read existing data to avoid duplicates
        existing_data = self.read_existing_data(sheet_id)
        
        # Filter out products that already exist
        filtered_products = self.filter_existing_products(products_data, existing_data)
        
        if filtered_products:
            # Append only new products
            self.append_new_products(filtered_products, include_images=include_images)
            print(f"HALARA_MAIN UPDATE: {sum(len(products) for products in filtered_products.values())} new products appended")
        else:
            print("HALARA_MAIN UPDATE: All products already exist, nothing to append")

if __name__ == '__main__':
    writer = LarkSpreadsheetWriter()
    
    # Test connection first
    if not writer.test_connection():
        print("❌ Cannot proceed without successful connection")
        exit(1)
    
    try:
        with open('halara_products_with_analysis.json', 'r') as f:
            products_data = json.load(f)
        
        # Write data and upload images to a new sheet
        writer.write_products(products_data, include_images=True, create_new_sheet=True)
        
    except FileNotFoundError:
        print("ERROR: halara_products_with_analysis.json not found. Run analysis first!") 