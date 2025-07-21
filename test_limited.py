#!/usr/bin/env python3
"""
Test script with limited pages
"""

from alaska_scraper import AlaskaScraper
import time

def test_limited_crawl():
    scraper = AlaskaScraper()
    
    # Test first 3 pages only
    all_urls = []
    for page in range(1, 4):  # Test first 3 pages
        if page == 1:
            page_url = scraper.products_url
        else:
            page_url = f"{scraper.products_url}page/{page}/"
        
        print(f"Scraping page {page}: {page_url}")
        urls = scraper.extract_product_urls_from_listing(page_url)
        
        if not urls:
            print(f"No products found on page {page}")
            break
            
        all_urls.extend(urls)
        print(f"Found {len(urls)} products on page {page}")
        time.sleep(1)
    
    # Remove duplicates
    all_urls = list(set(all_urls))
    print(f"\nTotal unique products found: {len(all_urls)}")
    
    # Test extracting details from first 3 products
    print("\nTesting product detail extraction...")
    for i, url in enumerate(all_urls[:3], 1):
        print(f"Testing product {i}: {url}")
        product = scraper.extract_product_details(url)
        if product:
            print(f"✓ Success: {product['name']} (MSP: {product['msp']})")
        else:
            print(f"✗ Failed")

if __name__ == "__main__":
    test_limited_crawl()