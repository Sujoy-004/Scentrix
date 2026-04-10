import json
from collections import Counter

def slugify(text):
    if not text: return "None"
    return str(text).lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "").replace("+", "plus")

with open("ml/data/fra_elite_24k.json", "r") as f:
    data = json.load(f)
    
    new_ids = []
    for frag in data:
        name = frag.get("name", "unknown")
        brand = frag.get("brand", "unknown")
        year = frag.get("year", "0")
        new_id = f"frag_{slugify(name)}-{slugify(brand)}-{slugify(year)}"
        new_ids.append(new_id)
        
    id_counts = Counter(new_ids)
    duplicates = {id: count for id, count in id_counts.items() if count > 1}
    
    print("--- 10 Sample Remaining Duplicates ---")
    for i, (dupe_id, count) in enumerate(duplicates.items()):
        if i >= 10: break
        print(f"ID: {dupe_id} ({count} matches)")
        matches = [frag for frag, nid in zip(data, new_ids) if nid == dupe_id]
        for j, m in enumerate(matches):
            print(f"  Match {j+1}: Gender: {m.get('gender_label')}, Notes: {m.get('top_notes', [])[:2]}")
