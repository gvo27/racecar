"""Keep colcon test / CI from collecting the hardware test (needs the physical Mapper)."""
import os

collect_ignore_glob = [] if os.environ.get('RCCAR_HW_TEST') == '1' else ['test_*.py']
