import sys

with open('tests/test_persona.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = (
    "def _make_pg_conn(agent, rows):\n"
    '    """Return a mock asyncpg connection that returns `rows` from fetch()."""\n'
    "    conn = AsyncMock()\n"
    "    conn.fetch = AsyncMock(return_value=rows)\n"
    "    agent.pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)\n"
    "    agent.pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)\n"
    "    return conn"
)

new = (
    "def _make_pg_conn(agent, rows):\n"
    '    """Return a mock asyncpg connection that returns `rows` from fetch()."""\n'
    "    conn = AsyncMock()\n"
    "    conn.fetch = AsyncMock(return_value=rows)\n"
    "    cm = MagicMock()\n"
    "    cm.__aenter__ = AsyncMock(return_value=conn)\n"
    "    cm.__aexit__ = AsyncMock(return_value=False)\n"
    "    agent.pool.acquire = MagicMock(return_value=cm)\n"
    "    return conn"
)

if old not in content:
    print("PATTERN NOT FOUND")
    sys.exit(1)

content = content.replace(old, new, 1)
with open('tests/test_persona.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("PATCHED OK")
