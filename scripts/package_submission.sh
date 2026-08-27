#!/usr/bin/env bash
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

echo "==> 1. Generating latest CSDL DDL & seeding database..."
python3 backend/init_db.py

echo "==> 2. Compiling latest report to nhom1.docx..."
python3 scripts/generate_docx.py

echo "==> 3. Packaging deliverables using Python tar/zip..."
python3 -c "
import zipfile, os

base_dir = '$BASE_DIR'
zip_path = os.path.join(base_dir, 'nhom1.zip')

include_dirs = ['docs', 'backend/db', 'backend/app', 'src']
include_files = [
    'nhom1.docx',
    'backend/init_db.py',
    'backend/requirements.txt',
    'CLAUDE.md',
    'package.json',
    'vite.config.ts',
    'tsconfig.json',
    'README.md'
]

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for f in include_files:
        full_p = os.path.join(base_dir, f)
        if os.path.exists(full_p):
            zipf.write(full_p, f)
            
    for d in include_dirs:
        full_d = os.path.join(base_dir, d)
        for root, _, files in os.walk(full_d):
            if '__pycache__' in root or 'node_modules' in root or 'dist' in root:
                continue
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, base_dir)
                zipf.write(full_path, rel_path)

print('Packaged nhom1.zip successfully!')
"

echo "==> Packaging complete! Generated: $BASE_DIR/nhom1.zip"
