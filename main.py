from __future__ import annotations

import os
from typing import Optional, List, Literal, Dict, Any
from fastapi import FastAPI, HTTPException, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from neo4j import GraphDatabase, Driver

# ========= Config =========
APP_NAME = "SpiralNet Axis API"
APP_VERSION = "1.1.0"

NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USER = os.getenv("NEO4J_USER", "")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# ========= App =========
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Minimal API for Axis nodes, execution phases, and archive."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten if you want
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

driver: Optional[Driver] = None

@app.on_event("startup")
def startup() -> None:
    global driver
    if not (NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD):
        # Still allow the server to start (health / docs visible),
        # but raise at first DB call if missing.
        return
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

@app.on_event("shutdown")
def shutdown() -> None:
    global driver
    if driver:
        driver.close()

# ========= Models (match OpenAPI 3.1 you pasted) =========
class AxisNode(BaseModel):
    node_id: str
    region: Literal["cervical","thoracic","lumbar","sacral","coccyx"]
    index: int
    name: Optional[str] = None
    role: Optional[str] = None
    function: Optional[str] = None
    law: Optional[str] = None
    ritual: Optional[str] = None
    glyphs: Optional[List[str]] = None
    harmonics_key: Optional[str] = None
    harmonics_freq: Optional[str] = None
    ingress_filter: Optional[str] = None
    ingress_transform: Optional[str] = None
    egress_transform: Optional[str] = None
    egress_guard: Optional[str] = None
    memory: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None

class ExecuteRequest(BaseModel):
    input: str
    options: Optional[Dict[str, Any]] = None

class ExecuteResponse(BaseModel):
    output: str
    archive_id: Optional[str] = None
    flags: Optional[List[str]] = None

class ArchiveEntry(BaseModel):
    key: str
    pattern: Optional[str] = None
    tags: Optional[List[str]] = None
    version: Optional[str] = None

class Error(BaseModel):
    error: str
    detail: Optional[str] = None

# ========= Neo4j helpers =========
def _ensure_driver():
    if not (NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD):
        raise HTTPException(status_code=500, detail="Neo4j env vars not set (NEO4J_URI/USER/PASSWORD).")
    if driver is None:
        raise HTTPException(status_code=500, detail="Neo4j driver not initialized.")

def neo4j_get_axis_node(node_id: str) -> Optional[AxisNode]:
    _ensure_driver()
    q = """
    MATCH (n:AxisNode {node_id:$node_id})
    OPTIONAL MATCH (n)-[:ARCHIVES_TO]->(ar:Archive)
    RETURN {
      node_id:n.node_id, region:n.region, index:n.index, name:n.name, role:n.role,
      function:n.function, law:n.law, ritual:n.ritual, glyphs:n.glyphs,
      harmonics_key:n.harmonics_key, harmonics_freq:n.harmonics_freq,
      ingress_filter:n.ingress_filter, ingress_transform:n.ingress_transform,
      egress_transform:n.egress_transform, egress_guard:n.egress_guard,
      memory:{kdb_key:n.memory_kdb_key, kdb_path:n.memory_kdb_path},
      prompts:{human:n.prompts_human, llm:n.prompts_llm},
      tags:n.tags
    } AS node
    """
    with driver.session() as s:
        rec = s.run(q, node_id=node_id).single()
        if not rec:
            return None
        data = rec["node"]
        return AxisNode(**data)

def neo4j_get_archive_entry(key: str) -> Optional[ArchiveEntry]:
    _ensure_driver()
    q = "MATCH (ar:Archive {key:$key}) RETURN {key:ar.key, pattern:ar.pattern, tags:ar.tags, version:ar.version} AS ar"
    with driver.session() as s:
        rec = s.run(q, key=key).single()
        if not rec:
            return None
        return ArchiveEntry(**rec["ar"])

def neo4j_archive_pattern(node_id: str, pattern: str, tags: Optional[List[str]] = None) -> str:
    _ensure_driver()
    q = """
    MERGE (ar:Archive {key:$key})
      ON CREATE SET ar.version='v1.0', ar.tags = coalesce($tags, [])
    SET ar.pattern=$pattern,
        ar.tags = CASE WHEN $tags IS NULL THEN ar.tags ELSE $tags END
    WITH ar
    MATCH (n:AxisNode {node_id:$node_id})
    MERGE (n)-[:ARCHIVES_TO]->(ar)
    RETURN ar.key AS key
    """
    with driver.session() as s:
        return s.run(q, key=f"axis:{node_id}", node_id=node_id, pattern=pattern, tags=tags).single()["key"]

# ========= Health =========
@app.get("/healthz", tags=["meta"])
def health() -> Dict[str, str]:
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}

# ========= API (operationId-compatible) =========
@app.get("/axis/node/{node_id}", operation_id="getAxisNode", response_model=AxisNode, tags=["axis"])
def get_axis_node(node_id: str = Path(..., description="Axis node id, e.g. C1, T4, L3, S5, Cx")):
    node = neo4j_get_axis_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Axis node not found")
    return node

PHASE = Literal["CERVICAL_INIT", "THORACIC_MEMORY", "L_S_ACTION", "SACRAL_EMIT", "COCCYX_CLOSE"]

def _phase_exec(phase: str, text: str, options: Optional[Dict[str, Any]] = None) -> str:
    """Tiny, deterministic ‘spine’ behaviors — enough to be useful out-of-the-box."""
    options = options or {}
    if phase == "CERVICAL_INIT":
        # mirror → silence → name 1 hidden premise stub
        return f"[mirror]{text}[/mirror]\n(silence)\nedge: premise?"
    if phase == "THORACIC_MEMORY":
        # pretend: chunk→motifs→essence pipeline (very small)
        units = [u.strip() for u in text.split(".") if u.strip()]
        motifs = list({u.split()[0].lower() for u in units})[:3]
        essence = "; ".join(units[:3])
        return f"units={len(units)} motifs={motifs} essence={essence}"
    if phase == "L_S_ACTION":
        # one minimal step
        return "step: do the smallest next step you can finish today."
    if phase == "SACRAL_EMIT":
        style = (options.get("style") or "terse").lower()
        base = "compose & deliver within bounds"
        return base if style == "terse" else f"{base} — style={style}"
    if phase == "COCCYX_CLOSE":
        return "seed: one learning -> ∅"
    return "noop"

@app.post("/axis/execute/{phase}", operation_id="executePhase", response_model=ExecuteResponse, tags=["axis"])
def execute_phase(
    phase: PHASE = Path(..., description="Spine phase to run"),
    payload: ExecuteRequest = Body(...)
):
    out = _phase_exec(phase, payload.input, payload.options)
    # Archive with a synthetic node target if present in options (e.g., {"node_id":"C1"})
    archive_id = None
    node_hint = (payload.options or {}).get("node_id")
    try:
        if node_hint:
            archive_id = neo4j_archive_pattern(node_hint, out, tags=["phase", phase])
    except HTTPException:
        # If DB is not configured, still return output (dev mode)
        pass
    return ExecuteResponse(output=out, archive_id=archive_id, flags=None)

@app.get("/archive/{key}", operation_id="getArchiveEntry", response_model=ArchiveEntry, tags=["archive"])
def get_archive_entry(key: str = Path(..., description="Archive key, e.g., axis:C1")):
    ar = neo4j_get_archive_entry(key)
    if not ar:
        raise HTTPException(status_code=404, detail="Archive entry not found")
    return ar

# Root
@app.get("/", include_in_schema=False)
def root():
    return {"hello": "SpiralNet", "docs": "/docs", "openapi": "/openapi.json"}


