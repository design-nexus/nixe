#!/usr/bin/env python3
"""Record completed source publication without relabeling prior binary artifacts."""
import argparse
import json
from pathlib import Path
import tomllib
ROOT = Path(__file__).resolve().parents[1]


def value(item):
    if isinstance(item, dict):
        return '{ ' + ', '.join(json.dumps(key) + ' = ' + value(val) for key, val in item.items()) + ' }'
    return json.dumps(item)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-partial', action='store_true', help='Record a truthful checkpoint while GitHub is throttling')
    args = parser.parse_args()
    state = json.loads((ROOT / '.nixe-local.json').read_text())
    suite = tomllib.loads((ROOT / 'suite.toml').read_text())
    receipt = json.loads((ROOT / 'docs/migration/publication.json').read_text())
    if len(receipt['repositories']) != 25 or not all(r.get('prepared') and (args.allow_partial or r.get('published')) for r in receipt['repositories'].values()):
        raise RuntimeError('All 25 source repositories must be published first')
    for repo in suite['repositories']:
        if repo['id'] == 'monorepo':
            repo['mode'] = 'self'  # The umbrella cannot embed its own commit hash.
            continue
        record = state['repositories'][repo['id']]
        checkpoint = receipt['repositories'][repo['id']]
        if repo.get('artifacts'):
            repo.setdefault('artifact_revision', repo['revision'])
        repo.update(status='published' if checkpoint.get('published') else 'prepared', revision=checkpoint['revision'])
        if record.get('url'):
            repo['url'] = record['url'].removesuffix('.git') + '.git'
        if 'dependency_revision' in record:
            repo['dependency_revision'] = record['dependency_revision']
    lines = ['# Source publication checkpoint. Binary snapshots retain their original artifact_revision.',
             'schema_version = 1', 'baseline = ' + value(suite['baseline']), '', '[compatibility]']
    for key, item in suite['compatibility'].items():
        lines.append(key + ' = ' + value(item))
    for section in ['repositories', 'applications']:
        for entry in suite[section]:
            lines += ['', '[[' + section + ']]']
            lines += [key + ' = ' + value(item) for key, item in entry.items()]
    (ROOT / 'suite.toml').write_text('\n'.join(lines) + '\n')
    (ROOT / 'docs/migration/repositories.json').write_text(json.dumps(state, indent=2) + '\n')
    count = sum(bool(r.get('published')) for r in receipt['repositories'].values())
    print(f'Recorded {count}/25 published source repositories; prior binary receipts preserved.')


if __name__ == '__main__':
    main()
