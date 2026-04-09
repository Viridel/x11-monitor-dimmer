#!/usr/bin/env python3
import sys
from pathlib import Path

BASE = Path("/home/media/.local/bin")
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from dimmerlib.app import main

if __name__ == "__main__":
    raise SystemExit(main())
