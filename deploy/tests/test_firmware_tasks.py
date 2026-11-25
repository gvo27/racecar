"""Firmware tasks are in the reference doc, and each ISR is in IRAM (skill: firmware/.claude/skills/firmware-rtos)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'firmware' / 'esp32' / 'src'
DOC = ROOT / 'docs' / 'firmware' / 'README.md'
TASK_RE = re.compile(r'xTaskCreate(?:PinnedToCore)?\(\s*(\w+)')
ISR_RE = re.compile(r'(?:attachInterrupt(?:Arg)?|gpio_isr_handler_add)\(\s*[^,]+,\s*(\w+)')


def sources():
    return '\n'.join(p.read_text() for p in sorted(SRC.glob('*.cpp')))


def tasks_section():
    text = DOC.read_text()
    start = text.index('## Tasks and peripherals')
    end = text.find('\n## ', start + 1)
    return text[start:end if end > 0 else None]


def undocumented_tasks(src, section):
    return [name for name in TASK_RE.findall(src) if f'`{name}()`' not in section]


def isrs_not_in_iram(src):
    return [name for name in ISR_RE.findall(src)
            if not re.search(rf'IRAM_ATTR[^;{{]*\b{name}\s*\(', src)]


def test_parsers_find_violations():
    src = ('xTaskCreatePinnedToCore(fooTask, "foo", 4096, nullptr, 1, nullptr, 0);\n'
           'static void onEdge() {}\nattachInterrupt(digitalPinToInterrupt(PIN_ENC_A), onEdge, RISING);\n')
    assert undocumented_tasks(src, '- `barTask()`: core 0') == ['fooTask']
    assert isrs_not_in_iram(src) == ['onEdge']
    assert isrs_not_in_iram(src.replace('static void onEdge', 'static void IRAM_ATTR onEdge')) == []


def test_each_task_is_in_the_doc():
    src = sources()
    assert TASK_RE.findall(src), 'no xTaskCreate call found: check TASK_RE'
    assert undocumented_tasks(src, tasks_section()) == [], 'add the task to docs/firmware/README.md "Tasks and peripherals"'


def test_each_isr_is_in_iram():
    assert isrs_not_in_iram(sources()) == [], 'mark the ISR IRAM_ATTR (references/isr.md of skill firmware-rtos)'
