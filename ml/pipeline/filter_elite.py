import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def filter_elite_dataset(
    input_path: Path, 
    output_path: Path, 
    min_reviews: int = 500,
    min_popularity: float = 60.0,
    min_rating: float = 3.6,
    min_views: int = 2000
):
    """Filters the fragrance dataset by performance metrics."""
    
    if not input_path.exists():
        logger.error(f"Input dataset not found: {input_path}")
        return
    
    logger.info(f"Loading dataset from {input_path}...")
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    initial_count = len(data)
    logger.info(f"Initial record count: {initial_count}")
    
    # Apply combined Elite-grade filters
    filtered = [
        r for r in data 
        if (r.get("review_count") or 0) >= min_reviews
        and (r.get("popularity_score") or 0) >= min_popularity
        and (r.get("rating") or 0) >= min_rating
        and (r.get("view_count") or 0) >= min_views
    ]
    
    final_count = len(filtered)
    removed_count = initial_count - final_count
    
    logger.info(f"Filtered record count: {final_count}")
    logger.info(f"Records removed: {removed_count}")
    
    # Save the elite dataset
    logger.info(f"Saving elite dataset to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*50)
    print("SCENTRIX ELITE DATASET RECOVERY REPORT")
    print("="*50)
    print(f"Source: {input_path.name}")
    print(f"Pool: {initial_count:,} items")
    print("-" * 50)
    print("GATE THRESHOLDS:")
    print(f"Review Count: >= {min_reviews}")
    print(f"Popularity:   >= {min_popularity}")
    print(f"Rating:       >= {min_rating}")
    print(f"Views:        >= {min_views}")
    print("-" * 50)
    print(f"Elite Subset: {final_count:,} items")
    print(f"Excluded: {removed_count:,} items")
    print(f"Output: {output_path}")
    print("="*50)

if __name__ == "__main__":
    input_file = Path("ml/data/scentrix_master.json")
    output_file = Path("ml/data/scentrix_elite_subset.json")
    filter_elite_dataset(input_file, output_file)
