import logging
import os
from typing import Any, Dict, List, Optional

try:
    from neo4j import GraphDatabase
except Exception:
    GraphDatabase = None

logger = logging.getLogger(__name__)


class GraphFraudEngine:
    """Neo4j-powered fraud intelligence engine for relational listing analysis."""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "neo4j")
        self.database = os.getenv("NEO4J_DATABASE", "neo4j")

        self.driver = None
        self.available = False

        if GraphDatabase is None:
            logger.warning("neo4j driver is unavailable. Graph fraud engine disabled.")
            return

        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Validate connection once at startup.
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1 AS ok")
            self.available = True
            logger.info("GraphFraudEngine connected to Neo4j")
        except Exception as exc:
            logger.warning(f"Neo4j connection failed; graph fraud engine disabled: {exc}")
            self.available = False
            self.driver = None

    def close(self) -> None:
        if self.driver is not None:
            try:
                self.driver.close()
            except Exception:
                pass

    def insert_listing(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge listing entities and relations:
        (:Broker)-[:LISTED]->(:Property)-[:USES_PHONE]->(:Phone)
        (:Property)-[:HAS_IMAGE]->(:Image)
        """
        if not self.available or self.driver is None:
            return {"success": False, "available": False, "message": "Neo4j unavailable"}

        property_id = str(data.get("property_id", "")).strip()
        broker_name = str(data.get("broker_name", "unknown")).strip() or "unknown"
        phone_number = str(data.get("phone_number", "")).strip()
        image_hash = str(data.get("image_hash", "")).strip()

        if not property_id:
            return {"success": False, "available": True, "message": "property_id is required"}

        try:
            with self.driver.session(database=self.database) as session:
                session.run(
                    """
                    MERGE (b:Broker {name: $broker_name})
                    MERGE (p:Property {id: $property_id})
                    MERGE (b)-[:LISTED]->(p)
                    """,
                    broker_name=broker_name,
                    property_id=property_id,
                )

                if phone_number:
                    session.run(
                        """
                        MATCH (p:Property {id: $property_id})
                        MERGE (ph:Phone {number: $phone_number})
                        MERGE (p)-[:USES_PHONE]->(ph)
                        """,
                        property_id=property_id,
                        phone_number=phone_number,
                    )

                if image_hash:
                    session.run(
                        """
                        MATCH (p:Property {id: $property_id})
                        MERGE (img:Image {hash: $image_hash})
                        MERGE (p)-[:HAS_IMAGE]->(img)
                        """,
                        property_id=property_id,
                        image_hash=image_hash,
                    )

            return {"success": True, "available": True, "property_id": property_id}
        except Exception as exc:
            logger.warning(f"Neo4j insert_listing failed: {exc}")
            return {"success": False, "available": True, "message": str(exc)}

    def detect_duplicate_listings(self) -> Dict[str, Any]:
        """Find suspicious property clusters by shared phone and image hash."""
        if not self.available or self.driver is None:
            return {
                "available": False,
                "shared_phone_clusters": [],
                "shared_image_clusters": [],
            }

        phone_clusters: List[Dict[str, Any]] = []
        image_clusters: List[Dict[str, Any]] = []

        try:
            with self.driver.session(database=self.database) as session:
                phone_result = session.run(
                    """
                    MATCH (p:Property)-[:USES_PHONE]->(ph:Phone)
                    WITH ph, collect(p.id) AS property_ids, count(p) AS cnt
                    WHERE cnt > 1
                    RETURN ph.number AS phone_number, property_ids, cnt
                    ORDER BY cnt DESC
                    """
                )
                for row in phone_result:
                    phone_clusters.append(
                        {
                            "phone_number": row.get("phone_number"),
                            "property_ids": row.get("property_ids", []),
                            "count": row.get("cnt", 0),
                        }
                    )

                image_result = session.run(
                    """
                    MATCH (p:Property)-[:HAS_IMAGE]->(img:Image)
                    WITH img, collect(p.id) AS property_ids, count(p) AS cnt
                    WHERE cnt > 1
                    RETURN img.hash AS image_hash, property_ids, cnt
                    ORDER BY cnt DESC
                    """
                )
                for row in image_result:
                    image_clusters.append(
                        {
                            "image_hash": row.get("image_hash"),
                            "property_ids": row.get("property_ids", []),
                            "count": row.get("cnt", 0),
                        }
                    )

            return {
                "available": True,
                "shared_phone_clusters": phone_clusters,
                "shared_image_clusters": image_clusters,
            }
        except Exception as exc:
            logger.warning(f"Neo4j detect_duplicate_listings failed: {exc}")
            return {
                "available": True,
                "error": str(exc),
                "shared_phone_clusters": [],
                "shared_image_clusters": [],
            }

    def compute_fraud_score(self, property_id: str) -> Dict[str, Any]:
        """
        Compute graph fraud risk score (0-100):
        - Broker degree centrality signal
        - Shared phone count
        - Shared image count
        """
        if not self.available or self.driver is None:
            return {
                "available": False,
                "property_id": property_id,
                "graph_fraud_score": 0.0,
                "broker_degree": 0,
                "shared_phone_count": 0,
                "shared_image_count": 0,
            }

        metrics = {
            "broker_degree": 0,
            "shared_phone_count": 0,
            "shared_image_count": 0,
        }

        try:
            with self.driver.session(database=self.database) as session:
                broker_row = session.run(
                    """
                    MATCH (b:Broker)-[:LISTED]->(p:Property {id: $property_id})
                    MATCH (b)-[:LISTED]->(other:Property)
                    RETURN count(DISTINCT other) AS broker_degree
                    """,
                    property_id=property_id,
                ).single()
                if broker_row:
                    metrics["broker_degree"] = int(broker_row.get("broker_degree", 0))

                phone_row = session.run(
                    """
                    MATCH (p:Property {id: $property_id})-[:USES_PHONE]->(ph:Phone)<-[:USES_PHONE]-(other:Property)
                    WHERE other.id <> $property_id
                    RETURN count(DISTINCT other) AS shared_phone_count
                    """,
                    property_id=property_id,
                ).single()
                if phone_row:
                    metrics["shared_phone_count"] = int(phone_row.get("shared_phone_count", 0))

                image_row = session.run(
                    """
                    MATCH (p:Property {id: $property_id})-[:HAS_IMAGE]->(img:Image)<-[:HAS_IMAGE]-(other:Property)
                    WHERE other.id <> $property_id
                    RETURN count(DISTINCT other) AS shared_image_count
                    """,
                    property_id=property_id,
                ).single()
                if image_row:
                    metrics["shared_image_count"] = int(image_row.get("shared_image_count", 0))

            # Convert graph metrics to risk signals.
            broker_risk = min(100.0, max(0.0, (metrics["broker_degree"] - 1) * 15.0))
            phone_risk = min(100.0, metrics["shared_phone_count"] * 30.0)
            image_risk = min(100.0, metrics["shared_image_count"] * 35.0)

            graph_fraud_score = (
                0.25 * broker_risk + 0.40 * phone_risk + 0.35 * image_risk
            )

            return {
                "available": True,
                "property_id": property_id,
                "graph_fraud_score": round(float(graph_fraud_score), 2),
                **metrics,
            }
        except Exception as exc:
            logger.warning(f"Neo4j compute_fraud_score failed for {property_id}: {exc}")
            return {
                "available": True,
                "property_id": property_id,
                "graph_fraud_score": 0.0,
                "broker_degree": 0,
                "shared_phone_count": 0,
                "shared_image_count": 0,
                "error": str(exc),
            }

    def get_example_cypher_queries(self) -> List[str]:
        return [
            "MATCH (b:Broker)-[:LISTED]->(p:Property) RETURN b.name, count(p) AS listings ORDER BY listings DESC",
            "MATCH (p:Property)-[:USES_PHONE]->(ph:Phone)<-[:USES_PHONE]-(other:Property) WHERE p.id <> other.id RETURN ph.number, collect(DISTINCT p.id) AS property_ids",
            "MATCH (p:Property)-[:HAS_IMAGE]->(img:Image)<-[:HAS_IMAGE]-(other:Property) WHERE p.id <> other.id RETURN img.hash, collect(DISTINCT p.id) AS property_ids",
            "MATCH (p:Property {id: $property_id})-[:USES_PHONE|HAS_IMAGE]->(x)<-[:USES_PHONE|HAS_IMAGE]-(other:Property) RETURN p.id, collect(DISTINCT other.id)",
        ]
