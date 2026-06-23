"""Scrapy pipelines for data storage and processing.

Includes Cloudflare R2 pipeline for storing raw fragrance data as JSONL.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Generator

import boto3
from itemadapter import ItemAdapter
from botocore.exceptions import ClientError


class CloudflareR2Pipeline:
    """Pipeline to store scraped items to Cloudflare R2.
    
    Writes items as JSONL (newline-delimited JSON) to R2 bucket.
    Path format: raw/fragrantica/YYYY-MM-DD/fragrances.jsonl
    """

    def __init__(self, settings):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # R2 configuration
        self.bucket_name = settings.get("CLOUDFLARE_R2_BUCKET_NAME", "scentrix-raw")
        self.account_id = settings.get("CLOUDFLARE_R2_ACCOUNT_ID")
        self.access_key_id = settings.get(
            "CLOUDFLARE_R2_ACCESS_KEY_ID", os.getenv("CLOUDFLARE_R2_ACCESS_KEY_ID")
        )
        self.secret_access_key = settings.get(
            "CLOUDFLARE_R2_SECRET_ACCESS_KEY",
            os.getenv("CLOUDFLARE_R2_SECRET_ACCESS_KEY"),
        )
        
        # Initialize S3 client for R2
        self.s3_client = None
        self.file_buffer = []
        self.item_count = 0
        
        if self.access_key_id and self.secret_access_key:
            try:
                # Construct R2 endpoint
                endpoint_url = f"https://{self.account_id}.r2.cloudflarestorage.com"
                
                self.s3_client = boto3.client(
                    "s3",
                    endpoint_url=endpoint_url,
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name="auto",
                )
                self.logger.info(
                    f"Initialized Cloudflare R2 client for bucket: {self.bucket_name}"
                )
            except Exception as e:
                self.logger.error(f"Failed to initialize R2 client: {e}")
                self.s3_client = None
        else:
            self.logger.warning(
                "R2 credentials not found. Will skip R2 upload. "
                "Set CLOUDFLARE_R2_ACCESS_KEY_ID and CLOUDFLARE_R2_SECRET_ACCESS_KEY environment variables."
            )

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def open_spider(self, spider):
        """Called when spider is opened."""
        self.logger.info(f"Opening spider: {spider.name}")

    def close_spider(self, spider):
        """Called when spider is closed. Flush remaining items."""
        self._flush_items()
        self.logger.info(
            f"Closed spider {spider.name}. Total items processed: {self.item_count}"
        )

    def process_item(self, item: dict, spider) -> dict:
        """Process an item and buffer it for batch upload."""
        self.item_count += 1
        self.file_buffer.append(item)
        
        # Flush every 100 items or on last item
        if len(self.file_buffer) >= 100:
            self._flush_items()
        
        return item

    def _flush_items(self):
        """Flush buffered items to R2 or local file."""
        if not self.file_buffer:
            return
        
        # Create path: raw/fragrantica/YYYY-MM-DD/fragrances.jsonl
        today = datetime.utcnow().strftime("%Y-%m-%d")
        s3_key = f"raw/fragrantica/{today}/fragrances.jsonl"
        
        # Convert items to JSONL format
        jsonl_content = "\n".join(json.dumps(item, default=str) for item in self.file_buffer)
        
        if self.s3_client:
            try:
                # Upload to R2
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    Body=jsonl_content.encode("utf-8"),
                    ContentType="application/x-ndjson",
                )
                self.logger.info(
                    f"Uploaded {len(self.file_buffer)} items to R2: s3://{self.bucket_name}/{s3_key}"
                )
            except ClientError as e:
                self.logger.error(f"Failed to upload to R2: {e}")
        else:
            # Fallback: Save to local file
            local_path = f"raw/fragrantica/{today}"
            os.makedirs(local_path, exist_ok=True)
            file_path = os.path.join(local_path, "fragrances.jsonl")
            
            try:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(jsonl_content + "\n")
                self.logger.info(
                    f"Saved {len(self.file_buffer)} items to local file: {file_path}"
                )
            except IOError as e:
                self.logger.error(f"Failed to save to local file: {e}")
        
        self.file_buffer = []
