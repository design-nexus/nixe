#!/usr/bin/env python3
"""Publish the explicitly approved 25 local Nixe splits, without force pushes."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import tomllib
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.nixe-local.json'
RECEIPT = ROOT / 'docs/migration/publication.json'
ORDER = ['core', 'design', 'passwords', 'glimpse', 'archive', 'notepad', 'tasks', 'chat',
         'fonts', 'music', 'torrents', 'pdf', 'contacts', 'photos', 'office', 'weather',
         'git', 'store', 'news', 'capture', 'media-player', 'theater', 'pulse', 'settings', 'assistant']


def run(*args, cwd=ROOT, capture=False):
    result = subprocess.run(args, cwd=cwd, check=True, text=True,
                            env=dict(os.environ, CARGO_NET_GIT_FETCH_WITH_CLI='true'),
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def save(state, receipt):
    STATE.write_text(json.dumps(state, indent=2) + '\n')
    RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n')


def registry_versions(lock):
    return {(p['name'], p['version']) for p in tomllib.loads(lock.read_text()).get('package', [])
            if p.get('source', '').startswith('registry+')}


def prepare(id, root, state):
    changed = False
    paths = run('git', 'ls-files', '*Cargo.toml', cwd=root, capture=True).splitlines()
    for name in paths:
        path = root / name
        lines = path.read_text().splitlines(keepends=True)
        for index, line in enumerate(lines):
            match = re.search(r'\bgit\s*=\s*"([^"]+)"', line)
            if not match:
                continue
            repo = Path(urlparse(match[1]).path).name.removesuffix('.git')
            owner = repo.removeprefix('nixe-')
            if owner not in state['repositories']:
                if match[1].startswith('file://'):
                    raise RuntimeError(f'Unknown local dependency in {path}')
                continue
            dependency = state['repositories'][owner]
            if dependency.get('publication_status') != 'published':
                raise RuntimeError(f'{id} requires unpublished dependency {owner}')
            url = 'https://github.com/design-nexus/nixe-' + owner + '.git'
            revision = dependency.get('dependency_revision', dependency['revision'])
            line = line[:match.start(1)] + url + line[match.end(1):]
            if not re.search(r'\brev\s*=', line):
                raise RuntimeError(f'Unpinned dependency in {path}')
            line = re.sub(r'\brev\s*=\s*"[^"]+"', 'rev = "' + revision + '"', line)
            changed |= line != lines[index]
            lines[index] = line
        path.write_text(''.join(lines))
    for name in ['AGENTS.md', 'README.md']:
        path = root / name
        if not path.exists():
            continue
        text = path.read_text()
        text = re.sub(r'This is a local migration pilot\.[\s\S]*$',
            'Shared dependencies use immutable GitHub revisions. Coordinate public API changes\n'
            'with the suite manifest and affected consumers in design-nexus/nixe.\n'
            'Historical application tags preserve provenance; standalone builds use main\n'
            'or subsequent releases. Original release assets remain in the umbrella repo.\n', text)
        text = re.sub(r'Shared dependencies (?:currently )?use (?:local immutable Git sources|immutable local Git sources)[\s\S]*$',
            'Shared dependencies are pinned to immutable GitHub revisions.\n'
            'Use main for the standalone build; preserved tags describe historical source.\n', text)
        text = text.replace('Publication remains gated.', 'Shared dependencies are pinned to published GitHub commits.')
        path.write_text(text)
    if id in ['core', 'design'] and not (root / 'README.md').exists():
        content = ('# Core\n\nShared Rust workspace: nixe-core (identity, paths, preferences, control),\n'
                   'nixe-accounts (GOA/EDS metadata discovery), and nixe-sync (WebDAV journal).\n\n'
                   'Check: `cargo check --locked --workspace`. Headless foundation: '
                   '`cargo check --locked -p nixe-core --no-default-features`.\n\n'
                   'Architecture and public API boundaries: [AGENTS.md](AGENTS.md).\n') if id == 'core' else (
                   '# Design\n\nCanonical [STYLE.md](STYLE.md), GTK widgets, themes/CSS, icons, and shared playback.\n'
                   'Crates: nixe-theme, nixe-ui, nixe-icons, nixe-playback.\n\n'
                   'Check: `cargo check --locked --workspace`. Assets: `python3 tools/package-assets.py`.\n\n'
                   'Architecture and public API boundaries: [AGENTS.md](AGENTS.md).\n')
        (root / 'README.md').write_text(content)
    workflow = root / '.github/workflows/check.yml'
    text = workflow.read_text().replace('on: workflow_dispatch', 'on:\n  pull_request:\n  workflow_dispatch:')
    text = re.sub(r'^# (?:Enable PR/push events|Remains manual).*\n', '', text, flags=re.M)
    workflow.write_text(text)
    installer = root / 'install.sh'
    if installer.exists():
        text = installer.read_text().replace('REPO="design-nexus/nixe"', 'REPO="design-nexus/nixe-' + id + '"')
        # Full standalone clones include companion plugins and every owned crate;
        # sparse monorepo trimming would invalidate their lockfiles/membership.
        text = text.replace('--filter=blob:none --sparse', '--filter=blob:none')
        text = re.sub(r'^\s*git -C "\$work/(?:src|assistant)" sparse-checkout set[^\n]*\n', '', text, flags=re.M)
        text = text.replace('  locked=()\n', '  # Complete standalone checkout retains its committed lockfile.\n')
        installer.write_text(text)
    manifest = root / ('apps/assistant/Cargo.toml' if id == 'assistant' else 'Cargo.toml')
    lock = manifest.with_name('Cargo.lock')
    versions = registry_versions(lock)
    run('cargo', 'metadata', '--format-version', '1', '--manifest-path', str(manifest), cwd=root, capture=True)
    if registry_versions(lock) - versions:
        raise RuntimeError(f'Registry packages unexpectedly changed for {id}')
    if id == 'glimpse':
        run('cargo', 'metadata', '--format-version', '1', '--manifest-path',
            str(root / 'apps/glimpse/examples/rust-plugin/Cargo.toml'), cwd=root, capture=True)
    if installer.exists():
        run('bash', '-n', str(installer), cwd=root)
    for path in paths:
        if 'file://' in (root / path).read_text():
            raise RuntimeError(f'Unconverted local dependency {path}')
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true', help='Convert and commit consumers without creating remotes')
    args = parser.parse_args()
    state = json.loads(STATE.read_text())
    receipt = json.loads(RECEIPT.read_text()) if RECEIPT.exists() else {'approval': 'User approved publication of all 25 repositories.', 'repositories': {}}
    existing = {r['name'] for r in json.loads(run('gh', 'repo', 'list', 'design-nexus', '--limit', '200', '--json', 'name', capture=True))}
    if args.prepare_only and any(state['repositories'][id].get('publication_status') != 'published' for id in ['core', 'design', 'passwords', 'glimpse']):
        raise RuntimeError('Publish the four dependency owners before batching remaining consumers')
    for id in ORDER:
        record = state['repositories'][id]
        root = Path(record['path'])
        if record.get('publication_status') == 'published':
            print(f'{id}: already published', flush=True)
            continue
        name = 'nixe-' + id
        prior = receipt['repositories'].get(id, {})
        if name in existing and not prior.get('created'):
            raise RuntimeError(f'{name} already exists outside this publication; refusing to overwrite')
        if not prior.get('prepared'):
            if run('git', 'status', '--porcelain', cwd=root, capture=True):
                raise RuntimeError(f'{id}: unexpected local changes')
            before = run('git', 'rev-parse', 'HEAD', cwd=root, capture=True)
            prepare(id, root, state)
            run('git', 'add', '.', cwd=root)
            run('git', 'commit', '-m', 'Publish standalone repository with immutable GitHub dependencies', cwd=root)
            revision = run('git', 'rev-parse', 'HEAD', cwd=root, capture=True)
            prior.update(prepared=True, previous_revision=before, revision=revision)
            receipt['repositories'][id] = prior
            save(state, receipt)
        if args.prepare_only:
            continue
        revision = prior['revision']
        if not prior.get('created'):
            # GitHub applies a separate repository-creation throttle. Respect it
            # with bounded backoff; checkpoints make interruption/resumption safe.
            for attempt in range(7):
                result = subprocess.run(['gh', 'repo', 'create', 'design-nexus/' + name,
                    '--public', '--source', str(root), '--remote', 'origin',
                    '--description', 'Nixe ' + id.replace('-', ' ') + ' — native Rust/GTK components for Omarchy'],
                    text=True, capture_output=True)
                print(result.stdout + result.stderr, end='', flush=True)
                if result.returncode == 0:
                    break
                if 'created too many repositories, too quickly' not in result.stderr or attempt == 6:
                    raise RuntimeError(f'{name}: repository creation failed; checkpoint retained')
                delay = min(900, 120 * (2 ** attempt))
                print(f'{name}: GitHub creation throttle; backing off {delay}s', flush=True)
                for _ in range(delay // 60):
                    time.sleep(60)
            prior['created_at'] = int(time.time())
            prior['created'] = True
            save(state, receipt)
        run('git', 'push', '-u', 'origin', 'main', cwd=root)
        if run('git', 'tag', '-l', cwd=root, capture=True):
            run('git', 'push', 'origin', '--tags', cwd=root)
        record.update(revision=revision, publication_status='published', url='https://github.com/design-nexus/' + name)
        if id in ['design', 'passwords', 'glimpse']:
            record['dependency_revision'] = revision
        prior.update(published=True, url=record['url'])
        save(state, receipt)
        print(f'{id}: published {revision[:12]} {record["url"]}', flush=True)
        if id != ORDER[-1]:
            time.sleep(65)
    print('All consumer metadata prepared.' if args.prepare_only else 'All 25 repositories published without force pushes.', flush=True)


if __name__ == '__main__':
    main()
