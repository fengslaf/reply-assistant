#!/usr/bin/env python3
"""Entry point - No TCL/TK setup needed (PyInstaller hook handles it)"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from start_gui import main

if __name__ == '__main__':
    main()