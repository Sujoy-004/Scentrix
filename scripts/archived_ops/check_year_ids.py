import json
from collections import Counter

def slugify(text):
    if not text: return "None"
    return str(text).lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "").replace("+", "plus")

with open("ml/data/fra_elite_24k.json", "r") as f:
    data = json.load(f)
    print(f"Total entries: {len(data)}")
    
    # Try generating new IDs with year
    new_ids = []
    for frag in data:
        name = frag.get("name", "unknown")
        brand = frag.get("brand", "unknown")
        year = frag.get("year", "0")
        new_id = f"frag_{slugify(name)}-{slugify(brand)}-{slugify(year)}"
        new_ids.append(new_id)
        
    id_counts = Counter(new_ids)
    unique_ids = len(id_counts)
    print(f"Unique IDs generated with frag_{{name}}-{{brand}}-{{year}}: {unique_ids}")
    
    if unique_ids < len(data):
        print(f"STILL not unique! Missing: {len(data) - unique_ids}")
    else:
        print("PERFECT! Year inclusion makes all 24,063 records unique.")
