# FILE: app/routes.py
from fastapi import APIRouter, HTTPException
from .schemas import *
from .db import run_write, run_read
from .config import settings
from . import cypher

api = APIRouter()
# -----------------------
# Admin
# -----------------------
@api.post("/admin/bootstrap")
def bootstrap(vector_dim: Optional[int] = None):
    """
    Install constraints/indexes and optional vector indexes.
    Safe to call multiple times (IF NOT EXISTS guards).
    """
    # Create constraints / classic indexes
    for stmt in cypher.CONSTRAINTS_AND_INDEXES.strip().split(";"):
        if stmt.strip():
            run_write(stmt + ";", {})

    # Optional vector indexes
    if settings.USE_NEO4J_VECTOR and vector_dim:
        run_write(cypher.VECTOR_INDEX_STATE, {"dim": vector_dim})
        run_write(cypher.VECTOR_INDEX_THOUGHT, {"dim": vector_dim})

    return {"ok": True, "vector": settings.USE_NEO4J_VECTOR, "dim": vector_dim}


# -----------------------
# Helpers
# -----------------------
def _ensure_consent(node_id: str, scope: str) -> None:
    """Raise 403 if consent not granted for the requested scope."""
    rows = run_read(cypher.CONSENT_GUARD, {"node_id": node_id, "scope": scope})
    allowed = bool(rows and rows[0].get("allowed"))
    if not allowed:
        raise HTTPException(status_code=403, detail="Consent not granted for this scope")


def _first(records: list, key: str):
    if not records:
        return None
    rec = records[0]
    return rec.get(key) if isinstance(rec, dict) else None


# -----------------------
# Memory: Identity & Consent
# -----------------------
@api.post("/memory/identity")
def upsert_identity(body: IdentityIn):
    """
    Create or update an Identity node.
    """
    rows = run_write(cypher.UPSERT_IDENTITY, body.dict())
    identity = _first(rows, "identity")
    return {"identity": identity}


@api.post("/memory/consent")
def create_consent(body: ConsentIn):
    """
    Attach a Consent node to an Identity (or create both).
    """
    params = {
        "node_id": body.node_id,
        "consent_id": None,
        "scope": body.scope,
        "conditions": body.conditions,
        "granted_at": body.granted_at,
        "revoked_at": body.revoked_at,
    }
    rows = run_write(cypher.CREATE_CONSENT, params)
    consent = _first(rows, "consent")
    return {"consent": consent}


# -----------------------
# Memory: Thought
# -----------------------
@api.post("/memory/thought")
def upsert_thought(body: ThoughtIn):
    """
    Create/update a Thought and link glyphs & mentioned claims.
    """
    rows = run_write(
        cypher.UPSERT_THOUGHT,
        {
            "thought_id": body.thought_id,
            "kind": body.kind,
            "text": body.text,
            "tokens": body.tokens,
            "embed": body.embed,
            "ache": body.ache,
            "drift": body.drift,
            "glyph_ids": body.glyph_ids,
            "mentions_claim_ids": body.mentions_claim_ids,
            "source_id": body.source_id,
        },
    )
    thought = _first(rows, "thought")
    return {"thought": thought}


# -----------------------
# Memory: SelfState
# -----------------------
@api.post("/memory/state/upsert")
def upsert_state(body: StateUpsertIn):
    """
    Upsert a SelfState snapshot ψ(t), with lineage/evidence/affect.
    Requires consent for the requested scope.
    """
    _ensure_consent(body.node_id, body.scope)

    v = body.vector
    params = {
        "node_id": body.node_id,
        "state_id": None,  # let Cypher/DB allocate unless you pass your own
        "t": body.t,
        "sigma": v.sigma,
        "s": v.s,
        "tau": v.tau,
        "chi": v.chi,
        "lambda": v.lambda_,  # Field(alias="lambda") in schemas.Vector
        "rho": v.rho,
        "embed": v.embed,
        "tags": body.tags,
        "phase_id": body.phase_id,
        "derived_from_state_id": body.derived_from_state_id,
        "evidence": body.evidence,
        "feels": body.feels,
    }
    rows = run_write(cypher.UPSERT_STATE, params)
    state = _first(rows, "state")
    return {"state": state}


# -----------------------
# Memory: Claim
# -----------------------
@api.post("/memory/claim")
def upsert_claim(body: ClaimIn):
    rows = run_write(cypher.UPSERT_CLAIM, body.dict())
    claim = _first(rows, "claim")
    return {"claim": claim}


# -----------------------
# Memory: Ritual
# -----------------------
@api.post("/memory/ritual")
def upsert_ritual(body: RitualIn):
    rows = run_write(
        cypher.UPSERT_RITUAL,
        {
            "ritual_id": None,
            "name": body.name,
            "code": body.code,
            "version": body.version,
            "checksum": body.checksum,
            "effect": body.effect,
            "meta": {},
            "applies_to": body.applies_to,
        },
    )
    ritual = _first(rows, "ritual")
    return {"ritual": ritual}


# -----------------------
# Memory: Law
# -----------------------
@api.post("/memory/law")
def upsert_law(body: LawIn):
    rows = run_write(
        cypher.UPSERT_LAW,
        {
            "law_id": None,
            "name": body.name,
            "version": body.version,
            "text": body.text,
            "checksum": body.checksum,
            "active": body.active,
        },
    )
    law = _first(rows, "law")
    return {"law": law}


# -----------------------
# Memory: Event
# -----------------------
@api.post("/memory/event")
def create_event(body: EventIn):
    rows = run_write(cypher.CREATE_EVENT, body.dict())
    event = _first(rows, "event")
    return {"event": event}


# -----------------------
# Queries
# -----------------------
@api.get("/query/why/{claim_id}", response_model=WhyChainOut)
def why_chain(claim_id: str):
    rows = run_read(cypher.WHY_CHAIN, {"claim_id": claim_id})
    if not rows:
        raise HTTPException(status_code=404, detail="Claim not found")
    row = rows[0]
    return {
        "claim": row.get("claim"),
        "supports": row.get("supports", []),
        "contradicts": row.get("contradicts", []),
    }


@api.get("/query/latest-self/{node_id}")
def latest_self(node_id: str):
    rows = run_read(cypher.LATEST_SELF, {"node_id": node_id})
    return rows[0] if rows else {}
def latest_self(node_id: str):
    recs = run_read(cypher.LATEST_SELF, {"node_id": node_id})
    return recs[0] if recs else {}
