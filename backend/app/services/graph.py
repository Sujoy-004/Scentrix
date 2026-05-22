"""Neo4j graph client service — lazy init, graceful degradation."""

import logging
import os
import threading
from typing import Any

try:
    from neo4j import Driver as Neo4jClient
    from neo4j import GraphDatabase
except ImportError:
    GraphDatabase = None  # type: ignore[assignment,misc]
    Neo4jClient = Any  # type: ignore[assignment,misc]

from app.config import settings

logger = logging.getLogger(__name__)

_driver: Any = None
_init_lock = threading.Lock()


def init_neo4j(
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> Any:
    """Initialize Neo4j driver. Thread-safe, idempotent. Returns driver or None."""
    global _driver
    if _driver is not None:
        return _driver

    if not GraphDatabase:  # type: ignore[truthy-function]
        logger.warning("Neo4j driver not installed. Skipping graph connection.")
        return None

    uri = uri or settings.neo4j_uri
    user = user or settings.neo4j_user
    password = password or settings.neo4j_password

    # Docker URI override (same pattern as catalog.py)
    if os.environ.get("RUNNING_IN_DOCKER") == "true" and uri == "neo4j://localhost:7687":
        uri = "bolt://neo4j:7687"

    with _init_lock:
        if _driver is not None:
            return _driver
        try:
            _driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info(f"Neo4j driver initialized: {uri}")
            return _driver
        except Exception as e:
            logger.error(f"Failed to init Neo4j driver: {e}")
            return None


def get_neo4j() -> Any:
    """Get existing Neo4j driver or None."""
    return _driver


def close_neo4j() -> None:
    """Close Neo4j driver if initialized."""
    global _driver
    if _driver:
        try:
            _driver.close()
        except Exception as e:
            logger.error(f"Error closing Neo4j driver: {e}")
        _driver = None
