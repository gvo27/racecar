#!/usr/bin/env python3
"""
PreToolUse guard for an agent running on the Pi with the lidar attached (stdlib only).

Rules: .claude/rules/hw-testing.md. Registered in .claude/settings.json for Bash and
Edit|Write|MultiEdit|NotebookEdit. Output is the documented PreToolUse JSON on stdout
(exit 0): permissionDecision "ask" (a human must approve) or "deny" (reason goes to the agent).
No output = no opinion (normal permission flow).

- Bash: hardware (re)starts (car-up, drivers-start, flash, compose up/start/restart,
  systemctl start/restart/enable ...rccar, reboot, poweroff ...) => ask. Never deny these.
  Stops (drivers-stop, car-down, compose stop) => no opinion.
- Bash `make ros-image|setup`, `docker build` while the drivers container runs => deny.
- Edit/Write under rccar_drivers/, rccar_description/, docker/ros.Dockerfile while the
  drivers container runs => deny ("make drivers-stop" first).
- docker missing or erroring => allow (dev laptops, cloud sessions).
Known gap: edits made through shell redirection/sed in Bash are not path-checked.
"""
import json
import os
import re
import shlex
import subprocess
import sys

ASK_MAKE = {'car-up', 'drivers-start', 'install-host', 'flash', 'car-shutdown'}
BUILD_MAKE = {'ros-image', 'setup'}
COMPOSE_ASK = {'up', 'restart', 'start'}
DOCKER_ASK = {'restart', 'start'}
SYSTEMCTL_ASK = {'start', 'restart', 'enable', 'reload-or-restart', 'try-restart'}
SYSTEMCTL_ALWAYS = {'reboot', 'poweroff', 'halt', 'kexec'}
POWER_CMDS = {'reboot', 'poweroff', 'shutdown', 'halt'}
DRIVER_PATHS = ('rccar_drivers/', 'rccar_description/')
DRIVER_FILES = ('docker/ros.Dockerfile',)
PREFIX_CMDS = {'sudo', 'env', 'command', 'nohup', 'time', 'exec', 'nice', 'stdbuf'}
SEPARATORS = {';', '&&', '||', '|', '&', '|&'}
# docker global options that take a value (compose + docker)
VALUE_OPTS = {'-f', '--file', '--env-file', '-p', '--project-name', '--profile',
              '--project-directory', '-H', '--host', '-c', '--context', '--parallel',
              '--ansi', '--progress'}
DENY_RUNNING = ('lidar driver container is running: run `make drivers-stop` before '
                'changing driver code or rebuilding the image')


def _tokens(command):
    """Shell-ish tokens with ; && || | & as separate tokens (quotes respected)."""
    out = []
    for line in command.splitlines():
        try:
            lex = shlex.shlex(line, posix=True, punctuation_chars=True)
            lex.whitespace_split = True
            lex.commenters = ''
            out.extend(list(lex))
        except ValueError:
            out.extend(re.split(r'\s+|(;|&&|\|\||\|)', line))
        out.append(';')
    return [t for t in out if t]


def _segments(command):
    seg, segs = [], []
    for t in _tokens(command):
        if t in SEPARATORS or set(t) <= set(';&|()'):
            if seg:
                segs.append(seg)
            seg = []
        else:
            seg.append(t)
    if seg:
        segs.append(seg)
    return segs


def _strip_prefix(seg):
    """Drop leading VAR=val, sudo/env/... (and their options) from a segment."""
    i = 0
    while i < len(seg):
        t = seg[i]
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', t):
            i += 1
        elif os.path.basename(t) in PREFIX_CMDS:
            i += 1
            while i < len(seg) and seg[i].startswith('-'):
                i += 1
        else:
            break
    return seg[i:]


def _docker_sub(args):
    """First subcommand after docker [options] (value options skipped)."""
    i = 0
    while i < len(args):
        a = args[i]
        if a in VALUE_OPTS:
            i += 2
        elif a.startswith('-'):
            i += 1
        else:
            return a, args[i + 1:]
    return None, []


def _inner(seg):
    """Commands nested in `bash -c '...'` / `sh -c`."""
    if seg and os.path.basename(seg[0]) in ('bash', 'sh', 'zsh', 'dash') and '-c' in seg:
        k = seg.index('-c')
        if k + 1 < len(seg):
            return seg[k + 1]
    return None


def _flags(command):
    """Return (asks: list of reasons, builds: bool) for the whole command string."""
    asks, builds = [], False
    for seg in _segments(command):
        seg = _strip_prefix(seg)
        if not seg:
            continue
        inner = _inner(seg)
        if inner:
            a, b = _flags(inner)
            asks += a
            builds = builds or b
            continue
        prog, args = os.path.basename(seg[0]), seg[1:]
        if prog == 'make':
            targets = [a for a in args if not a.startswith('-') and '=' not in a]
            asks += ['make %s' % t for t in targets if t in ASK_MAKE]
            builds = builds or any(t in BUILD_MAKE for t in targets)
        elif prog in ('docker', 'docker-compose'):
            sub, rest = _docker_sub(args)
            if prog == 'docker-compose' or sub == 'compose':
                if prog == 'docker':
                    sub, rest = _docker_sub(rest)
                if sub in COMPOSE_ASK:
                    asks.append('docker compose %s' % sub)
                if sub == 'build':
                    builds = True
            elif sub in DOCKER_ASK:
                asks.append('docker %s' % sub)
            elif sub == 'container':
                s2, _ = _docker_sub(rest)
                if s2 in DOCKER_ASK:
                    asks.append('docker container %s' % s2)
            elif sub in ('build', 'buildx', 'builder'):
                builds = True
        elif prog == 'systemctl':
            sub, rest = _docker_sub(args)
            if sub in SYSTEMCTL_ALWAYS:
                asks.append('systemctl %s' % sub)
            elif sub in SYSTEMCTL_ASK and any('rccar' in r for r in rest):
                asks.append('systemctl %s rccar' % sub)
        elif prog in POWER_CMDS:
            asks.append(prog)
        elif prog in ('init', 'telinit') and args and args[0] in ('0', '6'):
            asks.append('%s %s' % (prog, args[0]))
    return asks, builds


def classify(command):
    """'ask' if the command (re)starts hardware / reboots, else 'allow'."""
    return 'ask' if _flags(command)[0] else 'allow'


def is_build(command):
    """True for make ros-image|setup, docker build, docker compose build."""
    return _flags(command)[1]


def is_driver_path(path, root=None):
    """True if path is under rccar_drivers/, rccar_description/ or is docker/ros.Dockerfile."""
    if not path:
        return False
    if os.path.isabs(path):
        root = root or os.environ.get('CLAUDE_PROJECT_DIR') or os.getcwd()
        rel = os.path.relpath(os.path.realpath(path), os.path.realpath(root))
    else:
        rel = os.path.normpath(path)
    if rel.startswith('..'):
        return False
    rel = rel.replace(os.sep, '/')
    return rel.startswith(DRIVER_PATHS) or rel in DRIVER_FILES


def drivers_running():
    """True iff the compose `drivers` container (project rccar) runs; False on any error."""
    try:
        r = subprocess.run(
            ['docker', 'ps', '-q', '--filter', 'status=running',
             '--filter', 'label=com.docker.compose.project=rccar',
             '--filter', 'label=com.docker.compose.service=drivers'],
            capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0 and bool(r.stdout.strip())


def decide(data, running=drivers_running):
    """Return (decision, reason) or None for a PreToolUse payload."""
    tool = data.get('tool_name', '')
    ti = data.get('tool_input') or {}
    if tool == 'Bash':
        cmd = ti.get('command', '')
        asks, builds = _flags(cmd)
        if builds and running():
            return 'deny', DENY_RUNNING
        if asks:
            return 'ask', ('hardware (re)start / reboot requested (%s): needs explicit human '
                           'approval (.claude/rules/hw-testing.md)' % ', '.join(asks))
        return None
    if tool in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
        path = ti.get('file_path') or ti.get('notebook_path') or ''
        if is_driver_path(path) and running():
            return 'deny', DENY_RUNNING
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    res = decide(data)
    if res:
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': 'PreToolUse', 'permissionDecision': res[0],
            'permissionDecisionReason': res[1]}}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
