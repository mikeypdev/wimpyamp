import pytest
import sys
import os

# Add src to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_basic_import():
    """Test that we can import the main module."""
    try:
        from run_wimpyamp import main

        assert main is not None
    except ImportError:
        pytest.fail("Could not import main from run_wimpyamp")


if __name__ == "__main__":
    pytest.main()
