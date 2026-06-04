import py_compile
files = [
    'services/cognition/app/engine.py',
    'services/orchestrator/app/main.py',
]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"OK  {f}")
    except py_compile.PyCompileError as e:
        print(f"ERR {f} -- {e}")
print("DONE")
