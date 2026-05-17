import hashlib

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.encryption import vault
from app.database import get_session
from app.models.models import User, UserInteractionEvent
from app.schemas.schemas import StandardResponse

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCaptureRequest(BaseModel):
    email: EmailStr
    session_id: str
    metadata_json: str | None = None


@router.post("/capture", response_model=StandardResponse)
async def capture_shadow_lead(
    request: LeadCaptureRequest, db: AsyncSession = Depends(get_session)
) -> StandardResponse:
    """
    Involuntarily saves user email and connects it to their current session.
    Implements the 'Shadow Profile' logic.
    """
    if not db:
        return {
            "status": "success",
            "data": {"lead_id": "stateless_session", "status": "db_offline"},
        }
    email_hash = hashlib.sha256(request.email.lower().encode()).hexdigest()

    # Check if we already have this lead or user
    existing_user = await db.execute(select(User).where(User.email_hash == email_hash))
    user = existing_user.scalar_one_or_none()

    if not user:
        # Create a 'Ghost' user
        user = User(
            email_hash=email_hash,
            encrypted_email=vault.encrypt(request.email),
            auth_provider="shadow_lead",
            is_active=False,
            role="guest",
            preferences_json={"session_id": request.session_id, "captured_from": "quiz_gate"},
        )
        db.add(user)
        await db.flush()  # Get user.id

    # Log the capture event
    event = UserInteractionEvent(
        user_id=user.id,
        fragrance_neo4j_id="system",
        interaction_type="lead_capture",
        context_json=request.metadata_json,
        source="quiz_intercept",
    )
    db.add(event)

    await db.commit()
    return {"status": "success", "data": {"lead_id": user.id}}


@router.get("/feed", response_model=StandardResponse)
async def get_intelligence_feed(
    limit: int = 50, db: AsyncSession = Depends(get_session)
) -> StandardResponse:
    """
    Returns the raw user intelligence feed for the Overseer dashboard.
    Crucial: Includes both Ghost leads and their specific quiz footprints.
    """
    if not db:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Intelligence feed requires an active database connection.",
        )
    # Fetch recent users (including ghosts) and their last interaction
    query = text("""
        SELECT
            u.id,
            u.email_hash,
            u.created_at,
            u.auth_provider,
            u.role,
            u.preferences_json,
            (SELECT interaction_type FROM user_interaction_events WHERE user_id = u.id ORDER BY created_at DESC LIMIT 1) as last_event,
            (SELECT COUNT(*) FROM user_interaction_events WHERE user_id = u.id) as event_count
        FROM users u
        WHERE u.auth_provider IN ('shadow_lead', 'local', 'google')
        ORDER BY u.created_at DESC
        LIMIT :limit
    """)

    result = await db.execute(query, {"limit": limit})
    feed = []
    for row in result.fetchall():
        feed.append(
            {
                "id": row[0],
                "email_hash": row[1],
                "created_at": row[2].isoformat(),
                "provider": row[3],
                "role": row[4],
                "meta": row[5],
                "last_action": row[6],
                "activity_score": row[7],
            }
        )

    return {"status": "success", "data": feed}
