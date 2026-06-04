# NEUROTWIN OS — Quick Reference Guide

## ⚡ Quick Start

### Start Everything
```powershell
cd D:\neurotwin
.\START_NEUROTWIN.ps1
```

### Health Check
```powershell
cd D:\neurotwin
.\CHECK_HEALTH.ps1
```

---

## 🔗 Service Endpoints

| Service | URL | Port |
|---------|-----|------|
| **Web Dashboard** | http://localhost | 80 |
| **Web (Direct)** | http://localhost:3000 | 3000 |
| **API** | http://localhost:8000 | 8000 |
| **Perception** | http://localhost:8001 | 8001 |
| **Memory** | http://localhost:8002 | 8002 |
| **Avatar** | http://localhost:8003 | 8003 |
| **Grafana** | http://localhost:3001 | 3001 |
| **Prometheus** | http://localhost:9090 | 9090 |
| **Neo4j** | http://localhost:7474 | 7474 |

---

## 📋 Container Management

### View all containers
```powershell
docker ps
```

### View container logs
```powershell
docker logs neurotwin-api -f      # Follow API logs
docker logs neurotwin-web -f      # Follow web logs
docker logs neurotwin-nginx -f    # Follow nginx logs
```

### Restart specific service
```powershell
cd D:\neurotwin
docker-compose restart api
docker-compose restart web
docker-compose restart nginx
```

### Stop everything
```powershell
cd D:\neurotwin
docker-compose down
```

### Start everything
```powershell
cd D:\neurotwin
docker-compose up -d
```

### Clean volumes and restart
```powershell
cd D:\neurotwin
docker-compose down -v
docker-compose up -d
```

---

## 🐛 Troubleshooting

### Docker daemon not responding
1. Kill all Docker processes
2. Restart Docker Desktop from Start Menu
3. Wait 45 seconds for daemon to initialize
4. Run health check

### Nginx not starting (SSL error)
- The nginx.conf has been fixed (HTTP only, no SSL)
- Restart nginx: `docker-compose restart nginx`

### API not responding
```powershell
docker logs neurotwin-api -f
# Check for database connection errors
```

### Web frontend not loading
```powershell
docker logs neurotwin-web -f
# Check for build errors
```

---

## 📍 Project Structure

```
D:\neurotwin\
├── services/           # Microservices (api, perception, avatar, memory, worker)
├── web/                # Next.js frontend
├── infra/
│   ├── nginx/          # Nginx configuration (fixed ✓)
│   ├── monitoring/     # Prometheus & Grafana
│   ├── sql/            # Database init scripts
│   └── terraform/      # IaC
├── docker-compose.yml  # All services defined
├── .env                # Environment variables
├── START_NEUROTWIN.ps1 # Startup script
└── CHECK_HEALTH.ps1    # Health check script
```

---

## 🔐 Environment Variables

All critical variables are in `D:\neurotwin\.env`:
- Database: `DATABASE_URL`
- Redis: `REDIS_URL`
- Neo4j: `NEO4J_URI`
- API Keys: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.

---

## 🚀 Next Steps

1. **Run the startup script**: `.\START_NEUROTWIN.ps1`
2. **Check health**: `.\CHECK_HEALTH.ps1`
3. **Open browser**: `http://localhost`
4. **View logs**: Monitor service logs as needed

---

**Created:** March 15, 2026  
**Status:** ✅ All systems configured and ready
