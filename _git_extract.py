"""
Extract frontend files from checkpoint-1 commit by calling git via subprocess.
Run this manually: python _git_extract.py
"""
import subprocess, os, sys

os.chdir(r"e:\major_project_datacollection")

COMMIT = "41f7cd82bd3542005b76fd41634d9d6271f5a698"
OUT_DIR = r"e:\major_project_datacollection\_checkpoint1_frontend"

# List all frontend/src files
result = subprocess.run(
    ["git", "ls-tree", "-r", "--name-only", COMMIT, "frontend/src/"],
    capture_output=True, text=True
)

if result.returncode != 0:
    print("ERROR:", result.stderr)
    sys.exit(1)

files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
print(f"Found {len(files)} files")

for fpath in files:
    # Extract file content
    r2 = subprocess.run(
        ["git", "show", f"{COMMIT}:{fpath}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if r2.returncode != 0:
        print(f"  SKIP {fpath}: {r2.stderr.strip()}")
        continue

    out_path = os.path.join(OUT_DIR, fpath.replace("frontend/src/", ""))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(r2.stdout)
    print(f"  ✅ {fpath} -> {out_path}")

print(f"\nDone! Files extracted to {OUT_DIR}")
