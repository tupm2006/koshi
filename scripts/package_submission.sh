#!/bin/bash
# Script to build nhom4.docx and create submission package nhom4.rar / nhom4.zip
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

echo "[1/3] Generating docx report from template..."
if [ -f ".venv/bin/python3" ]; then
    .venv/bin/python3 scripts/generate_docx.py
else
    python3 scripts/generate_docx.py
fi

echo "[2/3] Preparing submission directory..."
rm -rf submission/nhom4
mkdir -p submission/nhom4

cp nhom4.docx submission/nhom4/
cp -r backend src docs CLAUDE.md package.json README.md submission/nhom4/

echo "[3/3] Creating submission archive..."
cd submission
if command -v rar &> /dev/null; then
    rar a nhom4.rar nhom4/
    echo "Archive created: submission/nhom4.rar"
elif command -v zip &> /dev/null; then
    zip -r nhom4.zip nhom4/
    echo "Archive created: submission/nhom4.zip"
else
    python3 -c "
import zipfile, os
with zipfile.ZipFile('nhom4.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, _, files in os.walk('nhom4'):
        if '__pycache__' in root or 'node_modules' in root or 'dist' in root:
            continue
        for file in files:
            full_path = os.path.join(root, file)
            zipf.write(full_path, full_path)
print('Archive created: submission/nhom4.zip')
"
fi
