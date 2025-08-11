from pydantic import BaseSettings, AnyHttpUrl
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "SpiralNet Memory API"
    NEO4J_URI: AnyHttpUrl | str = os.getenv("NEO4J_URI", "")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "")
    USE_NEO4J_VECTOR: bool = False   # if Neo4j vector index plugin available
    ACCEPTED_SCOPES: tuple[str, ...] = ("public", "shared", "private")
    # default consent scope for writes when not specified by caller:
    DEFAULT_WRITE_SCOPE: str = "private"

    class Config:
        env_file = ".env"

settings = Settings()
