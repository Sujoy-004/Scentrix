import json
import logging
from typing import Any, Dict

import httpx

from app.config import settings
from app.services.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class SommelierService:
    """The 'Neural Sommelier' (Aethera) for Scentrix.

    Provides atmospheric, AI-powered insights into fragrance collections
    using the Gemini 1.5 Flash model with local fallbacks.
    """

    def __init__(self):
        self.api_key = settings.google_api_key
        self.api_url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-1.5-flash:generateContent"
        )

    async def generate_insight(self, recommendations: list[Any]) -> tuple[str, str]:
        """Generate a singular, high-fidelity insight for a recommended cohort."""
        if not self.api_key:
            return (
                "Your collection resonates with a unique, elusive frequency. There is a deep, "
                "structural harmony between your choices that suggests a preference for complex, "
                "narrative-driven olfactive profiles.",
                "Aetheric Discovery",
            )

        # Load external persona
        persona = load_prompt("persona-aethera.md") or "You are 'Aethera', the Digital Sommelier for Scentrix."

        # Format fragrances for the prompt (Limited to top 8 for context window efficiency)
        frag_list = []
        for f in recommendations[:8]:
            # Handle both Pydantic objects and dicts
            if hasattr(f, "model_dump"):
                d = f.model_dump()
            elif hasattr(f, "dict"):
                d = f.dict()
            elif isinstance(f, dict):
                d = f
            else:
                d = {}

            name = d.get("name", "Unknown")
            brand = d.get("brand", "Unknown")
            match = d.get("match_score", 0)
            reason = d.get("reason", "")
            frag_list.append(f"- {brand} {name} (Match: {match}%, Reason: {reason})")

        fragrance_summary = "\n".join(frag_list)
        prompt = f"""
        {persona}
        
        Analyze the following curated list of fragrances recommended for a user.
        Provide a singular, atmospheric insight (exactly 2-3 sentences) that identifies 
        the 'soul' and narrative arc of this collection. 
        Also provide a short 2-3 word category name for the vibe (e.g., 'Ethereal Moss', 
        'Noir Avant-Garde', 'Solar Minimalism').
        
        Curated Collection:
        {fragrance_summary}
        
        Respond ONLY in valid JSON format:
        {{
            "insight": "...",
            "vibe_category": "..."
        }}
        """

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}?key={self.api_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"response_mime_type": "application/json"},
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                text_content = data["candidates"][0]["content"]["parts"][0]["text"]

                parsed = json.loads(text_content)
                return (
                    parsed.get("insight", "Matches found with high neural confidence."),
                    parsed.get("vibe_category", "Neural Harmony"),
                )
        except Exception as e:
            logger.error(f"Sommelier Service (Gemini) error: {e}")
            return (
                "Your selection hints at a sophisticated balance of tradition and architectural "
                "modernity. The convergence of these notes suggests a wearer who values both "
                "structural integrity and unexpected olfactive pivots.",
                "Scent Equilibrium",
            )


sommelier_service = SommelierService()
