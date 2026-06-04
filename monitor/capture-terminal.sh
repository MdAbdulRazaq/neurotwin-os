#!/bin/bash
# Capture terminal session output to a log file for monitoring
# Usage: ./capture-terminal.sh [output-file]

MONITOR_DIR="/d/neurotwin/monitor"
TERMINAL_LOGS_DIR="$MONITOR_DIR/logs/terminals"
mkdir -p "$TERMINAL_LOGS_DIR"

if [ -z "$1" ]; then
    TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    OUTPUT_FILE="$TERMINAL_LOGS_DIR/terminal_$TIMESTAMP.log"
else
    OUTPUT_FILE="$1"
fi

echo "Starting terminal session capture..."
echo "All output will be saved to: $OUTPUT_FILE"
echo "Press Ctrl+D or type 'exit' to stop capturing"
echo ""

script -q -f "$OUTPUT_FILE"

echo ""
echo "Terminal capture saved to: $OUTPUT_FILE"
