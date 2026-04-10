import asyncio
import os
import sys
import hashlib
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Force current dir to be in path
sys.path.append(os.path.abspath(os.curdir))

from app.auth.encryption import vault
from app.config import settings

async def migrate_users_to_vault():
    """Migrate plain-text user emails to the DataVault (Encrypted + Hashed)."""
    engine = create_async_engine(settings.database_url)
    
    async with engine.begin() as session:
        print("--- PII VAULT MIGRATION: SECURING USER EMAILS ---")
        res = await session.execute(text("SELECT id, email FROM users WHERE email IS NOT NULL AND email_hash IS NULL"))
        users = res.all()
        print(f"Found {len(users)} users to migrate.")

        for user_id, email in users:
            e_email = vault.encrypt(email)
            h_email = hashlib.sha256(email.lower().strip().encode()).hexdigest()
            
            await session.execute(
                text("UPDATE users SET encrypted_email = :e, email_hash = :h WHERE id = :idx"),
                {"e": e_email, "h": h_email, "idx": user_id}
            )
            
        print("Vault Migration Complete.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(migrate_users_to_vault())
