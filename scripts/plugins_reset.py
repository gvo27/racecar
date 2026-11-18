"""Remove the session-only plugin enables. Called by make close (target plugins-reset).

Usage: uv run --no-project python scripts/plugins_reset.py [SETTINGS_FILE]
SETTINGS_FILE defaults to .claude/settings.local.json. A plugin enabled for one session
(`claude plugin enable <plugin> --scope local`) writes `enabledPlugins` into that file, and
the file lasts across sessions. This script deletes the `enabledPlugins` key and keeps all
other local settings, so the next session starts with the project default set
(`enabledPlugins` in .claude/settings.json). The running session keeps its loaded plugins
until /reload-plugins or exit. Standard library only. Safe to run again.
"""

import json
import sys
from pathlib import Path


def reset(path):
    """Delete `enabledPlugins` from the settings file. Return the removed plugin ids, sorted."""
    path = Path(path)
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict) or not isinstance(data.get("enabledPlugins"), dict):
        return []
    removed = sorted(data.pop("enabledPlugins"))
    path.write_text(json.dumps(data, indent=2) + "\n")
    return removed


def main(argv):
    path = Path(argv[0]) if argv else Path(".claude/settings.local.json")
    removed = reset(path)
    if removed:
        print(f"OK   plugins: removed the session-only enables from {path}: {', '.join(removed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
