import json
import os
import sys
import logging
from pathlib import Path
import asyncio

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from ml.models.text_encoder import TextEncoder
from backend.app.services.catalog import load_recommendation_catalog

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Pinecone Vector Sync...")
    
    # 1. Load data from Neo4j (the current truth)
    # We use the catalog service to get the hydrated data
    catalog = load_recommendation_catalog()
    if not catalog:
        logger.error("Catalog is empty. Has Neo4j been hydrated? check_neo4j.py reported 22k nodes.")
        return

    logger.info(f"Loaded {len(catalog)} fragrances from Neo4j Graph.")

    # 2. Initialize Encoder
    try:
        encoder = TextEncoder()
    except Exception as e:
        logger.error(f"Failed to initialize TextEncoder: {e}")
        return

    if not encoder.pc:
        logger.error("Pinecone API key is missing. Check your .env file.")
        return

    logger.info(f"Target Index: {encoder.index_name}")

    # 3. Process and Upload in batches
    # The process_and_upload method handles text feature extraction and parallel upsert.
    encoder.process_and_upload(catalog, batch_size=200)

    logger.info("Pinecone Sync Complete. Milestone 1: Phase 4 achieved.")

if __name__ == "__main__":
    # Ensure environment variables are loaded if not already
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    
    asyncio.run(main())
