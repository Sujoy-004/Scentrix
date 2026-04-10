"""Pydantic request/response schemas for ScentScape API."""

from datetime import datetime
from typing import Any, Optional, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ============================================================================
# AUTH SCHEMAS
# ============================================================================


class UserRegister(BaseModel):
    """Register new user."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    opt_in_training: bool = False


class UserLogin(BaseModel):
    """Login request."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


# ============================================================================
# USER PROFILE SCHEMAS
# ============================================================================


class UserProfile(BaseModel):
    """User profile response."""

    id: int
    email: str
    is_active: bool
    created_at: datetime
    opt_in_training: bool

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# FRAGRANCE RATING SCHEMAS
# ============================================================================


class FragranceRatingCreate(BaseModel):
    """Create fragrance rating."""

    fragrance_neo4j_id: str
    rating_sweetness: float = Field(..., ge=0, le=5)
    rating_woodiness: float = Field(..., ge=0, le=5)
    rating_longevity: float = Field(..., ge=0, le=5)
    rating_projection: float = Field(..., ge=0, le=5)
    rating_freshness: float = Field(..., ge=0, le=5)
    overall_satisfaction: float = Field(..., ge=0, le=5)


class FragranceRatingResponse(FragranceRatingCreate):
    """Fragrance rating response."""

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# FRAGRANCE SCHEMAS
# ============================================================================


class FragranceNote(BaseModel):
    """Fragrance note with intensity."""

    id: str
    name: str
    category: str  # "top", "middle", "base"
    intensity: float = 1.0


class FragranceAccord(BaseModel):
    """Fragrance accord."""

    id: str
    name: str
    certainty: float = 1.0


class FragranceBase(BaseModel):
    """Base fragrance info."""

    id: str
    name: str
    brand: str
    year: Optional[int] = None
    concentration: str
    gender_label: str = "N/A"
    description: str


class FragranceSearchResult(BaseModel):
    """Fragrance search result."""

    id: str
    name: str
    brand: str
    year: Optional[int] = None
    top_accords: list[str] = []
    top_notes: list[str] = []
    similarity_score: Optional[float] = None
    match_score: Optional[float] = None
    availability: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[float] = None
    reason: Optional[str] = None


class FragranceDetail(FragranceBase):
    """Full fragrance detail with notes and accords."""

    top_notes: list[FragranceNote] = []
    middle_notes: list[FragranceNote] = []
    base_notes: list[FragranceNote] = []
    accords: list[FragranceAccord] = []
    neighbors: Optional[list[FragranceSearchResult]] = None
    similarity_score: Optional[float] = None  # To user profile if authenticated


class FragranceCatalogItem(BaseModel):
    """Catalog item for paginated fragrance browsing."""

    id: str
    name: str
    brand: str
    family: str = "Unknown"
    year: Optional[int] = None
    concentration: str = "N/A"
    gender_label: str = "N/A"
    description: str = ""
    top_notes: list[str] = []
    middle_notes: list[str] = []
    base_notes: list[str] = []
    accords: list[str] = []
    rating: Optional[float] = None
    match_score: Optional[float] = None


class FragranceCatalogPage(BaseModel):
    """Paginated catalog response."""

    items: list[FragranceCatalogItem]
    total: int
    limit: int
    offset: int


# ============================================================================
# RECOMMENDATION SCHEMAS
# ============================================================================


class RecommendationJob(BaseModel):
    """Async recommendation job response."""

    job_id: str
    status: str  # "processing", "completed", "failed"
    message: str = ""


class RecommendationResult(BaseModel):
    """Recommendation result with ranked fragrances."""

    job_id: str
    status: str = "completed"
    fragrances: list[FragranceSearchResult]
    generated_at: datetime
    message: str = ""


class TextRecommendationRequest(BaseModel):
    """Text-based recommendation request."""

    query: str = Field(..., min_length=5, max_length=500)
    limit: int = Field(10, ge=1, le=50)


class RecommendationInteractionEventCreate(BaseModel):
    """Recommendation interaction event for feedback loop ingestion."""

    fragrance_id: str = Field(..., min_length=1, max_length=100)
    interaction_type: Literal[
        "impression",
        "click_detail",
        "click_similar",
        "wishlist_add",
        "purchase",
        "refine_prompt_click",
    ]
    interaction_value: Optional[float] = None
    match_score: Optional[float] = Field(default=None, ge=0, le=100)
    confidence_tier: Optional[Literal["low", "medium", "high", "unknown"]] = None
    availability: Optional[str] = None
    source: str = Field(default="web", min_length=1, max_length=50)
    context: dict[str, Any] = Field(default_factory=dict)


class RecommendationInteractionBatchRequest(BaseModel):
    """Batch recommendation events payload."""

    events: list[RecommendationInteractionEventCreate] = Field(
        ..., min_length=1, max_length=100
    )


class RecommendationInteractionBatchResponse(BaseModel):
    """Acknowledgement for ingested recommendation events."""

    accepted: int
    rejected: int = 0


class RecommendationWeeklyMetrics(BaseModel):
    """7-day recommendation quality and engagement summary."""

    window_days: int = 7
    impressions: int
    detail_clicks: int
    similar_clicks: int
    wishlist_adds: int
    purchases: int
    avg_match_score: Optional[float] = None
    low_confidence_share_pct: float
    click_through_rate_pct: float
    wishlist_rate_pct: float
    conversion_rate_pct: float
    stock_coverage_pct: float
    high_vs_low_ctr_delta_pct: float


# ============================================================================
# ADAPTIVE QUIZ SCHEMAS
# ============================================================================


class QuizSessionStartFilters(BaseModel):
    """Optional filters for adaptive quiz session creation."""

    exclude_seen: bool = True


class QuizSessionStartRequest(BaseModel):
    """Start adaptive quiz session request."""

    seed_count: int = Field(8, ge=6, le=12)
    candidate_pool_size: int = Field(200, ge=50, le=5000)
    filters: QuizSessionStartFilters = QuizSessionStartFilters()


class QuizQuestion(BaseModel):
    """Quiz question card payload."""

    fragrance_id: str
    name: str
    brand: str
    top_notes: list[str] = []
    accords: list[str] = []


class QuizSessionRules(BaseModel):
    """Server-side adaptive quiz stopping rules."""

    min_core_questions: int
    max_total_questions: int
    medium_extension: int
    low_extension: int
    confidence_threshold: float


class QuizSessionStartResponse(BaseModel):
    """Adaptive quiz session start response."""

    session_id: str
    seed_questions: list[QuizQuestion]
    rules: QuizSessionRules
    expires_at: datetime


class QuizSessionSubmitResponseRequest(BaseModel):
    """Single adaptive quiz response submission."""

    fragrance_id: str
    rating_1_to_10: float = Field(..., ge=1, le=10)
    source: str = "quiz_core"


class QuizSessionSubmitResponseResponse(BaseModel):
    """Adaptive quiz response acknowledgement."""

    accepted: bool
    normalized_rating_0_to_5: float
    answers_count: int


class QuizSessionEvaluateRequest(BaseModel):
    """Evaluate adaptive quiz confidence."""

    force: bool = False


class QuizConfidenceComponents(BaseModel):
    """Confidence sub-scores for observability."""

    stability: float
    margin: float
    consistency: float
    coverage: float


class QuizSessionEvaluateResponse(BaseModel):
    """Adaptive quiz evaluation outcome."""

    confidence_score: float
    confidence_band: str
    extension_required: bool
    additional_questions_target: int
    total_answered: int
    stop_reason: Optional[str] = None
    components: QuizConfidenceComponents


class QuizSessionNextQuestionsResponse(BaseModel):
    """Next adaptive extension questions."""

    questions: list[QuizQuestion]
    count: int


# ============================================================================
# COLLECTION SCHEMAS
# ============================================================================


class SavedFragranceCreate(BaseModel):
    """Add fragrance to collection."""

    fragrance_neo4j_id: str
    notes: Optional[str] = None


class SavedFragranceResponse(BaseModel):
    """Saved fragrance response."""

    id: int
    user_id: int
    fragrance_neo4j_id: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# HEALTH & STATUS SCHEMAS
# ============================================================================


class HealthCheck(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    detail: Optional[str] = None
    code: int
