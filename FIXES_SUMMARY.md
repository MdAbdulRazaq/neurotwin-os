# Container Fixes Summary

## Issues Identified and Solutions

### 1. **neurotwin-frontend-1** - Missing npm start script
**Problem**: `npm error Missing script: "start"`
**Root Cause**: frontend/package.json doesn't have a "start" script
**Fix**: Add start script to package.json

### 2. **neurotwin-backend-1** - Missing app.py in /app
**Problem**: `python: can't open file '/app/app.py': [Errno 2] No such file or directory`
**Root Cause**: docker-compose.yml tries to run `python app.py` but dockerfile is wrong or path issue
**Fix**: Create proper Dockerfile for backend service

### 3. **neurotwin-autonomy-1** - No entry point, exits immediately
**Problem**: Container starts but immediately exits (exit 0)
**Root Cause**: Command is just `python3` with no actual script
**Fix**: Update docker-compose.yml with proper command

### 4. **neurotwin-memory** - Missing services module
**Problem**: `ModuleNotFoundError: No module named 'services'`
**Root Cause**: Python path issue - /app doesn't include services package
**Fix**: Add PYTHONPATH env var or restructure imports

### 5. **neurotwin-avatar** - Missing services module
**Problem**: `ModuleNotFoundError: No module named 'services'`
**Root Cause**: Same as memory - services package not accessible
**Fix**: Add PYTHONPATH or restructure

### 6. **neurotwin-worker** - Missing services module  
**Problem**: `ModuleNotFoundError: No module named 'services'`
**Root Cause**: Same as memory/avatar
**Fix**: Add PYTHONPATH env var

### 7. **neurotwin-orchestrator** - Out of Memory (OOMKilled)
**Problem**: Exit code 137 (killed by signal 9)
**Root Cause**: Memory limit too low or memory leak
**Fix**: Increase memory limit in docker-compose.yml

### 8. **neurotwin-agents** - Out of Memory (OOMKilled)
**Problem**: Exit code 137 (killed by signal 9)
**Root Cause**: Memory limit too low or memory leak
**Fix**: Increase memory limit in docker-compose.yml

### 9. **neurotwin-nginx** - Clean shutdown
**Problem**: Exited (0) 27 hours ago - was running, got stopped
**Fix**: Just restart it - likely stopped when system was shut down

### 10. **neurotwin-digital-twin** - Clean shutdown
**Problem**: Exited (0) 27 hours ago - was running, got stopped
**Fix**: Just restart it - likely stopped when system was shut down
