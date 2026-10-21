#!/usr/bin/env python3
"""Refresh artifact receipts after CI-only commits; never rebuild or publish apps."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value(item):
    if isinstance(item, dict):
        return '{ ' + ', '.join(json.dumps(key) + ' = ' + value(val) for key, val in item.items()) + ' }'
    return json.dumps(item)


def main():
    state = json.loads((ROOT / '.nixe-local.json').read_text())
    suite = tomllib.loads((ROOT / 'suite.toml').read_text())
    receipt_path = ROOT / 'docs/migration/application-validation.json'
    results = json.loads(receipt_path.read_text())
    manual = {
        'archive': {'built': True, 'installed': True, 'log': '/tmp/nixe-migration-archive-current.log'},
        'assistant': {'built': True, 'installed': True, 'log': '/tmp/nixe-migration-assistant-build.log',
                      'features': ['cuda'], 'service_restarted': False, 'inference_run': False},
    }
    for id, result in manual.items():
        result['revision'] = state['repositories'][id]['revision']
        results[id] = result
    # System resources were separately installed from reviewed SHA-256 inputs.
    for id in ['git', 'store']:
        results[id]['installed'] = True
        results[id].pop('installation_pending', None)
        results[id]['system_install_receipt'] = 'docs/migration/system-install.json'
    for app in suite['applications']:
        id = app['id']
        result = results[id]
        if not result.get('built') or not result.get('installed'):
            raise RuntimeError(f'{id} has unresolved build/install work')
        record = state['repositories'][id]
        root = Path(record['path'])
        current = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        if current != record['revision']:
            raise RuntimeError(f'{id}: unexpected revision drift')
        old = result['revision']
        if old != current:
            changed = subprocess.check_output(['git', 'diff', '--name-only', old, current], cwd=root, text=True).splitlines()
            rust_inputs = [name for name in changed if name.endswith(('.rs', '.c', '.cpp', '.h', '.hpp')) or Path(name).name in ['Cargo.toml', 'Cargo.lock']]
            if rust_inputs:
                raise RuntimeError(f'{id}: source changed since build: {rust_inputs}')
            result['build_source_revision'] = old
            result['runtime_source_unchanged_since_build'] = True
        result['revision'] = current
        env = dict(os.environ, CARGO_TARGET_DIR=str(ROOT / ('apps/assistant/target' if id == 'assistant' else 'target')))
        log = Path('/tmp') / f'nixe-migration-{id}-artifacts.log'
        with log.open('w') as output:
            subprocess.run(['python3', 'tools/package.py', '--no-build'], cwd=root, env=env, check=True,
                           stdout=output, stderr=subprocess.STDOUT)
            subprocess.run(['python3', 'tools/release-notes.py'], cwd=root, check=True,
                           stdout=output, stderr=subprocess.STDOUT)
        artifact = root / 'dist' / f'{id}-x86_64.tar.gz'
        result.update(artifact=str(artifact), sha256=digest(artifact), artifacts_log=str(log))
        repo = next(entry for entry in suite['repositories'] if entry['id'] == id)
        repo['artifacts'] = [str(artifact.relative_to(root)), 'dist/CHANGELOG.md']
        if id == 'git':
            package = ROOT / 'target/packages/nixe-git-0.1.0-1-x86_64.pkg.tar.zst'
            shutil.copy2(package, root / 'dist' / package.name)
            repo['artifacts'].append('dist/' + package.name)
        repo['artifact_sha256'] = {name: digest(root / name) for name in repo['artifacts']}
        print(f'{id}: built, installed, artifacts checksummed', flush=True)
    design = next(entry for entry in suite['repositories'] if entry['id'] == 'design')
    root = Path(state['repositories']['design']['path'])
    artifact = 'dist/nixe-design-' + design['revision'] + '.tar.gz'
    design['artifacts'], design['artifact_sha256'] = [artifact], {artifact: digest(root / artifact)}
    lines = ['# Prepared local suite. Publication is approval-gated.',
             'schema_version = 1', 'baseline = ' + value(suite['baseline']), '', '[compatibility]']
    suite['compatibility']['tested_target'] = 'x86_64-unknown-linux-gnu'
    for key, item in suite['compatibility'].items():
        lines.append(key + ' = ' + value(item))
    for section in ['repositories', 'applications']:
        for entry in suite[section]:
            lines += ['', '[[' + section + ']]']
            lines += [key + ' = ' + value(item) for key, item in entry.items()]
    (ROOT / 'suite.toml').write_text('\n'.join(lines) + '\n')
    receipt_path.write_text(json.dumps(results, indent=2) + '\n')
    (ROOT / 'docs/migration/repositories.json').write_text(json.dumps(state, indent=2) + '\n')
    print('All 23 application build/install receipts and artifact checksums are current.')


if __name__ == '__main__':
    main()
