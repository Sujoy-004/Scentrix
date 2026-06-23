"""Custom middleware for rate limiting and user agent rotation."""

import random
import time
from typing import Optional

from scrapy import signals
from scrapy.http import Request, Response


class RandomDelayMiddleware:
    """Implements random delay between requests (0.5-2.0 seconds).
    
    This middleware adds random delays to respect server resources and avoid
    being perceived as a bot. Combined with DOWNLOAD_DELAY, actual delay will
    be: DOWNLOAD_DELAY + random(0.5, 2.0) seconds.
    """

    def __init__(self):
        self.min_delay = 0.5
        self.max_delay = 2.0

    @classmethod
    def from_crawler(cls, crawler):
        return cls()

    def process_request(self, request: Request, spider) -> Optional[Request]:
        """Add random delay before processing request."""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
        return None


class RotatingUserAgentMiddleware:
    """Rotates User-Agent header on each request.
    
    Pulls from ROTATING_USER_AGENTS list in settings to avoid detection.
    """

    def __init__(self, settings):
        self.user_agents = settings.getlist("ROTATING_USER_AGENTS", [])
        if not self.user_agents:
            self.user_agents = [settings.get("USER_AGENT", "Scrapy")]

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request: Request, spider) -> Optional[Request]:
        """Set random User-Agent."""
        user_agent = random.choice(self.user_agents)
        request.headers["User-Agent"] = user_agent
        return None
