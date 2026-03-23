"""Tasks module initialization."""

from app.tasks.recommend_tasks import (
    recommend_by_text_task,
    recommend_by_profile_task,
    generate_user_embeddings_task,
)

__all__ = [
    "recommend_by_text_task",
    "recommend_by_profile_task",
    "generate_user_embeddings_task",
]
