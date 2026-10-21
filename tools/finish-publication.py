#!/usr/bin/env python3
"""Finish the approved source publication after GitHub's creation cooldown."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]


def run(*args, capture=False):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip() if capture else subprocess.check_call(args, cwd=ROOT)


def complete():
    records = json.loads((ROOT / 'docs/migration/publication.json').read_text())['repositories']
    return len(records) == 25 and all(r.get('published') for r in records.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wait-for-pid', type=int)
    args = parser.parse_args()
    expected_head = run('git', 'rev-parse', 'HEAD', capture=True)
    if args.wait_for_pid:
        while True:
            try:
                os.kill(args.wait_for_pid, 0)
            except ProcessLookupError:
                break
            time.sleep(30)
    for attempt in range(3):
        if complete():
            break
        print('Publication incomplete; allowing a further 15-minute server cooldown.', flush=True)
        time.sleep(900)
        result = subprocess.run(['python3', 'tools/publish-migration.py'], cwd=ROOT)
        if result.returncode and attempt == 2:
            raise RuntimeError('Publication remains blocked; receipts preserved')
    if not complete():
        raise RuntimeError('Publication incomplete; receipts preserved')
    # A concurrent agent or user must not have unrelated work committed/pushed.
    if run('git', 'rev-parse', 'HEAD', capture=True) != expected_head:
        raise RuntimeError('Umbrella HEAD changed; final pins retained in receipt, automatic commit stopped')
    allowed = {'docs/migration/publication.json', 'docs/migration/repositories.json', 'suite.toml'}
    changed = set(run('git', 'diff', '--name-only', capture=True).splitlines())
    if changed - allowed or run('git', 'diff', '--cached', '--name-only', capture=True):
        raise RuntimeError('Unrelated umbrella changes; automatic commit stopped')
    run('python3', 'tools/record-publication.py')
    run('bin/nixe', 'release', 'check', '--structure-only')
    run('git', 'add', *sorted(allowed))
    run('git', 'commit', '-m', 'Record all 25 published standalone source repositories')
    run('git', 'push', 'origin', 'main')
    print('All 25 source repositories published and umbrella manifest pushed.', flush=True)


if __name__ == '__main__':
    main()
