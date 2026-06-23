"""Scrapy settings for Fragrantica scraper.

Includes rate limiting, user agent rotation, middleware, and R2 pipeline configuration.
"""

BOT_NAME = "fragrantica-scraper"
SPIDER_MODULES = ["scraper.spiders"]
NEWSPIDER_MODULE = "scraper.spiders"

# Respect robots.txt
ROBOTSTXT_OBEY = True

# Crawl responsibly
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CONCURRENT_REQUESTS = 1
DOWNLOAD_DELAY = 1.0  # Base delay in seconds

# User agent rotation list
ROTATING_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
]

# Middleware
DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware": 100,
    "scraper.middleware.RandomDelayMiddleware": 300,
    "scraper.middleware.RotatingUserAgentMiddleware": 400,
}

# Pipelines (R2 storage)
ITEM_PIPELINES = {
    "scraper.pipelines.CloudflareR2Pipeline": 300,
}

# Logging
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

# Storage settings
CLOUDFLARE_R2_BUCKET_NAME = "scentrix-raw"
CLOUDFLARE_R2_ACCOUNT_ID = ""  # Set via .env or environment variables
CLOUDFLARE_R2_ACCESS_KEY_ID = ""
CLOUDFLARE_R2_SECRET_ACCESS_KEY = ""

# Retry policy
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
REDIRECT_ENABLED = True
REDIRECT_TIMES = 3

# Cache settings
CACHE_ENABLED = True
CACHE_DIR = ".cache"

# Request timeout
DOWNLOAD_TIMEOUT = 20

# DNS timeout
DNS_TIMEOUT = 10
