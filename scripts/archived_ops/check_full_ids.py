import json
from collections import Counter

def slugify(text):
    if not text: return "None"
    return str(text).lower().replace(" ", "-").replace("(", "").replace(")", "").replace("'", "").replace("+", "plus")

with open("ml/data/fra_elite_24k.json", "r") as f:
    data = json.load(f)
    print(f"Total entries: {len(data)}")
    
    # Try generating new IDs with year and gender
    new_ids = []
    for frag in data:
        name = frag.get("name", "unknown")
        brand = frag.get("brand", "unknown")
        year = frag.get("year", "0")
        gender = frag.get("gender_label", "unisex")
        new_id = f"frag_{slugify(name)}-{slugify(brand)}-{slugify(gender)}-{slugify(year)}"
        new_ids.append(new_id)
        
    id_counts = Counter(new_ids)
    unique_ids = len(id_counts)
    print(f"Unique IDs generated with frag_{{name}}-{{brand}}-{{gender}}-{{year}}: {unique_ids}")
    
    if unique_ids < len(data):
        print(f"STILL not unique! Missing: {len(data) - unique_ids}")
        # One last scan for these persistent dupes
        duplicates = {id: count for id, count in id_counts.items() if count > 1}
        print("Sample final duplicates:")
        for i, (id, count) in enumerate(duplicates.items()):
            if i >= 5: break
            print(f"  {id}: {count} times")
    else:
        print("PERFECT! This scheme makes all 24,063 records unique.")
