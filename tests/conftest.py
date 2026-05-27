import os
import pytest


@pytest.fixture
def default_skin_path():
    """Path to the bundled default skin."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "resources", "default_skin", "base-2.91.wsz")


@pytest.fixture
def default_skin_dir():
    """Path to the extracted default skin directory (base-2.91.png is alongside the wsz)."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "resources", "default_skin")
