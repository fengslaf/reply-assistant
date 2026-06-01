import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from version import APP_VERSION, VERSION_LABEL


def test_version_metadata():
    assert APP_VERSION == "0.2.4"
    assert VERSION_LABEL == "V0.2.04"
