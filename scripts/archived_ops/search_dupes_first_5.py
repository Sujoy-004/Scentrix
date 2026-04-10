import json

with open("ml/data/fra_elite_24k.json", "r") as f:
    data = json.load(f)
    print("--- Searching for 1-million Paco Rabanne (First 5) ---")
    matches = [frag for frag in data if "1-million" in frag["name"].lower() and "paco-rabanne" in frag["brand"].lower()]
    for i, frag in enumerate(matches[:5]):
        print(f"Match {i+1}:")
        print(f"  Name: {frag.get('name')}")
        print(f"  Brand: {frag.get('brand')}")
        print(f"  Year: {frag.get('year')}")
        print(f"  ID: {frag.get('id')}")
        print(f"  Notes: {frag.get('top_notes', [])[:2]}...")
