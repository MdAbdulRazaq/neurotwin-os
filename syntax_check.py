"""Syntax validate all digital_twin and cognition service files."""
import py_compile, os, sys

files = [
    r"D:\neurotwin\services\digital_twin\app\config.py",
    r"D:\neurotwin\services\digital_twin\app\graph.py",
    r"D:\neurotwin\services\digital_twin\app\logging_utils.py",
    r"D:\neurotwin\services\digital_twin\app\personality.py",
    r"D:\neurotwin\services\digital_twin\app\memory_synthesizer.py",
    r"D:\neurotwin\services\digital_twin\app\timeline.py",
    r"D:\neurotwin\services\digital_twin\app\predictor.py",
    r"D:\neurotwin\services\digital_twin\app\profile.py",
    r"D:\neurotwin\services\digital_twin\app\event_consumer.py",
    r"D:\neurotwin\services\digital_twin\app\main.py",
    r"D:\neurotwin\services\cognition\app\config.py",
    r"D:\neurotwin\services\cognition\app\logging_utils.py",
    r"D:\neurotwin\services\cognition\app\state.py",
    r"D:\neurotwin\services\cognition\app\state_model.py",
    r"D:\neurotwin\services\cognition\app\decision.py",
    r"D:\neurotwin\services\cognition\app\feedback_consumer.py",
    r"D:\neurotwin\services\cognition\app\suggestions.py",
    r"D:\neurotwin\services\cognition\app\engine.py",
    r"D:\neurotwin\services\cognition\app\main.py",
]

errors = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"OK  {os.path.basename(f)}")
    except py_compile.PyCompileError as e:
        errors.append((f, str(e)))
        print(f"ERR {os.path.basename(f)} -- {e}")

print(f"\n{'ALL OK' if not errors else str(len(errors)) + ' ERRORS'} -- {len(files)} files checked")
sys.exit(1 if errors else 0)
