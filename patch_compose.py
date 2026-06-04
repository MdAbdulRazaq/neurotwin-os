with open(r'D:\neurotwin\docker-compose.yml', 'r', encoding='utf-8') as f:
    c = f.read()

# Add DIGITAL_TWIN_URL to orchestrator env block
old = "      - DATABASE_URL=postgresql+asyncpg://neurotwin:password@postgres:5432/neurotwin_db\n    depends_on:\n      redis:\n        condition: service_healthy\n      postgres:\n        condition: service_healthy\n    healthcheck:\n      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8010/health\"]"

new = "      - DATABASE_URL=postgresql+asyncpg://neurotwin:password@postgres:5432/neurotwin_db\n      - DIGITAL_TWIN_URL=http://digital_twin:8014\n    depends_on:\n      redis:\n        condition: service_healthy\n      postgres:\n        condition: service_healthy\n      digital_twin:\n        condition: service_healthy\n    healthcheck:\n      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:8010/health\"]"

if old not in c:
    print("PATTERN NOT FOUND -- checking current compose...")
    # Print the orchestrator block for diagnosis
    start = c.find("  orchestrator:")
    print(repr(c[start:start+800]))
    import sys; sys.exit(1)

c = c.replace(old, new, 1)
with open(r'D:\neurotwin\docker-compose.yml', 'w', encoding='utf-8') as f:
    f.write(c)
print("PATCHED OK -- docker-compose.yml")
