"""Tasks module initialization."""

from app.tasks.recommend_tasks import (
    generate_user_embeddings_task,
    recommend_by_profile_task,
    recommend_by_text_task,
)

__all__ = [
    "recommend_by_text_task",
    "recommend_by_profile_task",
    "generate_user_embeddings_task",
]
