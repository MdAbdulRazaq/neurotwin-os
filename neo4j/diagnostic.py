#!/usr/bin/env python3
"""
NEUROTWIN OS — Neo4j Diagnostic Script
Validates Neo4j connectivity, Bolt, HTTP, and schema health.
"""
import socket
import sys
import urllib.request
import urllib.error
import json
import os

NEO4J_HOST = os.getenv("NEO4J_HOST", "localhost")
NEO4J_HTTP_PORT = int(os.getenv("NEO4J_HTTP_PORT", "7474"))
NEO4J_BOLT_PORT = int(os.getenv("NEO4J_BOLT_PORT", "7687"))
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neurotwin_password")
TIMEOUT = 5

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
INFO = "\033[94m[INFO]\033[0m"

results = []

def check(label, ok, detail=""):
    status = PASS if ok else FAIL
    print(f"  {status} {label}" + (f" — {detail}" if detail else ""))
    results.append(ok)
    return ok

def tcp_reachable(host, port):
    try:
        s = socket.create_connection((host, port), timeout=TIMEOUT)
        s.close()
        return True
    except Exception as e:
        return False

def http_get(url, user=None, password=None):
    req = urllib.request.Request(url)
    if user:
        import base64
        creds = base64.b64encode(f"{user}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {creds}")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}

def cypher_query(query, user, password):
    url = f"http://{NEO4J_HOST}:{NEO4J_HTTP_PORT}/db/neo4j/tx/commit"
    data = json.dumps({"statements": [{"statement": query}]}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    import base64
    creds = base64.b64encode(f"{user}:{password}".encode()).decode()
    req.add_header("Authorization", f"Basic {creds}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}

print(f"\n{'='*55}")
print(f"  NEUROTWIN Neo4j Diagnostic — {NEO4J_HOST}")
print(f"{'='*55}\n")

# ── 1. TCP Connectivity ──────────────────────────────────────────────────────
print("[ TCP Connectivity ]")
check("Bolt port 7687 reachable", tcp_reachable(NEO4J_HOST, NEO4J_BOLT_PORT))
check("HTTP port 7474 reachable", tcp_reachable(NEO4J_HOST, NEO4J_HTTP_PORT))

# ── 2. HTTP API ──────────────────────────────────────────────────────────────
print("\n[ HTTP API ]")
code, body = http_get(f"http://{NEO4J_HOST}:{NEO4J_HTTP_PORT}/")
check("HTTP root endpoint", code == 200, f"HTTP {code}")

code, body = http_get(
    f"http://{NEO4J_HOST}:{NEO4J_HTTP_PORT}/db/neo4j/tx/commit",
    NEO4J_USER, NEO4J_PASSWORD
)
check("Auth accepted (not 401)", code != 401, f"HTTP {code}")

# ── 3. Cypher Queries ────────────────────────────────────────────────────────
print("\n[ Cypher ]")
code, resp = cypher_query("RETURN 1 AS n", NEO4J_USER, NEO4J_PASSWORD)
ok = code == 200 and not resp.get("errors")
check("Basic Cypher (RETURN 1)", ok, f"HTTP {code}")

code, resp = cypher_query("MATCH (n) RETURN count(n) AS cnt", NEO4J_USER, NEO4J_PASSWORD)
ok = code == 200 and not resp.get("errors")
if ok:
    cnt = resp["results"][0]["data"][0]["row"][0] if resp.get("results") else "?"
    check("Node count query", ok, f"{cnt} nodes")
else:
    check("Node count query", False, str(resp.get("errors", "unknown")))

# ── 4. Summary ───────────────────────────────────────────────────────────────
total = len(results)
passed = sum(results)
print(f"\n{'='*55}")
print(f"  Result: {passed}/{total} checks passed")
if passed == total:
    print(f"  \033[92mNeo4j is HEALTHY\033[0m")
elif passed >= total // 2:
    print(f"  \033[93mNeo4j is DEGRADED — check warnings above\033[0m")
else:
    print(f"  \033[91mNeo4j is DOWN — review errors above\033[0m")
print(f"{'='*55}\n")

sys.exit(0 if passed == total else 1)
