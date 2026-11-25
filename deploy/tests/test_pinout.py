"""The pin diagram of the root README equals firmware/esp32/include/pins.h (rule: .claude/rules/firmware.md)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PINS_H = ROOT / 'firmware' / 'esp32' / 'include' / 'pins.h'
README = ROOT / 'README.md'


def pins_h():
    """GPIO number -> P1 header pin, from the constexpr lines and their '// P1-<n>' comment."""
    found = re.findall(r'constexpr int PIN_\w+\s*=\s*(\d+);\s*//\s*P1-(\d+)', PINS_H.read_text())
    return {int(gpio): int(p1) for gpio, p1 in found}


def readme_diagram():
    """GPIO number -> P1 header pin, from the diagram lines '  GPIO4 │  4  │ ...'."""
    found = re.findall(r'^\s*GPIO(\d+)\s*│\s*(\d+)\s*│', README.read_text(), re.MULTILINE)
    return {int(gpio): int(p1) for gpio, p1 in found}


def test_pins_h_parses():
    """Each pin constant has its '// P1-<n>' comment, so the test sees every pin."""
    assert len(pins_h()) >= 8
    assert len(re.findall(r'constexpr int PIN_', PINS_H.read_text())) == len(pins_h()), 'a PIN_ constant without // P1-<n>'


def test_readme_diagram_matches_pins_h():
    diagram = readme_diagram()
    wrong = {g: (p1, diagram.get(g)) for g, p1 in pins_h().items() if diagram.get(g) != p1}
    assert not wrong, f'GPIO: (pins.h P1 pin, README P1 pin) differ: {wrong}'
