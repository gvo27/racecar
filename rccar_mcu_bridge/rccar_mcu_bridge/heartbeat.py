"""Heartbeat file for docker healthchecks (``find /run/hb -mmin -0.1``)."""
import os
from pathlib import Path


def touch(path: str) -> bool:
    """Refresh the heartbeat file; return False when disabled or unwritable."""
    if not path:
        return False
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch(exist_ok=True)
        os.utime(p, None)
        return True
    except OSError:
        return False
