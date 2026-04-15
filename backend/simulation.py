import httpx
import asyncio
import random
import uuid
import statistics

BASE_URL = "http://localhost:8000"

async def run_simulation(it_name, rating_logic):
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Create unique user per run
        email = f"test_{uuid.uuid4().hex[:6]}@scentrix.ai"
        password = "password123"
        
        reg_resp = await client.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password, "full_name": "Test Runner"})
        if reg_resp.status_code not in (200, 201):
            return {"Iteration": it_name, "Error": f"Reg Failed: {reg_resp.status_code} {reg_resp.text}"}
        
        token = reg_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Start Quiz Session
        start_resp = await client.post(f"{BASE_URL}/quiz/session/start", 
                                   json={"seed_count": 8, "candidate_pool_size": 100, "filters": {"exclude_seen": False}},
                                   headers=headers)
        
        if start_resp.status_code != 200:
            return {"Iteration": it_name, "Error": "Start Failed"}
        
        session_data = start_resp.json()
        session_id = session_data["session_id"]
        questions = session_data["seed_questions"]
        
        # 3. Submit 8 Responses based on logic
        for i, q in enumerate(questions):
            rating = rating_logic(i, q)
            await client.post(f"{BASE_URL}/quiz/session/{session_id}/responses", 
                          json={"fragrance_id": q["fragrance_id"], "rating_1_to_10": rating, "source": "simulation"},
                          headers=headers)
            
        # 4. Evaluate Session
        eval_resp = await client.post(f"{BASE_URL}/quiz/session/{session_id}/evaluate", json={"force": False}, headers=headers)
        eval_data = eval_resp.json()
        
        # 5. Get Fidelity (Personalized Recommendations)
        await asyncio.sleep(0.5)
        rec_resp = await client.get(f"{BASE_URL}/recommendations/personalized", headers=headers)
        recs = rec_resp.json()
        
        if isinstance(recs, list) and len(recs) > 0:
            avg_fidelity = sum(r.get("match_score", 0) for r in recs) / len(recs)
        else:
            avg_fidelity = 0.0
            
        return {
            "Iteration": it_name,
            "Conf. Score": round(eval_data.get("confidence_score", 0), 3),
            "Fidelity": f"{round(avg_fidelity, 1)}%",
            "Band": eval_data.get("confidence_band", "N/A"),
            "Ext. Required": eval_data.get("extension_required", False),
            "Stop Reason": eval_data.get("stop_reason", "N/A")
        }

async def main():
    logics = [
        ("Elite High (All 10s)", lambda i, q: 10.0),
        ("Deep Dislike (All 1s)", lambda i, q: 1.0),
        ("High Volatility (1, 10...)", lambda i, q: 10.0 if i % 2 == 0 else 1.0),
        ("Median (All 5s)", lambda i, q: 5.0),
        ("Random Uniform", lambda i, q: random.uniform(1, 10)),
        ("Linear Growth (1-8)", lambda i, q: float(i + 1)),
        ("High Affinity Niche", lambda i, q: random.uniform(8.5, 10.0)),
        ("Skeptical Critic", lambda i, q: random.uniform(2.5, 4.5)),
        ("Binary Polar", lambda i, q: random.choice([1.0, 10.0])),
        ("Steady Professional (7.5)", lambda i, q: 7.5),
        ("Bell Curve (Mean 5)", lambda i, q: max(1.0, min(10.0, random.gauss(5.0, 1.5)))),
        ("Descending Curve (10-3)", lambda i, q: float(10 - i)),
        ("Nuance Mode (4.5-5.5)", lambda i, q: random.uniform(4.5, 5.5)),
        ("Polar Reversal", lambda i, q: 9.0 if i < 4 else 2.0),
        ("Targeted Signal (8.4)", lambda i, q: 8.4)
    ]

    print("Starting 15-Iteration Adaptive Quiz Simulation...")
    tasks = [run_simulation(it_name, logic) for it_name, logic in logics]
    results = await asyncio.gather(*tasks)

    header = f"{'ITERATION':<28} | {'CONF.':<6} | {'FIDELITY':<8} | {'BAND':<8} | {'EXT?':<5} | {'STOP REASON'}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))
    for r in results:
        if "Error" in r:
            print(f"{r['Iteration']:<28} | ERROR: {r['Error']}")
            continue
        print(f"{r['Iteration']:<28} | {r['Conf. Score']:<6} | {r['Fidelity']:<8} | {r['Band']:<8} | {str(r['Ext. Required'])[0]:<5} | {r['Stop Reason']}")

if __name__ == "__main__":
    asyncio.run(main())
