import json
from collections import Counter

with open("ml/data/fra_elite_24k.json", "r") as f:
    data = json.load(f)
    print(f"Total entries in JSON: {len(data)}")
    
    ids = [frag["id"] for frag in data]
    id_counts = Counter(ids)
    
    duplicates = {id: count for id, count in id_counts.items() if count > 1}
    print(f"Number of duplicate IDs: {len(duplicates)}")
    
    total_dupes = sum(count - 1 for count in duplicates.values())
    print(f"Total redundant entries due to ID duplication: {total_dupes}")
    
    # Let's see some duplicates
    if duplicates:
        print("Sample Duplicates:")
        for i, (id, count) in enumerate(duplicates.items()):
            if i >= 5: break
            print(f"  {id}: {count} times")
            
    # Maybe names are unique but IDs are not? 
    names = [frag["name"] for frag in data]
    name_counts = Counter(names)
    unique_names = len(name_counts)
    print(f"Unique Names: {unique_names}")
