---
name: Engine Routing
description: 8-core engine routing table for NEUROTWIN OS
type: reference
---

## NEUROTWIN OS Engine Routing Table

| User Intent | Route To | Skill Path |
|---|---|---|
| system health check | system-check | `claude/skills/system-check/SKILL.md` |
| voice / emotion detection | perception-engine | `claude/skills/perception-engine/SKILL.md` |
| memory / recall / context | memory-engine | `claude/skills/memory-engine/SKILL.md` |
| LLM / reasoning / response | cognition-engine | `claude/skills/cognition-engine/SKILL.md` |
| tone / personality / warmth | personality-engine | `claude/skills/personality-engine/SKILL.md` |
| emotion state / mood | emotion-engine | `claude/skills/emotion-engine/SKILL.md` |
| behavioral model / twin | behavior-engine | `claude/skills/behavior-engine/SKILL.md` |
| avatar / lip sync / expression | avatar-engine | `claude/skills/avatar-engine/SKILL.md` |
| character design / anime look | visual-identity-engine | `claude/skills/visual-identity-engine/SKILL.md` |
| dashboard / metrics | analytics-engine | `claude/skills/analytics-engine/SKILL.md` |
| full pipeline test | e2e-test-engine | `claude/skills/e2e-test-engine/SKILL.md` |
| conversation summary | summarizer-engine | `claude/skills/summarizer-engine/SKILL.md` |

## Engine Responsibilities

- **system-check**: Validate all services are running, database connections, container health
- **perception-engine**: Speech-to-text, voice emotion detection, audio preprocessing
- **memory-engine**: Memory storage, retrieval, context windows, vector search
- **cognition-engine**: LLM interaction, reasoning, response generation
- **personality-engine**: Tone adjustment, warmth, conversational style, persona management
- **emotion-engine**: Track and respond to user emotional state, mood analysis
- **behavior-engine**: Behavioral modeling, twin simulation, pattern recognition
- **avatar-engine**: 3D/2D avatar rendering, lip-sync, facial expressions
- **visual-identity-engine**: Character design, anime-style customization, visual branding
- **analytics-engine**: Metrics, dashboards, engagement tracking, mood timelines
- **summarizer-engine**: Conversation summaries, session recaps, insights extraction
- **e2e-test-engine**: Full pipeline integration tests across all services

## Critical Orchestration Rules

1. **ALWAYS run system-check first** before any engine work
2. **Never merge engine responsibilities** - one engine = one subagent = one SKILL.md
3. **Follow the strict build order** when constructing/rebuilding the platform

## Available Engines in claude/skills/

All 12 engines exist with SKILL.md defining their capabilities:
```
claude/skills/
├── analytics-engine/
├── avatar-engine/
├── behavior-engine/
├── code-review-graph-integration/
├── cognition-engine/
├── e2e-test-engine/
├── emotion-engine/
├── grafana-observability/
├── image-generation/
├── memory-engine/
├── n8n-automation/
├── perception-engine/
├── personality-engine/
├── playwright-e2e/
├── ruflo-integration/
├── sentry-triage/
├── summarizer-engine/
├── supabase-integration/
├── system-check/
└── visual-identity-engine/
```
