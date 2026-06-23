import json
from collections import Counter
from pathlib import Path

def generate_note_map():
    # Requires fra_elite_24k.json (removed from repo; regenerate or restore from backup)
    data_path = Path("fra_elite_24k.json")
    map_output = Path("note_map.json")
    
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Get frequency of all notes
    all_notes = []
    for d in data:
        all_notes.extend(d.get("top_notes", []) or [])
        all_notes.extend(d.get("middle_notes", []) or [])
        all_notes.extend(d.get("base_notes", []) or [])
        
    note_counts = Counter(all_notes)
    
    # 1. Define Pillars: Top 200 most frequent notes
    pillars = [n for n, count in note_counts.most_common(200)]
    variants = [n for n in note_counts.keys() if n not in pillars]
    
    note_map = {}
    
    # 2. Map Variants to Pillars using substring matching
    # We sort pillars by length (descending) to match "Italian Lemon" before "Lemon"
    sorted_pillars = sorted(pillars, key=len, reverse=True)
    
    for variant in variants:
        matched = False
        v_low = variant.lower()
        for pillar in sorted_pillars:
            if pillar.lower() in v_low:
                note_map[variant] = pillar
                matched = True
                break
        if not matched:
            # If no pillar match, it remains unique or could be flagged for manual review
            note_map[variant] = "Other" 

    # Save the map
    result = {
        "pillars_count": len(pillars),
        "variants_mapped": len(note_map),
        "mapping": note_map
    }
    
    with open(map_output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        
    print(f"Pillars identified: {len(pillars)}")
    print(f"Variants mapped: {len(note_map)}")
    print(f"Map saved to: {map_output}")

if __name__ == "__main__":
    generate_note_map()
