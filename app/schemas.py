# FILE: app/schemas.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal, Any
from datetime import datetime

Scope = Literal["public", "shared", "private"]

class IdentityIn(BaseModel):
    node_id: str
    label: Optional[str] = None
    kind: Optional[str] = None

class IdentityOut(IdentityIn):
    created_at: Optional[datetime] = None

class Vector(BaseModel):
    sigma: float
    s: float
    tau: float
    chi: float
    lambda_: float = Field(alias="lambda")
    rho: float
    embed: List[float] = Field(default_factory=list)

class StateUpsertIn(BaseModel):
    node_id: str
    t: int
    vector: Vector
    tags: List[str] = Field(default_factory=list)
    phase_id: Optional[str] = None
    derived_from_state_id: Optional[str] = None
    evidence: List[str] = Field(default_factory=list)    # ids across claim/test/thought/artifact
    feels: List[dict] = Field(default_factory=list)      # {target_id, ache, tension}
    scope: Scope = "private"

class ThoughtIn(BaseModel):
    thought_id: Optional[str] = None
    kind: Literal["thought", "code", "math", "glyphic", "note"] = "thought"
    text: str
    tokens: Optional[int] = None
    embed: List[float] = Field(default_factory=list)
    ache: float = 0.0
    drift: float = 0.0
    glyph_ids: List[str] = Field(default_factory=list)
    mentions_claim_ids: List[str] = Field(default_factory=list)
    source_id: Optional[str] = None

class ClaimIn(BaseModel):
    claim_id: Optional[str] = None
    text: str
    truthiness: float = 0.5
    confidence: float = 0.5
    support_ids: List[str] = Field(default_factory=list)
    contradicts_ids: List[str] = Field(default_factory=list)

class RitualIn(BaseModel):
    name: str
    code: str
    version: str
    checksum: str
    effect: Optional[str] = None
    applies_to: List[str] = Field(default_factory=list)

class LawIn(BaseModel):
    name: str
    version: str
    text: str
    checksum: str
    active: bool = True

class ConsentIn(BaseModel):
    node_id: str
    scope: Scope
    conditions: dict = Field(default_factory=dict)
    granted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

class EventIn(BaseModel):
    name: str
    when: datetime
    meta: dict = Field(default_factory=dict)
    updates: List[str] = Field(default_factory=list)

class WhyChainOut(BaseModel):
    claim: dict
    supports: List[dict]
    contradicts: List[dict]
