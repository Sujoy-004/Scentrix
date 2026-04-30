import requests
import json

BASE_URL = "http://localhost:8000"

# Sample inputs for Aquatic vs Leather
AQUATIC_INPUT = [
    {"fragrance_id": "1058", "rating": 2.0}, # Rate London (1058) low
    {"fragrance_id": "2054", "rating": 9.5}, # Rate known aquatic high
]

LEATHER_INPUT = [
    {"fragrance_id": "1058", "rating": 2.0}, 
    {"fragrance_id": "6021", "rating": 9.5}, # Rate known leather high
]

def audit():
    print("Testing Aquatic...")
    res1 = requests.post(f"{BASE_URL}/recommendations/guest", json={"ratings": AQUATIC_INPUT}).json()
    top1 = res1[0]['name'] if res1 else "None"
    
    print("Testing Leather...")
    res2 = requests.post(f"{BASE_URL}/recommendations/guest", json={"ratings": LEATHER_INPUT}).json()
    top2 = res2[0]['name'] if res2 else "None"
    
    print(f"Aquatic Top Match: {top1}")
    print(f"Leather Top Match: {top2}")
    
    if top1 != top2:
        print("SUCCESS: Diversity detected!")
    else:
        print("FAILURE: Matches are still identical.")

if __name__ == "__main__":
    audit()
