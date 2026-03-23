"""T2.6: Celery async task configuration.

Configures Celery for async recommendation job processing, including:
- Recommendation inference (GraphSAGE + Sentence-BERT)
- Ranking pipeline (BPR personalization)
- Result caching (Redis, 24h TTL per user)
"""

import os
from celery import Celery


# Configure Celery
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend_url = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "scentscape",
    broker=broker_url,
    backend=result_backend_url,
)

celery_app.conf.update(
    # Task configuration
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Routing
    task_routes={
        "app.tasks.recommend_by_text": {"queue": "recommendations"},
        "app.tasks.recommend_by_profile": {"queue": "recommendations"},
        "app.tasks.generate_user_embeddings": {"queue": "ml"},
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    
    # Result settings
    result_expires=86400,  # 24 hours
    result_extended=True,
    
    # Beat schedule (if using periodic tasks)
    beat_schedule={
        # Can add periodic tasks here for weekly retraining
    },
)


# Import tasks to register them with Celery
from app.tasks import recommend_tasks  # noqa
