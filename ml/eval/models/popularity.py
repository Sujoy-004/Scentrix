from typing import Optional


class PopularityBaseline:
    def __init__(self, data_path: str = "ml/data/scentrix_master_cleaned.json"):
        self.data_path = data_path
        self._item_ids = []
        self._scores: dict[str, float] = {}

    def _load_data(self):
        if self._scores:
            return
        import json
        import os
        if not os.path.exists(self.data_path):
            self._item_ids = []
            self._scores = {}
            return
        try:
            with open(self.data_path) as f:
                data = json.load(f)
            if not isinstance(data, list):
                self._item_ids = []
                self._scores = {}
                return
            scores: dict[str, float] = {}
            for item in data:
                fid = item.get("id", "")
                if not fid:
                    continue
                accords = item.get("accords", [])
                if isinstance(accords, list):
                    count = len(accords)
                else:
                    count = 1
                scores[fid] = float(count)
            self._scores = scores
            self._item_ids = sorted(scores.keys(), key=lambda x: -scores[x])
        except Exception as e:
            print(f"Warning: Could not load data from {self.data_path}: {e}")
            self._item_ids = []
            self._scores = {}

    def get_rankings(self, user_id: Optional[str] = None, k: Optional[int] = None) -> list[str]:
        self._load_data()
        items = self._item_ids
        if k is not None:
            return items[:k]
        return items.copy()