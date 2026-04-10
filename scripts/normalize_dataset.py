import csv
import json
import os
from pathlib import Path

def normalize_csv_to_json(csv_path: str, output_path: str):
    """Integrates CSV dataset into the ScentScape neural format."""
    print(f"Integrating dataset from {csv_path}...")
    
    normalized_records = []
    
    with open(csv_path, mode='r', encoding='ISO-8859-1') as f:
        # The dataset uses ';' as delimiter based on previous preview
        reader = csv.DictReader(f, delimiter=';')
        
        for row in reader:
            try:
                # 1. Identity & Metadata
                frag_id = row.get("Perfume", "").lower().replace(" ", "-")
                if not frag_id:
                    continue
                    
                # 2. Decimal Normalization (Convert '1,42' to 1.42)
                rating_raw = row.get("Rating Value", "0").replace(",", ".")
                try:
                    rating = float(rating_raw)
                except ValueError:
                    rating = 0.0
                    
                # 3. Note Tokenization
                # Format: "note1, note2" -> ["note1", "note2"]
                def split_notes(note_str):
                    if not note_str or note_str.lower() == "unknown":
                        return []
                    return [n.strip() for n in note_str.split(",") if n.strip()]

                # 4. Accord Positional Mapping
                accords = []
                for i in range(1, 6):
                    accord = row.get(f"mainaccord{i}")
                    if accord and accord.lower() != "unknown" and accord.strip():
                        accords.append(accord.strip())

                # 5. Build ScentScape Schema
                record = {
                    "id": f"frag_{frag_id}",
                    "name": row.get("Perfume", "Unknown"),
                    "brand": row.get("Brand", "Unknown"),
                    "year": int(row["Year"]) if row.get("Year") and row["Year"].isdigit() else None,
                    "gender_label": row.get("Gender", "Unisex"),
                    "rating_value": rating,
                    "rating_count": int(row["Rating Count"]) if row.get("Rating Count") and row["Rating Count"].isdigit() else 0,
                    "top_notes": split_notes(row.get("Top", "")),
                    "middle_notes": split_notes(row.get("Middle", "")),
                    "base_notes": split_notes(row.get("Base", "")),
                    "accords": accords,
                    "description": f"A sophisticated {accords[0] if accords else 'aromatic'} creation by {row.get('Brand', 'the house')}."
                }
                
                normalized_records.append(record)
                
            except Exception as e:
                # Log corruption but continue processing (ruthless production stance)
                print(f"Skipping corrupted record: {row.get('Perfume')} - {str(e)}")
                continue

    # Final Serialization
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(normalized_records, out, indent=2, ensure_ascii=False)
        
    print(f"Integration complete. {len(normalized_records)} records serialized to {output_path}")

if __name__ == "__main__":
    SOURCE_CSV = r"C:\Users\KIIT0001\Downloads\fra_cleaned.csv"
    TARGET_JSON = r"c:\Users\KIIT0001\Downloads\Telegram Desktop\Scentrix\ml\data\fra_elite_24k.json"
    
    normalize_csv_to_json(SOURCE_CSV, TARGET_JSON)
