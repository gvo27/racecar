"""Keep colcon test / CI from collecting the hardware test (needs the physical Mapper)."""
import os

import pytest


# no argument defaults: pluggy only passes arguments without defaults
@pytest.hookimpl(tryfirst=True)
def pytest_ignore_collect(collection_path, config):
    """Ignore test_*.py unless RCCAR_HW_TEST=1 (tryfirst beats the launch_testing hook)."""
    if os.environ.get('RCCAR_HW_TEST') == '1':
        return None
    return True if os.path.basename(str(collection_path)).startswith('test_') else None
