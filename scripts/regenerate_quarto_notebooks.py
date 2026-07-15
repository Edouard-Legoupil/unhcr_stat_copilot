#!/usr/bin/env python3
"""
Utility script to regenerate missing Quarto notebooks (.qmd) from existing analysis history JSON files.

Run this when a history entry has "quarto_content" but no corresponding .qmd file under data/quarto_analyses/.
"""
import json
import os
import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH for backend imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))
from backend.history import HISTORY_DIR, QUARTO_DIR


def main():
    Path(QUARTO_DIR).mkdir(parents=True, exist_ok=True)
    for fname in os.listdir(HISTORY_DIR):
        if not fname.endswith(".json"):
            continue
        history_path = os.path.join(HISTORY_DIR, fname)
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
        except Exception as e:
            print(f"Skipping {fname}: failed to read JSON: {e}")
            continue

        qcontent = entry.get('quarto_content')
        if not qcontent:
            continue  # no Quarto content to write

        # Determine filename: use existing metadata filepath or generate from ID
        qm_metadata = entry.get('quarto_metadata', {})
        filepath = qm_metadata.get('filepath')
        if filepath:
            qpath = Path(filepath)
        else:
            qname = qm_metadata.get('quarto_filename') or f"{entry.get('id')}.qmd"
            qpath = Path(QUARTO_DIR) / qname

        if qpath.exists():
            print(f"Exists: {qpath}")
            continue

        # Write the .qmd file
        try:
            qpath.parent.mkdir(parents=True, exist_ok=True)
            with open(qpath, 'w', encoding='utf-8') as f:
                f.write(qcontent)
            print(f"Regenerated: {qpath}")
        except Exception as e:
            print(f"Failed to write {qpath}: {e}")


if __name__ == '__main__':
    main()
