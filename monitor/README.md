# NEUROTWIN Activity Monitor

Real-time monitoring system for Docker containers, log files, and directory changes.

## Quick Start

```bash
# Start the monitor (from project root)
./monitor/neurotwin-monitor.sh
```

## What Gets Monitored

### Docker Container Logs
All running containers are monitored via `docker logs -f`. Unhealthy/stopped containers are skipped.

### Log Files
Tail -f style monitoring of:
- `/d/neurotwin/logs/app.log`
- `/d/neurotwin/logs/error.log`
- `docker-compose.yml` changes

### Directory Changes
File create/modify/delete/move events in:
- `/d/neurotwin/src`
- `/d/neurotwin/claude`
- `/d/neurotwin/monitor/logs`

## Capturing Another Terminal Session

To monitor output from another terminal running Claude (or any command):

1. Start capture in the other terminal:
```bash
./monitor/capture-terminal.sh
```

2. In your current terminal, start the monitor:
```bash
./monitor/neurotwin-monitor.sh
```

The captured terminal output will appear under `[terminals/...]` in the monitor.

## Customization

Edit `monitor/config.sh` to change what gets monitored:

```bash
# Add/remove containers
CONTAINERS=("neurotwin-api" "neurotwin-web" "my-custom-container")

# Add/remove log files
FILES_TO_WATCH=("/path/to/my.log" "/another/log.txt")

# Add/remove directories
DIRS_TO_WATCH=("/path/to/watch")
```

Then restart the monitor.

## Output Format

```
[container-name] 14:30:25 | log message here
[filename]      14:30:26 | log line
[DIR]           14:30:27 | /path | MODIFY | file.txt
```

Colors:
- Cyan: Docker container logs
- Magenta: File content changes
- White: Directory events
- Blue: Informational messages
- Yellow: Warnings
- Green: Success/startup messages

## Requirements

- `docker` CLI (for container logs)
- `inotifywait` (optional, for efficient file watching)
  - Install: `sudo apt-get install inotify-tools` (Linux) or `brew install inotify-tools` (macOS)

If `inotifywait` is not available, the script falls back to polling every 2 seconds.

## Stopping

Press `Ctrl+C` to stop all monitors cleanly.
