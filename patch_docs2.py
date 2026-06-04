import pathlib
p = pathlib.Path("/app/app/main.py")
t = p.read_text()
t = t.replace(
    'docs_url="/docs" if settings.DEBUG else None',
    'docs_url="/docs"'
).replace(
    'redoc_url="/redoc" if settings.DEBUG else None',
    'redoc_url="/redoc"'
)
p.write_text(t)
print("OK: docs_url always enabled")
