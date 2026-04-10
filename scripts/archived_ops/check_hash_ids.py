import json
import hashlib
from collections import Counter

def slugify(text):
    if not text: return "None"
    return str(text).lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "").replace("+", "plus")

def calculate_id(f):
    name = slugify(f.get("name", "unknown"))
    brand = slugify(f.get("brand", "unknown"))
    gender = slugify(f.get("gender_label", "unisex"))
    year = slugify(f.get("year", "0"))
    
    # Hash notes to differentiate near-identical records
    notes = f.get("top_notes", []) + f.get("middle_notes", []) + f.get("base_notes", [])
    notes_str = "".join(sorted(notes))
    notes_hash = hashlib.md5(notes_str.encode()).hexdigest()[:6]
    
    return f"frag_{name}-{brand}-{gender}-{year}-{notes_hash}"

with open("ml/data/fra_elite_24k.json", "r") as f:
    data = json.load(f)
    print(f"Total entries: {len(data)}")
    
    new_ids = [calculate_id(frag) for frag in data]
    id_counts = Counter(new_ids)
    unique_ids = len(id_counts)
    
    print(f"Unique IDs generated with Full Hash: {unique_ids}")
    
    if unique_ids < len(data):
        print(f"STILL not unique! Missing: {len(data) - unique_ids}")
        # Let's see these absolute duplicates
        duplicates = {id: count for id, count in id_counts.items() if count > 1}
        print("Sample final duplicates (likely true redundancies):")
        for i, (id, count) in enumerate(duplicates.items()):
            if i >= 5: break
            print(f"  {id}: {count} times")
    else:
        print("PERFECT! This scheme makes all 24,063 records unique.")
