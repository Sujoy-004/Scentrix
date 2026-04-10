import json

with open("ml/data/fra_elite_24k.json", "r") as f:
    data = json.load(f)
    print(f"Total records in JSON: {len(data)}")
    
    hyphen_count = sum(1 for d in data if "-" in d["id"])
    no_hyphen_count = sum(1 for d in data if "-" not in d["id"])
    
    print(f"IDs with Hyphens: {hyphen_count}")
    print(f"IDs without Hyphens: {no_hyphen_count}")
    
    if len(data) > 0:
        print(f"Sample First ID: {data[0]['id']}")
        print(f"Sample Last ID: {data[-1]['id']}")
