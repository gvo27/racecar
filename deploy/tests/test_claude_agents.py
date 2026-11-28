"""Every .claude agent and skill has valid frontmatter. Each repo path that an agent, a skill,
a rule or a CLAUDE.md file names exists."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGENTS = sorted((ROOT / '.claude' / 'agents').glob('*.md'))
# root skills, and nested skills that load when Claude works in their subproject (ADR 0001)
SKILL_DIRS = [ROOT / '.claude' / 'skills'] + sorted(ROOT.glob('*/.claude/skills'))
SKILLS = sorted(p for d in SKILL_DIRS for p in d.glob('*/SKILL.md'))
SKILL_FILES = sorted(p for d in SKILL_DIRS for p in d.glob('*/**/*.md'))
RULES = sorted((ROOT / '.claude' / 'rules').glob('*.md'))
SKIP = {'.git', '.venv', '.cache', '.pio', '.pio-core', 'build', 'install', 'log', 'logs', 'node_modules', 'cache'}
CLAUDE_MDS = sorted(p for p in ROOT.glob('**/CLAUDE.md') if not SKIP & set(p.relative_to(ROOT).parts))
PATH_RE = re.compile(r'`((?:\.claude|docs|docker|deploy|ros2_ws|firmware|pcb|models|simulation|mechanical|scripts)/[A-Za-z0-9_./-]+)`')
GENERATED = ('models/cache', 'deploy/car/.env.generated', 'firmware/esp32/.pio',
             '.claude/settings.local.json')  # gitignored, made at run time
VERSION_RE = re.compile(r'\b\d+\.\d+\.\d+\b')  # same as the project-context check script
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


@pytest.mark.parametrize('path', AGENTS + SKILL_FILES + RULES + CLAUDE_MDS, ids=rel)
def test_named_paths_exist(path):
    named = {p.rstrip('.') for p in PATH_RE.findall(path.read_text()) if '<' not in p and '*' not in p and not p.startswith(GENERATED)}
    dead = sorted(p for p in named if not (ROOT / p).exists())
    assert not dead, f'{rel(path)}: names paths that do not exist: {dead}'


def test_pcb_files_name_existing_skills_and_agents():
    known = {p.parent.name for p in SKILLS} | {p.stem for p in AGENTS} | MAKE_TARGETS
    for path in AGENTS + SKILL_FILES:
        if not (path.stem.startswith('pcb-') or 'pcb' in path.relative_to(ROOT).parts[:1]):
            continue
        unknown = set(re.findall(r'`(pcb-[a-z-]+)`', path.read_text())) - known
        assert not unknown, f'{rel(path)}: names {sorted(unknown)}, which is not a project skill, agent or make target'


@pytest.mark.parametrize('path', SKILLS, ids=rel)
def test_skill_has_verify_section(path):
    """Each project skill tells how to verify its result."""
    assert re.search(r'^## Verify\s*$', path.read_text(), re.MULTILINE), f'{rel(path)}: no "## Verify" section'


@pytest.mark.parametrize('path', SKILL_FILES, ids=rel)
def test_skill_files_hold_no_versions(path):
    """A skill holds no repo facts: versions live in their owner file (docs/dependencies.md, settings.json)."""
    hits = [(n, line.strip()) for n, line in enumerate(path.read_text().splitlines(), 1) if VERSION_RE.search(line)]
    assert not hits, f'{rel(path)}: x.y.z versions {hits}'
