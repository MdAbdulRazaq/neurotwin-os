# NEUROTWIN Monitor Configuration
# Edit this file to customize what gets monitored

# Docker containers to monitor (space-separated)
CONTAINERS=(
    "neurotwin-web"
    "neurotwin-action"
    "neurotwin-voice"
    "neurotwin-prediction"
    "neurotwin-orchestrator"
    "neurotwin-agents"
    "neurotwin-avatar"
    "neurotwin-behavior"
    "neurotwin-api"
    "neurotwin-memory"
    "neurotwin-perception"
    "neurotwin-worker"
    "neurotwin-postgres"
    "neurotwin-redis"
    "neurotwin-neo4j"
)

# Log files to watch (space-separated paths)
FILES_TO_WATCH=(
    "/d/neurotwin/logs/app.log"
    "/d/neurotwin/logs/error.log"
    "/d/neurotwin/docker-compose.yml"
)

# Directories to watch for changes (space-separated paths)
DIRS_TO_WATCH=(
    "/d/neurotwin/src"
    "/d/neurotwin/claude"
    "/d/neurotwin/monitor/logs"
)
