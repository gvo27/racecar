"""Start a session. Template: skill setup-shop (templates/scripts/open.py).

Usage: uv run --no-project python scripts/open.py [--no-plugins] [REPO ...]
REPO defaults to ".". The first REPO is the project: open also sets up its environment.
The other REPOs get the git step only.

Steps, safe to run again:
  1. git: fetch, then fast-forward the current branch. Stop if the branch diverged.
  2. env: uv sync (pyproject.toml), direnv allow (.envrc).
  3. plugins: install each plugin that settings.json enables and that is not installed.
     Skip the plugins of the builtin marketplace (<name>@builtin). Claude Code manages them.
  4. Print a checklist. Write the stamp <git dir>/make-open.stamp if no step failed.
Each line is: STATUS message. Exit 1 if a step failed. Standard library only.
The script never resets, rebases, stashes, or pushes.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

FETCH_TIMEOUT = 60  # seconds; a stalled network must not block the session
SYNC_TIMEOUT = 600  # uv sync can download many packages
TOOL_TIMEOUT = 300  # direnv, claude plugin list and install
BUILTIN = "@builtin"  # plugin id suffix of the marketplace that Claude Code manages
# Paths whose change needs a reload in Claude Code, and the command for it.
RELOADS = [
    (
        (
            "skills/",
            ".claude/skills/",
            "commands/",
            ".claude/commands/",
            "agents/",
            ".claude/agents/",
        ),
        "/reload-skills",
    ),
    (("settings.json", ".claude/settings.json", ".claude-plugin/", "hooks/"), "/reload-plugins"),
]
# Variables that point git at another repo. git -C must use the repo that we give it.
ENV = {
    k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
}
ENV["GIT_TERMINAL_PROMPT"] = "0"
STAMP = "make-open.stamp"


def run(cmd, cwd=None, timeout=None):
    try:
        return subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=False, env=ENV, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", f"timeout after {timeout}s")
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, 127, "", f"{cmd[0]}: command not found")


def git(repo, *args, timeout=None):
    return run(["git", "-C", str(repo), *args], timeout=timeout)


def out(repo, *args):
    return git(repo, *args).stdout.strip()


def first_line(text):
    return (text.strip().splitlines() or ["unknown error"])[0]


def sync_git(repo, name, lines, reloads, stale):
    """Fetch and fast-forward. Return False if a step failed."""
    if git(repo, "rev-parse", "--git-dir").returncode != 0:
        lines.append(f"FAIL {name}: not a git repo")
        return False
    r = git(repo, "fetch", "--quiet", "--prune", "--all", timeout=FETCH_TIMEOUT)
    if r.returncode != 0:
        lines.append(
            f"WARN {name}: fetch failed, the remote state can be old: {first_line(r.stderr)}"
        )
        stale.add(name)
    branch = out(repo, "branch", "--show-current")
    if not branch:
        lines.append(f"WARN {name}: HEAD is detached: not pulled")
        return True
    if git(repo, "rev-parse", "--verify", "--quiet", f"{branch}@{{u}}").returncode != 0:
        why = "upstream gone" if out(repo, "config", f"branch.{branch}.merge") else "no upstream"
        lines.append(f"WARN {name}: branch {branch}: {why}: not pulled")
        return True
    r = git(repo, "rev-list", "--left-right", "--count", "HEAD...@{u}")
    if r.returncode != 0:
        lines.append(f"FAIL {name}: cannot compare {branch} with upstream: {first_line(r.stderr)}")
        return False
    ahead, behind = (int(n) for n in r.stdout.split())
    if behind == 0:
        note = f", {ahead} commit(s) not pushed" if ahead else ""
        lines.append(f"OK   {name}: {branch} up to date{note}")
        return True
    if ahead:
        lines.append(
            f"WARN {name}: {branch} diverged ({ahead} ahead, {behind} behind): not pulled."
            " Rebase or merge by hand"
        )
        return True
    old = out(repo, "rev-parse", "HEAD")
    r = git(repo, "merge", "--ff-only", "--quiet", "@{u}")
    if r.returncode != 0:
        lines.append(f"FAIL {name}: {branch} fast-forward failed: {first_line(r.stderr)}")
        return False
    lines.append(f"OK   {name}: pulled {branch} +{behind} commit(s)")
    changed = [
        p for p in git(repo, "diff", "-z", "--name-only", old, "HEAD").stdout.split("\0") if p
    ]
    for prefixes, command in RELOADS:
        if any(p.startswith(prefixes) for p in changed):
            reloads.add(command)
    return True


def setup_env(repo, lines):
    """uv sync and direnv allow. Return False if a step failed."""
    ok = True
    if (repo / "pyproject.toml").is_file():
        cmd = ["uv", "sync", "--frozen"] if (repo / "uv.lock").is_file() else ["uv", "sync"]
        r = run(cmd, cwd=repo, timeout=SYNC_TIMEOUT)
        if r.returncode == 0:
            lines.append(f"OK   env: {' '.join(cmd)}")
        else:
            lines.append(f"FAIL env: {' '.join(cmd)}: {first_line(r.stderr)}")
            ok = False
    if (repo / ".envrc").is_file():
        if not shutil.which("direnv"):
            lines.append(
                "FAIL env: .envrc needs direnv. Install it on the host, then run make open"
            )
            ok = False
        elif run(["direnv", "allow", "."], cwd=repo, timeout=TOOL_TIMEOUT).returncode == 0:
            lines.append("OK   env: direnv allow")
        else:
            lines.append("FAIL env: direnv allow failed: run it by hand in the repo")
            ok = False
    return ok


def enabled(path):
    """The plugin ids that a settings file enables. Builtin plugins are not included."""
    try:
        plugins = json.loads(path.read_text()).get("enabledPlugins") or {}
    except (OSError, ValueError, AttributeError):
        return []
    if not isinstance(plugins, dict):
        return []
    return sorted(k for k, v in plugins.items() if v and not k.endswith(BUILTIN))


def install_plugins(repo, lines, reloads):
    """Install the enabled plugins that are missing. Return False if an install failed."""
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    wanted = [(p, "user") for p in enabled(config / "settings.json")]
    wanted += [(p, "project") for p in enabled(repo / ".claude/settings.json")]
    if not wanted:
        return True
    if not shutil.which("claude"):
        lines.append("WARN plugins: claude not found: cannot check the enabled plugins")
        return True
    r = run(["claude", "plugin", "list", "--json"], cwd=repo, timeout=TOOL_TIMEOUT)
    try:
        installed = json.loads(r.stdout)
        if not isinstance(installed, list) or not all(isinstance(p, dict) for p in installed):
            raise ValueError("not a list of objects")
    except ValueError:
        lines.append(f"WARN plugins: cannot read claude plugin list --json: {first_line(r.stderr)}")
        return True
    here = str(repo.resolve())
    have = {
        (p.get("id"), p.get("scope"))
        for p in installed
        if p.get("scope") == "user" or p.get("projectPath") == here
    }
    ok, missing = True, [(p, s) for p, s in wanted if (p, s) not in have]
    for plugin, scope in missing:
        cmd = ["claude", "plugin", "install", plugin, "--scope", scope]
        r = run(cmd, cwd=repo, timeout=TOOL_TIMEOUT)
        if r.returncode == 0:
            lines.append(f"OK   plugins: installed {plugin} ({scope})")
            reloads.add("/reload-plugins")
        else:
            lines.append(f"FAIL plugins: {' '.join(cmd)}: {first_line(r.stderr or r.stdout)}")
            ok = False
    if not missing:
        lines.append(f"OK   plugins: {len(wanted)} enabled plugin(s) installed")
    return ok


def write_stamp(repo):
    path = Path(out(repo, "rev-parse", "--git-path", STAMP))
    path = path if path.is_absolute() else repo / path
    path.write_text("")


def main(argv):
    plugins = "--no-plugins" not in argv
    repos = [Path(a).expanduser() for a in argv if a != "--no-plugins"] or [Path(".")]
    lines, reloads, stale, ok = [], set(), set(), True
    for i, repo in enumerate(repos):
        name = "." if i == 0 else str(repo)
        ok &= sync_git(repo, name, lines, reloads, stale)
    project = repos[0]
    ok &= setup_env(project, lines)
    if plugins:
        ok &= install_plugins(project, lines, reloads)
    lines += [f"TODO type {c} in Claude Code" for c in sorted(reloads)]
    if ok and "." not in stale:  # no stamp after a failed fetch: the hook keeps reminding
        write_stamp(project)
        lines.append("OK   open: ready. Fix each WARN line before you depend on it")
    else:
        lines.append("FAIL open: fix each FAIL line, then run make open again")
    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
