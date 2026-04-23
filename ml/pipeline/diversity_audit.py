"""
Olfactive Diversity Audit for Scentrix.
Analyzes the distribution of fragrances across olfactive kingdoms and identifying data gaps.
"""

import json
import argparse
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any

def audit_dataset(dataset_path: Path):
    if not dataset_path.exists():
        print(f"Error: Dataset not found at {dataset_path}")
        return

    print(f"--- Olfactive Diversity Audit: {dataset_path.name} ---")
    
    with open(dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total = len(data)
    print(f"Total Fragrances: {total}")

    # 1. Family Distribution
    families = []
    for row in data:
        f = row.get('family')
        if not f and row.get('accords'):
            f = row.get('accords')[0]
        families.append(f or 'Unknown')
        
    family_counts = Counter(families)
    
    print("\n[Family Distribution]")
    for family, count in family_counts.most_common():
        percentage = (count / total) * 100
        print(f"{family:20} : {count:6} ({percentage:5.1f}%)")

    # 2. Note Coverage
    all_notes = []
    for row in data:
        all_notes.extend(row.get('top_notes', []))
        all_notes.extend(row.get('middle_notes', []))
        all_notes.extend(row.get('base_notes', []))
    
    note_counts = Counter(all_notes)
    print(f"\nUnique Notes Found: {len(note_counts)}")
    print("Top 10 Notes:")
    for note, count in note_counts.most_common(10):
        print(f"  - {note}: {count}")

    # 3. Data Deserts (Underrepresented families)
    threshold = total * 0.01  # Less than 1% representation
    deserts = [f for f, c in family_counts.items() if c < threshold and f != 'Unknown']
    
    if deserts:
        print("\n[Warning: Potential Data Deserts]")
        print("The following families may be under-represented (<1%):")
        for f in deserts:
            print(f"  - {f} ({family_counts[f]} items)")
    else:
        print("\n[Health Check: Kingdoms are well-balanced]")

    # 4. Neural Ready Check
    avg_notes = sum(len(row.get('top_notes', [])) + len(row.get('middle_notes', [])) + len(row.get('base_notes', [])) for row in data) / total
    neural_ready = sum(1 for row in data if row.get('description') and len(row.get('top_notes', [])) > 0)
    nr_pct = (neural_ready / total) * 100
    
    print(f"\nAverage Notes per Fragrance: {avg_notes:.1f}")
    print(f"Neural-Ready Coverage: {neural_ready} ({nr_pct:.1f}%)")
    
    if nr_pct < 80:
        print("Warning: Low neural-ready coverage. Enrichment recommended.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("ml/data/fra_elite_24k.json"))
    args = parser.parse_args()
    
    audit_dataset(args.dataset)
