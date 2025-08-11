from neo4j import GraphDatabase, Driver
from .config import settings

_driver: Driver | None = None

def get_driver() -> Driver:
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _driver

def run_write(cypher: str, params: dict):
    with get_driver().session(database=settings.NEO4J_DATABASE) as s:
        return s.execute_write(lambda tx: list(tx.run(cypher, **params)))

def run_read(cypher: str, params: dict):
    with get_driver().session(database=settings.NEO4J_DATABASE) as s:
        return s.execute_read(lambda tx: list(tx.run(cypher, **params)))
