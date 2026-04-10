import os
import json
import time
import random
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

REVIEW_TEMPLATES = [
    "A cinematic masterpiece. The opening is fresh, but the dry down is pure silent luxury.",
    "The AI nailed the woody resonance. This is my new signature pulse.",
    "An ethereal olfactory profile. It feels like a second skin of pure elegance.",
    "Breathtakingly sophisticated. The notes transition like a slow-burn film score.",
    "Minimalist yet profound. This is the definition of understated opulence.",
    "A DNA match for my soul. The leather accords are incredibly realistic.",
    "Pure sensory indulgence. One of the best captures in the Elite 24k set.",
    "The sillage is whispers of gold. Truly 'Quiet Luxury' in a bottle."
]
REVIEWERS = ["Elena R.", "Marcus C.", "Julian V.", "Sophia L.", "Xavier M.", "Amara J."]

def patch_social_proof():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USERNAME", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "neo4j_password")

    print(f"--- SOCIAL PROOF SYNTHESIS: PATCHING 24,063 NODES ---")
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    
    with driver.session() as session:
        # Get all Fragrance IDs that lack reviews
        res = session.run("MATCH (f:Fragrance) WHERE f.review_sample IS NULL RETURN f.id as id")
        ids = [r["id"] for r in res]
        print(f"Found {len(ids)} nodes to patch.")

        batch_size = 200
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_data = []
            for bid in batch_ids:
                batch_data.append({
                    "id": bid,
                    "review": random.choice(REVIEW_TEMPLATES),
                    "reviewer": random.choice(REVIEWERS)
                })
            
            session.run("""
            UNWIND $batch as item
            MATCH (f:Fragrance {id: item.id})
            SET f.review_sample = item.review,
                f.reviewer_sample = item.reviewer,
                f.updated_at = $ts
            """, {"batch": batch_data, "ts": int(time.time() * 1000)})
            
            if (i // batch_size) % 10 == 0:
                print(f"Patched {min(i+batch_size, len(ids))} nodes...")

    print("Social Proof Synthesis Complete.")
    driver.close()

if __name__ == "__main__":
    patch_social_proof()
