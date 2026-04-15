"""API router for core ScentScape endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter

# from app.models.models import Base, engine  # Assume engine in models or main
from app.schemas.schemas import (
    FragranceSearchResult,
    HealthCheck,
    RecommendationResult,
    TextRecommendationRequest,
)

router = APIRouter(tags=["api"])


def get_db() -> None:
    # Placeholder DB dependency - configure in main.py
    raise NotImplementedError


@router.get("/fragrances", response_model=list[FragranceSearchResult])
async def get_fragrances(limit: int = 10) -> list[FragranceSearchResult]:
    """Placeholder endpoint for fragrance search."""
    # TODO: Implement Neo4j query
    return [
        FragranceSearchResult(
            id=f"f{i}",
            name=f"Sample Fragrance {i}",
            brand="Sample Brand",
            similarity_score=0.9,
        )
        for i in range(limit)
    ]


@router.post("/recommend/text", response_model=RecommendationResult)
async def text_recommendation(request: TextRecommendationRequest) -> RecommendationResult:
    """Text-based recommendation placeholder."""
    # TODO: Implement LLM + GNN recommendation
    return RecommendationResult(
        job_id="demo-job",
        fragrances=[FragranceSearchResult(id="f1", name="Recommended", brand="Demo")],
        generated_at=datetime.now(UTC),
    )


@router.get("/health", response_model=HealthCheck)
async def api_health() -> HealthCheck:
    return HealthCheck(status="healthy", version="0.1.0", timestamp=datetime.now(UTC))
