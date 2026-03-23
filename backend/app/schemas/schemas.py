"""Pydantic request/response schemas for ScentScape API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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


class FragranceDetail(FragranceBase):
    """Full fragrance detail with notes and accords."""

    top_notes: list[FragranceNote] = []
    middle_notes: list[FragranceNote] = []
    base_notes: list[FragranceNote] = []
    accords: list[FragranceAccord] = []
    similarity_score: Optional[float] = None  # To user profile if authenticated


class FragranceSearchResult(BaseModel):
    """Fragrance search result."""

    id: str
    name: str
    brand: str
    year: Optional[int] = None
    top_accords: list[str] = []
    similarity_score: Optional[float] = None


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
    fragrances: list[FragranceSearchResult]
    generated_at: datetime


class TextRecommendationRequest(BaseModel):
    """Text-based recommendation request."""

    query: str = Field(..., min_length=5, max_length=500)
    limit: int = Field(10, ge=1, le=50)


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

    class Config:
        from_attributes = True


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
