"""Clean all __pycache__ directories and stale .pyc files."""
import shutil, os

root = r"e:\major_project_datacollection\src"
count = 0
for dirpath, dirnames, filenames in os.walk(root):
    for d in dirnames:
        if d == "__pycache__":
            full = os.path.join(dirpath, d)
            shutil.rmtree(full)
            print(f"  Removed: {full}")
            count += 1

print(f"\nCleaned {count} __pycache__ directories")
