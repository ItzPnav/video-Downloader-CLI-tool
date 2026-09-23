import sys
from pathlib import Path

# Ensure src directory is in sys.path for local executions
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from video_downloader.cli import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n  ! Cancelled.")
        sys.exit(130)
