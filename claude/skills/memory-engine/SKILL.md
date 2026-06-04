# SKILL: memory-engine

## Purpose
Store and retrieve user context across sessions. Feeds short-term and semantic memory into every LLM prompt.

## Scope
services/api/app/core/memory.py, Redis, PostgreSQL conversation_messages, Neo4j graph

## Allowed Files
- services/api/app/core/memory.py
- services/api/app/routers/convo.py (context injection)
- services/api/app/core/neo4j_client.py

## Memory Layers
1. SHORT-TERM → Redis key `st:{user_id}:{session_id}` → last 20 messages
2. STRUCTURED → PostgreSQL conversation_messages table
3. GRAPH → Neo4j: User→Message→Session nodes
4. SEMANTIC → Pinecone (when API key set)

## Exact Tasks
1. Confirm store_message() writes to Redis AND PostgreSQL AND Neo4j
2. Confirm get_context_for_prompt() returns short-term list + semantic contexts
3. Verify memory injected into LLM system prompt as [Memory N]: blocks
4. Verify Neo4j node count increases after each message send

## Pass Criteria
- Redis key exists after message: `docker exec neurotwin-redis redis-cli keys "st:*"`
- PostgreSQL row exists: SELECT COUNT(*) FROM conversation_messages;
- Neo4j node: MATCH (m:Message) RETURN count(m); → > 0
- LLM prompt contains "Relevant memories" section

## Failure Rule
Never skip DB writes. If Pinecone key missing, gracefully skip — do not crash.

## Output Format
```json
{"short_term_count": N, "neo4j_nodes": N, "db_rows": N, "semantic_contexts": N}
```
