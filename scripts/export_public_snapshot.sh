#!/usr/bin/env bash
# Copy an OSS-safe tree (no textbook content, outputs, or git history).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${1:-"$ROOT/dist/oss-snapshot"}"
rm -rf "$DEST"
mkdir -p "$DEST"
rsync -a \
  --exclude-from="$ROOT/.gitignore.public" \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude 'dist' \
  "$ROOT/" "$DEST/"
mkdir -p "$DEST/assets/avatars"
# Keep demo course even if rsync exclude was too aggressive
rsync -a "$ROOT/content/courses/_demo/" "$DEST/content/courses/_demo/"
echo "Snapshot: $DEST"
echo "Next: cd $DEST && git init && git add . && git status"
python3 - "$DEST" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
banned = []
for p in root.rglob("*"):
    rel = str(p.relative_to(root))
    if any(x in rel for x in ("content/source", "content/chapters/", "01-scaling", "system-design-notes")):
        banned.append(rel)
    if p.suffix.lower() in {".mp4", ".wav"} and "sfx" not in rel:
        banned.append(rel)
if banned:
    print("REFUSE: leftover paths:")
    print("\n".join(banned[:50]))
    raise SystemExit(1)
print("check: no textbook/source/media leftovers")
PY
