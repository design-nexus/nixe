#!/usr/bin/env python3
"""Nixe suite development and non-publishing release checks (Python 3.11+)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def run(args, cwd=None, capture=False):
    return subprocess.run(args, cwd=cwd, text=True, check=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def load():
    manifest = Path(os.environ.get('NIXE_SUITE_MANIFEST', ROOT / 'suite.toml')).resolve()
    data = tomllib.loads(manifest.read_text())
    if data.get('schema_version') != 1:
        raise ValueError('Unsupported suite manifest schema')
    repos = {entry['id']: entry for entry in data['repositories']}
    apps = {entry['id']: entry for entry in data['applications']}
    if len(repos) != len(data['repositories']) or len(apps) != len(data['applications']):
        raise ValueError('Duplicate manifest identifiers')
    for repo in repos.values():
        if not all(re.fullmatch('[0-9a-f]{40}', value) for value in [repo['revision'], repo.get('dependency_revision', repo['revision']), repo.get('release_revision', repo['revision'])]):
            raise ValueError(f"Unpinned repository: {repo['id']}")
    for app in apps.values():
        if app['repository'] not in repos:
            raise ValueError(f"Unknown repository for {app['id']}")
        if Path(app['manifest']).is_absolute() or '..' in Path(app['manifest']).parts:
            raise ValueError('Application manifests must stay inside the checkout')
    state_path = ROOT / '.nixe-local.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    return repos, apps, state


def checkout(repo, state):
    if repo.get('mode') == 'self':
        return ROOT
    # Explicit local overrides are useful before GitHub repositories exist.
    override = state.get('repositories', {}).get(repo['id'], {}).get('path')
    if override:
        return Path(override)
    workspace = Path(os.environ.get('NIXE_DEV_HOME', ROOT.parent))
    return workspace / repo['name']


def selected(apps, target):
    if target == 'all':
        return [app for app in apps.values() if app.get('default', True)]
    if target not in apps:
        raise ValueError(f"Unknown app {target!r}; choose {', '.join(apps)} or all")
    return [apps[target]]


def revision(path):
    return run(['git', '-C', str(path), 'rev-parse', 'HEAD'], capture=True).strip()


def status(repos, state):
    for repo in repos.values():
        path = checkout(repo, state)
        if not (path / '.git').exists():
            print(f"{repo['id']:12} missing  {path}")
            continue
        head = revision(path)
        dirty = bool(run(['git', '-C', str(path), 'status', '--porcelain'], capture=True).strip())
        flags = ['self' if repo.get('mode') == 'self' else ('pinned' if head == repo['revision'] else 'DRIFT')]
        if dirty:
            flags.append('dirty')
        overrides = list(path.glob('.cargo/config*'))
        if any('patch.' in p.read_text() for p in overrides if p.is_file()):
            flags.append('Cargo patch')
        print(f"{repo['id']:12} {head[:12]} {', '.join(flags):20} {path}")


def setup(repos, state):
    missing = [name for name in ['git', 'cargo', 'pkg-config'] if not shutil.which(name)]
    if missing:
        raise ValueError('Missing prerequisites: ' + ', '.join(missing))
    for repo in repos.values():
        path = checkout(repo, state)
        if path.exists():
            print(f'Keeping existing checkout: {path}')
            continue
        if repo['status'] != 'published':
            raise ValueError(f"{repo['id']} is unpublished; run the local preparation script first")
        path.parent.mkdir(parents=True, exist_ok=True)
        run(['git', 'clone', '--no-checkout', repo['url'], str(path)])
        run(['git', '-C', str(path), 'checkout', '--detach', repo['revision']])
    status(repos, state)


def build_or_test(repos, apps, state, target, action):
    # Group packages to avoid repeatedly invoking Cargo for the same workspace.
    groups = {}
    for app in selected(apps, target):
        repo = repos[app['repository']]
        path = checkout(repo, state)
        if not path.exists():
            raise ValueError(f'Missing checkout: {path}; run nixe dev setup')
        if revision(path) != repo['revision']:
            raise ValueError(f"{repo['id']} has revision drift; inspect nixe dev status")
        for command in app.get('prepare', []):
            run(command, cwd=path)
        groups.setdefault((path, app['manifest']), []).extend(app['packages'])
    for (path, manifest), packages in groups.items():
        command = ['cargo', action, '--locked', '--manifest-path', str(path / manifest)]
        for package in dict.fromkeys(packages):
            command += ['-p', package]
        run(command, cwd=path)


def is_ancestor(path, older, newer):
    """True when commit `older` is `newer` or comes before it in `path`'s history."""
    if older == newer:
        return True
    return subprocess.run(['git', '-C', str(path), 'merge-base', '--is-ancestor', older, newer],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def compatibility_errors(repos, apps, state):
    owners = {name: owner for owner, names in {
        'core': ['nixe-core', 'nixe-accounts', 'nixe-sync'],
        'design': ['nixe-theme', 'nixe-ui', 'nixe-playback'],
        'passwords': ['nixe-passwords-proto'],
        'cloud': ['nixe-cloud'],
        'glimpse': ['glimpse-plugin-sdk'],
    }.items() for name in names}
    errors = []
    for app in apps.values():
        repo = repos[app['repository']]
        root = checkout(repo, state)
        lock = root / Path(app['manifest']).parent / 'Cargo.lock'
        if not lock.exists():
            errors.append(f"{app['id']}: missing lockfile {lock}")
            continue
        seen = {}
        for package in tomllib.loads(lock.read_text()).get('package', []):
            owner = owners.get(package['name'])
            source = package.get('source', '')
            if owner not in repos or not source.startswith('git+'):
                continue
            expected = repos[owner].get('dependency_revision', repos[owner]['revision'])
            # The shared revision, or an older one in its history: apps move to a
            # newer one when they need it, not all together.
            pinned = source.rsplit('#', 1)[-1]
            if ('rev=' + pinned) not in source or not is_ancestor(checkout(repos[owner], state), pinned, expected):
                errors.append(f"{app['id']}: incompatible {package['name']} Git revision")
            if package['name'] in seen and source != seen[package['name']]:
                errors.append(f"{app['id']}: duplicate sources for {package['name']}")
            seen[package['name']] = source
    return errors


def release_check(repos, apps, state, structural=False):
    errors = compatibility_errors(repos, apps, state)
    for repo in repos.values():
        path = checkout(repo, state)
        if not path.exists():
            errors.append(f"{repo['id']}: missing checkout")
            continue
        if repo.get('mode') != 'self' and revision(path) != repo['revision']:
            errors.append(f"{repo['id']}: revision drift")
        if not structural:
            release_revision = repo.get('release_revision', repo['revision'])
            if repo.get('artifacts') and repo.get('artifact_revision', repo['revision']) != release_revision:
                errors.append(f"{repo['id']}: release artifacts predate published dependency metadata")
            if release_revision != repo['revision']:
                changed = run(['git', '-C', str(path), 'diff', '--name-only', release_revision, repo['revision']], capture=True).splitlines()
                if any(name not in ['build-environment.json', 'tools/ci-bootstrap.sh'] and not name.startswith('.github/workflows/') for name in changed):
                    errors.append(f"{repo['id']}: application source changed since supported release")
            if repo['status'] != 'published':
                errors.append(f"{repo['id']}: local pilot, not published")
            if run(['git', '-C', str(path), 'status', '--porcelain'], capture=True).strip():
                errors.append(f"{repo['id']}: uncommitted changes")
            manifests = run(['git', '-C', str(path), 'ls-files', '*Cargo.toml'], capture=True).splitlines()
            for name in manifests:
                text = (path / name).read_text()
                if 'file://' in text:
                    errors.append(f"{repo['id']}: local Git dependency in {name}")
            for artifact in repo.get('artifacts', []):
                resource = path / artifact
                if not resource.is_file():
                    errors.append(f"{repo['id']}: missing artifact {artifact}")
                else:
                    expected = repo.get('artifact_sha256', {}).get(artifact)
                    actual = hashlib.sha256(resource.read_bytes()).hexdigest()
                    if not expected or actual != expected:
                        errors.append(f"{repo['id']}: missing/mismatched checksum for {artifact}")
    for app in apps.values():
        if not structural and app['target_repository'] != repos[app['repository']]['name']:
            errors.append(f"{app['id']}: still in monorepo; target {app['target_repository']}")
        path = checkout(repos[app['repository']], state)
        if path.exists() and not (path / app['manifest']).is_file():
            errors.append(f"{app['id']}: missing Cargo manifest")
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print('Suite structure is valid.' if structural else 'Release checks passed.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='group', required=True)
    dev = commands.add_parser('dev').add_subparsers(dest='action', required=True)
    dev.add_parser('setup')
    dev.add_parser('status')
    for action in ['build', 'test']:
        dev.add_parser(action).add_argument('target')
    release = commands.add_parser('release').add_subparsers(dest='action', required=True)
    release.add_parser('check').add_argument('--structure-only', action='store_true')
    release.add_parser('notes').add_argument('target')
    args = parser.parse_args()
    try:
        repos, apps, state = load()
        if args.group == 'release':
            if args.action == 'notes':
                app = selected(apps, args.target)
                if len(app) != 1:
                    raise ValueError('Choose one application for release notes')
                app = app[0]
                root = checkout(repos[app['repository']], state)
                tags = run(['git', 'tag', '-l', app['id'] + '-v*', '--sort=-version:refname'], cwd=root, capture=True).splitlines()
                revision_range = tags[0] + '..HEAD' if tags else 'HEAD'
                print('# ' + app['id'] + ' release notes\n')
                print(run(['git', 'log', revision_range, '--format=- %s (%h)', '--', app['source'], 'crates'], cwd=root, capture=True))
                return 0
            return release_check(repos, apps, state, args.structure_only)
        if args.action == 'setup':
            setup(repos, state)
        elif args.action == 'status':
            status(repos, state)
        else:
            build_or_test(repos, apps, state, args.target, args.action)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'nixe: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
