import pytest

from app.tasks.recommend_tasks import (
    _fragrance_feature_vector,
    _rank_by_profile,
    _split_train_val_test,
    generate_user_embeddings_task,
    recommend_by_text_task,
)

def test_generate_user_embeddings_task():
    """Test Celery task for generating user embeddings (synchronous execution)"""
    result = generate_user_embeddings_task.apply(args=[1])
    assert result.successful()
    assert result.result["status"] == "completed"
    assert result.result["user_id"] == 1
    assert "split" in result.result
    assert {"train", "val", "test"}.issubset(result.result["split"].keys())

def test_recommend_by_text_task():
    """Test Celery task for text recommendations"""
    result = recommend_by_text_task.apply(args=["test_job_123", "vanilla and leather", 5])
    assert result.successful()
    assert result.result["job_id"] == "test_job_123"
    assert result.result["status"] == "completed"
    assert "split" in result.result
    assert {"train", "val", "test"}.issubset(result.result["split"].keys())


def test_split_train_val_test_is_deterministic_and_total_preserved():
    rows = list(range(20))

    split_a = _split_train_val_test(rows, seed=42)
    split_b = _split_train_val_test(rows, seed=42)

    assert split_a == split_b
    assert len(split_a["train"]) + len(split_a["val"]) + len(split_a["test"]) == len(rows)


def test_split_train_val_test_keeps_all_three_partitions_for_small_non_trivial_input():
    rows = ["a", "b", "c"]
    split = _split_train_val_test(rows, seed=42)

    assert len(split["train"]) == 1
    assert len(split["val"]) == 1
    assert len(split["test"]) == 1


def test_rank_by_profile_excludes_already_rated_items():
    catalog = [
        {
            "id": "frag_a",
            "name": "Woody Spice",
            "brand": "House A",
            "description": "woody spicy cedar pepper",
            "top_notes": ["Pepper"],
            "middle_notes": ["Cedar"],
            "base_notes": ["Vetiver"],
            "accords": ["Woody", "Spicy"],
            "review_count": 120,
        },
        {
            "id": "frag_b",
            "name": "Fresh Citrus",
            "brand": "House B",
            "description": "fresh lemon bergamot aromatic",
            "top_notes": ["Lemon"],
            "middle_notes": ["Lavender"],
            "base_notes": ["Musk"],
            "accords": ["Citrus", "Fresh"],
            "review_count": 80,
        },
        {
            "id": "frag_c",
            "name": "Deep Woods",
            "brand": "House C",
            "description": "oud cedar patchouli smoky",
            "top_notes": ["Pepper"],
            "middle_notes": ["Oud"],
            "base_notes": ["Patchouli"],
            "accords": ["Woody", "Smoky"],
            "review_count": 200,
        },
    ]

    user_taste_vector = _fragrance_feature_vector(catalog[0])
    ranked = _rank_by_profile(
        catalog=catalog,
        user_taste_vector=user_taste_vector,
        rated_ids={"frag_a"},
        limit=5,
    )

    returned_ids = {row["id"] for row in ranked}
    assert "frag_a" not in returned_ids
    assert returned_ids
    assert all(row["similarity_score"] >= 0 for row in ranked)
