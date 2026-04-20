"""Fragrantica fragrance scraper spider.

Scrapes fragrance data from Fragrantica including name, brand, accords,
notes (top/middle/base), concentration, gender, description, and review count.

Respects robots.txt and implements responsible crawling practices.
"""

from typing import Any, Generator, Optional
from urllib.parse import urljoin

import scrapy
from scrapy import Request


class FragranticaSpider(scrapy.Spider):
    """Spider for scraping fragrance data from Fragrantica.
    
    Target URL: https://www.fragrantica.com/perfumes/ (public fragrance listings)
    
    Scraped fields:
    - id: Fragrantica fragrance ID
    - name: Fragrance name
    - brand: Brand name
    - year: Release year (if available)
    - concentration: EDP, EDT, Cologne, etc.
    - gender_label: Gender classification (male, female, unisex)
    - description: Fragrance description
    - top_notes: List of top notes
    - middle_notes: List of middle notes
    - base_notes: List of base notes
    - accords: List of fragrance accords
    - review_count: Number of user reviews
    - url: Link to fragrance page on Fragrantica
    """

    name = "fragrantica"
    allowed_domains = ["fragrantica.com"]
    start_urls = ["https://www.fragrantica.com/perfumes/"]
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 1.0,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_count = 0
        self.error_count = 0

    def parse(self, response) -> Generator:
        """Parse fragrance listing page and extract fragrance links."""
        self.logger.info(f"Parsing page: {response.url}")
        
        # Extract fragrance links from listing page
        fragrance_links = response.css("a.fragrance-link::attr(href)").getall()
        
        if not fragrance_links:
            self.logger.warning(f"No fragrance links found on {response.url}")
            fragrance_links = response.css(
                "div.fragment a::attr(href)"
            ).getall()  # Fallback selector
        
        for link in fragrance_links:
            fragrance_url = urljoin(response.url, link)
            yield Request(
                fragrance_url,
                callback=self.parse_fragrance,
                meta={"dont_cache": True},
                errback=self.errback_parse_fragrance,
            )
        
        # Follow pagination links
        next_page = response.css("a.next::attr(href)").get()
        if next_page:
            next_url = urljoin(response.url, next_page)
            self.logger.info(f"Following pagination: {next_url}")
            yield Request(
                next_url,
                callback=self.parse,
                meta={"dont_cache": True},
            )

    def parse_fragrance(self, response) -> Generator[dict[str, Any], None, None]:
        """Parse individual fragrance page and extract data."""
        try:
            fragrance_id = self._extract_fragrance_id(response.url)
            
            if not fragrance_id:
                self.logger.warning(f"Could not extract ID from URL: {response.url}")
                self.error_count += 1
                return None
            
            # Extract fragrance data
            item = {
                "id": fragrance_id,
                "url": response.url,
                "name": self._extract_text(response, "h1.fragranceName::text"),
                "brand": self._extract_text(
                    response, "h3.brandName a::text"
                ),
                "year": self._extract_year(response),
                "concentration": self._extract_concentration(response),
                "gender_label": self._extract_gender(response),
                "description": self._extract_description(response),
                "top_notes": self._extract_notes(response, "top"),
                "middle_notes": self._extract_notes(response, "middle"),
                "base_notes": self._extract_notes(response, "base"),
                "accords": self._extract_accords(response),
                "review_count": self._extract_review_count(response),
            }
            
            # Validate item
            if self._validate_item(item):
                self.item_count += 1
                if self.item_count % 10 == 0:
                    self.logger.info(f"Processed {self.item_count} fragrances")
                yield item
            else:
                self.logger.warning(f"Validation failed for: {item.get('name')}")
                self.error_count += 1
        
        except Exception as e:
            self.logger.error(f"Error parsing fragrance page {response.url}: {e}")
            self.error_count += 1

    def errback_parse_fragrance(self, failure):
        """Handle request errors for fragrance pages."""
        self.logger.error(f"Error fetching {failure.request.url}: {failure.value}")
        self.error_count += 1

    @staticmethod
    def _extract_fragrance_id(url: str) -> Optional[str]:
        """Extract fragrance ID from Fragrantica URL."""
        try:
            # URL format: https://www.fragrantica.com/perfumes/<id>/<name>.html
            parts = url.rstrip("/").split("/")
            if len(parts) >= 5 and parts[-2].isdigit():
                return parts[-2]
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_text(response, selector: str) -> Optional[str]:
        """Extract and clean text from response."""
        text = response.css(selector).get()
        if text:
            return text.strip()
        return None

    @staticmethod
    def _extract_year(response) -> Optional[int]:
        """Extract fragrance release year."""
        year_text = response.css(
            "span:contains('Year')::text"
        ).get()  # Fallback selectors
        if not year_text:
            year_text = response.xpath("//text()[contains(., 'Year')]").get()
        
        if year_text:
            try:
                # Extract 4-digit year
                import re
                match = re.search(r"\d{4}", year_text)
                if match:
                    return int(match.group())
            except Exception:
                pass
        return None

    @staticmethod
    def _extract_concentration(response) -> str:
        """Extract fragrance concentration (EDP, EDT, etc.)."""
        concentration = response.css("span.concentration::text").get()
        if concentration:
            return concentration.strip()
        
        # Fallback: look in page text
        page_text = " ".join(response.css("::text").getall())
        if "Eau de Parfum" in page_text or "EDP" in page_text:
            return "EDP"
        elif "Eau de Toilette" in page_text or "EDT" in page_text:
            return "EDT"
        elif "Cologne" in page_text:
            return "Cologne"
        
        return "EDP"  # Default

    @staticmethod
    def _extract_gender(response) -> str:
        """Extract gender label (male, female, unisex)."""
        # Default to neutral per Scentrix requirements
        gender_text = response.css("span.gender::text").get()
        if gender_text:
            gender = gender_text.lower().strip()
            if "female" in gender or "women" in gender:
                return "Female"
            elif "male" in gender or "men" in gender:
                return "Male"
            elif "unisex" in gender:
                return "Unisex"
        
        return "N/A"  # Gender-neutral default

    @staticmethod
    def _extract_description(response) -> Optional[str]:
        """Extract fragrance description."""
        description = response.css("div.description::text").get()
        if not description:
            description = response.xpath(
                "//div[@class='fragment']//text()"
            ).get()  # Fallback
        
        if description:
            text = description.strip()
            # Cap at 500 characters
            return text[:500] if text else None
        return None

    @staticmethod
    def _extract_notes(response, note_type: str) -> list:
        """Extract fragrance notes (top, middle, base)."""
        notes = []
        
        # XPath selectors for different note types
        selectors = {
            "top": "//div[@id='top-notes']//span[@class='note-name']::text",
            "middle": "//div[@id='heart-notes']//span[@class='note-name']::text",
            "base": "//div[@id='base-notes']//span[@class='note-name']::text",
        }
        
        note_elements = response.xpath(selectors.get(note_type, "")).getall()
        
        if not note_elements:
            # Fallback CSS selectors
            css_selectors = {
                "top": "div.top-notes span.note::text",
                "middle": "div.middle-notes span.note::text",
                "base": "div.base-notes span.note::text",
            }
            note_elements = response.css(css_selectors.get(note_type, "")).getall()
        
        for note in note_elements:
            cleaned = note.strip()
            if cleaned and cleaned not in notes:
                notes.append(cleaned)
        
        return notes[:5]  # Max 5 notes per category

    @staticmethod
    def _extract_accords(response) -> list:
        """Extract fragrance accords."""
        accords = []
        
        accord_elements = response.css("span.accord::text").getall()
        if not accord_elements:
            accord_elements = response.xpath(
                "//div[@class='accord']//text()"
            ).getall()
        
        for accord in accord_elements:
            cleaned = accord.strip()
            if cleaned and cleaned not in accords:
                accords.append(cleaned)
        
        return accords[:5]  # Max 5 accords

    @staticmethod
    def _extract_review_count(response) -> int:
        """Extract number of user reviews."""
        review_text = response.css("span.review-count::text").get()
        if review_text:
            try:
                import re
                match = re.search(r"\d+", review_text)
                if match:
                    return int(match.group())
            except Exception:
                pass
        return 0

    @staticmethod
    def _validate_item(item: dict) -> bool:
        """Validate scraped item."""
        # Required fields
        required = ["id", "name", "brand"]
        for field in required:
            if not item.get(field):
                return False
        
        # At least some notes
        note_count = (
            len(item.get("top_notes", []))
            + len(item.get("middle_notes", []))
            + len(item.get("base_notes", []))
        )
        if note_count < 1:
            return False
        
        return True
