"""Fix setup_logging call signature mismatch in orchestrator/main.py."""
with open(r'D:\neurotwin\services\orchestrator\app\main.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix the call that passes service_name= kwarg
old = 'setup_logging(service_name="neurotwin.orchestrator")'
new = 'setup_logging()'

if old in c:
    c = c.replace(old, new, 1)
    print(f"Fixed: {old!r} -> {new!r}")
else:
    # Try other variants
    import re
    m = re.search(r'setup_logging\([^)]*\)', c)
    if m:
        print(f"Found call: {m.group()!r}")
        c = re.sub(r'setup_logging\([^)]*\)', 'setup_logging()', c, count=1)
        print("Replaced with setup_logging()")
    else:
        print("No setup_logging() call found -- no change needed")

with open(r'D:\neurotwin\services\orchestrator\app\main.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("DONE")
