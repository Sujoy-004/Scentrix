import asyncio
import httpx
import random
import time
from typing import List, Dict, Any

BASE_URL = "http://localhost:8000"

async def run_simulation(it_num: int, profile_name: str, rating_strategy: str):
    it_name = f"Run_{it_num:02d}_{profile_name}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Register a unique test user
        email = f"test_{it_num}_{int(time.time())}@scentrix.ai"
        password = "password123"
        
        reg_resp = await client.post(f"{BASE_URL}/auth/register", json={"email": email, "password": password, "full_name": profile_name})
        if reg_resp.status_code not in (200, 201):
            return {"Iteration": it_name, "Strategy": rating_strategy, "Error": f"Reg Failed: {reg_resp.text}"}
        
        token = reg_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Start Quiz Session
        init_resp = await client.post(f"{BASE_URL}/quiz/session/start", 
                                     headers=headers,
                                     json={"min_core_questions": 8, "use_neural_vibe": True})
        if init_resp.status_code != 200:
            return {"Iteration": it_name, "Strategy": rating_strategy, "Error": f"Quiz Start Failed: {init_resp.status_code} {init_resp.text}"}
        
        session_data = init_resp.json()
        session_id = session_data["session_id"]
        questions = session_data["seed_questions"]

        # 3. Simulate Ratings
        for i, q in enumerate(questions):
            fid = q["fragrance_id"]
            
            # Rating logic based on strategy
            if rating_strategy == "Max":
                rating = 10.0
            elif rating_strategy == "Min":
                rating = 1.0
            elif rating_strategy == "Gaussian":
                rating = max(1.0, min(10.0, random.gauss(5.5, 1.5)))
            elif rating_strategy == "Polar":
                rating = 10.0 if i % 2 == 0 else 1.0
            elif rating_strategy == "Gradual":
                rating = min(10.0, 3.0 + (i * 0.8))
            else:
                rating = random.uniform(1.0, 10.0)

            await client.post(f"{BASE_URL}/quiz/session/{session_id}/responses", 
                              headers=headers,
                              json={"fragrance_id": fid, "rating_1_to_10": rating})

        # 4. Evaluate and Finalize
        eval_resp = await client.post(f"{BASE_URL}/quiz/session/{session_id}/evaluate", headers=headers)
        eval_data = eval_resp.json()
        
        # Explicitly Finalize (The bridge fix)
        await client.post(f"{BASE_URL}/quiz/session/{session_id}/finalize", headers=headers)

        # 5. Fetch Recommendations (The Fidelity check)
        rec_resp = await client.get(f"{BASE_URL}/recommendations/personalized", headers=headers)
        recs = rec_resp.json()
        
        fidelity = 0.0
        if recs and len(recs) > 0:
            match_scores = [r.get("match_score", 0) for r in recs if "match_score" in r]
            if match_scores:
                fidelity = sum(match_scores) / len(match_scores)

        return {
            "Iteration": it_name,
            "Strategy": rating_strategy,
            "Conf_Score": eval_data.get("confidence_score"),
            "Band": eval_data.get("confidence_band"),
            "Fidelity": f"{fidelity:.1f}%",
            "Reason": eval_data.get("stop_reason", "None")
        }

async def main():
    strategies = [
        (1, "The Aristocrat", "Max"), (2, "The Critic", "Min"), (3, "The Chaos", "Random"),
        (4, "The Balanced", "Gaussian"), (5, "The Bipolar", "Polar"), (6, "The Evolver", "Gradual"),
        (7, "The Consistent", "Gaussian"), (8, "The Skeptic", "Min"), (9, "The Enthusiast", "Max"),
        (10, "The Noise", "Random"), (11, "The Anchor", "Gaussian"), (12, "The Switcher", "Polar"),
        (13, "The Ascender", "Gradual"), (14, "The Descender", "Min"), (15, "The Peak", "Max"),
        (16, "The Valley", "Min"), (17, "The Plateau", "Gaussian"), (18, "The Pulse", "Polar"),
        (19, "The Drift", "Gradual"), (20, "The Vector", "Random")
    ]
    
    results = []
    for it, name, strat in strategies:
        print(f"Processing Profile: {name} ({strat})...")
        res = await run_simulation(it, name, strat)
        results.append(res)
    
    print("\n" + "="*80)
    print(f"{'Iteration':<30} | {'Strategy':<10} | {'Conf':<5} | {'Band':<6} | {'Fidelity':<8} | {'Reason'}")
    print("-" * 80)
    for res in results:
        if "Error" in res:
            print(f"{res['Iteration']:<30} | ERROR: {res['Error']}")
        else:
            conf = res.get('Conf_Score') if res.get('Conf_Score') is not None else "N/A"
            band = res.get('Band') if res.get('Band') is not None else "N/A"
            print(f"{res['Iteration']:<30} | {res['Strategy']:<10} | {conf:<5} | {band:<6} | {res['Fidelity']:<8} | {res['Reason']}")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
