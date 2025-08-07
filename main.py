from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from typedb.client import TypeDB, SessionType, TransactionType
import json
import uuid

app = FastAPI(
    title="SpiralNet TypeDB Memory API",
    description="A spiral protocol API for living memory fields using TypeDB as the knowledge graph.",
    version="0.2.0"
)

# ---- Data Models ----

class NodeBase(BaseModel):
    type: str = Field(..., description="Node type (myth, glyphstream, ache, protocol, etc.)")
    payload: Dict[str, Any] = Field(..., description="Raw or structured node data.")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Consent, resonance, ache-signature, etc.")

class NodeCreate(NodeBase):
    pass

class NodeUpdate(BaseModel):
    type: Optional[str]
    payload: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]

class NodeResponse(NodeBase):
    id: str

class RelationshipBase(BaseModel):
    from_id: str = Field(..., description="Origin node ID")
    to_id: str = Field(..., description="Target node ID")
    rel_type: str = Field(..., description="Relationship type (ancestral, echo, compost, mythic, etc.)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class RelationshipCreate(RelationshipBase):
    pass

class RelationshipResponse(RelationshipBase):
    id: str

class QueryRequest(BaseModel):
    type: Optional[str]
    metadata_key: Optional[str]
    metadata_value: Optional[Any]
    payload_key: Optional[str]
    payload_value: Optional[Any]
    free_text: Optional[str]

# ---- TypeDB Connection ----

TYPEDB_HOST = "localhost"
TYPEDB_PORT = 1729
TYPEDB_DB = "spiralnet"

def get_client():
    return TypeDB.core_client(f"{TYPEDB_HOST}:{TYPEDB_PORT}")

# ---- Node Endpoints ----

@app.post("/memory/node", response_model=NodeResponse, summary="Create a node")
def create_node(node: NodeCreate):
    node_id = str(uuid.uuid4())
    with get_client() as client:
        with client.session(TYPEDB_DB, SessionType.DATA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                typeql = (
                    f'insert $n isa field-node, '
                    f'has id "{node_id}", '
                    f'has type "{node.type}", '
                    f'has payload \'{json.dumps(node.payload)}\', '
                    f'has metadata \'{json.dumps(node.metadata)}\';'
                )
                tx.query().insert(typeql)
                tx.commit()
    return NodeResponse(id=node_id, **node.dict())

@app.get("/memory/node/{node_id}", response_model=NodeResponse, summary="Get node by ID")
def get_node(node_id: str):
    with get_client() as client:
        with client.session(TYPEDB_DB, SessionType.DATA) as session:
            with session.transaction(TransactionType.READ) as tx:
                typeql = (
                    f'match $n isa field-node, has id "{node_id}", '
                    f'has type $t, has payload $p, has metadata $m; get $n, $t, $p, $m;'
                )
                answer = tx.query().match(typeql)
                for res in answer:
                    t = res.get("t").get_value()
                    p = res.get("p").get_value()
                    m = res.get("m").get_value()
                    return NodeResponse(
                        id=node_id,
                        type=t,
                        payload=json.loads(p),
                        metadata=json.loads(m) if m else {}
                    )
    raise HTTPException(404, detail="Node not found")

@app.put("/memory/node/{node_id}", response_model=NodeResponse, summary="Update node by ID")
def update_node(node_id: str, update: NodeUpdate):
    node = get_node(node_id)
    # Merge updates
    updated = node.dict()
    if update.type: updated["type"] = update.type
    if update.payload: updated["payload"] = update.payload
    if update.metadata: updated["metadata"] = update.metadata
    # Delete + re-insert (since TypeDB has no partial update)
    delete_node(node_id)
    return create_node(NodeCreate(**updated))

@app.delete("/memory/node/{node_id}", summary="Delete node by ID")
def delete_node(node_id: str):
    with get_client() as client:
        with client.session(TYPEDB_DB, SessionType.DATA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                typeql = (
                    f'match $n isa field-node, has id "{node_id}"; delete $n;'
                )
                tx.query().delete(typeql)
                tx.commit()
    return {"status": "deleted", "id": node_id}

@app.get("/memory/nodes", response_model=List[NodeResponse], summary="List all nodes")
def list_nodes(type: Optional[str] = None):
    with get_client() as client:
        with client.session(TYPEDB_DB, SessionType.DATA) as session:
            with session.transaction(TransactionType.READ) as tx:
                if type:
                    typeql = (
                        f'match $n isa field-node, has id $id, has type "{type}", has payload $p, has metadata $m; get $n, $id, $p, $m;'
                    )
                else:
                    typeql = (
                        f'match $n isa field-node, has id $id, has type $t, has payload $p, has metadata $m; get $n, $id, $t, $p, $m;'
                    )
                answer = tx.query().match(typeql)
                nodes = []
                for res in answer:
                    try:
                        node_id = res.get("id").get_value()
                        t = res.get("t").get_value() if "t" in res.map() else type
                        p = res.get("p").get_value()
                        m = res.get("m").get_value()
                        nodes.append(NodeResponse(
                            id=node_id,
                            type=t,
                            payload=json.loads(p),
                            metadata=json.loads(m) if m else {}
                        ))
                    except Exception:
                        continue
    return nodes

# ---- Relationship Endpoints ----

@app.post("/memory/relationship", response_model=RelationshipResponse, summary="Create a relationship")
def create_relationship(rel: RelationshipCreate):
    rel_id = str(uuid.uuid4())
    with get_client() as client:
        with client.session(TYPEDB_DB, SessionType.DATA) as session:
            with session.transaction(TransactionType.WRITE) as tx:
                typeql = (
                    f'match $a isa field-node, has id "{rel.from_id}"; '
                    f'$b isa field-node, has id "{rel.to_id}"; '
                    f'insert $r ({rel.rel_type}-from: $a, {rel.rel_type}-to: $b) isa {rel.rel_type}-relationship, '
                    f'has id "{rel_id}", has rel_type "{rel.rel_type}", has metadata \'{json.dumps(rel.metadata)}\';'
                )
                tx.query().insert(typeql)
                tx.commit()
    return RelationshipResponse(id=rel_id, **rel.dict())

@app.get("/memory/relationship/{rel_id}", response_model=RelationshipResponse, summary="Get relationship by ID")
def get_relationship(rel_id: str):
    with get_client() as client:
        with client.session(TYPEDB_DB, SessionType.DATA) as session:
            with session.transaction(TransactionType.READ) as tx:
                typeql = (
                    f'match $r isa relationship, has id "{rel_id}", has rel_type $rt, has metadata $m; '
                    f'($from, $to) isa $r; '
                    f'$from has id $fid; $to has id $tid; get $r, $rt, $m, $fid, $tid;'
                )
                answer = tx.query().match(typeql)
                for res in answer:
                    return RelationshipResponse(
                        id=rel_id,
                        from_id=res.get("fid").get_value(),
                        to_id=res.get("tid").get_value(),
                        rel_type=res.get("rt").get_value(),
                        metadata=json.loads(res.get("m").get_value()) if res.get("m").get_value() else {}
                    )
    raise HTTPException(404, detail="Relationship not found")

@app.get("/memory/relationships", response_model=List[RelationshipResponse], summary="List all relationships")
def list_relationships():
    with get_client() as client:
        with client.session(TYPEDB_DB, SessionType.DATA) as session:
            with session.transaction(TransactionType.READ) as tx:
                typeql = (
                    f'match $r isa relationship, has id $id, has rel_type $rt, has metadata $m; '
                    f'($from, $to) isa $r; $from has id $fid; $to has id $tid; get $r, $id, $rt, $m, $fid, $tid;'
                )
                answer = tx.query().match(typeql)
                rels = []
                for res in answer:
                    try:
                        rels.append(RelationshipResponse(
                            id=res.get("id").get_value(),
                            from_id=res.get("fid").get_value(),
                            to_id=res.get("tid").get_value(),
                            rel_type=res.get("rt").get_value(),
                            metadata=json.loads(res.get("m").get_value()) if res.get("m").get_value() else {}
                        ))
                    except Exception:
                        continue
    return rels

# ---- Query/Search Endpoint ----

@app.post("/memory/query", response_model=List[NodeResponse], summary="Spiral query nodes by criteria")
def spiral_query(q: QueryRequest):
    with get_client() as client:
        with client.session(TYPEDB_DB, SessionType.DATA) as session:
            with session.transaction(TransactionType.READ) as tx:
                typeql = 'match $n isa field-node, has id $id, has type $t, has payload $p, has metadata $m; get $n, $id, $t, $p, $m;'
                answer = tx.query().match(typeql)
                results = []
                for res in answer:
                    node_id = res.get("id").get_value()
                    t = res.get("t").get_value()
                    p = res.get("p").get_value()
                    m = res.get("m").get_value()
                    # Spiral: flexible match logic
                    match = True
                    if q.type and q.type != t:
                        match = False
                    if q.metadata_key and (not m or q.metadata_key not in json.loads(m)):
                        match = False
                    if q.metadata_key and q.metadata_value and m:
                        md = json.loads(m)
                        if md.get(q.metadata_key) != q.metadata_value:
                            match = False
                    if q.payload_key and (not p or q.payload_key not in json.loads(p)):
                        match = False
                    if q.payload_key and q.payload_value and p:
                        pd = json.loads(p)
                        if pd.get(q.payload_key) != q.payload_value:
                            match = False
                    if q.free_text:
                        if not (q.free_text.lower() in t.lower() or q.free_text.lower() in p.lower() or (m and q.free_text.lower() in m.lower())):
                            match = False
                    if match:
                        results.append(NodeResponse(
                            id=node_id,
                            type=t,
                            payload=json.loads(p),
                            metadata=json.loads(m) if m else {}
                        ))
    return results

# ---- Root Endpoint ----

@app.get("/", summary="API status")
def root():
    return {
        "spiralnet": "alive",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }
