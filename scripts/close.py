"""End a session. Template: skill setup-shop (templates/scripts/close.py).

Usage: uv run --no-project python scripts/close.py [--ignore PREFIX ...] [REPO ...]
REPO defaults to ".". The first REPO is the project: close also cleans its caches and
checks its docs. --ignore skips changed or untracked paths with that prefix.

Steps, safe to run again:
  1. Delete the caches that git ignores: __pycache__, .pytest_cache, .ruff_cache.
  2. Report uncommitted paths, stashes, commits that are not pushed, and gone branches.
     Ignore a change to settings.json that changes only builtin plugins (<name>@builtin)
     or the key order. Claude Code writes these entries.
  3. Report plans in docs/plan/ with "Status: done" or "Status: cancelled".
  4. Delete the make open stamp, so the next session asks for make open.
Each line is: STATUS message. Exit 1 if a line needs action. Standard library only.
The script never pushes, resets, or deletes a tracked file or a branch.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FETCH_TIMEOUT = 60  # seconds
ENV = {
    k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
}
ENV["GIT_TERMINAL_PROMPT"] = "0"
CACHES = ("__pycache__", ".pytest_cache", ".ruff_cache")
SKIP_DIRS = {".git", ".venv", "node_modules"}
DONE = re.compile(
    r"^\W*status\W*:?\W*(done|cancelled|canceled|complete|completed)\b",
    re.IGNORECASE | re.MULTILINE,
)
STAMP = "make-open.stamp"
BUILTIN = "@builtin"  # plugin id suffix of the marketplace that Claude Code manages
SETTINGS = ("settings.json", ".claude/settings.json")


def git(repo, *args, timeout=None):
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
            env=ENV,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(args, 124, "", f"timeout after {timeout}s")


def out(repo, *args):
    return git(repo, *args).stdout.strip()


def first_line(text):
    return (text.strip().splitlines() or ["unknown error"])[0]


def clean_caches(repo, lines):
    found = []
    for root, dirs, _ in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for d in [d for d in dirs if d in CACHES]:
            found.append(Path(root) / d)
            dirs.remove(d)
    ignored = [
        p
        for p in found
        if git(repo, "check-ignore", "-q", str(p)).returncode == 0
        and not out(repo, "ls-files", "--", str(p))  # never delete a tracked file
    ]
    for p in ignored:
        shutil.rmtree(p, ignore_errors=True)
    if ignored:
        lines.append(f"OK   .: deleted {len(ignored)} cache dir(s)")


def done_plans(repo, lines):
    """Return 1 for each plan in docs/plan/ that is done and not archived."""
    code = 0
    for plan in sorted((repo / "docs/plan").glob("*.md")):
        head = "\n".join(plan.read_text(errors="replace").splitlines()[:10])
        if m := DONE.search(head):
            rel = plan.relative_to(repo)
            lines.append(
                f"TODO .: {rel} has status {m.group(1).lower()}: git mv it to docs/archive/plans/"
            )
            code = 1
    return code


def default_branches(repo):
    refs = []
    for remote in out(repo, "remote").splitlines():
        ref = out(repo, "symbolic-ref", "--quiet", "--short", f"refs/remotes/{remote}/HEAD")
        if ref:
            refs.append(ref)
    return refs


def unpushed(repo, rev):
    """Count commits of rev on no remote. A commit whose patch is on a remote default
    branch (a squash merge of one commit, a cherry-pick) counts as pushed."""
    commits = set(out(repo, "rev-list", rev, "--not", "--remotes").splitlines())
    for ref in default_branches(repo):
        if not commits:
            break
        for line in out(repo, "cherry", ref, rev).splitlines():
            if line.startswith("- "):
                commits.discard(line[2:])
    return len(commits)


def without_builtin(text):
    """Parsed settings without the builtin plugin entries. None if the text is not a JSON object."""
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    plugins = data.get("enabledPlugins")
    if isinstance(plugins, dict):
        data["enabledPlugins"] = {k: v for k, v in plugins.items() if not k.endswith(BUILTIN)}
    return data


def builtin_drift_only(repo, path):
    """True if the settings file differs from HEAD only in builtin plugins or key order."""
    head = git(repo, "show", f"HEAD:{path}")
    if head.returncode != 0:
        return False
    try:
        now = (repo / path).read_text()
    except OSError:
        return False
    old = without_builtin(head.stdout)
    return old is not None and old == without_builtin(now)


def dirty_paths(repo, ignore):
    """Changed and untracked paths. For a rename, the new path."""
    fields = git(repo, "status", "--porcelain", "-z", "--untracked-files=all").stdout.split("\0")
    paths, i = [], 0
    while i < len(fields):
        entry = fields[i]
        i += 1
        if not entry:
            continue
        if entry[0] in "RC":
            i += 1  # the next field is the old path
        path = entry[3:]
        if path.startswith(tuple(ignore)):
            continue
        if path in SETTINGS and entry[:2] in (" M", "M ", "MM") and builtin_drift_only(repo, path):
            continue
        paths.append(path)
    return paths


def check_git(repo, name, lines, ignore):
    if git(repo, "rev-parse", "--git-dir").returncode != 0:
        lines.append(f"FAIL {name}: not a git repo")
        return 1
    code = 0
    r = git(repo, "fetch", "--quiet", "--prune", "--all", timeout=FETCH_TIMEOUT)
    if r.returncode != 0:
        lines.append(
            f"TODO {name}: fetch failed, cannot check what is pushed: {first_line(r.stderr)}"
        )
        code = 1
    dirty = dirty_paths(repo, ignore)
    if dirty:
        shown = ", ".join(dirty[:10]) + (f" (+{len(dirty) - 10} more)" if len(dirty) > 10 else "")
        lines.append(f"TODO {name}: {len(dirty)} path(s) not committed: {shown}")
        code = 1
    if stashes := out(repo, "stash", "list").splitlines():
        lines.append(f"TODO {name}: {len(stashes)} stash(es): commit them or drop them")
        code = 1
    if (
        not out(repo, "branch", "--show-current")
        and git(repo, "rev-parse", "--verify", "--quiet", "HEAD").returncode == 0
    ) and (n := unpushed(repo, "HEAD")):
        lines.append(f"TODO {name}: detached HEAD has {n} commit(s) on no branch and no remote")
        code = 1
    for branch in out(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines():
        has_upstream = (
            git(repo, "rev-parse", "--verify", "--quiet", f"{branch}@{{u}}").returncode == 0
        )
        if has_upstream:
            n = int(out(repo, "rev-list", "--count", f"{branch}@{{u}}..{branch}") or 0)
        else:
            n = unpushed(repo, branch)
        if n:
            lines.append(f"TODO {name}: branch {branch}: {n} commit(s) not on the remote")
            code = 1
        elif not has_upstream and out(repo, "config", f"branch.{branch}.merge"):
            lines.append(
                f"INFO {name}: branch {branch}: upstream gone. If its PR merged: git branch -D {branch}"
            )
    if code == 0:
        lines.append(f"OK   {name}: clean, all branches pushed")
    return code


def remove_stamp(repo):
    path = Path(out(repo, "rev-parse", "--git-path", STAMP))
    (path if path.is_absolute() else repo / path).unlink(missing_ok=True)


def main(argv):
    rest, ignore, repos = list(argv), [], []
    while rest:
        arg = rest.pop(0)
        if arg == "--ignore":
            if not rest:
                print("error: --ignore needs a path prefix", file=sys.stderr)
                return 2
            ignore.append(rest.pop(0))
        else:
            repos.append(Path(arg).expanduser())
    repos = repos or [Path(".")]
    project, lines, code = repos[0], [], 0
    if git(project, "rev-parse", "--git-dir").returncode == 0:
        clean_caches(project, lines)
        code |= done_plans(project, lines)
    for i, repo in enumerate(repos):
        code |= check_git(repo, "." if i == 0 else str(repo), lines, ignore)
    if git(project, "rev-parse", "--git-dir").returncode == 0:
        remove_stamp(project)
    if code == 0:
        lines.append("OK   close: ready. Type /exit in Claude Code")
    else:
        lines.append("TODO close: fix each TODO line, then run make close again")
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
