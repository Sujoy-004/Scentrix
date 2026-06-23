"""Scripts for running the Fragrantica scraper."""

import logging
import sys
from pathlib import Path

from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from scraper.settings import *
from scraper.spiders.fragrantica import FragranticaSpider


def run_scraper(
    spider_name: str = "fragrantica",
    output_format: str = "jsonl",
    start_url: str = None,
    max_pages: int = None,
):
    """Run the Fragrantica scraper.
    
    Args:
        spider_name: Name of spider to run
        output_format: Output format (jsonl, json)
        start_url: Custom start URL (optional)
        max_pages: Max pages to crawl (optional)
    """
    configure_logging({"LOG_LEVEL": "INFO"})
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Fragrantica scraper: {spider_name}")
    
    # Configure crawler
    process = CrawlerProcess(
        {
            "LOG_LEVEL": "INFO",
            "ITEM_PIPELINES": {
                "scraper.pipelines.CloudflareR2Pipeline": 300,
            },
            "ROBOTSTXT_OBEY": True,
            "CONCURRENT_REQUESTS": 1,
            "DOWNLOAD_DELAY": 1.0,
        }
    )
    
    # Run spider
    process.crawl(FragranticaSpider)
    process.start()
    
    logger.info("Scraper completed")


if __name__ == "__main__":
    run_scraper()
