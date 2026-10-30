#!/usr/bin/env python3
"""Bundle canonical Nyx icon resources for offline CLI use."""
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
source = Path(sys.argv[1]) if len(sys.argv) > 1 else root.parent / 'nyx-design'
source = source / 'crates/nyx-icons'
target = root / 'assets/icons'
target.mkdir(parents=True, exist_ok=True)
for name in ['make_icons.py', 'third-party-glyphs.json']:
    shutil.copy2(source / name, target / name)
print('Bundled canonical Nyx icon resources.')
