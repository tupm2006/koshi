#!/bin/bash
# Script to build nhom4.docx and create submission package nhom4.zip
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "[1/3] Generating docx report..."
python3 source_code/scripts/generate_docx.py

echo "[2/3] Preparing submission directory..."
rm -rf submission/nhom4
mkdir -p submission/nhom4

cp nhom4.docx URD.md SRS.md user_story.md README.md CLAUDE.md submission/nhom4/ 2>/dev/null || true
cp -r docs source_code submission/nhom4/ 2>/dev/null || true

echo "[3/3] Creating submission archive..."
cd submission
if command -v zip &> /dev/null; then
    rm -f nhom4.zip
    zip -r nhom4.zip nhom4/ -x "*/node_modules/*" "*/__pycache__/*" "*/.pytest_cache/*" "*/dist/*"
    echo "Archive created: submission/nhom4.zip"
else
    python3 -c "
import zipfile, os
with zipfile.ZipFile('nhom4.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, _, files in os.walk('nhom4'):
        if '__pycache__' in root or 'node_modules' in root or 'dist' in root or '.pytest_cache' in root:
            continue
        for file in files:
            full_path = os.path.join(root, file)
            zipf.write(full_path, full_path)
print('Archive created: submission/nhom4.zip')
"
fi
