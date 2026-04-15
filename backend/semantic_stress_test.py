import asyncio
import httpx
import time
import sys
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000"

QUERIES = [
    "Metallic rose in a cold rain",
    "Burnt rubber and gasoline jasmine",
    "Damp basement earth",
    "Hot asphalt and ozone",
    "Old library books and dry vanilla",
    "Frozen smoke",
    "Sweaty citrus",
    "Powdery leather",
    "Salty caramel wood",
    "Medicinal honey",
    "Sacrificial church incense with cold stone",
    "Rotten fruit and sweet decay",
    "Wet forest floor after a storm",
    "Animalic honeycomb",
    "Tobacco leaves drying in a humid barn",
    "Skin scent that smells like nothing",
    "Solar white floral",
    "Boozy velvet dark chocolate",
    "Green chili and ginger spice",
    "Lavender fields in a thunderstorm"
]

async def poll_job_status(client: httpx.AsyncClient, job_id: str):
    """Wait for the neural synthesis to complete."""
    for _ in range(30): # 30 second timeout
        resp = await client.get(f"{BASE_URL}/fragrances/recommend/{job_id}")
        if resp.status_code != 200:
            return {"status": "failed", "error": f"Poll Failed: {resp.status_code} {resp.text}"}
        
        data = resp.json()
        if data.get("status") == "completed":
            return {"status": "completed", "fragrances": data.get("fragrances", [])}
        elif data.get("status") in {"failed", "timed_out"}:
            return {"status": "failed", "error": data.get("message") or data.get("error")}
        
        await asyncio.sleep(1)
    return {"status": "failed", "error": "Timeout"}

async def test_semantic_query(it: int, query: str):
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Submit the semantic job
        submit_resp = await client.post(f"{BASE_URL}/fragrances/recommend/text", 
                                       json={"query": query, "limit": 1})
        if submit_resp.status_code != 200:
            return {"Query": query, "Result": "Submit Failed", "Error": f"{submit_resp.status_code} {submit_resp.text}"}
        
        job_id = submit_resp.json().get("job_id")
        
        # 2. Poll for completion
        outcome = await poll_job_status(client, job_id)
        
        if outcome["status"] == "completed" and outcome["fragrances"]:
            top = outcome["fragrances"][0]
            return {
                "Query": query,
                "Match": f"{top.get('name')} ({top.get('brand')})",
                "Fidelity": f"{top.get('match_score') or top.get('similarity_score') or 0:.1f}%",
                "Notes": ", ".join(top.get("top_notes", [])[:2])
            }
        else:
            return {"Query": query, "Match": "No Result", "Error": outcome.get("error", "Unknown")}

async def main():
    print(f"\nLaunching Semantic Audit for 20 Queries...")
    print(f"Server: {BASE_URL}")
    print("-" * 100)
    
    tasks = [test_semantic_query(i, q) for i, q in enumerate(QUERIES)]
    results = await asyncio.gather(*tasks)
    
    print("\n" + "="*110)
    print(f"{'Query Search Profile':<45} | {'Top Match (Fragrance)':<35} | {'Fidelity':<10} | {'Primary Note'}")
    print("-" * 110)
    for res in results:
        if "Error" in res:
            print(f"{res['Query']:<45} | ERROR: {res['Error'][:30]:<35} | {'N/A':<10} | N/A")
        else:
            print(f"{res['Query']:<45} | {res['Match']:<35} | {res['Fidelity']:<10} | {res['Notes']}")
    print("="*110 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
