# SKILL: code-review-graph-integration

## Purpose
Apply tirth8205/code-review-graph Neo4j patterns to extend NEUROTWIN's Digital Twin behavioral graph.

## Repo Location
D:\neurotwin\external\code-review-graph\

## What Code-Review-Graph Provides
- Neo4j graph schema for relationship modeling
- Node and edge patterns for AI-based analysis
- Graph traversal queries for pattern detection
- Visualization of graph-based insights

## Integration Points for NEUROTWIN

### 1. Extend Neo4j Graph Schema
Current NEUROTWIN nodes: User, Session, Message
Add from code-review-graph patterns:
- (User)-[HAS_PATTERN]->(EmotionPattern)
- (User)-[PREFERS]->(Topic)
- (Topic)-[RELATED_TO]->(Topic)
- (Session)-[FOLLOWS]->(Session)
- (Message)-[TRIGGERS]->(EmotionPattern)

### 2. Graph Query Patterns
Borrow Cypher query patterns for:
- Finding recurring topics: MATCH (u:User)-[SENT]->(m:Message) WHERE m.content CONTAINS $topic
- Emotion trend analysis: MATCH (m:Message) RETURN m.emotion, count(m) ORDER BY count(m) DESC
- Session pattern: MATCH path=(s1:Session)-[FOLLOWS*]->(s2:Session) RETURN path

### 3. Visualization
Code-review-graph's visualization approach → NEUROTWIN dashboard graph view
Shows user's behavioral twin as a live knowledge graph

## Reading Plan
1. Read D:\neurotwin\external\code-review-graph\README.md
2. Find Neo4j schema definitions
3. Extract Cypher queries applicable to conversation analysis
4. Add new relationship types to neo4j_client.py

## New neo4j_client.py methods to add
- create_topic_node(user_id, topic, session_id)
- create_emotion_pattern(user_id, emotion, frequency)
- link_session_chain(prev_session_id, next_session_id)
- get_user_twin_profile(user_id) → behavioral summary

## Output Format
```json
{"neo4j_schema_extended": true, "new_node_types": 3, "new_relationship_types": 4, "twin_profile_queryable": true}
```
