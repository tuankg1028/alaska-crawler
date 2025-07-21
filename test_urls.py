#!/usr/bin/env python3
"""
Test script to check URL extraction
"""

from alaska_scraper import AlaskaScraper

def test_url_extraction():
    scraper = AlaskaScraper()
    
    # Test first page only
    print("Testing URL extraction from first page...")
    urls = scraper.extract_product_urls_from_listing("https://alaska.vn/product/")
    
    print(f"Found {len(urls)} product URLs:")
    for i, url in enumerate(urls, 1):
        print(f"{i}. {url}")
    
    return urls

if __name__ == "__main__":
    test_url_extraction()