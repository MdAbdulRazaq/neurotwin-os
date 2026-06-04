import pathlib, sys
p = pathlib.Path("app/main.py")
t = p.read_text()
changed = False
for old, new in [
    ('docs_url=None', 'docs_url="/docs"'),
    ('redoc_url=None', 'redoc_url="/redoc"'),
]:
    if old in t:
        t = t.replace(old, new)
        changed = True
if not changed:
    if 'docs_url="/docs"' in t or "docs_url='/docs'" in t:
        print("SKIP: docs already enabled"); sys.exit(0)
    for line in t.splitlines():
        if "FastAPI(" in line or "docs_url" in line:
            print("CONTEXT:", line)
    print("WARN: pattern not found - see CONTEXT lines above"); sys.exit(1)
p.write_text(t)
print("OK: /docs enabled")
