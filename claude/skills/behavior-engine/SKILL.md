# SKILL: behavior-engine (Digital Twin)

## Purpose
Learn and model user behavioral patterns over time. Build the user's digital twin profile.

## Scope
services/api/app/core/neo4j_client.py, services/api/app/core/memory.py
Neo4j graph database (bolt://neurotwin-neo4j:7687)

## Graph Schema
Nodes: User, Session, Message, Topic, EmotionPattern, Preference
Relationships:
- (User)-[SENT]->(Message)
- (Message)-[PART_OF_SESSION]->(Session)
- (User)-[HAS_PATTERN]->(EmotionPattern)
- (User)-[PREFERS]->(Topic)
- (Session)-[FOLLOWS]->(Session) -- temporal chain

## Behavioral Signals to Track
- Most active hours (from session timestamps)
- Most discussed topics (keyword extraction from messages)
- Dominant emotion per day/week
- Average session length
- Response length preference (short vs detailed answers)
- Question frequency (does user ask more than tell?)

## Twin Profile Structure
```json
{
  "user_id": "uuid",
  "dominant_emotion": "joy",
  "top_topics": ["work", "family", "creativity"],
  "avg_session_length_min": 12.4,
  "peak_activity_hour": 21,
  "prefers_detailed_responses": false,
  "emotional_volatility": 0.3
}
```

## Neo4j Queries (canonical)
Pattern count: MATCH (u:User {id:$uid})-[SENT]->(m:Message) RETURN count(m)
Emotion trend: MATCH (m:Message {user_id:$uid}) RETURN m.emotion, count(m) ORDER BY count(m) DESC

## Pass Criteria
- Neo4j nodes increment after every message send
- Twin profile queryable from Neo4j
- Behavior data feeds into cognition engine system prompt

## Output Format
```json
{"twin_profile_built": true, "neo4j_nodes": 4, "top_topic": "work", "dominant_emotion": "joy"}
```
