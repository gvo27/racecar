"""
Read-only rosbag2 recorder of the lidar topics (offline sensor-fusion work).

Wraps ``ros2 bag record`` (storage mcap) for a fixed duration; publishes nothing.
Jazzy CLI: ``ros2 bag record [-s STORAGE] [-o OUTPUT] [topics ...]``.
"""
import argparse
from datetime import datetime, timezone
import os
import signal
import subprocess
import sys
import time

TOPICS = [
    '/rccar/lidar/scan', '/rccar/lidar/imu', '/rccar/mapper/pose', '/rccar/mapper/map',
    '/tf', '/tf_static', '/diagnostics', '/robot_description',
]
MIN_SECS = 1
MAX_SECS = 600
DEFAULT_SECS = 30
DEFAULT_OUT_DIR = '/ws/src/racecar/logs'
STOP_TIMEOUT_S = 15.0

HINT = ('open the .mcap in Foxglove (Open local file) or read it with rosbag2_py; '
        'logs/ is gitignored')


def parse_secs(value) -> int:
    """Parse a duration in whole seconds within [MIN_SECS, MAX_SECS]."""
    try:
        secs = int(str(value).strip())
    except ValueError:
        raise ValueError(f'secs must be an integer, got {value!r}') from None
    if not MIN_SECS <= secs <= MAX_SECS:
        raise ValueError(f'secs must be in [{MIN_SECS}, {MAX_SECS}], got {secs}')
    return secs


def bag_dirname(t_unix: float) -> str:
    """lidar_bag_<UTC YYYYmmddTHHMMSSZ> for a wall-clock time."""
    stamp = datetime.fromtimestamp(t_unix, timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return f'lidar_bag_{stamp}'


def build_command(topics, out_path, storage='mcap') -> list:
    """Return the argv for ``ros2 bag record`` of ``topics`` into ``out_path``."""
    return ['ros2', 'bag', 'record', '-s', storage, '-o', out_path, *topics]


def info_command(out_path) -> list:
    """Return the argv for ``ros2 bag info`` of a finished bag."""
    return ['ros2', 'bag', 'info', out_path]


def _out_dir_ok(out_dir) -> bool:
    return os.path.isdir(out_dir) and os.access(out_dir, os.W_OK | os.X_OK)


def _stop(proc, timeout_s=STOP_TIMEOUT_S, signalled=False) -> str:
    """
    SIGINT the recorder so the mcap is closed; fall back to terminate/kill.

    signalled: the terminal's Ctrl+C already reached the recorder (same process
    group), so do not send a second SIGINT that could cut its shutdown short.
    """
    if proc.poll() is not None:
        return 'exited'
    if not signalled:
        proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=timeout_s)
        return 'stopped'
    except subprocess.TimeoutExpired:
        pass
    print(f'recorder ignored SIGINT for {timeout_s:.0f} s, terminating (bag may be '
          'incomplete)', file=sys.stderr)
    proc.terminate()
    try:
        proc.wait(timeout=5.0)
        return 'terminated'
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return 'killed'


def main(argv=None, popen=subprocess.Popen, run=subprocess.run, sleep=time.sleep,
         now=time.time) -> int:
    """Record the lidar topics for --secs seconds; return 0 if the bag exists."""
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('--secs', type=parse_secs, default=DEFAULT_SECS,
                        help=f'duration in s ({MIN_SECS}..{MAX_SECS}, default '
                             f'{DEFAULT_SECS})')
    parser.add_argument('--out-dir',
                        default=os.environ.get('RCCAR_LOG_DIR', DEFAULT_OUT_DIR),
                        help='directory for the bag (default $RCCAR_LOG_DIR or '
                             f'{DEFAULT_OUT_DIR})')
    args = parser.parse_args(argv)

    if not _out_dir_ok(args.out_dir):
        print(f'error: out dir {args.out_dir} does not exist or is not writable',
              file=sys.stderr)
        return 2
    out_path = os.path.join(args.out_dir, bag_dirname(now()))
    print(f'recording {len(TOPICS)} topics for {args.secs} s (Ctrl+C stops early):')
    for topic in TOPICS:
        print(f'  {topic}')
    print(f'bag: {out_path}', flush=True)

    proc = popen(build_command(TOPICS, out_path))
    interrupted = False
    try:
        sleep(args.secs)
    except KeyboardInterrupt:
        interrupted = True
        print('stopping early (Ctrl+C)', flush=True)
    result = _stop(proc, signalled=interrupted)
    print(f'recorder {result}', flush=True)

    if not os.path.isdir(out_path):
        print(f'error: no bag written at {out_path}', file=sys.stderr)
        return 1
    run(info_command(out_path), check=False)
    print(HINT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
