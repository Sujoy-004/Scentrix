#!/usr/bin/env python3
"""Phase 6 Production Deployment Verification Script.

Run this after deployment to verify all services are operational.

Usage:
    python verify_deployment.py
    
Prerequisites:
    - All services deployed (Vercel, Railway, databases, Sentry)
    - Environment variables configured
    - .env file set up locally
"""

import sys
import asyncio
from typing import Dict

# Import with error handling for optional dependencies
missing_packages = []

try:
    import requests
except ImportError:
    missing_packages.append('requests')

try:
    import redis
except ImportError:
    missing_packages.append('redis')

try:
    import asyncpg
except ImportError:
    missing_packages.append('asyncpg')

try:
    from neo4j import GraphDatabase
except ImportError:
    missing_packages.append('neo4j')

try:
    import pinecone
except ImportError:
    missing_packages.append('pinecone-client')

if missing_packages:
    print("❌ Missing dependencies:")
    for pkg in missing_packages:
        print(f"   - {pkg}")
    print("\nInstall with:")
    print(f"   pip install {' '.join(missing_packages)}")
    sys.exit(1)


class DeploymentVerifier:
    """Verification suite for Phase 6 deployment."""

    def __init__(self):
        self.results: Dict[str, bool] = {}
        self.urls: Dict[str, str] = {}
        
    def test_frontend_health(self, url: str) -> bool:
        """Test frontend is responding."""
        print(f"🔍 Testing frontend: {url}")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print("✅ Frontend health: OK")
                return True
            else:
                print(f"❌ Frontend returned {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Frontend error: {e}")
            return False

    def test_backend_health(self, url: str) -> bool:
        """Test backend /health endpoint."""
        print(f"🔍 Testing backend: {url}/health")
        try:
            response = requests.get(f"{url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    print("✅ Backend health: OK")
                    return True
                else:
                    print(f"❌ Backend status not ok: {data}")
                    return False
            else:
                print(f"❌ Backend returned {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Backend error: {e}")
            return False

    def test_backend_root(self, url: str) -> bool:
        """Test backend root endpoint."""
        print(f"🔍 Testing backend root: {url}/")
        try:
            response = requests.get(f"{url}/", timeout=10)
            if response.status_code == 200:
                print("✅ Backend root: OK")
                return True
            else:
                print(f"❌ Backend root returned {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Backend root error: {e}")
            return False

    def test_postgresql(self, connection_string: str) -> bool:
        """Test PostgreSQL connection."""
        print("🔍 Testing PostgreSQL...")
        try:
            async def test_conn():
                conn = await asyncpg.connect(connection_string)
                result = await conn.fetchval("SELECT 1")
                await conn.close()
                return result == 1
            
            result = asyncio.run(test_conn())
            if result:
                print("✅ PostgreSQL: Connected")
                return True
            else:
                print("❌ PostgreSQL: Query failed")
                return False
        except Exception as e:
            print(f"❌ PostgreSQL error: {e}")
            return False

    def test_neo4j(self, uri: str, username: str, password: str) -> bool:
        """Test Neo4j connection."""
        print("🔍 Testing Neo4j...")
        driver = None
        try:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            with driver.session() as session:
                result = session.run("RETURN 1")
                if result.single()[0] == 1:
                    print("✅ Neo4j: Connected")
                    return True
            return False
        except Exception as e:
            print(f"❌ Neo4j error: {e}")
            return False
        finally:
            if driver:
                driver.close()

    def test_redis(self, redis_url: str) -> bool:
        """Test Redis connection."""
        print("🔍 Testing Redis...")
        try:
            r = redis.from_url(redis_url)
            ping = r.ping()
            if ping:
                print("✅ Redis: Connected")
                return True
            else:
                print("❌ Redis: Ping failed")
                return False
        except Exception as e:
            print(f"❌ Redis error: {e}")
            return False

    def test_pinecone(self, api_key: str, environment: str, index_name: str) -> bool:
        """Test Pinecone connection."""
        print("🔍 Testing Pinecone...")
        try:
            pinecone.init(api_key=api_key, environment=environment)
            indexes = pinecone.list_indexes()
            if index_name in indexes:
                pinecone.describe_index(index_name)  # Verify index exists
                print(f"✅ Pinecone: Connected (index: {index_name})")
                return True
            else:
                print(f"❌ Pinecone: Index '{index_name}' not found")
                return False
        except Exception as e:
            print(f"❌ Pinecone error: {e}")
            return False

    def test_sentry(self, sentry_dsn: str) -> bool:
        """Test Sentry DSN validity."""
        print("🔍 Testing Sentry DSN...")
        try:
            if not sentry_dsn:
                print("⚠️  Sentry: DSN not configured (optional)")
                return True
            
            # DSN format validation
            if "sentry.io" not in sentry_dsn:
                print("❌ Sentry: Invalid DSN format")
                return False
            
            print("✅ Sentry: DSN configured")
            return True
        except Exception as e:
            print(f"❌ Sentry error: {e}")
            return False

    def print_summary(self) -> int:
        """Print test summary and return exit code."""
        print("\n" + "="*60)
        print("DEPLOYMENT VERIFICATION SUMMARY")
        print("="*60)
        
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        
        for service, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{service:.<40} {status}")
        
        print("="*60)
        print(f"Result: {passed}/{total} services healthy")
        print("="*60)
        
        return 0 if passed == total else 1


def main():
    """Main verification routine."""
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    print("="*60)
    print("PHASE 6 DEPLOYMENT VERIFICATION")
    print("="*60 + "\n")
    
    # Get configuration from environment
    frontend_url = os.getenv("FRONTEND_URL", "https://scentscape-xxxxx.vercel.app")
    backend_url = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:8000")
    database_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/scentscape")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_username = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    pinecone_api_key = os.getenv("PINECONE_API_KEY", "")
    pinecone_env = os.getenv("PINECONE_ENVIRONMENT", "us-west1-gcp")
    pinecone_index = os.getenv("PINECONE_INDEX_NAME", "scentscape-fragrances")
    sentry_dsn = os.getenv("SENTRY_DSN", "")
    
    print(f"Frontend URL:     {frontend_url}")
    print(f"Backend URL:      {backend_url}")
    print(f"Neo4j URI:        {neo4j_uri}")
    print(f"Redis URL:        {redis_url}")
    print(f"Pinecone Index:   {pinecone_index}\n")
    
    verifier = DeploymentVerifier()
    
    # Run tests
    print("Running verification tests...\n")
    
    verifier.results["Frontend Health"] = verifier.test_frontend_health(frontend_url)
    verifier.results["Backend Health"] = verifier.test_backend_health(backend_url)
    verifier.results["Backend Root"] = verifier.test_backend_root(backend_url)
    verifier.results["PostgreSQL"] = verifier.test_postgresql(database_url)
    verifier.results["Neo4j"] = verifier.test_neo4j(neo4j_uri, neo4j_username, neo4j_password)
    verifier.results["Redis"] = verifier.test_redis(redis_url)
    verifier.results["Pinecone"] = verifier.test_pinecone(pinecone_api_key, pinecone_env, pinecone_index)
    verifier.results["Sentry DSN"] = verifier.test_sentry(sentry_dsn)
    
    print()
    exit_code = verifier.print_summary()
    
    if exit_code == 0:
        print("\n🎉 All services healthy! Production deployment successful.")
    else:
        print("\n⚠️  Some services failed. Check configuration and logs.")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
