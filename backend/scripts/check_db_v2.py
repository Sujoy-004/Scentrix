import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Force current dir to be in path for app imports
sys.path.append(os.path.abspath(os.curdir))

from app.config import settings

async def check():
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"))
        cols = [r[0] for r in res.all()]
        print(f"COLUMNS: {cols}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
