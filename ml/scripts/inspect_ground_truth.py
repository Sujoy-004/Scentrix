"""Ground truth size distribution across all cold items."""
import json
from pathlib import Path

data_path = "ml/data/scentrix_master_cleaned.json"

with open(data_path) as f:
    all_items = json.load(f)

item_map = {}
for item in all_items:
    fid = item.get("id", "")
    top = {str(n).lower() for n in (item.get("top_notes") or []) if n}
    mid = {str(n).lower() for n in (item.get("middle_notes") or []) if n}
    base = {str(n).lower() for n in (item.get("base_notes") or []) if n}
    raw_accords = [str(a).lower() for a in (item.get("accords") or []) if a]
    item_map[fid] = {
        "all_notes": top | mid | base,
        "primary_accord": raw_accords[0] if raw_accords else "Unknown",
    }

split_file = Path("archive/research/evaluation-runs/20260526_035624/splits/cold_items.csv")
with open(split_file) as f:
    cold_ids = [line.split(",")[0].strip() for line in f.readlines()[1:] if line.strip()]

cold_ids = [cid for cid in cold_ids if cid in item_map]

bins = {0: 0, "1-10": 0, "11-50": 0, "51+": 0}
sizes = []

for cid in cold_ids:
    ci = item_map[cid]
    cold_notes = ci["all_notes"]
    cold_primary = ci["primary_accord"]

    count = 0
    for oid, oi in item_map.items():
        if oid == cid:
            continue
        if oi["primary_accord"] != cold_primary:
            continue
        union = cold_notes | oi["all_notes"]
        jaccard = len(cold_notes & oi["all_notes"]) / len(union) if union else 0.0
        if jaccard > 0.20:
            count += 1

    sizes.append(count)
    if count == 0:
        bins[0] += 1
    elif count <= 10:
        bins["1-10"] += 1
    elif count <= 50:
        bins["11-50"] += 1
    else:
        bins["51+"] += 1

print(f"Total cold items: {len(cold_ids)}")
print(f"  Count with 0:     {bins[0]:>4}")
print(f"  Count with 1-10:  {bins['1-10']:>4}")
print(f"  Count with 11-50: {bins['11-50']:>4}")
print(f"  Count with 51+:   {bins['51+']:>4}")
print(f"  Min size: {min(sizes)}")
print(f"  Max size: {max(sizes)}")
print(f"  Avg size: {sum(sizes) / len(sizes):.1f}")
print(f"  Median size: {sorted(sizes)[len(sizes)//2]}")
