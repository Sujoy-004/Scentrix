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
        print("Migrating 'users' table...")
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS encrypted_email TEXT"))
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_hash VARCHAR(64)")
        )
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(100)")
        )
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user'")
        )

        print("Migrating 'fragrance_ratings' table...")
        await conn.execute(
            text("ALTER TABLE fragrance_ratings ADD COLUMN IF NOT EXISTS quiz_rating FLOAT")
        )

        # Make perceptual dims nullable if they aren't already
        for col in [
            "rating_sweetness",
            "rating_woodiness",
            "rating_longevity",
            "rating_projection",
            "rating_freshness",
            "overall_satisfaction",
        ]:
            await conn.execute(
                text(f"ALTER TABLE fragrance_ratings ALTER COLUMN {col} DROP NOT NULL")
            )

        print("Creating index on email_hash...")
        try:
            await conn.execute(
                text("CREATE UNIQUE INDEX IF NOT EXISTS idx_email_hash ON users(email_hash)")
            )
        except Exception as e:
            print(f"Warning: Index creation failed: {e}")

    await engine.dispose()
    print("Schema Migration Complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
