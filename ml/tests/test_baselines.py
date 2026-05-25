"""Tests for baseline ranking models: PopularityBaseline (accord-count) and RandomBaseline (uniform shuffle)."""
import json
import random

import pytest

from ml.eval.models.popularity import PopularityBaseline
from ml.eval.models.random_baseline import RandomBaseline

DATA_PATH = "ml/data/scentrix_master_cleaned.json"


# ---------------------------------------------------------------------------
# EVAL-04: PopularityBaseline
# ---------------------------------------------------------------------------


class TestPopularityBaseline:
    """PopularityBaseline ranks items by accord count (complexity proxy)."""

    def _load_item_scores(self):
        """Helper: return {id: accord_count} from the real data file."""
        with open(DATA_PATH) as f:
            data = json.load(f)
        scores = {}
        for item in data:
            fid = item.get("id", "")
            if not fid:
                continue
            accords = item.get("accords", [])
            scores[fid] = float(len(accords) if isinstance(accords, list) else 1)
        return scores

    def test_rankings_sorted_by_accord_count_descending(self):
        """Returned rankings are in descending order of accord count."""
        expected_scores = self._load_item_scores()
        baseline = PopularityBaseline(DATA_PATH)
        rankings = baseline.get_rankings()

        for i in range(len(rankings) - 1):
            a, b = rankings[i], rankings[i + 1]
            assert expected_scores[a] >= expected_scores[b], (
                f"Rank {i} ({a}: {expected_scores[a]} accords) "
                f"< rank {i + 1} ({b}: {expected_scores[b]} accords)"
            )

    def test_rankings_include_all_items(self):
        """Every item with a valid id appears in the rankings exactly once."""
        with open(DATA_PATH) as f:
            data = json.load(f)
        all_ids = {item["id"] for item in data if item.get("id")}
        baseline = PopularityBaseline(DATA_PATH)
        rankings = baseline.get_rankings()

        assert len(rankings) == len(all_ids)
        assert set(rankings) == all_ids, (
            f"Missing from rankings: {all_ids - set(rankings)}"
        )

    def test_k_truncation_returns_first_k(self):
        """When k is specified, only the first k ranked items are returned."""
        baseline = PopularityBaseline(DATA_PATH)
        full = baseline.get_rankings()
        truncated = baseline.get_rankings(k=5)
        assert len(truncated) == 5
        assert truncated == full[:5]

    def test_k_greater_than_total_returns_all(self):
        """k larger than total item count returns all items."""
        baseline = PopularityBaseline(DATA_PATH)
        rankings = baseline.get_rankings(k=99999)
        assert len(rankings) == len(baseline.get_rankings())

    def test_user_id_is_accepted_but_ignored(self):
        """The user_id parameter is accepted (API compatibility) but doesn't change results."""
        baseline = PopularityBaseline(DATA_PATH)
        default = baseline.get_rankings()
        with_user = baseline.get_rankings(user_id="test_user_123")
        assert with_user == default

    def test_missing_data_file_returns_empty_list(self, tmp_path):
        """When the data file does not exist, get_rankings returns [].

        The implementation silently returns an empty list (logged as a warning).
        """
        missing = tmp_path / "nonexistent.json"
        baseline = PopularityBaseline(str(missing))
        assert baseline.get_rankings() == []

    def test_malformed_json_returns_empty_list(self, tmp_path):
        """Invalid JSON content produces an empty rankings list gracefully."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json at all")
        baseline = PopularityBaseline(str(bad_file))
        assert baseline.get_rankings() == []

    def test_non_list_json_returns_empty_list(self, tmp_path):
        """JSON that is valid but not a list (e.g. a dict) returns empty list."""
        obj_file = tmp_path / "obj.json"
        obj_file.write_text('{"key": "value"}')
        baseline = PopularityBaseline(str(obj_file))
        assert baseline.get_rankings() == []

    def test_items_with_zero_accords_at_end(self, tmp_path):
        """Items with no accords (empty or missing key) score 0 and sort to the end."""
        test_data = [
            {"id": "item_a", "accords": ["Citrus", "Woody"]},
            {"id": "item_b", "accords": []},
            {"id": "item_c"},  # no "accords" key → defaults to []
            {"id": "item_d", "accords": ["Floral", "Fresh", "Sweet"]},
        ]
        data_file = tmp_path / "test_popularity.json"
        with open(data_file, "w") as f:
            json.dump(test_data, f)

        baseline = PopularityBaseline(str(data_file))
        rankings = baseline.get_rankings()
        # item_d (3 accords) first, item_a (2 accords) second, then item_b/item_c (0 each)
        assert rankings[0] == "item_d", f"Expected item_d first, got {rankings[0]}"
        assert rankings[1] == "item_a", f"Expected item_a second, got {rankings[1]}"
        assert rankings[2] == "item_b", f"Expected item_b third, got {rankings[2]}"
        assert rankings[3] == "item_c", f"Expected item_c fourth, got {rankings[3]}"

    def test_ties_are_grouped_by_score(self, tmp_path):
        """Items with the same accord count appear in a contiguous block (tie order is insertion-order, not specified)."""
        test_data = [
            {"id": "z_item", "accords": ["A", "B"]},
            {"id": "a_item", "accords": ["A", "B"]},
            {"id": "m_item", "accords": ["A", "B", "C"]},
        ]
        data_file = tmp_path / "test_pop_alpha.json"
        with open(data_file, "w") as f:
            json.dump(test_data, f)

        baseline = PopularityBaseline(str(data_file))
        rankings = baseline.get_rankings()
        # m_item (3) first, then z_item + a_item (2 each) in whatever order
        assert rankings[0] == "m_item", f"Expected m_item (3 accords) first, got {rankings[0]}"
        # The two items with score 2 should be in positions 1 and 2
        score2 = {"z_item", "a_item"}
        assert rankings[1] in score2
        assert rankings[2] in score2
        assert rankings[1] != rankings[2]


# ---------------------------------------------------------------------------
# EVAL-05: RandomBaseline
# ---------------------------------------------------------------------------


class TestRandomBaseline:
    """RandomBaseline returns uniformly random shuffles of fragrance IDs."""

    def test_returns_permutation_of_all_ids(self):
        """The returned list contains exactly the same set of ids as the data file."""
        with open(DATA_PATH) as f:
            data = json.load(f)
        all_ids = {item["id"] for item in data if item.get("id")}

        baseline = RandomBaseline(DATA_PATH)
        rankings = baseline.get_rankings()

        assert len(rankings) == len(all_ids)
        assert set(rankings) == all_ids

    def test_successive_calls_produce_different_orders(self):
        """Two consecutive calls produce different orderings (random shuffle).

        With 4559 items the probability of identical order is astronomically small.
        """
        baseline = RandomBaseline(DATA_PATH)
        r1 = baseline.get_rankings()
        r2 = baseline.get_rankings()
        assert r1 != r2, "Two random shuffles produced identical order (extremely unlikely)"

    def test_k_truncation(self):
        """k parameter limits the number of returned items."""
        with open(DATA_PATH) as f:
            data = json.load(f)
        all_ids = {item["id"] for item in data if item.get("id")}

        baseline = RandomBaseline(DATA_PATH)
        truncated = baseline.get_rankings(k=10)
        assert len(truncated) == 10
        for item in truncated:
            assert item in all_ids, f"Unexpected id {item} not in data"

    def test_missing_data_file_returns_empty_list(self, tmp_path):
        """When the data file does not exist, get_rankings returns []."""
        missing = tmp_path / "nonexistent.json"
        baseline = RandomBaseline(str(missing))
        assert baseline.get_rankings() == []

    def test_malformed_json_returns_empty_list(self, tmp_path):
        """Invalid JSON content produces an empty list gracefully."""
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{{{broken json")
        baseline = RandomBaseline(str(bad_file))
        assert baseline.get_rankings() == []

    def test_non_list_json_returns_empty_list(self, tmp_path):
        """Valid JSON that is not a list (e.g. a dict) returns empty list."""
        obj_file = tmp_path / "obj.json"
        obj_file.write_text('{"hello": "world"}')
        baseline = RandomBaseline(str(obj_file))
        assert baseline.get_rankings() == []

    def test_every_returned_id_is_string(self):
        """All items in the rankings list are strings."""
        baseline = RandomBaseline(DATA_PATH)
        rankings = baseline.get_rankings(k=50)
        for item in rankings:
            assert isinstance(item, str), f"Expected str, got {type(item)}: {item}"

    def test_user_id_accepted_but_ignored(self):
        """user_id parameter is accepted but does not change the result shape."""
        baseline = RandomBaseline(DATA_PATH)
        with_user = baseline.get_rankings(user_id="anyone")
        without_user = baseline.get_rankings()
        # Both should have same length and same set of ids
        assert len(with_user) == len(without_user)
        assert set(with_user) == set(without_user)
