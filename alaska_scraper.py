#!/usr/bin/env python3
"""
Alaska.vn Product Scraper using Firecrawl
Scrapes detailed product data from Alaska.vn and exports to JSON
"""

import json
import re
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
from firecrawl import FirecrawlApp
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
import os


class AlaskaProduct(BaseModel):
    """Comprehensive schema for Alaska product data"""
    name: str = Field(description="Product name/model")
    category: str = Field(description="Product category")
    msp: str = Field(description="Product code/MSP")
    short_description_features: List[str] = Field(
        description="All features from the short description section (Mô tả ngắn)",
        default_factory=list
    )
    prices: Dict[str, str] = Field(
        description="Regional pricing (MIỀN BẮC, MIỀN TRUNG, MIỀN NAM)",
        default_factory=dict
    )
    technical_specs: Dict[str, str] = Field(
        description="Complete technical specifications (THÔNG SỐ KỸ THUẬT)",
        default_factory=dict
    )
    characteristics: List[str] = Field(
        description="Product characteristics (Các Đặc Tính)",
        default_factory=list
    )
    store_locator_link: Optional[str] = Field(
        description="Link to store locator (Tìm điểm bán hàng)",
        default=None
    )
    document_download_link: Optional[str] = Field(
        description="Link to document download (Tải tài liệu)",
        default=None
    )
    images: List[str] = Field(
        description="List of product image URLs",
        default_factory=list
    )
    full_description: str = Field(
        description="Complete product description",
        default=""
    )
    warranty_info: str = Field(
        description="Warranty information",
        default=""
    )
    scraped_at: str = Field(description="Timestamp of scraping")


class AlaskaScraper:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the scraper with Firecrawl API key"""
        # Try to get API key from parameter, environment, or default to None
        if not api_key:
            api_key = os.getenv('FIRECRAWL_API_KEY')
        
        if api_key:
            self.firecrawl = FirecrawlApp(api_key=api_key)
            print("Initialized with Firecrawl API - using extract feature")
        else:
            self.firecrawl = None
            print("Warning: No Firecrawl API key provided. Using fallback scraping method.")
        
        self.base_url = "https://alaska.vn"
        self.products_url = "https://alaska.vn/product/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_page_content(self, url: str) -> Optional[str]:
        """Get page content using Firecrawl or fallback to requests"""
        try:
            if self.firecrawl:
                result = self.firecrawl.scrape_url(url, params={'formats': ['html']})
                return result.get('html', '')
            else:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_product_urls_from_listing(self, page_url: str) -> List[str]:
        """Extract product URLs from a listing page"""
        content = self.get_page_content(page_url)
        if not content:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        product_urls = []
        
        # Find the products container
        products_container = soup.find('div', class_='row products')
        if not products_container:
            return []
        
        # Find all product items within the container
        product_items = products_container.find_all('div', class_='item')
        
        for item in product_items:
            # Look for product links within each item
            product_links = item.find_all('a', href=True)
            
            for link in product_links:
                href = link.get('href')
                if href:
                    # Skip non-product links
                    if any(skip in href for skip in ['/page/', '/category/', '/tag/', 'javascript:', 'mailto:', 'tel:', '#']):
                        continue
                    
                    # Make sure it's a full URL
                    full_url = urljoin(self.base_url, href) if href.startswith('/') else href
                    
                    # Check if it's a product URL (contains specific patterns)
                    if (full_url.startswith(self.base_url) and 
                        full_url != self.base_url + '/' and
                        full_url != page_url and
                        not any(skip in full_url for skip in ['/page/', '/category/', '/tag/'])):
                        
                        if full_url not in product_urls:
                            product_urls.append(full_url)
        
        return product_urls
    
    def get_all_product_urls(self) -> List[str]:
        """Get all product URLs from all listing pages using best available method"""
        all_urls = []
        page = 1
        
        while True:
            if page == 1:
                page_url = self.products_url
            else:
                page_url = f"{self.products_url}page/{page}/"
            
            print(f"Scraping page {page}: {page_url}")
            
            # Try Firecrawl extract first, fallback to manual extraction
            if self.firecrawl:
                urls = self.extract_product_urls_with_firecrawl(page_url)
                if not urls:  # Fallback if Firecrawl fails
                    print("Firecrawl extraction failed, falling back to manual extraction")
                    urls = self.extract_product_urls_from_listing(page_url)
            else:
                urls = self.extract_product_urls_from_listing(page_url)
            
            if not urls:
                print(f"No more products found on page {page}")
                break
                
            all_urls.extend(urls)
            print(f"Found {len(urls)} products on page {page}")
            
            page += 1
            time.sleep(1)  # Be respectful to the server
            
            # Safety limit
            if page > 30:
                print("Reached maximum page limit (30)")
                break
        
        return list(set(all_urls))  # Remove duplicates
    
    def extract_category(self, soup: BeautifulSoup) -> str:
        """Extract product category"""
        category = ""
        
        # Look for breadcrumbs
        breadcrumb_selectors = ['.breadcrumb', '.breadcrumbs', '.woocommerce-breadcrumb', 'nav[aria-label="breadcrumb"]']
        for selector in breadcrumb_selectors:
            breadcrumb = soup.select_one(selector)
            if breadcrumb:
                links = breadcrumb.find_all('a')
                if len(links) > 1:  # Skip "Home" link
                    category = links[-1].get_text(strip=True)
                    break
        
        # Alternative: look for category in title or meta
        if not category:
            title = soup.find('title')
            if title:
                title_text = title.get_text()
                if 'Tủ mát' in title_text:
                    category = 'Tủ mát'
                elif 'Tủ đông' in title_text:
                    category = 'Tủ đông'
        
        return category
    
    def extract_msp(self, soup: BeautifulSoup, product_url: str) -> str:
        """Extract MSP (Model/Product Code)"""
        msp = ""
        
        # Look for MSP in text content
        text_content = soup.get_text()
        msp_match = re.search(r'MSP[:\s]*([A-Z0-9-]+)', text_content, re.IGNORECASE)
        if msp_match:
            msp = msp_match.group(1)
        
        # Fallback: extract from URL
        if not msp:
            url_match = re.search(r'/([a-zA-Z0-9-]+)/$', product_url)
            if url_match:
                slug = url_match.group(1)
                # Extract model code from slug (e.g., "tu-mat-lc-535c" -> "LC-535C")
                model_match = re.search(r'([a-z]{2}-\d+[a-z]?)$', slug, re.IGNORECASE)
                if model_match:
                    msp = model_match.group(1).upper()
        
        return msp
    
    def extract_prices(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract regional prices from product page"""
        prices = {}
        
        # Get all text content and search for price patterns
        text_content = soup.get_text()
        
        # More comprehensive price patterns
        price_patterns = [
            r'(MIỀN\s+\w+)\s*[:\-]\s*([\d,.\s]+)\s*VNĐ',
            r'(Miền\s+\w+)\s*[:\-]\s*([\d,.\s]+)\s*VNĐ',
            r'(MIỀN\s+\w+)\s*[:\-]\s*([\d,.\s]+)\s*vnđ',
            r'(Miền\s+\w+)\s*[:\-]\s*([\d,.\s]+)\s*vnđ',
            r'(MIỀN\s+\w+)\s*[:\-]\s*([\d,.\s]+)\s*đ',
            r'(Miền\s+\w+)\s*[:\-]\s*([\d,.\s]+)\s*đ',
            # Additional patterns without colons
            r'(Miền\s+\w+)\s+([\d,.\s]+)\s*VNĐ',
            r'(MIỀN\s+\w+)\s+([\d,.\s]+)\s*VNĐ',
            # Price table patterns
            r'(Miền\s+\w+).*?([\d,]+,\d+)\s*VNĐ',
            r'(MIỀN\s+\w+).*?([\d,]+,\d+)\s*VNĐ'
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for region, price in matches:
                # Clean the price string
                clean_price = re.sub(r'[,.\s]', '', price)
                if clean_price.isdigit():
                    formatted_price = f"{int(clean_price):,} VNĐ"
                    prices[region.strip()] = formatted_price
        
        return prices
    
    def extract_specifications(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract detailed product specifications"""
        specs = {}
        
        # Get all text and extract key-value pairs
        text_content = soup.get_text()
        
        # Common specification patterns (avoid price-related patterns)
        spec_patterns = [
            # Vietnamese patterns
            r'Kích thước\s*[:\-]?\s*([^\n]+)',
            r'Trọng lượng\s*[:\-]?\s*([^\n]+)',
            r'Dung tích\s*[:\-]?\s*([^\n]+)',
            r'Nhiệt độ\s*[:\-]?\s*([^\n]+)',
            r'Công suất\s*[:\-]?\s*([^\n]+)',
            r'Điện áp\s*[:\-]?\s*([^\n]+)',
            r'Gas\s*[:\-]?\s*([^\n]+)',
            r'Môi chất\s*[:\-]?\s*([^\n]+)',
            r'Tần số\s*[:\-]?\s*([^\n]+)',
            r'Chất làm lạnh\s*[:\-]?\s*([^\n]+)',
            r'Xuất xứ\s*[:\-]?\s*([^\n]+)',
            r'Bảo hành\s*[:\-]?\s*([^\n]+)',
            # English patterns
            r'Dimensions?\s*[:\-]?\s*([^\n]+)',
            r'Weight\s*[:\-]?\s*([^\n]+)',
            r'Capacity\s*[:\-]?\s*([^\n]+)',
            r'Temperature\s*[:\-]?\s*([^\n]+)',
            r'Power\s*[:\-]?\s*([^\n]+)',
            r'Voltage\s*[:\-]?\s*([^\n]+)',
            r'Refrigerant\s*[:\-]?\s*([^\n]+)',
            # Alternative patterns
            r'(\d+x\d+x\d+)\s*mm',  # Dimensions pattern
            r'(\d+)\s*kg',  # Weight pattern
            r'(\d+)L',  # Capacity pattern
            r'(R\d+[A-Z]?)',  # Refrigerant pattern
            r'(\d+~\d+ºC)',  # Temperature range pattern
            r'(\d+W)',  # Power pattern
            r'(\d+~?\d*V/?\d*Hz)',  # Voltage pattern
        ]
        
        for i, pattern in enumerate(spec_patterns):
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        value = match[0] if match[0] else (match[1] if len(match) > 1 else "")
                    else:
                        value = match
                    
                    value = value.strip()
                    
                    # Skip price-related values
                    if value and len(value) < 100 and 'VNĐ' not in value.upper() and 'MIỀN' not in value.upper():
                        # Determine key based on pattern
                        if i < 12:  # Named patterns
                            key = pattern.split('\\s*')[0].replace('?', '').replace('(', '').replace(')', '')
                        else:  # Alternative patterns - determine by value format
                            if 'x' in value and 'mm' in value:
                                key = 'Dimensions'
                            elif 'kg' in value:
                                key = 'Weight'
                            elif 'L' in value:
                                key = 'Capacity'
                            elif value.startswith('R') and any(c.isdigit() for c in value):
                                key = 'Refrigerant'
                            elif '~' in value and 'ºC' in value:
                                key = 'Temperature'
                            elif 'W' in value and value[:-1].isdigit():
                                key = 'Power'
                            elif 'V' in value or 'Hz' in value:
                                key = 'Voltage'
                            else:
                                continue
                        
                        specs[key] = value
        
        # Look for table structures
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    # Skip price-related entries
                    if (key and value and len(value) < 100 and 
                        'VNĐ' not in value.upper() and 'MIỀN' not in key.upper() and 'MIỀN' not in value.upper()):
                        specs[key] = value
        
        return specs
    
    def extract_features(self, soup: BeautifulSoup) -> List[str]:
        """Extract product features list"""
        features = []
        
        # Look for feature lists
        feature_containers = soup.find_all(['ul', 'ol'], class_=re.compile(r'feature|tính-năng|đặc-điểm'))
        
        for container in feature_containers:
            items = container.find_all('li')
            for item in items:
                feature_text = item.get_text(strip=True)
                if feature_text and len(feature_text) < 200:
                    features.append(feature_text)
        
        # Also search in text content for bullet points
        text_content = soup.get_text()
        feature_patterns = [
            r'[•▪▫▶→✓]\s*([^\n]+)',
            r'[-–—]\s*([^\n]+)'
        ]
        
        for pattern in feature_patterns:
            matches = re.findall(pattern, text_content)
            for match in matches:
                feature_text = match.strip()
                if len(feature_text) > 10 and len(feature_text) < 200:
                    features.append(feature_text)
        
        return list(set(features))  # Remove duplicates
    
    def extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract product images"""
        images = []
        
        # Find all images
        img_elements = soup.find_all('img', src=True)
        
        for img in img_elements:
            src = img.get('src')
            alt = img.get('alt', '').lower()
            
            # Filter for product images
            if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                # Skip common non-product images
                if not any(skip in src.lower() for skip in ['logo', 'icon', 'banner', 'header', 'footer']):
                    full_url = urljoin(self.base_url, src)
                    if full_url not in images:
                        images.append(full_url)
        
        return images
    
    def extract_short_description(self, soup: BeautifulSoup) -> str:
        """Extract short description (Mô tả ngắn)"""
        short_description = ""
        
        # Look for various patterns that might contain short description
        short_desc_selectors = [
            '.short-description',
            '.product-short-description', 
            '.excerpt',
            '.summary .excerpt',
            '.woocommerce-product-details__short-description',
            '[class*="short"]',
            '.entry-summary .excerpt'
        ]
        
        for selector in short_desc_selectors:
            element = soup.select_one(selector)
            if element:
                short_description = element.get_text(strip=True)
                if short_description and len(short_description) > 20:  # Make sure it's substantial
                    break
        
        # If no dedicated short description found, look for first paragraph in content
        if not short_description:
            content_selectors = ['.entry-content', '.product-content', '.content']
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    # Get first paragraph
                    first_p = element.find('p')
                    if first_p:
                        text = first_p.get_text(strip=True)
                        if text and len(text) > 20 and len(text) < 500:
                            short_description = text
                            break
        
        # Alternative: look for text patterns in the full content
        if not short_description:
            text_content = soup.get_text()
            lines = text_content.split('\n')
            for line in lines:
                line = line.strip()
                # Look for lines that might be short descriptions
                if (line and len(line) > 20 and len(line) < 300 and 
                    not any(skip in line.upper() for skip in ['GIÁ', 'MIỀN', 'VNĐ', 'MSP:', 'KÍCHước', 'TRỌNG LƯỢNG'])):
                    short_description = line
                    break
        
        return short_description[:500]  # Limit to reasonable length
    
    def extract_product_details(self, product_url: str) -> Optional[Dict]:
        """Extract detailed product information from a product page"""
        print(f"Extracting details from: {product_url}")
        
        content = self.get_page_content(product_url)
        if not content:
            return None
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract product name
        name = ""
        title_selectors = ['h1', '.product-title', '.entry-title']
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text(strip=True)
                break
        
        # Fallback to page title
        if not name:
            title = soup.find('title')
            if title:
                name = title.get_text(strip=True).split('|')[0].split('-')[0].strip()
        
        # Extract all detailed information
        category = self.extract_category(soup)
        msp = self.extract_msp(soup, product_url)
        prices = self.extract_prices(soup)
        specifications = self.extract_specifications(soup)
        features = self.extract_features(soup)
        images = self.extract_images(soup)
        short_description = self.extract_short_description(soup)
        
        # Extract full description
        description = ""
        desc_selectors = ['.product-description', '.entry-content', '.description', '.summary']
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                description = element.get_text(strip=True)[:1000]  # Limit length
                break
        
        product_data = {
            'url': product_url,
            'name': name,
            'category': category,
            'msp': msp,
            'short_description': short_description,
            'description': description,
            'prices': prices,
            'specifications': specifications,
            'features': features,
            'images': images,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return product_data
    
    def extract_product_details_with_firecrawl(self, product_url: str) -> Optional[Dict]:
        """Extract detailed product information using Firecrawl enhanced scraping"""
        if not self.firecrawl:
            return None
            
        print(f"Extracting details with Firecrawl from: {product_url}")
        
        try:
            # Use Firecrawl scrape_url with extraction instructions
            # Note: The extract feature may not be available in current SDK version
            # Using enhanced scraping with structured extraction prompt
            
            extraction_prompt = """
            Please extract and structure the following information from this Alaska product page:
            
            1. Product name and model
            2. Product category 
            3. MSP/product code (usually after "MSP:")
            4. All features from short description section (Mô tả ngắn)
            5. Regional pricing (MIỀN BẮC, MIỀN TRUNG, MIỀN NAM)
            6. Technical specifications (THÔNG SỐ KỸ THUẬT)
            7. Store/document links
            8. Warranty information
            
            Format as structured JSON following the schema provided.
            """
            
            # Use scrape_url with extraction parameters
            result = self.firecrawl.scrape_url(
                product_url, 
                params={
                    'formats': ['extract'],
                    'extract': {
                        'prompt': extraction_prompt,
                        'schema': AlaskaProduct.model_json_schema()
                    }
                }
            )
            
            if result and result.get('extract'):
                extracted_data = result['extract']
                
                # Add timestamp and URL
                extracted_data['scraped_at'] = time.strftime('%Y-%m-%d %H:%M:%S')  
                extracted_data['url'] = product_url
                
                return extracted_data
            else:
                print(f"Firecrawl enhanced scraping failed for {product_url}")
                return None
                
        except Exception as e:
            print(f"Error with Firecrawl enhanced scraping for {product_url}: {e}")
            return None
    
    def extract_product_urls_with_firecrawl(self, page_url: str) -> List[str]:
        """Extract product URLs from listing page using Firecrawl enhanced scraping"""
        if not self.firecrawl:
            return []
            
        try:
            # Create URL extraction prompt
            url_extraction_prompt = """
            Extract all individual product URLs from this Alaska.vn product listing page.
            Look for links to specific products (not category or navigation links).
            Return only the complete URLs to individual product pages.
            """
            
            # Simple schema for URL extraction
            url_schema = {
                "type": "object",
                "properties": {
                    "product_urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of product page URLs"
                    }
                }
            }
            
            # Use scrape_url with extraction parameters
            result = self.firecrawl.scrape_url(
                page_url,
                params={
                    'formats': ['extract'],
                    'extract': {
                        'prompt': url_extraction_prompt,
                        'schema': url_schema
                    }
                }
            )
            
            if result and result.get('extract'):
                extracted_data = result['extract']
                return extracted_data.get('product_urls', [])
            else:
                print(f"Firecrawl URL extraction failed for {page_url}")
                return []
                
        except Exception as e:
            print(f"Error with Firecrawl URL extraction for {page_url}: {e}")
            return []
    
    def scrape_all_products(self) -> List[Dict]:
        """Scrape all products from Alaska.vn"""
        print("Getting all product URLs...")
        product_urls = self.get_all_product_urls()
        print(f"Found {len(product_urls)} total products")
        
        all_products = []
        
        for i, url in enumerate(product_urls, 1):
            print(f"Processing product {i}/{len(product_urls)}")
            
            # Try Firecrawl extract first, fallback to manual extraction
            product_data = None
            if self.firecrawl:
                product_data = self.extract_product_details_with_firecrawl(url)
                if not product_data:  # Fallback if Firecrawl fails
                    print("Firecrawl extraction failed, falling back to manual extraction")
                    product_data = self.extract_product_details(url)
            else:
                product_data = self.extract_product_details(url)
            
            if product_data:
                all_products.append(product_data)
                print(f"✓ Extracted: {product_data.get('name', 'Unknown')} (MSP: {product_data.get('msp', 'N/A')})")
            else:
                print(f"✗ Failed to extract data from {url}")
            
            # Be respectful to the server
            time.sleep(2)
        
        return all_products
    
    def scrape_single_product(self, product_url: str) -> Optional[Dict]:
        """Scrape a single product for testing using best available method"""
        # Try Firecrawl extract first, fallback to manual extraction
        if self.firecrawl:
            product_data = self.extract_product_details_with_firecrawl(product_url)
            if product_data:
                return product_data
            else:
                print("Firecrawl extraction failed, falling back to manual extraction")
        
        return self.extract_product_details(product_url)
    
    def export_to_json(self, products: List[Dict], filename: str = 'alaska_products.json'):
        """Export products data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        
        print(f"Exported {len(products)} products to {filename}")


def main():
    """Main function to run the scraper"""
    import sys
    
    # Initialize scraper (add your Firecrawl API key if you have one)
    scraper = AlaskaScraper()
    
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--full':
        # Full crawl mode
        print("Starting full Alaska.vn product scraping...")
        all_products = scraper.scrape_all_products()
        scraper.export_to_json(all_products, 'alaska_products.json')
        print(f"Scraping completed! Total products: {len(all_products)}")
    else:
        # Test mode (default)
        test_urls = [
            "https://alaska.vn/tu-mat-lc-535c/",
            "https://alaska.vn/tu-mat-2-canh-lc-800c/"
        ]
        
        print("Testing with sample products...")
        test_products = []
        for url in test_urls:
            product = scraper.scrape_single_product(url)
            if product:
                test_products.append(product)
                print(f"✓ Test successful: {product['name']} (MSP: {product['msp']})")
        
        # Export test results
        if test_products:
            scraper.export_to_json(test_products, 'test_products.json')
        
        print("\nTo run full crawl, use: python alaska_scraper.py --full")


if __name__ == "__main__":
    main()