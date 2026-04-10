import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Force current dir to be in path
sys.path.append(os.path.abspath(os.curdir))

from app.config import settings

async def migrate():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        print("Migrating 'users' table for PII Vault...")
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS encrypted_email TEXT"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_hash VARCHAR(64)"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user'"))
        
        # We need a separate step for the index if it fails on columns not existing yet
        print("Creating index on email_hash...")
        try:
            await conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_email_hash ON users(email_hash)"))
        except Exception as e:
            print(f"Warning: Index creation failed (might already exist): {e}")

    await engine.dispose()
    print("Schema Migrated.")

if __name__ == "__main__":
    asyncio.run(migrate())
