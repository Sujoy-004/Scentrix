import random
from typing import List, Optional
import json
import os


class RandomBaseline:
    def __init__(self, data_path: str = "ml/data/scentrix_master_cleaned.json"):
        self.data_path = data_path
        self._item_ids: list[str] = []

    def _load_item_ids(self):
        if self._item_ids:
            return
        if not os.path.exists(self.data_path):
            self._item_ids = []
            return
        try:
            with open(self.data_path) as f:
                data = json.load(f)
            if isinstance(data, list):
                ids = []
                for item in data:
                    fid = item.get("id", "")
                    if fid:
                        ids.append(str(fid))
                # Deduplicate (each fragrance appears once in catalog)
                self._item_ids = list(dict.fromkeys(ids))
            else:
                self._item_ids = []
        except Exception as e:
            print(f"Warning: Could not load item IDs from {self.data_path}: {e}")
            self._item_ids = []

    def get_rankings(self, user_id: Optional[str] = None, k: Optional[int] = None) -> list[str]:
        self._load_item_ids()
        shuffled = self._item_ids.copy()
        random.shuffle(shuffled)
        if k is not None:
            return shuffled[:k]
        return shuffled