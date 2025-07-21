# Alaska.vn Product Scraper

A Python web scraper that extracts detailed product information from Alaska.vn and exports it to JSON format. The scraper uses Firecrawl API for enhanced data extraction with fallback to standard web scraping.

## Features

- Scrapes all products from https://alaska.vn/product/
- Extracts comprehensive product details:
  - Product name and MSP (model code)
  - Category information
  - Regional pricing (Miền Bắc, Miền Trung, Miền Nam)
  - Technical specifications (dimensions, weight, capacity, power, etc.)
  - Product features list
  - High-quality product images
  - Product descriptions
- Exports data to JSON format
- Respectful scraping with rate limiting
- Support for both Firecrawl API and fallback scraping

## Installation

1. Clone or download this repository
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Test Mode (Default)
Test the scraper with sample products:

```bash
python alaska_scraper.py
```

This will scrape 2 sample products and export to `test_products.json`.

### Full Crawl Mode
Scrape all products from Alaska.vn:

```bash
python alaska_scraper.py --full
```

This will scrape all products and export to `alaska_products.json`.

### With Firecrawl API
If you have a Firecrawl API key, you can modify the script to use it:

```python
# In the main() function, replace:
scraper = AlaskaScraper()
# with:
scraper = AlaskaScraper(api_key="your_firecrawl_api_key")
```

## Output Format

The scraper exports data in JSON format with the following structure:

```json
[
  {
    "url": "https://alaska.vn/tu-mat-lc-535c/",
    "name": "Tủ Mát LC-535C",
    "category": "Tủ mát 1 cửa",
    "msp": "LC-535C",
    "prices": {
      "MIỀN BẮC": "18,980,000 VNĐ",
      "MIỀN TRUNG": "18,860,000 VNĐ",
      "MIỀN NAM": "18,260,000 VNĐ"
    },
    "specifications": {
      "Kích thước": "700x690x2079mm",
      "Trọng lượng": "83kg",
      "Dung tích": "525L",
      "Nhiệt độ": "1~10ºC",
      "Công suất": "310W",
      "Voltage": "220~240V/50Hz",
      "Refrigerant": "R134a"
    },
    "features": [
      "Double-layer anti-condensation glass",
      "LED lighting system",
      "Automatic power cut-off when door is open"
    ],
    "description": "Product description...",
    "images": [
      "https://alaska.vn/wp-content/uploads/2025/05/LC-535C-2-w.jpg",
      "https://alaska.vn/wp-content/uploads/2025/05/LC-535C-3-w.jpg"
    ],
    "scraped_at": "2025-07-21 10:00:55"
  }
]
```

## Data Fields

| Field | Description |
|-------|-------------|
| `url` | Product page URL |
| `name` | Product name |
| `category` | Product category |
| `msp` | Model/Product code |
| `prices` | Regional pricing information |
| `specifications` | Technical specifications |
| `features` | Product features list |
| `description` | Product description |
| `images` | Product image URLs |
| `scraped_at` | Timestamp of data extraction |

## Rate Limiting

The scraper includes built-in rate limiting:
- 1 second delay between listing pages
- 2 seconds delay between product detail pages
- Maximum 50 listing pages per run (safety limit)

## Dependencies

- `firecrawl-py==1.4.0` - Firecrawl API client
- `requests==2.31.0` - HTTP requests
- `beautifulsoup4==4.12.2` - HTML parsing
- `lxml==4.9.3` - XML/HTML parser

## Notes

- The scraper is designed to be respectful to the server with appropriate delays
- Product images may include some general site images; filtering is applied to prioritize product-specific images
- Some specifications may appear in multiple formats (Vietnamese/English) for better data coverage
- The scraper handles various price and specification formats found on the site

## Legal and Ethical Use

This scraper is intended for educational and research purposes. Please ensure you:
- Respect the website's robots.txt file
- Use appropriate delays between requests
- Do not overload the server
- Comply with the website's terms of service
- Consider the legal implications of web scraping in your jurisdiction