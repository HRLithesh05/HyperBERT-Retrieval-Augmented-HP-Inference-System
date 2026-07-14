"""
IMMEDIATE COPY — Run this file directly to restore checkpoint-1 frontend.
Usage:  python _restore_frontend.py
"""
import shutil, os, sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_checkpoint1_frontend")
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "src")

files = [
    ("pages/ResultsDashboard.tsx", "pages/ResultsDashboard.tsx"),
    ("pages/ComparisonDashboard.tsx", "pages/ComparisonDashboard.tsx"),
    ("pages/NotebookViewer.tsx", "pages/NotebookViewer.tsx"),
    ("pages/Landing.tsx", "pages/Landing.tsx"),
    ("pages/CorpusExplorer.tsx", "pages/CorpusExplorer.tsx"),
    ("pages/EvaluationDashboard.tsx", "pages/EvaluationDashboard.tsx"),
    ("components/CustomCursor.tsx", "components/CustomCursor.tsx"),
    ("components/GlassCard.tsx", "components/GlassCard.tsx"),
    ("components/ThemeProvider.tsx", "components/ThemeProvider.tsx"),
    ("components/ThemeToggle.tsx", "components/ThemeToggle.tsx"),
    ("components/NavBar.tsx", "components/NavBar.tsx"),
    ("lib/utils.ts", "lib/utils.ts"),
    ("main.tsx", "main.tsx"),
    ("styles/globals.css", "styles/globals.css"),
]

copied = 0
for src_rel, dst_rel in files:
    src_path = os.path.join(SRC, src_rel)
    dst_path = os.path.join(DST, dst_rel)
    if not os.path.exists(src_path):
        print(f"  SKIP (not found): {src_rel}")
        continue
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    shutil.copy2(src_path, dst_path)
    src_size = os.path.getsize(src_path)
    print(f"  OK  {src_rel} ({src_size:,} bytes)")
    copied += 1

print(f"\nRestored {copied} checkpoint-1 files.")
print("Files NOT overwritten: App.tsx, api.ts, UploadProcess.tsx (already customized)")
