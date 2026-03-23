"""Data cleaning pipeline for ScentScape.

Validates raw fragrance data, deduplicates records, normalizes note names,
and ensures data quality before Neo4j ingestion.
"""

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class FragranceDataCleaner:
    """Cleans and validates fragrance data from raw scrapi or seed sources."""

    # Normalized note name mappings (typos, variants → canonical names)
    NOTE_NAME_MAPPINGS = {
        "bergamote": "Bergamot",
        "bergamot": "Bergamot",
        "bergamota": "Bergamot",
        "amber": "Amber",
        "ambre": "Amber",
        "amber resinoid": "Amber",
        "ambroxan": "Ambroxan",
        "ambrette": "Ambrette",
        "musk": "Musk",
        "white musk": "Musk",
        "musks": "Musk",
        "cedar": "Cedar",
        "cedarwood": "Cedar",
        "cedryl acetate": "Cedar",
        "cinnamon": "Cinnamon",
        "cinnamon bark": "Cinnamon",
        "vanilla": "Vanilla",
        "tonka bean": "Tonka",
        "sandalwood": "Sandalwood",
        "sandal": "Sandalwood",
        "vetiver": "Vetiver",
        "vetivert": "Vetiver",
        "rose": "Rose",
        "rosa damascena": "Rose",
        "may rose": "Rose",
        "iris": "Iris",
        "jasmine": "Jasmine",
        "orange blossom": "Orange Blossom",
        "neroli": "Neroli",
        "lemon": "Lemon",
        "grapefruit": "Grapefruit",
        "mandarin": "Mandarin",
        "orange": "Orange",
        "coconut": "Coconut",
        "almond": "Almond",
        "peach": "Peach",
        "pineapple": "Pineapple",
        "leather": "Leather",
        "tobacco": "Tobacco",
        "oud": "Oud",
        "agarwood": "Oud",
        "galbanum": "Galbanum",
        "patchouli": "Patchouli",
        "patchouly": "Patchouli",
        "pepper": "Pepper",
        "pink pepper": "Pink Pepper",
        "black pepper": "Black Pepper",
        "cardamom": "Cardamom",
        "ginger": "Ginger",
        "lavender": "Lavender",
        "violet": "Violet",
        "coconut water": "Coconut",
        "tuberose": "Tuberose",
        "frangipani": "Frangipani",
        "myrrh": "Myrrh",
        "frankincense": "Frankincense",
        "incense": "Incense",
        "smoke": "Smoke",
        "hay": "Hay",
    }

    # Valid note categories
    VALID_CATEGORIES = {"top", "middle", "base"}

    # Minimum required notes per fragrance
    MIN_NOTES_REQUIRED = 3

    def __init__(self, strict_mode: bool = False):
        """Initialize cleaner.

        Args:
            strict_mode: If True, reject records with missing critical fields
        """
        self.strict_mode = strict_mode
        self.stats = {
            "total_input": 0,
            "total_output": 0,
            "duplicates_removed": 0,
            "invalid_records": 0,
            "records_fixed": 0,
        }

    def clean_fragrance_list(
        self,
        fragrances: list[dict[str, Any]],
        deduplicate_by: tuple[str, ...] = ("name", "brand"),
    ) -> list[dict[str, Any]]:
        """Clean list of fragrance records.

        Args:
            fragrances: Raw fragrance list
            deduplicate_by: Tuple of fields to use for deduplication

        Returns:
            Clean fragrance list
        """
        self.stats["total_input"] = len(fragrances)
        logger.info(f"Starting cleaning of {len(fragrances)} fragrances")

        cleaned = []
        seen = set()

        for frag in fragrances:
            # Validate required fields
            if not self._validate_required_fields(frag):
                self.stats["invalid_records"] += 1
                logger.warning(f"Skipping invalid fragrance: {frag.get('name', 'N/A')}")
                continue

            # Deduplicate by (name, brand)
            dedup_key = tuple(str(frag.get(field, "")).lower() for field in deduplicate_by)
            if dedup_key in seen:
                self.stats["duplicates_removed"] += 1
                logger.debug(f"Duplicate removed: {dedup_key}")
                continue
            seen.add(dedup_key)

            # Clean and normalize
            clean_frag = self._clean_fragrance(frag)
            if clean_frag:
                cleaned.append(clean_frag)
                self.stats["total_output"] += 1

        logger.info(
            f"Cleaning complete: {self.stats['total_output']} valid records, "
            f"{self.stats['duplicates_removed']} duplicates, "
            f"{self.stats['invalid_records']} invalid"
        )
        return cleaned

    def _validate_required_fields(self, frag: dict[str, Any]) -> bool:
        """Validate required fields are present.

        Args:
            frag: Fragrance record

        Returns:
            True if valid, False otherwise
        """
        required = {"id", "name", "brand", "top_notes", "middle_notes", "base_notes"}
        missing = required - set(frag.keys())

        if missing:
            if self.strict_mode:
                return False
            logger.warning(f"Missing fields: {missing}")

        # Check minimum notes
        total_notes = (
            len(frag.get("top_notes", [])) +
            len(frag.get("middle_notes", [])) +
            len(frag.get("base_notes", []))
        )
        if total_notes < self.MIN_NOTES_REQUIRED:
            logger.warning(
                f"Fragrance {frag.get('name')} has {total_notes} notes "
                f"(minimum {self.MIN_NOTES_REQUIRED} required)"
            )
            return False

        return True

    def _clean_fragrance(self, frag: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Clean individual fragrance record.

        Args:
            frag: Raw fragrance record

        Returns:
            Cleaned fragrance dict or None if invalid
        """
        try:
            clean = {
                "id": str(frag.get("id", "")).strip().lower(),
                "name": str(frag.get("name", "")).strip(),
                "brand": str(frag.get("brand", "")).strip(),
                "year": int(frag.get("year", 0)) if frag.get("year") else None,
                "concentration": str(frag.get("concentration", "")).strip(),
                "gender_label": str(frag.get("gender_label", "N/A")).strip().lower(),
                "description": str(frag.get("description", "")).strip()[:500],  # Max 500 chars
                "top_notes": self._normalize_notes(frag.get("top_notes", []), "top"),
                "middle_notes": self._normalize_notes(frag.get("middle_notes", []), "middle"),
                "base_notes": self._normalize_notes(frag.get("base_notes", []), "base"),
                "accords": self._validate_accords(frag.get("accords", [])),
            }

            # Validate result
            if not clean["id"] or not clean["name"]:
                logger.warning(f"Missing id or name after cleaning")
                return None

            if not all(
                [clean["top_notes"], clean["middle_notes"], clean["base_notes"]]
            ):
                logger.warning(
                    f"Fragrance {clean['name']} missing notes in one category"
                )
                return None

            return clean

        except Exception as e:
            logger.error(f"Error cleaning fragrance {frag.get('name')}: {e}")
            return None

    def _normalize_notes(self, notes: list[str], category: str) -> list[str]:
        """Normalize note names.

        Args:
            notes: Raw note list
            category: "top", "middle", or "base"

        Returns:
            Normalized note list
        """
        if not isinstance(notes, list):
            notes = [notes]

        normalized = []
        for note in notes:
            if isinstance(note, str):
                note_lower = note.strip().lower()
                # Use mapping or keep original if exact match doesn't exist
                canonical = self.NOTE_NAME_MAPPINGS.get(note_lower, note.strip())
                if canonical and canonical not in normalized:
                    normalized.append(canonical)

        return normalized[:5]  # Max 5 notes per category

    def _validate_accords(self, accords: list[str]) -> list[str]:
        """Validate and normalize accordrs.

        Args:
            accords: Raw accord list

        Returns:
            Clean accord list
        """
        if not isinstance(accords, list):
            accords = [accords]

        valid = []
        for accord in accords:
            if isinstance(accord, str):
                accord = accord.strip()
                if accord and accord not in valid:
                    valid.append(accord)

        return valid[:5]  # Max 5 accords

    def load_and_clean(self, filepath: Path) -> list[dict[str, Any]]:
        """Load JSON file and clean fragrances.

        Args:
            filepath: Path to fragrance JSON file

        Returns:
            Clean fragrance list
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            fragrances = data if isinstance(data, list) else [data]
            return self.clean_fragrance_list(fragrances)
        except Exception as e:
            logger.error(f"Error loading file {filepath}: {e}")
            return []

    def save_cleaned(
        self,
        fragrances: list[dict[str, Any]],
        output_path: Path,
    ) -> None:
        """Save cleaned fragrances to JSON.

        Args:
            fragrances: Clean fragrance list
            output_path: Path to save JSON
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(fragrances, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(fragrances)} fragrances to {output_path}")
        except Exception as e:
            logger.error(f"Error saving fragrances: {e}")

    def report(self) -> dict[str, Any]:
        """Get cleaning statistics.

        Returns:
            Stats dict
        """
        return {
            **self.stats,
            "removal_rate": (
                self.stats["duplicates_removed"] /
                max(self.stats["total_input"], 1) * 100
            ),
            "success_rate": (
                self.stats["total_output"] /
                max(self.stats["total_input"], 1) * 100
            ),
        }


def clean_fragrance_file(
    input_path: Path,
    output_path: Path,
    strict_mode: bool = False,
) -> None:
    """Standalone function to clean fragrance JSON file.

    Args:
        input_path: Path to raw JSON
        output_path: Path to save cleaned JSON
        strict_mode: Strict validation
    """
    cleaner = FragranceDataCleaner(strict_mode=strict_mode)
    fragrances = cleaner.load_and_clean(input_path)
    cleaner.save_cleaned(fragrances, output_path)
    print(json.dumps(cleaner.report(), indent=2))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python clean.py <input_json> [output_json]")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2] if len(sys.argv) > 2 else "cleaned_fragrances.json")

    clean_fragrance_file(input_file, output_file)
