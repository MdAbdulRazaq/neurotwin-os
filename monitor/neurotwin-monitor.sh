#!/bin/bash
# NEUROTWIN Comprehensive Activity Monitor
# Watches Docker logs, log files, and directory changes in real-time

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Configuration
MONITOR_DIR="/d/neurotwin/monitor"
LOG_DIR="$MONITOR_DIR/logs"
DOCKER_LOGS_DIR="$LOG_DIR/docker"
FILE_LOGS_DIR="$LOG_DIR/files"
mkdir -p "$DOCKER_LOGS_DIR" "$FILE_LOGS_DIR"

# Default configuration (can be overridden by config.sh)
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

FILES_TO_WATCH=(
    "/d/neurotwin/logs/app.log"
    "/d/neurotwin/logs/error.log"
    "/d/neurotwin/docker-compose.yml"
)

DIRS_TO_WATCH=(
    "/d/neurotwin/src"
    "/d/neurotwin/claude"
)

# Load custom config if exists
CONFIG_FILE="$MONITOR_DIR/config.sh"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# PID tracking
PIDS=()

# Cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}[MONITOR] Stopping all watchers...${NC}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    exit 0
}
trap cleanup INT TERM EXIT

# Log with timestamp and source
log_container() {
    local container=$1
    while IFS= read -r line; do
        [ -n "$line" ] && echo -e "${CYAN}[$container]${NC} $(date '+%H:%M:%S') | $line"
    done
}

log_file() {
    local file=$1
    local name=$(basename "$file")
    while IFS= read -r line; do
        [ -n "$line" ] && echo -e "${MAGENTA}[$name]${NC} $(date '+%H:%M:%S') | $line"
    done
}

# Start Docker log monitors
start_docker_monitors() {
    echo -e "${GREEN}[MONITOR] Starting Docker container log watchers...${NC}"
    for container in "${CONTAINERS[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^$container$"; then
            echo -e "${BLUE}  - Monitoring container: $container${NC}"
            docker logs -f --tail 0 "$container" 2>/dev/null | log_container "$container" &
            PIDS+=($!)
        else
            echo -e "${YELLOW}  - Skipping (not running): $container${NC}"
        fi
    done
}

# Start file monitors (using inotifywait if available, else polling)
start_file_monitors() {
    echo -e "${GREEN}[MONITOR] Starting file watchers...${NC}"

    if command -v inotifywait &> /dev/null; then
        echo -e "${BLUE}  Using inotifywait for file monitoring${NC}"
        for file in "${FILES_TO_WATCH[@]}"; do
            if [ -f "$file" ]; then
                echo -e "${BLUE}  - Watching file: $file${NC}"
                while inotifywait -e modify,move_self,create "$file" 2>/dev/null; do
                    [ -f "$file" ] && tail -n 1 "$file" 2>/dev/null | log_file "$file" || true
                done &
                PIDS+=($!)
            else
                echo -e "${YELLOW}  - File not found (will create if appears): $file${NC}"
                dir=$(dirname "$file")
                while inotifywait -e create -e moved_to "$dir" 2>/dev/null; do
                    if [ -f "$file" ]; then
                        echo -e "${GREEN}[MONITOR] File created: $file${NC}"
                        tail -f "$file" 2>/dev/null | log_file "$file" &
                        PIDS+=($!)
                        break
                    fi
                done &
                PIDS+=($!)
            fi
        done
    else
        echo -e "${YELLOW}  inotifywait not available - falling back to polling every 2s${NC}"
        for file in "${FILES_TO_WATCH[@]}"; do
            (
                last_size=0
                while true; do
                    if [ -f "$file" ]; then
                        current_size=$(stat -c%s "$file" 2>/dev/null || echo 0)
                        if [ "$current_size" -gt "$last_size" ]; then
                            tail -c +$((last_size + 1)) "$file" 2>/dev/null | log_file "$file" || true
                            last_size=$current_size
                        fi
                    fi
                    sleep 2
                done
            ) &
            PIDS+=($!)
        done
    fi
}

# Start directory change monitors
start_dir_monitors() {
    echo -e "${GREEN}[MONITOR] Starting directory change watchers...${NC}"
    if command -v inotifywait &> /dev/null; then
        for dir in "${DIRS_TO_WATCH[@]}"; do
            if [ -d "$dir" ]; then
                echo -e "${BLUE}  - Watching directory: $dir${NC}"
                (
                    inotifywait -m -r -e create,modify,delete,move "$dir" 2>/dev/null | while read -r path event file; do
                        echo -e "${WHITE}[DIR]${NC} $(date '+%H:%M:%S') | $dir | $event | $file"
                    done
                ) &
                PIDS+=($!)
            else
                echo -e "${YELLOW}  - Directory not found: $dir${NC}"
            fi
        done
    else
        echo -e "${YELLOW}  inotifywait not available - skipping directory monitoring${NC}"
    fi
}

# Main
clear
echo -e "${GREEN}=== NEUROTWIN ACTIVITY MONITOR ===${NC}"
echo -e "Started at: $(date)"
echo -e "Monitoring:"
echo -e "  - ${CYAN}Docker containers${NC}: ${CONTAINERS[*]}"
echo -e "  - ${MAGENTA}Log files${NC}: ${FILES_TO_WATCH[*]}"
echo -e "  - ${WHITE}Directories${NC}: ${DIRS_TO_WATCH[*]}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

start_docker_monitors
start_file_monitors
start_dir_monitors

# Wait for all background processes
wait
