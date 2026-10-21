#!/usr/bin/env python3
"""Build/package local splits once, install without launching, and record results."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apps', nargs='+')
    parser.add_argument('--skip-install', action='store_true')
    args = parser.parse_args()
    state = json.loads((ROOT / '.nixe-local.json').read_text())
    suite = tomllib.loads((ROOT / 'suite.toml').read_text())
    destination = ROOT / 'docs/migration/application-validation.json'
    results = json.loads(destination.read_text()) if destination.exists() else {}
    env = dict(os.environ, CARGO_TARGET_DIR=str(ROOT / 'target'), CARGO_BUILD_JOBS='2',
               NIXE_NATIVE_CACHE=str(ROOT / 'target/native'))
    for app in suite['applications']:
        id = app['id']
        if args.apps and id not in args.apps:
            continue
        if not args.apps and id in ['archive', 'assistant']:
            continue  # Archive was validated; Assistant has its own target/cache.
        if id not in state['repositories']:
            raise RuntimeError(f'{id} is not extracted')
        state = json.loads((ROOT / '.nixe-local.json').read_text())
        record = state['repositories'][id]
        repo = Path(record['path'])
        if results.get(id, {}).get('revision') == record['revision'] and results[id].get('installed'):
            print(f'{id}: already built and installed at the pinned revision', flush=True)
            continue
        log = Path('/tmp') / f'nixe-migration-{id}.log'
        try:
            with log.open('w') as output:
                print(f'{id}: building/package (log: {log})', flush=True)
                subprocess.run(['python3', 'tools/package.py'], cwd=repo, env=env,
                               stdout=output, stderr=subprocess.STDOUT, check=True)
                artifact = next((repo / 'dist').glob(f'{id}-*.tar.gz'))
                result = {'revision': record['revision'], 'built': True,
                          'artifact': str(artifact), 'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
                          'installed': False, 'log': str(log)}
                results[id] = result
                destination.write_text(json.dumps(results, indent=2) + '\n')
                if not args.skip_install and id not in ['git', 'store']:
                    marker = repo / '.prebuilt'
                    if marker.exists():
                        raise RuntimeError(f'Unexpected existing marker {marker}')
                    try:
                        marker.touch()
                        print(f'{id}: installing without launching', flush=True)
                        subprocess.run(['bash', 'install.sh', id], cwd=repo, env=env,
                                       stdout=output, stderr=subprocess.STDOUT, check=True)
                        result['installed'] = True
                    finally:
                        marker.unlink(missing_ok=True)
                elif id in ['git', 'store']:
                    result['installation_pending'] = 'administrator authorization'
                destination.write_text(json.dumps(results, indent=2) + '\n')
                print(f'{id}: ready' + (' (system installation pending)' if not result['installed'] else ''), flush=True)
        except subprocess.CalledProcessError:
            results.setdefault(id, {})['failure_log'] = str(log)
            destination.write_text(json.dumps(results, indent=2) + '\n')
            print(f'{id}: failed; see {log}', flush=True)
            # Independent failures must not prevent preparing other applications.
    print('Build/install receipts: ' + str(destination), flush=True)


if __name__ == '__main__':
    main()
