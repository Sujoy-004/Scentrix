from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_prompts_dir() -> Path:
    """Gets the path to the prompts directory."""
    # Assume we are in backend/app/services/utils.py
    # Root is 4 levels up
    root = Path(__file__).parent.parent.parent.parent
    prompts_path = root / ".github" / "prompts"
    return prompts_path


def load_prompt(filename: str) -> str:
    """Loads a prompt file from the .github/prompts directory."""
    path = get_prompts_dir() / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
