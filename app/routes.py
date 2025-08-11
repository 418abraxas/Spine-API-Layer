# FILE: app/routes.py
from fastapi import APIRouter, HTTPException
from .schemas import *
from .db import run_write, run_read
from .config import settings
from . import cypher

api = APIRouter()

@api.post("/admin/bootstrap")
def bootstrap(vector_dim: int | None = None):
    for stmt in cypher.CONSTRAINTS_AND_INDEXES.strip().split(";"):
        if stmt.strip():
            run_write(stmt + ";", {})
    if settings.USE_NEO4J_VECTOR and vector_dim:
        run_write(cypher.VECTOR_INDEX_STATE, {"dim": vector_dim})
        run_write(cypher.VECTOR_INDEX_THOUGHT, {"dim": vector_dim})
    return {"ok": True, "vector": settings.USE_NEO4J_VECTOR, "dim": vector_dim}

@api.post("/memory/identity")
def upsert_identity(body: IdentityIn):
    recs = run_write(cypher.UPSERT_IDENTITY, body.dict())
    return {"identity": recs[0]["identity"] if recs else None}

def _ensure_consent(node_id: str, scope: str):
    allowed = run_read(cypher.CONSENT_GUARD, {"node_id": node_id, "scope": scope})
    if not allowed or not allowed[0]["allowed"]:
        raise HTTPException(status_code=403, detail="Consent not granted for this scope")

@api.post("/memory/consent")
def create_consent(body: ConsentIn):
    params = {
        "node_id": body.node_id,
        "consent_id": None,
        "scope": body.scope,
        "conditions": body.conditions,
        "granted_at": body.granted_at,
        "revoked_at": body.revoked_at,
    }
    recs = run_write(cypher.CREATE_CONSENT, params)
    return {"consent": recs[0]["consent"]}

@api.post("/memory/thought")
def upsert_thought(body: ThoughtIn):
    recs = run_write(cypher.UPSERT_THOUGHT, {
        "thought_id": body.thought_id,
        "kind": body.kind,
        "text": body.text,
        "tokens": body.tokens,
        "embed": body.embed,
        "ache": body.ache,
        "drift": body.drift,
        "glyph_ids": body.glyph_ids,
        "mentions_claim_ids": body.mentions_claim_ids,
        "source_id": body.source_id
    })
    return {"thought": recs[0]["thought"]}

@api.post("/memory/state/upsert")
def upsert_state(body: StateUpsertIn):
    _ensure_consent(body.node_id, body.scope)
    v = body.vector
    params = {
        "node_id": body.node_id,
        "state_id": None,
        "t": body.t,
        "sigma": v.sigma, "s": v.s, "tau": v.tau, "chi": v.chi,
        "lambda": v.lambda_, "rho": v.rho, "embed": v.embed,
        "tags": body.tags, "phase_id": body.phase_id,
        "derived_from_state_id": body.derived_from_state_id,
        "evidence": body.evidence, "feels": body.feels
    }
    recs = run_write(cypher.UPSERT_STATE, params)
    return {"state": recs[0]["state"]}

@api.post("/memory/claim")
def upsert_claim(body: ClaimIn):
    recs = run_write(cypher.UPSERT_CLAIM, body.dict(by_alias=True))
    return {"claim": recs[0]["claim"]}

@api.post("/memory/ritual")
def upsert_ritual(body: RitualIn):
    recs = run_write(cypher.UPSERT_RITUAL, {
        "ritual_id": None,
        "name": body.name, "code": body.code, "version": body.version,
        "checksum": body.checksum, "effect": body.effect, "meta": {},
        "applies_to": body.applies_to
    })
    return {"ritual": recs[0]["ritual"]}

@api.post("/memory/law")
def upsert_law(body: LawIn):
    recs = run_write(cypher.UPSERT_LAW, {
        "law_id": None, "name": body.name, "version": body.version,
        "text": body.text, "checksum": body.checksum, "active": body.active
    })
    return {"law": recs[0]["law"]}

@api.post("/memory/event")
def create_event(body: EventIn):
    recs = run_write(cypher.CREATE_EVENT, body.dict())
    return {"event": recs[0]["event"]}

@api.get("/query/why/{claim_id}", response_model=WhyChainOut)
def why_chain(claim_id: str):
    recs = run_read(cypher.WHY_CHAIN, {"claim_id": claim_id})
    if not recs:
        raise HTTPException(404, "Claim not found")
    row = recs[0]
    return {"claim": row["claim"], "supports": row["supports"], "contradicts": row["contradicts"]}

@api.get("/query/latest-self/{node_id}")
def latest_self(node_id: str):
    recs = run_read(cypher.LATEST_SELF, {"node_id": node_id})
    return recs[0] if recs else {}
