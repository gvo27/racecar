"""Monorepo layout (docs/adr/0001-monorepo-layout.md): subproject folders, signs and links."""
from pathlib import Path
import os
import re
from urllib.parse import unquote

import pytest

ROOT = Path(__file__).resolve().parents[2]
SUBPROJECTS = ['docs', 'firmware', 'mechanical', 'models', 'pcb', 'ros2_ws', 'simulation']
COLCON_IGNORED = ['deploy', 'docker', 'docs', 'firmware', 'logs', 'mechanical', 'models', 'pcb', 'simulation']
LINK_RE = re.compile(r'!?\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)')


SKIP = {'.git', '.venv', '.cache', '.pio', '.pio-core', 'build', 'install', 'log', 'logs', 'node_modules'}


def files(name):
    """Repo files called name, without caches and build output."""
    found = []
    for root, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        found += [Path(root) / name] if name in names else []
    return found


def rel(path):
    return str(path.relative_to(ROOT))


def test_ros_packages_are_in_the_workspace():
    stray = [rel(p) for p in files('package.xml')
             if not rel(p).startswith(('ros2_ws/src/', 'firmware/'))]
    assert not stray, 'ROS packages outside ros2_ws/src/: %s' % stray
    assert len(list(ROOT.glob('ros2_ws/src/*/package.xml'))) >= 8


def test_no_package_dirs_at_the_root():
    stray = sorted(p.name for p in ROOT.glob('rccar_*') if p.is_dir())
    assert not stray, 'package dirs at the repo root: %s (move them to ros2_ws/src/)' % stray


@pytest.mark.parametrize('folder', SUBPROJECTS)
def test_subproject_has_readme(folder):
    assert (ROOT / folder / 'README.md').is_file(), '%s/README.md missing' % folder


@pytest.mark.parametrize('folder', COLCON_IGNORED)
def test_non_ros_folder_is_colcon_ignored(folder):
    assert (ROOT / folder / 'COLCON_IGNORE').is_file(), '%s/COLCON_IGNORE missing' % folder


def test_workspace_is_not_colcon_ignored():
    assert not (ROOT / 'ros2_ws' / 'COLCON_IGNORE').exists()


def test_invariants_have_one_owner():
    assert (ROOT / 'docs' / 'invariants.md').is_file()
    claude = (ROOT / '.claude' / 'CLAUDE.md').read_text()
    assert re.search(r'^@docs/invariants\.md\s*$', claude, re.M), '.claude/CLAUDE.md must import @docs/invariants.md'
    assert not re.search(r'^invariants:', claude, re.M), '.claude/CLAUDE.md must not copy the invariants'


def test_adr_folder_has_template_and_index():
    assert (ROOT / 'docs' / 'adr' / '0000-template.md').is_file()
    assert (ROOT / 'docs' / 'adr' / 'README.md').is_file()


READMES = [p for p in files('README.md')
           if not rel(p).startswith(('docs/archive/', 'firmware/esp32/extra_packages/'))]


@pytest.mark.parametrize('readme', READMES, ids=rel)
def test_readme_links_resolve(readme):
    """Each relative link or image in a README points to a file or folder that exists."""
    targets = [t for t in LINK_RE.findall(readme.read_text()) if '://' not in t and not t.startswith('mailto:')]
    dead = sorted(t for t in targets if not (readme.parent / unquote(t)).exists())
    assert not dead, '%s: dead links %s' % (rel(readme), dead)
