import os
import sys
import argparse
from pathlib import Path

# Add project root to path
# In Docker, project root is /app
sys.path.append(os.getenv("SCENTSCAPE_REPO_ROOT", "/app"))

from ml.graph import init_neo4j
from ml.pipeline.ingest import ingest_fragrances_from_file

def main():
    parser = argparse.ArgumentParser(description="Seed database from JSON file")
    parser.add_argument("--file", help="Path to seed file")
    args, _ = parser.parse_known_args()

    print("Starting data seeding process...")
    
    # Configuration from env
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")
    
    # Path to seed data
    if args.file:
        seed_file = Path(args.file)
    else:
        # Default to elite 24k
        seed_file = Path(os.getenv("SCENTSCAPE_REPO_ROOT", "/app")) / "ml" / "data" / "fra_elite_24k.json"
    
    if not seed_file.exists():
        print(f"Error: Seed file not found at {seed_file}")
        sys.exit(1)
        
    print(f"Using seed file: {seed_file}")
    
    # Initialize Neo4j and ingest
    try:
        # Check if running in Docker, if so modify URI to point to neo4j container
        uri = neo4j_uri
        if os.environ.get("RUNNING_IN_DOCKER") == "true":
             uri = "bolt://neo4j:7687"
        
        client = init_neo4j(uri, neo4j_user, neo4j_password)
        stats = ingest_fragrances_from_file(client, seed_file)
        print("Seeding complete!")
        # Clear global catalog cache to reflect new data
        try:
            from app.services.catalog import load_recommendation_catalog
            load_recommendation_catalog(force_reload=True)
            print("✓ Catalog cache flushed.")
        except ImportError:
            pass
        print(f"Stats: {stats}")
    except Exception as e:
        print(f"Seeding failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
