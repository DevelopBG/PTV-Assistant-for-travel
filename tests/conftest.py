"""
Pytest configuration and shared fixtures for all tests.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def data_dir(project_root):
    """Return the data directory."""
    return project_root / "data"


@pytest.fixture(scope="session")
def gtfs_dir():
    """Return the test GTFS fixtures directory."""
    return Path(__file__).parent / "test_data" / "fixtures"


@pytest.fixture(scope="session")
def real_gtfs_dir(data_dir):
    """Return the real GTFS data directory."""
    return data_dir / "gtfs"
