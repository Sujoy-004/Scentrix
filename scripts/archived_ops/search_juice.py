import json

with open("ml/data/fra_elite_24k.json", "r") as f:
    data = json.load(f)
    print("--- Searching for Juice Commodity ---")
    matches = [frag for frag in data if "juice" in frag["name"].lower() and "commodity" in frag["brand"].lower()]
    for i, frag in enumerate(matches):
        print(f"Match {i+1}:")
        print(f"  Name: {frag.get('name')}")
        print(f"  Brand: {frag.get('brand')}")
        print(f"  Year: {frag.get('year')}")
        print(f"  Gender: {frag.get('gender_label')}")
        print(f"  Notes: {frag.get('top_notes', [])[:2]}")
