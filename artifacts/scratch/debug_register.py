import asyncio
import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.abspath('backend'))

from app.database import get_session
from app.models.models import User
from app.schemas.schemas import UserRegister
from app.routers.auth import register
from unittest.mock import MagicMock

async def test_reg():
    print("Testing registration logic...")
    # Mock FastAPI request
    request = MagicMock()
    request.client.host = "127.0.0.1"
    
    user_data = UserRegister(
        email="user_test@gmail.com",
        password="SecurePassword123!",
        full_name="Test User",
        opt_in_training=True
    )
    
    try:
        async for session in get_session():
            print("Database session acquired.")
            res = await register(request, user_data, session)
            print("Registration success:", res)
            break
    except Exception as e:
        print("Registration failed with traceback:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reg())
