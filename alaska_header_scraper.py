#!/usr/bin/env python3
"""
Alaska.vn Header Navigation Scraper
Scrapes header navigation data from Alaska.vn (excluding product navigation)
"""

import json
import re
import time
from typing import List, Dict, Optional, Any
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
import os
from firecrawl import FirecrawlApp


class NavigationItem(BaseModel):
    """Schema for individual navigation items"""
    name: str = Field(description="Navigation item name")
    url: Optional[str] = Field(description="Navigation item URL", default=None)
    sub_items: List['NavigationItem'] = Field(description="Sub-navigation items", default_factory=list)


class HeaderElements(BaseModel):
    """Schema for additional header elements"""
    logo_url: Optional[str] = Field(description="Logo image URL", default=None)
    logo_link: Optional[str] = Field(description="Logo link URL", default=None)
    social_links: List[Dict[str, str]] = Field(description="Social media links", default_factory=list)
    language_options: List[str] = Field(description="Available language options", default_factory=list)
    contact_info: Dict[str, str] = Field(description="Header contact information", default_factory=dict)


class PageContent(BaseModel):
    """Schema for detailed page content"""
    title: str = Field(description="Page title", default="")
    meta_description: str = Field(description="Meta description", default="")
    headings: List[str] = Field(description="All headings (H1-H6)", default_factory=list)
    paragraphs: List[str] = Field(description="All paragraph content", default_factory=list)
    images: List[Dict[str, str]] = Field(description="Images with src, alt, title", default_factory=list)
    links: List[Dict[str, str]] = Field(description="Internal and external links", default_factory=list)
    lists: List[str] = Field(description="List items content", default_factory=list)
    tables: List[Dict[str, Any]] = Field(description="Table data", default_factory=list)
    contact_info: Dict[str, str] = Field(description="Contact information found", default_factory=dict)
    full_text: str = Field(description="Complete cleaned text content", default="")
    word_count: int = Field(description="Total word count", default=0)
    scraped_at: str = Field(description="Timestamp of scraping")


class NavigationPageDetail(BaseModel):
    """Schema for navigation page with full content"""
    name: str = Field(description="Navigation item name")
    url: str = Field(description="Page URL")
    content: PageContent = Field(description="Detailed page content")
    sub_pages: List['NavigationPageDetail'] = Field(description="Sub-page details", default_factory=list)


class AlaskaHeaderNavigation(BaseModel):
    """Complete schema for Alaska header navigation data"""
    main_navigation: List[NavigationItem] = Field(
        description="Main navigation menu items (excluding Sản phẩm)",
        default_factory=list
    )
    header_elements: HeaderElements = Field(
        description="Additional header elements (logo, social, language)",
        default_factory=HeaderElements
    )
    scraped_at: str = Field(description="Timestamp of scraping")
    source_url: str = Field(description="URL where data was scraped from")


class AlaskaFullNavigation(BaseModel):
    """Complete schema for Alaska navigation with full page content"""
    navigation_pages: List[NavigationPageDetail] = Field(
        description="Navigation pages with full content details",
        default_factory=list
    )
    header_elements: HeaderElements = Field(
        description="Additional header elements",
        default_factory=HeaderElements
    )
    total_pages_scraped: int = Field(description="Total number of pages scraped", default=0)
    scraping_duration: float = Field(description="Total scraping time in seconds", default=0.0)
    scraped_at: str = Field(description="Timestamp of scraping")
    source_url: str = Field(description="Base URL")


class AlaskaHeaderScraper:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the header scraper with optional Firecrawl API key"""
        # Try to get API key from parameter, environment, or default to None
        if not api_key:
            api_key = os.getenv('FIRECRAWL_API_KEY')
        
        if api_key:
            self.firecrawl = FirecrawlApp(api_key=api_key)
            print("Initialized with Firecrawl API")
        else:
            self.firecrawl = None
            print("Warning: No Firecrawl API key provided. Using fallback scraping method.")
        
        self.base_url = "https://alaska.vn"
        self.home_url = "https://alaska.vn/"
        
        # Create session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_page_content(self, url: str) -> Optional[str]:
        """Get page content using requests (fallback) or Firecrawl"""
        # For navigation extraction, direct requests work better than Firecrawl
        # as Firecrawl processes content differently and may miss header navigation
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error with direct request for {url}: {e}")
            # Try Firecrawl as fallback if direct requests fail
            if self.firecrawl:
                try:
                    print("Direct request failed, trying Firecrawl...")
                    result = self.firecrawl.scrape_url(url, params={'formats': ['html']})
                    content = result.get('html', '')
                    return content
                except Exception as firecrawl_error:
                    print(f"Firecrawl also failed: {firecrawl_error}")
            return None
    
    def extract_main_menu(self, soup: BeautifulSoup) -> List[NavigationItem]:
        """Extract main navigation menu items (excluding Sản phẩm)"""
        navigation_items = []
        
        # Target navigation items we want (excluding Sản phẩm)
        target_items = {
            'Giới thiệu': None,
            'Hỗ trợ khách hàng': None,
            'Dự án': None,
            'Tin tức': None,
            'Liên hệ': None
        }
        
        # Find all links that contain our target text
        all_links = soup.find_all('a', href=True)
        
        # If no links found with href, try all anchor tags
        if not all_links:
            all_links = soup.find_all('a')
        
        # Look through all links for our target navigation items
        for link in all_links:
            link_text = link.get_text(strip=True)
            link_url = link.get('href', '')
            
            # Check if this is one of our target items - use exact match or contains
            for target_name in target_items.keys():
                if (target_name == link_text or target_name in link_text) and target_items[target_name] is None:
                    # Make URL absolute if relative
                    if link_url and link_url.startswith('/'):
                        full_url = urljoin(self.base_url, link_url)
                    elif link_url and not link_url.startswith('http'):
                        full_url = urljoin(self.base_url, '/' + link_url)
                    else:
                        full_url = link_url
                    
                    # Extract sub-items for this navigation item
                    sub_items = self.extract_sub_menus(link.parent, target_name)
                    
                    nav_item = NavigationItem(
                        name=target_name,
                        url=full_url,
                        sub_items=sub_items
                    )
                    
                    target_items[target_name] = nav_item
                    break
        
        # Fallback: Look for known URLs if text matching fails
        found_via_url = []
        for target_name in target_items.keys():
            if target_items[target_name] is None:
                url_mappings = {
                    'Giới thiệu': ['/ve-chung-toi/', '/gioi-thieu/'],
                    'Hỗ trợ khách hàng': ['#', '/ho-tro/'],
                    'Dự án': ['/project/', '/du-an/'],
                    'Tin tức': ['/tin-tuc/', '/news/'],
                    'Liên hệ': ['/lien-he-alaska/', '/lien-he/', '/contact/']
                }
                
                if target_name in url_mappings:
                    for link in all_links:
                        link_url = link.get('href', '')
                        for url_part in url_mappings[target_name]:
                            if url_part in link_url:
                                # Make URL absolute if relative
                                if link_url and link_url.startswith('/'):
                                    full_url = urljoin(self.base_url, link_url)
                                elif link_url and not link_url.startswith('http'):
                                    full_url = urljoin(self.base_url, '/' + link_url)
                                else:
                                    full_url = link_url
                                
                                # Extract sub-items for this navigation item
                                sub_items = self.extract_sub_menus(link.parent, target_name)
                                
                                nav_item = NavigationItem(
                                    name=target_name,
                                    url=full_url,
                                    sub_items=sub_items
                                )
                                
                                target_items[target_name] = nav_item
                                found_via_url.append(target_name)
                                break
                        if target_items[target_name] is not None:
                            break
        
        # Convert found items to list (maintain order)
        for item_name in ['Giới thiệu', 'Hỗ trợ khách hàng', 'Dự án', 'Tin tức', 'Liên hệ']:
            if target_items[item_name]:
                navigation_items.append(target_items[item_name])
        
        return navigation_items
    
    def extract_sub_menus(self, parent_element, main_item_name: str) -> List[NavigationItem]:
        """Extract sub-navigation items for a main navigation item"""
        sub_items = []
        
        # Define expected sub-items for each main navigation item
        expected_sub_items = {
            'Giới thiệu': ['Video clip', 'Tuyển dụng', 'Thông cáo báo chí'],
            'Hỗ trợ khách hàng': ['Catalogue', 'Trung tâm bảo hành', 'Hỏi đáp']
        }
        
        if main_item_name not in expected_sub_items:
            return sub_items
        
        # Look for dropdown/submenu in the parent element or its siblings
        submenu_selectors = [
            '.sub-menu',
            '.dropdown-menu',
            'ul',
            '.submenu'
        ]
        
        for selector in submenu_selectors:
            submenu = parent_element.find(selector)
            if submenu:
                sub_links = submenu.find_all('a', href=True)
                
                for sub_link in sub_links:
                    sub_text = sub_link.get_text(strip=True)
                    sub_url = sub_link.get('href')
                    
                    # Check if this matches our expected sub-items
                    for expected_sub in expected_sub_items[main_item_name]:
                        if expected_sub in sub_text or sub_text in expected_sub:
                            full_url = urljoin(self.base_url, sub_url) if sub_url.startswith('/') else sub_url
                            
                            sub_item = NavigationItem(
                                name=expected_sub,
                                url=full_url
                            )
                            sub_items.append(sub_item)
                            break
                
                if sub_items:  # Found sub-items, break from selector loop
                    break
        
        return sub_items
    
    def extract_header_extras(self, soup: BeautifulSoup) -> HeaderElements:
        """Extract additional header elements (logo, social links, language switcher)"""
        header_elements = HeaderElements()
        
        # Extract logo information
        logo_selectors = [
            'img[alt*="logo" i]',
            '.logo img',
            '.site-logo img',
            'a[href="/"] img',
            'header img'
        ]
        
        for selector in logo_selectors:
            logo_img = soup.select_one(selector)
            if logo_img:
                logo_src = logo_img.get('src')
                if logo_src:
                    header_elements.logo_url = urljoin(self.base_url, logo_src)
                    
                    # Get logo link
                    logo_link = logo_img.find_parent('a')
                    if logo_link:
                        href = logo_link.get('href')
                        if href:
                            header_elements.logo_link = urljoin(self.base_url, href)
                    break
        
        # Extract social media links
        social_selectors = [
            'a[href*="facebook"]',
            'a[href*="twitter"]',
            'a[href*="instagram"]',
            'a[href*="youtube"]',
            'a[href*="linkedin"]',
            '.social-links a',
            '.social-media a'
        ]
        
        for selector in social_selectors:
            social_links = soup.select(selector)
            for link in social_links:
                href = link.get('href')
                text = link.get_text(strip=True)
                if href:
                    # Determine platform
                    platform = 'unknown'
                    if 'facebook' in href.lower():
                        platform = 'Facebook'
                    elif 'twitter' in href.lower():
                        platform = 'Twitter'
                    elif 'instagram' in href.lower():
                        platform = 'Instagram'
                    elif 'youtube' in href.lower():
                        platform = 'YouTube'
                    elif 'linkedin' in href.lower():
                        platform = 'LinkedIn'
                    
                    header_elements.social_links.append({
                        'platform': platform,
                        'url': href,
                        'text': text
                    })
        
        # Extract language options
        language_selectors = [
            '.language-switcher a',
            '.lang-switcher a',
            'a[hreflang]',
            'a[href*="/en"]',
            'a[href*="/vn"]'
        ]
        
        found_languages = set()
        for selector in language_selectors:
            lang_links = soup.select(selector)
            for link in lang_links:
                lang_text = link.get_text(strip=True)
                hreflang = link.get('hreflang')
                
                if hreflang:
                    found_languages.add(hreflang.upper())
                elif lang_text in ['VN', 'EN', 'Tiếng Việt', 'English']:
                    found_languages.add(lang_text.upper())
        
        header_elements.language_options = list(found_languages)
        
        return header_elements
    
    def scrape_header_navigation(self) -> Optional[AlaskaHeaderNavigation]:
        """Main method to scrape header navigation data"""
        print(f"Scraping header navigation from: {self.home_url}")
        
        content = self.get_page_content(self.home_url)
        if not content:
            print("Failed to fetch homepage content")
            return None
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract main navigation
        print("Extracting main navigation...")
        main_navigation = self.extract_main_menu(soup)
        
        # Extract header elements
        print("Extracting header elements...")
        header_elements = self.extract_header_extras(soup)
        
        # Create the complete navigation data
        navigation_data = AlaskaHeaderNavigation(
            main_navigation=main_navigation,
            header_elements=header_elements,
            scraped_at=time.strftime('%Y-%m-%d %H:%M:%S'),
            source_url=self.home_url
        )
        
        return navigation_data
    
    def extract_page_content(self, url: str, page_name: str) -> Optional[PageContent]:
        """Extract detailed content from a page"""
        print(f"Extracting content from: {page_name} ({url})")
        
        content = self.get_page_content(url)
        if not content:
            return None
        
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract title
        title = ""
        title_element = soup.find('title')
        if title_element:
            title = title_element.get_text(strip=True)
        
        # Extract meta description
        meta_desc = ""
        meta_element = soup.find('meta', attrs={'name': 'description'})
        if meta_element:
            meta_desc = meta_element.get('content', '')
        
        # Extract headings (H1-H6)
        headings = []
        for heading_tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            heading_elements = soup.find_all(heading_tag)
            for heading in heading_elements:
                heading_text = heading.get_text(strip=True)
                if heading_text and len(heading_text) > 2:
                    headings.append(f"{heading_tag.upper()}: {heading_text}")
        
        # Extract paragraphs
        paragraphs = []
        paragraph_elements = soup.find_all('p')
        for p in paragraph_elements:
            p_text = p.get_text(strip=True)
            if p_text and len(p_text) > 10:  # Filter out short/empty paragraphs
                paragraphs.append(p_text)
        
        # Extract images
        images = []
        img_elements = soup.find_all('img')
        for img in img_elements:
            img_src = img.get('src', '')
            img_alt = img.get('alt', '')
            img_title = img.get('title', '')
            
            if img_src:
                # Make URL absolute
                if img_src.startswith('/'):
                    img_src = urljoin(self.base_url, img_src)
                
                images.append({
                    'src': img_src,
                    'alt': img_alt,
                    'title': img_title
                })
        
        # Extract links
        links = []
        link_elements = soup.find_all('a', href=True)
        for link in link_elements:
            link_url = link.get('href', '')
            link_text = link.get_text(strip=True)
            
            if link_url and link_text:
                # Make URL absolute if relative
                if link_url.startswith('/'):
                    link_url = urljoin(self.base_url, link_url)
                
                # Categorize as internal or external
                link_type = 'internal' if self.base_url in link_url else 'external'
                
                links.append({
                    'url': link_url,
                    'text': link_text,
                    'type': link_type
                })
        
        # Extract lists
        list_items = []
        list_elements = soup.find_all(['ul', 'ol'])
        for list_el in list_elements:
            items = list_el.find_all('li')
            for item in items:
                item_text = item.get_text(strip=True)
                if item_text and len(item_text) > 3:
                    list_items.append(item_text)
        
        # Extract tables
        tables = []
        table_elements = soup.find_all('table')
        for table in table_elements:
            table_data = {'headers': [], 'rows': []}
            
            # Extract headers
            header_row = table.find('tr')
            if header_row:
                headers = header_row.find_all(['th', 'td'])
                table_data['headers'] = [h.get_text(strip=True) for h in headers]
            
            # Extract rows
            rows = table.find_all('tr')[1:]  # Skip header row
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_data = [cell.get_text(strip=True) for cell in cells]
                if any(row_data):  # Only add non-empty rows
                    table_data['rows'].append(row_data)
            
            if table_data['headers'] or table_data['rows']:
                tables.append(table_data)
        
        # Extract contact information
        contact_info = {}
        text_content = soup.get_text()
        
        # Phone patterns
        phone_patterns = [
            r'(?:Tel|Phone|Điện thoại|SĐT)[:\s]*([+\d\s\-\(\)]{10,})',
            r'(\+84[^\s]{9,})',
            r'(0[1-9]\d{8,9})'
        ]
        
        for pattern in phone_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            for match in matches:
                clean_phone = re.sub(r'[^\d+]', '', match)
                if len(clean_phone) >= 10:
                    contact_info['phone'] = match.strip()
                    break
            if 'phone' in contact_info:
                break
        
        # Email patterns
        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        email_matches = re.findall(email_pattern, text_content)
        if email_matches:
            contact_info['email'] = email_matches[0]
        
        # Address patterns
        address_patterns = [
            r'(?:Địa chỉ|Address)[:\s]*([^\n]{20,100})',
            r'([^\n]*(?:Quận|District|Phường|Ward)[^\n]{10,})'
        ]
        
        for pattern in address_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            if matches:
                contact_info['address'] = matches[0].strip()
                break
        
        # Extract full clean text
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        full_text = soup.get_text()
        # Clean up whitespace
        full_text = re.sub(r'\s+', ' ', full_text).strip()
        
        # Count words
        word_count = len(full_text.split()) if full_text else 0
        
        return PageContent(
            title=title,
            meta_description=meta_desc,
            headings=headings,
            paragraphs=paragraphs,
            images=images,
            links=links,
            lists=list_items,
            tables=tables,
            contact_info=contact_info,
            full_text=full_text,
            word_count=word_count,
            scraped_at=time.strftime('%Y-%m-%d %H:%M:%S')
        )
    
    def scrape_all_navigation_content(self) -> Optional[AlaskaFullNavigation]:
        """Scrape full content from all navigation pages"""
        print("Starting full navigation content scraping...")
        start_time = time.time()
        
        # First get the basic navigation structure
        basic_navigation = self.scrape_header_navigation()
        if not basic_navigation:
            return None
        
        navigation_pages = []
        total_pages = 0
        
        # Process each main navigation item
        for nav_item in basic_navigation.main_navigation:
            print(f"\nProcessing main page: {nav_item.name}")
            
            # Extract content from main page
            main_content = self.extract_page_content(nav_item.url, nav_item.name)
            if main_content:
                # Process sub-pages
                sub_pages = []
                for sub_item in nav_item.sub_items:
                    print(f"  Processing sub-page: {sub_item.name}")
                    sub_content = self.extract_page_content(sub_item.url, sub_item.name)
                    if sub_content:
                        sub_pages.append(NavigationPageDetail(
                            name=sub_item.name,
                            url=sub_item.url,
                            content=sub_content,
                            sub_pages=[]
                        ))
                        total_pages += 1
                
                # Create main page detail
                navigation_pages.append(NavigationPageDetail(
                    name=nav_item.name,
                    url=nav_item.url,
                    content=main_content,
                    sub_pages=sub_pages
                ))
                total_pages += 1
        
        end_time = time.time()
        scraping_duration = end_time - start_time
        
        return AlaskaFullNavigation(
            navigation_pages=navigation_pages,
            header_elements=basic_navigation.header_elements,
            total_pages_scraped=total_pages,
            scraping_duration=scraping_duration,
            scraped_at=time.strftime('%Y-%m-%d %H:%M:%S'),
            source_url=self.base_url
        )
    
    def export_to_json(self, navigation_data: AlaskaHeaderNavigation, filename: str = 'alaska_header_navigation.json'):
        """Export navigation data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(navigation_data.model_dump(), f, ensure_ascii=False, indent=2)
        
        print(f"Exported header navigation data to {filename}")
    
    def export_full_navigation_to_json(self, full_navigation: AlaskaFullNavigation, filename: str = 'alaska_full_navigation.json'):
        """Export full navigation data to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(full_navigation.model_dump(), f, ensure_ascii=False, indent=2)
        
        print(f"Exported full navigation data to {filename}")
        
        # Print summary
        total_words = sum(page.content.word_count for page in full_navigation.navigation_pages)
        total_images = sum(len(page.content.images) for page in full_navigation.navigation_pages)
        total_links = sum(len(page.content.links) for page in full_navigation.navigation_pages)
        
        print(f"\nScraping Summary:")
        print(f"• Pages scraped: {full_navigation.total_pages_scraped}")
        print(f"• Total words: {total_words:,}")
        print(f"• Total images: {total_images}")
        print(f"• Total links: {total_links}")
        print(f"• Scraping duration: {full_navigation.scraping_duration:.2f} seconds")


def main():
    """Main function to run the header navigation scraper"""
    import sys
    
    print("Alaska.vn Header Navigation Scraper")
    print("=" * 40)
    
    # Check command line arguments
    full_content = '--full' in sys.argv or '--content' in sys.argv
    
    # Initialize scraper
    scraper = AlaskaHeaderScraper()
    
    if full_content:
        # Scrape full content from all navigation pages
        print("Mode: Full content scraping (all navigation pages)")
        print("=" * 50)
        
        full_navigation = scraper.scrape_all_navigation_content()
        
        if full_navigation:
            # Export to JSON
            scraper.export_full_navigation_to_json(full_navigation)
            
            print(f"\nFull content scraping completed!")
            print(f"Processed {len(full_navigation.navigation_pages)} main navigation pages:")
            
            for page in full_navigation.navigation_pages:
                print(f"\n📄 {page.name} ({page.url})")
                print(f"   Title: {page.content.title}")
                print(f"   Words: {page.content.word_count:,}")
                print(f"   Paragraphs: {len(page.content.paragraphs)}")
                print(f"   Images: {len(page.content.images)}")
                print(f"   Links: {len(page.content.links)}")
                
                if page.sub_pages:
                    print(f"   Sub-pages ({len(page.sub_pages)}):")
                    for sub_page in page.sub_pages:
                        print(f"     • {sub_page.name} - {sub_page.content.word_count:,} words")
        else:
            print("Failed to scrape full navigation content")
    
    else:
        # Basic header navigation scraping (default)
        print("Mode: Basic header navigation")
        print("Use --full or --content for detailed page content scraping")
        print("=" * 50)
        
        start_time = time.time()
        navigation_data = scraper.scrape_header_navigation()
        end_time = time.time()
        
        if navigation_data:
            # Export to JSON
            scraper.export_to_json(navigation_data)
            
            print(f"\nScraping completed in {end_time - start_time:.2f} seconds!")
            print(f"Found {len(navigation_data.main_navigation)} main navigation items:")
            
            for nav_item in navigation_data.main_navigation:
                print(f"  • {nav_item.name} ({nav_item.url})")
                if nav_item.sub_items:
                    for sub_item in nav_item.sub_items:
                        print(f"    - {sub_item.name} ({sub_item.url})")
            
            print(f"\nHeader elements:")
            if navigation_data.header_elements.logo_url:
                print(f"  • Logo: {navigation_data.header_elements.logo_url}")
            if navigation_data.header_elements.social_links:
                print(f"  • Social links: {len(navigation_data.header_elements.social_links)} found")
            if navigation_data.header_elements.language_options:
                print(f"  • Languages: {', '.join(navigation_data.header_elements.language_options)}")
            
            print(f"\n💡 To scrape full page content, run: python alaska_header_scraper.py --full")
        else:
            print("Failed to scrape header navigation data")


if __name__ == "__main__":
    main()