import requests
import random
import time

BASE_URL = "http://localhost:8000"

def simulate_user(i):
    username = f"user{i:02d}"
    email = f"user{i:02d}@gmail.com"
    password = "SecurePassword123!"
    full_name = f"Test User {i:02d}"

    print(f"\n--- Simulating {username} ---")

    # 1. Register
    try:
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "opt_in_training": True
        })
        if reg_resp.status_code == 409:
            print(f"User {email} already exists. Logging in...")
            login_resp = requests.post(f"{BASE_URL}/auth/login", json={
                "email": email,
                "password": password
            })
            tokens = login_resp.json()
        else:
            reg_resp.raise_for_status()
            tokens = reg_resp.json()
            print(f"Registered {username}.")
    except Exception as e:
        print(f"Auth failed for {username}: {e}")
        return

    access_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Start Quiz
    quiz_start = requests.post(f"{BASE_URL}/fragrances/quiz/session/start", json={
        "seed_count": 8,
        "candidate_pool_size": 100,
        "filters": {"exclude_seen": True}
    }, headers=headers)
    quiz_start.raise_for_status()
    session_data = quiz_start.json()
    session_id = session_data["session_id"]
    questions = session_data["seed_questions"]
    print(f"Started quiz session: {session_id}")

    # 3. Submit Responses (Random preference logic)
    # user01-05 like citrus/floral (high ratings for citrus, low for oud)
    # user06-10 like woody/oriental 
    # user11-20 are balanced/random
    for q in questions:
        f_id = q["fragrance_id"]
        accords = [a.lower() for a in q.get("accords", [])]
        
        rating = random.randint(1, 10)
        if i <= 5: # Citrus fans
            if any(c in accords for c in ["citrus", "lemon", "bergamot"]):
                rating = random.randint(8, 10)
            elif any(o in accords for o in ["oud", "leather", "smoky"]):
                rating = random.randint(1, 3)
        elif i <= 10: # Woody fans
            if any(w in accords for w in ["woody", "sandalwood", "cedar"]):
                rating = random.randint(8, 10)
            elif any(f in accords for f in ["floral", "rose"]):
                rating = random.randint(1, 4)

        resp = requests.post(f"{BASE_URL}/fragrances/quiz/session/{session_id}/responses", json={
            "fragrance_id": f_id,
            "rating_1_to_10": float(rating),
            "source": "quiz"
        }, headers=headers)
        resp.raise_for_status()
    
    print(f"Submitted 8 responses for {username}.")

    # 4. Finalize
    finalize = requests.post(f"{BASE_URL}/fragrances/quiz/session/{session_id}/finalize", headers=headers)
    finalize.raise_for_status()
    print(f"Finalized session for {username}.")

    # 5. Fetch Recommendations
    recs = requests.get(f"{BASE_URL}/recommendations/personalized", headers=headers)
    recs.raise_for_status()
    print(f"Fetched {len(recs.json())} recommendations for {username}.")

def main():
    for i in range(1, 21):
        try:
            simulate_user(i)
        except Exception as e:
            print(f"Error for user {i}: {e}")
        # Small sleep just to be safe, though limiter is off
        time.sleep(0.1)

if __name__ == "__main__":
    main()
