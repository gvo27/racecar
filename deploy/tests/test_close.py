"""scripts/close.py: the done-plan check reads docs/plans/ (template: skill setup-shop)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('close', ROOT / 'scripts' / 'close.py')
close = importlib.util.module_from_spec(spec)
spec.loader.exec_module(close)


def _plan(repo, name, status):
    plans = repo / 'docs' / 'plans'
    plans.mkdir(parents=True, exist_ok=True)
    (plans / name).write_text(f'# Plan\n\nStatus: {status}\n')


def test_done_plan_in_docs_plans_is_reported(tmp_path):
    _plan(tmp_path, '2026-01-01-a.md', 'done')
    _plan(tmp_path, '2026-01-02-b.md', 'active')
    lines = []
    assert close.done_plans(tmp_path, lines) == 1
    assert len(lines) == 1 and 'docs/plans/2026-01-01-a.md' in lines[0]


def test_no_plans_folder(tmp_path):
    lines = []
    assert close.done_plans(tmp_path, lines) == 0 and not lines
