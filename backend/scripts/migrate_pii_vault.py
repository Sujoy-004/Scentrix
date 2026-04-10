import os
import asyncio
import hashlib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models.models import User
from app.auth.encryption import vault
from app.config import settings

async def migrate_users_to_vault():
    """Migrate plain-text user emails to the DataVault (Encrypted + Hashed)."""
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. Fetch all users
        # NOTE: If we already renamed 'email' to 'encrypted_email', this needs care.
        # Assuming we just added the fields and haven't fully switched yet.
        # But my models.py update REPLACEMENT of the email field.
        # This means the current 'users' table in DB still has 'email' column but the ORM thinks it's 'encrypted_email'.
        # I'll use a direct text query to avoid ORM mapping conflicts during migration.
        from sqlalchemy import text
        
        print("--- PII VAULT MIGRATION: SECURING USER EMAILS ---")
        res = await session.execute(text("SELECT id, email FROM users WHERE email_hash IS NULL"))
        users = res.all()
        print(f"Found {len(users)} users to migrate.")

        for user_id, email in users:
            e_email = vault.encrypt(email)
            h_email = hashlib.sha256(email.lower().strip().encode()).hexdigest()
            
            await session.execute(
                text("UPDATE users SET encrypted_email = :e, email_hash = :h WHERE id = :idx"),
                {"e": e_email, "h": h_email, "idx": user_id}
            )
            
        await session.commit()
        print("Vault Migration Complete.")

if __name__ == "__main__":
    asyncio.run(migrate_users_to_vault())
