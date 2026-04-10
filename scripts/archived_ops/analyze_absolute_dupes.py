import json
import hashlib
from collections import Counter

def calculate_id(f):
    # Use name, brand, gender, year AND notes
    name = f.get("name", "unknown")
    brand = f.get("brand", "unknown")
    gender = f.get("gender_label", "unisex")
    year = f.get("year", "0")
    notes = f.get("top_notes", []) + f.get("middle_notes", []) + f.get("base_notes", [])
    notes_str = "".join(sorted(notes))
    
    return f"{name}|{brand}|{gender}|{year}|{notes_str}"

with open("ml/data/fra_elite_24k.json", "r") as f:
    data = json.load(f)
    print(f"Total entries: {len(data)}")
    
    id_map = {}
    for i, frag in enumerate(data):
        id_str = calculate_id(frag)
        if id_str in id_map:
            id_map[id_str].append(frag)
        else:
            id_map[id_str] = [frag]
            
    duplicates = {k: v for k, v in id_map.items() if len(v) > 1}
    print(f"Number of groups with identical name, brand, year, gender, notes: {len(duplicates)}")
    
    # Check if they differ in description, ratings, accords?
    for k, v in duplicates.items():
        print(f"\nGroup: {k}")
        for i, frag in enumerate(v):
            print(f"  Match {i+1}: Rating: {frag.get('rating_value')}, Description Sample: {frag.get('description', '')[:50]}")
