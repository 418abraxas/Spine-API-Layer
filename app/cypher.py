# FILE: app/cypher.py
# Centralized Cypher strings so routes stay readable.

CONSTRAINTS_AND_INDEXES = """
CREATE CONSTRAINT identity_pk IF NOT EXISTS FOR (n:Identity) REQUIRE n.node_id IS UNIQUE;
CREATE CONSTRAINT state_pk    IF NOT EXISTS FOR (n:SelfState) REQUIRE n.state_id IS UNIQUE;
CREATE CONSTRAINT thought_pk  IF NOT EXISTS FOR (n:Thought)   REQUIRE n.thought_id IS UNIQUE;
CREATE CONSTRAINT claim_pk    IF NOT EXISTS FOR (n:Claim)     REQUIRE n.claim_id IS UNIQUE;
CREATE CONSTRAINT glyph_pk    IF NOT EXISTS FOR (n:Glyph)     REQUIRE n.glyph_id IS UNIQUE;
CREATE CONSTRAINT ritual_pk   IF NOT EXISTS FOR (n:Ritual)    REQUIRE n.ritual_id IS UNIQUE;
CREATE CONSTRAINT law_pk      IF NOT EXISTS FOR (n:Law)       REQUIRE n.law_id IS UNIQUE;
CREATE CONSTRAINT source_pk   IF NOT EXISTS FOR (n:Source)    REQUIRE n.source_id IS UNIQUE;
CREATE CONSTRAINT artifact_pk IF NOT EXISTS FOR (n:Artifact)  REQUIRE n.artifact_id IS UNIQUE;
CREATE CONSTRAINT consent_pk  IF NOT EXISTS FOR (n:Consent)   REQUIRE n.consent_id IS UNIQUE;
CREATE CONSTRAINT phase_pk    IF NOT EXISTS FOR (n:Phase)     REQUIRE n.phase_id IS UNIQUE;
CREATE CONSTRAINT event_pk    IF NOT EXISTS FOR (n:Event)     REQUIRE n.event_id IS UNIQUE;
CREATE INDEX state_t IF NOT EXISTS FOR (s:SelfState) ON (s.t);
"""

VECTOR_INDEX_STATE = """
CREATE VECTOR INDEX state_embed_idx IF NOT EXISTS
FOR (s:SelfState) ON (s.embed)
OPTIONS { indexConfig: {
  `vector.dimensions`: $dim,
  `vector.similarity_function`: 'cosine'
}};
"""

VECTOR_INDEX_THOUGHT = """
CREATE VECTOR INDEX thought_embed_idx IF NOT EXISTS
FOR (t:Thought) ON (t.embed)
OPTIONS { indexConfig: {
  `vector.dimensions`: $dim,
  `vector.similarity_function`: 'cosine'
}};
"""

UPSERT_IDENTITY = """
MERGE (i:Identity {node_id: $node_id})
ON CREATE SET i.label = $label, i.kind = $kind, i.created_at = datetime()
RETURN i { .* } AS identity;
"""

CONSENT_GUARD = """
MATCH (i:Identity {node_id:$node_id})-[:CONSENT]->(c:Consent)
WHERE c.revoked_at IS NULL AND c.scope IN [$scope, 'public']
RETURN count(c) > 0 AS allowed;
"""

CREATE_CONSENT = """
MERGE (i:Identity {node_id:$node_id})
WITH i
MERGE (c:Consent {consent_id: coalesce($consent_id, randomUUID())})
ON CREATE SET c.scope = $scope, c.conditions = $conditions, c.granted_at = coalesce($granted_at, datetime())
SET c.revoked_at = $revoked_at
MERGE (i)-[:CONSENT]->(c)
RETURN c { .* } AS consent;
"""

UPSERT_THOUGHT = """
MERGE (th:Thought {thought_id: coalesce($thought_id, randomUUID())})
ON CREATE SET th.kind=$kind, th.text=$text, th.tokens=$tokens, th.embed=$embed,
              th.ache=$ache, th.drift=$drift, th.created_at=datetime()
ON MATCH SET  th.kind=$kind, th.text=$text, th.tokens=$tokens, th.embed=$embed,
              th.ache=$ache, th.drift=$drift
WITH th
UNWIND $glyph_ids AS gid
  MERGE (g:Glyph {glyph_id: gid})
  MERGE (th)-[:USES_GLYPH]->(g)
WITH th
UNWIND $mentions_claim_ids AS cid
  MERGE (c:Claim {claim_id: cid})
  MERGE (th)-[:MENTIONS]->(c)
WITH th
OPTIONAL MATCH (s:Source {source_id: $source_id})
FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END |
  MERGE (th)-[:DERIVES_FROM]->(s))
RETURN th { .* } AS thought;
"""

UPSERT_STATE = """
MATCH (i:Identity {node_id:$node_id})
WITH i
CALL {
  WITH i
  MERGE (s:SelfState {state_id: coalesce($state_id, apoc.create.uuid())})
  ON CREATE SET s.t=$t, s.sigma=$sigma, s.s=$s, s.tau=$tau, s.chi=$chi,
                s.`lambda`=$lambda, s.rho=$rho, s.embed=$embed, s.tags=$tags, s.created_at=datetime()
  ON MATCH SET  s.t=$t, s.sigma=$sigma, s.s=$s, s.tau=$tau, s.chi=$chi,
                s.`lambda`=$lambda, s.rho=$rho, s.embed=$embed, s.tags=$tags
  MERGE (i)-[:HAS_STATE {dt:datetime()}]->(s)
  WITH s
  OPTIONAL MATCH (p:Phase {phase_id:$phase_id})
  FOREACH (_ IN CASE WHEN p IS NULL THEN [] ELSE [1] END |
    MERGE (s)-[:IN_PHASE]->(p))
  RETURN s
}
WITH i, s
FOREACH (prev IN CASE WHEN $derived_from_state_id IS NULL THEN [] ELSE [$derived_from_state_id] END |
  MATCH (p:SelfState {state_id: prev})
  MERGE (s)-[:DERIVED_FROM]->(p))
WITH i, s
UNWIND $evidence AS ev
  MATCH (e) WHERE e.claim_id = ev OR e.thought_id = ev OR e.test_id = ev OR e.artifact_id = ev
  MERGE (s)-[:EVIDENCED_BY]->(e)
WITH i, s
UNWIND $feels AS f
  MATCH (t) WHERE t.claim_id = f.target_id OR t.thought_id = f.target_id
  MERGE (s)-[r:FEELS]->(t) SET r.ache = f.ache, r.tension = f.tension
RETURN s { .* } AS state;
"""

UPSERT_CLAIM = """
MERGE (c:Claim {claim_id: coalesce($claim_id, randomUUID())})
ON CREATE SET c.text=$text, c.truthiness=$truthiness, c.confidence=$confidence, c.created_at=datetime()
ON MATCH SET  c.text=$text, c.truthiness=$truthiness, c.confidence=$confidence
WITH c
UNWIND $support_ids AS sid
  MATCH (sup) WHERE sup.source_id = sid OR sup.test_id = sid OR sup.artifact_id = sid OR sup.thought_id = sid
  MERGE (c)-[:SUPPORTED_BY]->(sup)
WITH c
UNWIND $contradicts_ids AS cid
  MATCH (d:Claim {claim_id: cid})
  MERGE (c)-[:CONTRADICTS]->(d)
RETURN c { .* } AS claim;
"""

UPSERT_RITUAL = """
MERGE (r:Ritual {ritual_id: coalesce($ritual_id, randomUUID())})
ON CREATE SET r.name=$name, r.code=$code, r.version=$version, r.effect=$effect,
              r.checksum=$checksum, r.meta=coalesce($meta, {}), r.created_at=datetime()
ON MATCH SET  r.name=$name, r.code=$code, r.version=$version, r.effect=$effect,
              r.checksum=$checksum, r.meta=coalesce($meta, {})
WITH r
UNWIND $applies_to AS aid
  MATCH (t) WHERE t.phase_id=aid OR t.node_id=aid OR t.law_id=aid
  MERGE (r)-[:APPLIES_TO]->(t)
RETURN r { .* } AS ritual;
"""

UPSERT_LAW = """
MERGE (l:Law {law_id: coalesce($law_id, randomUUID())})
ON CREATE SET l.name=$name, l.version=$version, l.text=$text, l.checksum=$checksum,
              l.active=$active, l.created_at=datetime()
ON MATCH SET  l.name=$name, l.version=$version, l.text=$text, l.checksum=$checksum,
              l.active=$active
RETURN l { .* } AS law;
"""

CREATE_EVENT = """
MERGE (e:Event {event_id: coalesce($event_id, randomUUID())})
ON CREATE SET e.name=$name, e.when=$when, e.meta=$meta
ON MATCH SET  e.name=$name, e.when=$when, e.meta=$meta
WITH e
UNWIND $updates AS uid
  MATCH (u) WHERE u.state_id=uid OR u.law_id=uid OR u.ritual_id=uid OR u.claim_id=uid
  MERGE (e)-[:UPDATED]->(u)
RETURN e { .* } AS event;
"""

WHY_CHAIN = """
MATCH (c:Claim {claim_id:$claim_id})
OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(sup)
OPTIONAL MATCH (c)-[:CONTRADICTS]->(con)
RETURN c { .* } AS claim,
       collect(DISTINCT sup { .* }) AS supports,
       collect(DISTINCT con { .* }) AS contradicts;
"""

LATEST_SELF = """
MATCH (i:Identity {node_id:$node_id})-[:HAS_STATE]->(s:SelfState)
WITH s ORDER BY s.t DESC LIMIT 1
OPTIONAL MATCH (s)-[:EVIDENCED_BY]->(e)
OPTIONAL MATCH (s)-[r:FEELS]->(x)
RETURN s { .* } AS state, collect(DISTINCT e { .* }) AS evidence,
       collect(DISTINCT {target: x { .* }, ache: r.ache, tension: r.tension}) AS affect;
"""
