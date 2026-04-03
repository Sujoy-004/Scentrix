import os
import sys
from pathlib import Path

# Add project root to path
# In Docker, project root is /app
sys.path.append(os.getenv("SCENTSCAPE_REPO_ROOT", "/app"))

from ml.graph import init_neo4j
from ml.pipeline.ingest import ingest_fragrances_from_file

def main():
    print("Starting data seeding process...")
    
    # Configuration from env
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")
    
    # Path to seed data
    # In Docker, it is at /app/ml/data/fra_elite_5k.json
    seed_file = Path(os.getenv("SCENTSCAPE_REPO_ROOT", "/app")) / "ml" / "data" / "fra_elite_5k.json"
    
    if not seed_file.exists():
        # Try fall back to full dataset if elite is missing
        seed_file = Path(os.getenv("SCENTSCAPE_REPO_ROOT", "/app")) / "ml" / "data" / "fra_cleaned_canonical.json"
        
    if not seed_file.exists():
        print(f"Error: Seed file not found at {seed_file}")
        sys.exit(1)
        
    print(f"Using seed file: {seed_file}")
    
    # Initialize Neo4j and ingest
    try:
        client = init_neo4j(neo4j_uri, neo4j_user, neo4j_password)
        stats = ingest_fragrances_from_file(client, seed_file)
        print("Seeding complete!")
        print(f"Stats: {stats}")
    except Exception as e:
        print(f"Seeding failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
