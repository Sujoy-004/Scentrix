"""Neo4j driver and connection management for ScentScape.

This module provides a singleton Neo4j driver with connection pooling,
retry logic, and context managers for transactions.
"""

import logging
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from neo4j import AsyncDriver, AsyncSession, Driver, Session
from neo4j import auth as neo4j_auth
from neo4j import exceptions

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Neo4j client with connection pooling and transaction management."""

    _instance: Optional["Neo4jClient"] = None
    _driver: Optional[Driver] = None
    _async_driver: Optional[AsyncDriver] = None

    def __new__(cls) -> "Neo4jClient":
        """Singleton pattern to ensure only one client instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        encrypted: bool = False,
        max_connection_pool_size: int = 50,
        connection_timeout: float = 30.0,
        max_retry_attempts: int = 3,
    ) -> None:
        """Initialize Neo4j client with connection pooling.

        Args:
            uri: Neo4j URI (e.g., neo4j://localhost:7687)
            user: Neo4j username
            password: Neo4j password
            encrypted: Whether to use encrypted connection
            max_connection_pool_size: Maximum connections to pool
            connection_timeout: Connection timeout in seconds
            max_retry_attempts: Max retry attempts for transient failures
        """
        if self._driver is None:
            try:
                self._driver = Driver(
                    uri,
                    auth=neo4j_auth.basic(user, password),
                    encrypted=encrypted,
                    max_connection_pool_size=max_connection_pool_size,
                    connection_timeout=connection_timeout,
                    max_retry_attempts=max_retry_attempts,
                )
                logger.info(f"Neo4j driver initialized: {uri}")
            except Exception as e:
                logger.error(f"Failed to initialize Neo4j driver: {e}")
                raise

    @classmethod
    def get_instance(cls) -> "Neo4jClient":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls.__new__(cls)
        return cls._instance

    def get_driver(self) -> Driver:
        """Get Neo4j driver instance."""
        if self._driver is None:
            raise RuntimeError("Neo4j driver not initialized")
        return self._driver

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Context manager for Neo4j session.

        Yields:
            Neo4j Session for transaction management

        Example:
            with neo4j_client.session() as sess:
                result = sess.run("MATCH (f:Fragrance) RETURN f LIMIT 10")
                fragrances = list(result)
        """
        driver = self.get_driver()
        session = driver.session()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def async_session(self) -> Iterator[AsyncSession]:
        """Context manager for async Neo4j session.

        Yields:
            Async Neo4j Session

        Example:
            async with neo4j_client.async_session() as sess:
                result = await sess.run("MATCH (f:Fragrance) RETURN f LIMIT 10")
        """
        driver = self.get_driver()
        session = driver.session()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def tx(self, access_mode: str = "WRITE") -> Iterator[Any]:
        """Context manager for Neo4j transaction.

        Args:
            access_mode: "READ" or "WRITE"

        Yields:
            Neo4j transaction context

        Example:
            with neo4j_client.tx() as tx:
                result = tx.run("CREATE (f:Fragrance $props) RETURN f", props={...})
        """
        with self.session() as session:
            if access_mode == "READ":
                with session.begin_transaction() as tx:
                    yield tx
            else:
                with session.begin_transaction(write=True) as tx:
                    yield tx

    def execute_query(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
        access_mode: str = "READ",
    ) -> list[Any]:
        """Execute a query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters (optional)
            access_mode: "READ" or "WRITE"

        Returns:
            List of query results

        Raises:
            neo4j.exceptions.Neo4jError: On query execution failure
        """
        try:
            with self.session() as session:
                result = session.run(query, parameters or {})
                return list(result)
        except exceptions.ClientError as e:
            logger.error(f"Neo4j query error: {e}")
            raise
        except exceptions.ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error executing query: {e}")
            raise

    def execute_write(
        self,
        query: str,
        parameters: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Execute a write query and return summary.

        Args:
            query: Cypher query string
            parameters: Query parameters (optional)

        Returns:
            Summary dict with nodes created/updated counts

        Raises:
            neo4j.exceptions.Neo4jError: On query execution failure
        """
        try:
            with self.session() as session:
                result = session.run(query, parameters or {})
                # Consume result to ensure write completes
                list(result)
                return {
                    "nodes_created": result.consume().counters.nodes_created,
                    "nodes_deleted": result.consume().counters.nodes_deleted,
                    "relationships_created": result.consume().counters.relationships_created,
                    "relationships_deleted": result.consume().counters.relationships_deleted,
                    "properties_set": result.consume().counters.properties_set,
                }
        except exceptions.ClientError as e:
            logger.error(f"Neo4j write error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in write operation: {e}")
            raise

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j driver closed")

    def verify_connection(self) -> bool:
        """Verify Neo4j connection is active.

        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            with self.session() as session:
                session.run("RETURN 1")
            logger.info("Neo4j connection verified")
            return True
        except Exception as e:
            logger.error(f"Neo4j connection verification failed: {e}")
            return False


# Global client instance
_neo4j_client: Optional[Neo4jClient] = None


def init_neo4j(
    uri: str,
    user: str,
    password: str,
    encrypted: bool = False,
    **kwargs: Any,
) -> Neo4jClient:
    """Initialize global Neo4j client.

    Args:
        uri: Neo4j URI
        user: Username
        password: Password
        encrypted: Whether to use encryption
        **kwargs: Additional driver options

    Returns:
        Neo4jClient instance
    """
    global _neo4j_client
    _neo4j_client = Neo4jClient(uri, user, password, encrypted, **kwargs)
    return _neo4j_client


def get_neo4j() -> Neo4jClient:
    """Get global Neo4j client instance.

    Returns:
        Neo4jClient singleton

    Raises:
        RuntimeError: If client not initialized
    """
    if _neo4j_client is None:
        raise RuntimeError("Neo4j client not initialized. Call init_neo4j() first.")
    return _neo4j_client


def close_neo4j() -> None:
    """Close global Neo4j client."""
    global _neo4j_client
    if _neo4j_client is not None:
        _neo4j_client.close()
        _neo4j_client = None
