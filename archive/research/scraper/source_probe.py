"""Probe source accessibility and robots endpoints for data ingestion planning.

This script does not scrape content. It only checks if target URLs are reachable
and writes a status artifact for compliance and operational visibility.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import requests


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class ProbeTarget:
    name: str
    data_url: str
    robots_url: str
    terms_url: str


@dataclass
class ProbeResult:
    name: str
    data_url: str
    data_status: Optional[int]
    robots_url: str
    robots_status: Optional[int]
    terms_url: str
    terms_status: Optional[int]
    blocked: bool
    notes: str


def _check(url: str, timeout: int = 20) -> Optional[int]:
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        return response.status_code
    except Exception:
        return None


def probe_target(target: ProbeTarget) -> ProbeResult:
    data_status = _check(target.data_url)
    robots_status = _check(target.robots_url)
    terms_status = _check(target.terms_url)

    blocked = data_status in {401, 403, 429} or data_status is None
    if blocked:
        notes = "Automated collection blocked or unavailable; use licensing/import path."
    else:
        notes = "Reachable. Continue with robots/terms review before scraping."

    return ProbeResult(
        name=target.name,
        data_url=target.data_url,
        data_status=data_status,
        robots_url=target.robots_url,
        robots_status=robots_status,
        terms_url=target.terms_url,
        terms_status=terms_status,
        blocked=blocked,
        notes=notes,
    )


def main() -> int:
    targets = [
        ProbeTarget(
            name="fragrantica",
            data_url="https://www.fragrantica.com/perfumes/",
            robots_url="https://www.fragrantica.com/robots.txt",
            terms_url="https://www.fragrantica.com/terms-and-conditions.phtml",
        ),
        ProbeTarget(
            name="basenotes",
            data_url="https://basenotes.com/fragrances",
            robots_url="https://basenotes.com/robots.txt",
            terms_url="https://basenotes.com/terms",
        ),
    ]

    now = datetime.now(UTC)
    results = [probe_target(target) for target in targets]

    artifact = {
        "generated_at_utc": now.isoformat().replace("+00:00", "Z"),
        "results": [asdict(item) for item in results],
    }

    out_dir = Path(__file__).resolve().parents[1] / "logs" / "source_probe"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"source_probe_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    out_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    registry_path = Path(__file__).resolve().parent / "source_registry.json"
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        source_map = {item["name"]: item for item in registry.get("sources", []) if isinstance(item, dict)}
        for result in results:
            existing = source_map.get(result.name)
            if not existing:
                continue
            if result.data_status is None:
                existing["access_status"] = "unreachable"
            elif result.data_status == 200:
                existing["access_status"] = "reachable"
            else:
                existing["access_status"] = f"blocked_{result.data_status}"
            existing["last_checked_utc"] = now.isoformat().replace("+00:00", "Z")
            existing["notes"] = result.notes
        registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    print(json.dumps(artifact, indent=2))
    print(f"artifact={out_path}")
    print(f"registry={registry_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
