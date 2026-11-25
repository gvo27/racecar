"""Safety checks on the firmware source (rule: .claude/rules/firmware.md, "Safety")."""
from pathlib import Path
import re

MAIN = Path(__file__).resolve().parents[2] / 'firmware' / 'esp32' / 'src' / 'main.cpp'


def save_branch(src):
    """The text of the SAVE branch of handleLine, up to the next command branch."""
    start = src.index('!strcasecmp(tok, "SAVE")')
    end = src.index('} else if', start)
    return src[start:end]


def refuses_when_armed(branch):
    """True if the branch reads g_armed and returns an ERR reply before saveConfig()."""
    before = branch[:branch.index('saveConfig()')]
    return bool(re.search(r'g_armed', before) and re.search(r'if\s*\(\s*armed\s*\)\s*\{[^}]*ERR[^}]*return', before))


def test_parser_finds_violation():
    bad = 'if (!strcasecmp(tok, "SAVE")) {\n  out.println(saveConfig() ? "OK" : "ERR");\n} else if (x) {}'
    good = ('if (!strcasecmp(tok, "SAVE")) {\n  bool armed; portENTER_CRITICAL(&g_mux); armed = g_armed; '
            'portEXIT_CRITICAL(&g_mux);\n  if (armed) { out.println("ERR x"); return; }\n'
            '  out.println(saveConfig() ? "OK" : "ERR");\n} else if (x) {}')
    assert not refuses_when_armed(save_branch(bad))
    assert refuses_when_armed(save_branch(good))


def test_save_refuses_while_armed():
    """An NVS write stops the flash cache, so controlTask stops. SAVE must refuse while armed."""
    assert refuses_when_armed(save_branch(MAIN.read_text())), 'SAVE must refuse while armed'
