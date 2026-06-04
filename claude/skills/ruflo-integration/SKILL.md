# SKILL: ruflo-integration

## Purpose
Integrate ruvnet/ruflo agent orchestration patterns into NEUROTWIN's 8-engine subagent architecture.

## Repo Location
D:\neurotwin\external\ruflo\

## What Ruflo Provides
- Multi-agent orchestration framework
- Skill/tool chaining pattern (maps to NEUROTWIN SKILL.md system)
- Agent dispatcher with intent routing
- Reusable playbook execution

## Integration Points for NEUROTWIN

### 1. Orchestrator Pattern
Ruflo's agent dispatcher → NEUROTWIN's CLAUDE.md router
Apply Ruflo's intent→agent routing logic to upgrade CLAUDE.md

### 2. Skill Chain Pattern
Ruflo's skill playbooks → NEUROTWIN's SKILL.md files
Each NEUROTWIN engine can use Ruflo's execution pattern

### 3. State Management
Ruflo's agent state → NEUROTWIN's Redis session state
Map Ruflo's stateful agent context to Redis key pattern

## Reading Plan
1. Read D:\neurotwin\external\ruflo\README.md — understand architecture
2. Read D:\neurotwin\external\ruflo\src\ — find agent dispatcher code
3. Extract patterns applicable to NEUROTWIN's 8 engines
4. Write integration notes to D:\neurotwin\claude\skills\ruflo-integration\NOTES.md

## Output Format
```json
{"ruflo_patterns_extracted": ["orchestrator", "skill_chain", "state_mgmt"], "applied_to": ["CLAUDE.md", "cognition-engine"]}
```
