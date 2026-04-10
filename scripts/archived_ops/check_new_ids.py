import json
from collections import Counter

def slugify(text):
    return text.lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "")

with open("ml/data/fra_elite_24k.json", "r") as f:
    data = json.load(f)
    print(f"Total entries: {len(data)}")
    
    # Try generating new IDs
    new_ids = []
    for frag in data:
        name = frag.get("name", "unknown")
        brand = frag.get("brand", "unknown")
        new_id = f"frag_{slugify(name)}-{slugify(brand)}"
        new_ids.append(new_id)
        
    id_counts = Counter(new_ids)
    unique_ids = len(id_counts)
    print(f"Unique IDs generated with frag_{{name}}-{{brand}}: {unique_ids}")
    
    if unique_ids < len(data):
        print(f"Still not unique! Remainder: {len(data) - unique_ids}")
        duplicates = {id: count for id, count in id_counts.items() if count > 1}
        print("Sample remaining duplicates:")
        for i, (id, count) in enumerate(duplicates.items()):
            if i >= 5: break
            print(f"  {id}: {count} times")
    else:
        print("PERFECT! This ID scheme makes all 24,063 records unique.")
