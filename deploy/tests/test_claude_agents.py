"""Every .claude agent and skill has valid frontmatter, and each repo path it names exists."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGENTS = sorted((ROOT / '.claude' / 'agents').glob('*.md'))
SKILLS = sorted((ROOT / '.claude' / 'skills').glob('*/SKILL.md'))
SKILL_FILES = sorted((ROOT / '.claude' / 'skills').glob('*/**/*.md'))
PATH_RE = re.compile(r'`((?:\.claude|docs|docker|deploy)/[A-Za-z0-9_./-]+)`')
MAKE_TARGETS = {'pcb-build', 'pcb-route', 'pcb-check', 'pcb-mill-check', 'pcb-review', 'pcb-fab', 'pcb-test', 'pcb-gate', 'pcb-all', 'pcb-sch', 'pcb-rules'}


def frontmatter(path) -> dict[str, str]:
    text = path.read_text()
    assert text.startswith('---\n'), f'{path}: no frontmatter'
    head = text[4:text.index('\n---', 4)]
    return {m.group(1): m.group(2) for m in re.finditer(r'^([a-z-]+):\s*(.*)$', head, re.MULTILINE)}


def rel(path):
    return str(path.relative_to(ROOT))


def test_files_exist():
    assert AGENTS and SKILLS


@pytest.mark.parametrize('path', AGENTS, ids=rel)
def test_agent_frontmatter(path):
    fm = frontmatter(path)
    assert fm.get('name') == path.stem, f'{rel(path)}: name must equal the file name'
    assert fm.get('description'), f'{rel(path)}: no description'


@pytest.mark.parametrize('path', SKILLS, ids=rel)
def test_skill_frontmatter(path):
    fm = frontmatter(path)
    desc = fm.get('description', '')
    assert fm.get('name') == path.parent.name, f'{rel(path)}: name must equal the directory name'
    assert desc.startswith('Use when'), f'{rel(path)}: the description is the trigger, start with "Use when"'
    assert len(desc) <= 1024 and '<' not in desc and '>' not in desc, f'{rel(path)}: description too long or has < >'
    lines = len(path.read_text().splitlines())
    assert lines <= 150, f'{rel(path)}: {lines} lines, move detail to a sibling file'


@pytest.mark.parametrize('path', AGENTS + SKILL_FILES, ids=rel)
def test_named_paths_exist(path):
    named = {p.rstrip('.') for p in PATH_RE.findall(path.read_text()) if '<' not in p and '*' not in p}
    dead = sorted(p for p in named if not (ROOT / p).exists())
    assert not dead, f'{rel(path)}: names paths that do not exist: {dead}'


def test_pcb_files_name_existing_skills_and_agents():
    known = {p.parent.name for p in SKILLS} | {p.stem for p in AGENTS} | MAKE_TARGETS
    for path in AGENTS + SKILL_FILES:
        if not (path.stem.startswith('pcb-') or path.parent.name.startswith('pcb-')):
            continue
        unknown = set(re.findall(r'`(pcb-[a-z-]+)`', path.read_text())) - known
        assert not unknown, f'{rel(path)}: names {sorted(unknown)}, which is not a project skill, agent or make target'
