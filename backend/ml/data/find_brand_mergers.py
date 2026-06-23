import json
from pathlib import Path

def find_brand_mergers():
    # Requires fra_elite_24k.json (removed from repo; regenerate or restore from backup)
    data_path = Path("fra_elite_24k.json")
    
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    brands = sorted(list(set([d.get("brand", "") for d in data if d.get("brand")])))
    
    mergers = []
    
    # Strategy 1: Acronym detection
    for b1 in brands:
        if len(b1) <= 4: # Short brands (YSL, D&G, HFC)
            acronym = b1.replace("-", "").replace("&", "").lower()
            for b2 in brands:
                if b1 == b2: continue
                # Check if b2's initials match b1
                initials = "".join([word[0] for word in b2.split("-") if word]).lower()
                if initials == acronym:
                    mergers.append((b1, b2, "Acronym match"))

    # Strategy 2: Partial name matching (e.g., "dior" in "christian-dior")
    for b1 in brands:
        for b2 in brands:
            if b1 == b2: continue
            if len(b1) > 3 and b1 in b2:
                # Flag if one is a subset of the other
                mergers.append((b1, b2, "Partial match"))

    # Strategy 3: Hyphenation variants
    for b1 in brands:
        b1_clean = b1.replace("-", "")
        for b2 in brands:
            if b1 == b2: continue
            if b1_clean == b2.replace("-", ""):
                mergers.append((b1, b2, "Hyphenation variant"))

    print(f"Total brands checked: {len(brands)}")
    print("\n--- POTENTIAL MERGERS FOUND ---")
    for b1, b2, reason in mergers[:20]: # Show first 20
        print(f"[{reason}] {b1} <--> {b2}")

if __name__ == "__main__":
    find_brand_mergers()
