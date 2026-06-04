import argparse, re, sys
from pathlib import Path

TARGET = "5.28.1"
PAT = re.compile(r"^(neo4j(?:\[.*?\])?)==.*$", re.MULTILINE)

def patch(path, dry_run):
    text = path.read_text()
    new = PAT.sub(r"\g<1>==" + TARGET, text)
    if new == text:
        return False, "", ""
    old_m = PAT.search(text)
    new_m = PAT.search(new)
    old = old_m.group(0) if old_m else "?"
    new_l = new_m.group(0) if new_m else "?"
    if not dry_run:
        path.write_text(new)
    return True, old, new_l

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--root", default=".")
args = parser.parse_args()
root = Path(args.root).resolve()
count = 0
for f in sorted(root.rglob("requirements*.txt")):
    changed, old, new = patch(f, args.dry_run)
    rel = f.relative_to(root)
    if changed:
        tag = "[DRY RUN]" if args.dry_run else "PATCHED"
        print(f"  {tag} {rel}")
        print(f"    {old!r} -> {new!r}")
        count += 1
    elif f"neo4j=={TARGET}" in f.read_text():
        print(f"  ok {rel}")
print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Changed {count} file(s) to neo4j=={TARGET}")
