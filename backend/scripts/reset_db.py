import asyncio
import asyncpg
import sys

async def reset_db():
    # Connect as superuser (postgres) without password (using trust)
    print("Attempting to connect to the vault as superuser...")
    try:
        conn = await asyncpg.connect(user='postgres', database='postgres', host='127.0.0.1')
        print("Vault Breach Successful! (Superuser Access Granted)")
        
        # Check if scentrix user exists, if not create it
        user_exists = await conn.fetchval("SELECT 1 FROM pg_roles WHERE rolname = 'scentrix'")
        if not user_exists:
            print("Creating 'scentrix' user...")
            await conn.execute("CREATE USER scentrix WITH PASSWORD 'scentrix_password' SUPERUSER")
        else:
            print("Resetting password for 'scentrix' user...")
            await conn.execute("ALTER USER scentrix WITH PASSWORD 'scentrix_password' SUPERUSER")
            
        # Check if scentrix database exists, if not create it
        db_exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = 'scentrix'")
        if not db_exists:
            print("Creating 'scentrix' database...")
            await conn.execute("CREATE DATABASE scentrix OWNER scentrix")
        else:
            print("'scentrix' database already exists.")
            
        await conn.close()
        print("\n--- DATABASE SYNCHRONIZATION COMPLETE ---")
        print("User: scentrix")
        print("Password: scentrix_password")
        print("Database: scentrix")
        
    except Exception as e:
        print(f"Error during vault reset: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(reset_db())
