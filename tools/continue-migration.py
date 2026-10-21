#!/usr/bin/env python3
"""Prepare remaining standalone Nixe repositories locally; never publish or rewrite source."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tomllib

spec = importlib.util.spec_from_file_location('pilot', Path(__file__).with_name('prepare-migration.py'))
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
SOURCE = pilot.SOURCE
BASELINE = pilot.BASELINE
run, write, commit = pilot.run, pilot.write, pilot.commit
COMMON = ['Cargo.toml', 'Cargo.lock', 'LICENSE', 'rustfmt.toml']
OWNED = {
    'passwords': ['nixe-passwords-core', 'nixe-passwords-proto'],
    'glimpse': ['glimpse-plugin-sdk'],
    'weather': ['nixe-weather-core'],
    'news': ['nixe-news-core'],
    'capture': ['nixe-capture-core'],
    'pulse': ['nixe-telegram-core', 'nixe-telegram-calls'],
    'theater': ['nixe-media-model', 'nixe-media-cache', 'nixe-plex', 'nixe-jellyfin'],
    'settings': ['nixe-goa-helper'],
}
ORDER = ['notepad', 'tasks', 'chat', 'fonts', 'music', 'torrents', 'pdf', 'contacts',
         'photos', 'office', 'weather', 'git', 'store', 'passwords', 'glimpse',
         'news', 'capture', 'media-player', 'theater', 'pulse', 'settings', 'assistant']
EXTRA = {key: [f'apps/{key}-glimpse/'] for key in ['news', 'capture', 'pulse']}
PREPARATION = {
    'pulse': [['bash', 'apps/pulse/packaging/prepare-native.sh']],
}


def tracked(revision=BASELINE, paths=None, cwd=SOURCE):
    return run('git', 'ls-tree', '-r', '--name-only', revision, '--', *(paths or []),
               cwd=cwd, capture=True).splitlines()


def legacy_groups(prefixes):
    groups = []
    lines = run('git', 'log', BASELINE, '--merges', '--format=%H%x09%P%x09%s',
                cwd=SOURCE, capture=True).splitlines()
    for line in lines:
        _, parents, message = line.split('\t', 2)
        for prefix in prefixes:
            plain = prefix.rstrip('/')
            if message.endswith(' into ' + plain) or message.startswith("Add '" + plain + "/'"):
                tip = parents.split()[1]
                groups.append({'prefix': plain + '/', 'tip': tip,
                               'commits': run('git', 'rev-list', tip, cwd=SOURCE, capture=True).splitlines(),
                               'roots': sorted({n.split('/')[0] for n in run('git', 'log', tip, '--format=', '--name-only', cwd=SOURCE, capture=True).splitlines() if n})})
    return groups


def extract(dest, name, paths, prefixes, tags):
    root = dest / name
    if root.exists():
        raise RuntimeError(f'{root} already exists; no repository is overwritten')
    run('git', 'clone', '--no-local', '--single-branch', '--no-tags', '--branch',
        'main', str(SOURCE), str(root))
    if run('git', 'rev-parse', 'HEAD', cwd=root, capture=True) != BASELINE:
        raise RuntimeError('Source moved; review baseline before continuing')
    for tag in tags:
        run('git', 'fetch', '--no-tags', str(SOURCE), f'refs/tags/{tag}:refs/tags/{tag}', cwd=root)
    groups = legacy_groups(prefixes)
    args = ['git', 'filter-repo']
    for path in dict.fromkeys(paths + [p for group in groups for p in group['roots']]):
        args += ['--path', path]
    callback = 'groups = ' + repr([(g['prefix'].encode(), {c.encode() for c in g['commits']}) for g in groups]) + '\n'
    callback += 'for prefix, commits in groups:\n'
    callback += '    if commit.original_id in commits:\n'
    callback += '        for change in commit.file_changes:\n'
    callback += '            change.filename = prefix + change.filename\n'
    callback += '        break\nelse:\n'
    callback += '    paths = ' + repr([p.encode() for p in paths]) + '\n'
    callback += '    commit.file_changes = [c for c in commit.file_changes if any(c.filename.startswith(p) if p.endswith(b"/") else c.filename == p for p in paths)]\n'
    args += ['--commit-callback', callback]
    run(*args, cwd=root)
    shutil.copy2(root / '.git/filter-repo/commit-map', dest / f'{name}-commit-map.txt')
    for name in tracked(paths=paths):
        expected = subprocess.check_output(['git', 'show', f'{BASELINE}:{name}'], cwd=SOURCE)
        if (root / name).read_bytes() != expected:
            raise RuntimeError(f'Extraction changed {name}')
    # Verify each imported ancestry retains a representative source blob and identity.
    mapping = dict(line.split() for line in (dest / f'{root.name}-commit-map.txt').read_text().splitlines()[1:])
    for group in groups:
        for old in group['commits']:
            new = mapping.get(old, '0' * 40)
            if new == '0' * 40:
                continue  # Commits emptied by the filter are recorded in the map.
            candidates = [n for n in tracked(old) if n.endswith(('.rs', '.py', '.cpp', '.qml'))]
            if not candidates:
                continue
            name = candidates[0]
            left = subprocess.check_output(['git', 'show', f'{old}:{name}'], cwd=SOURCE)
            right = subprocess.check_output(['git', 'show', f'{new}:{group["prefix"]}{name}'], cwd=root)
            if left != right:
                raise RuntimeError(f'Historical source mismatch: {old}:{name}')
            format = '--format=%an <%ae> %aI %cn <%ce> %cI'
            if subprocess.check_output(['git', 'show', '-s', format, old], cwd=SOURCE) != subprocess.check_output(['git', 'show', '-s', format, new], cwd=root):
                raise RuntimeError('History attribution changed')
    return root, [{'prefix': g['prefix'], 'tip': g['tip'], 'commits': len(g['commits'])} for g in groups]


def pin_dependencies(root, dependencies):
    for name in run('git', 'ls-files', '*Cargo.toml', cwd=root, capture=True).splitlines():
        path = root / name
        lines = path.read_text().splitlines()
        for index, line in enumerate(lines):
            match = re.match(r'([\w-]+)\s*=\s*\{.*\bpath\s*=\s*"[^"]+"', line)
            if match and match[1] in dependencies:
                source, revision = dependencies[match[1]]
                lines[index] = re.sub(r'\bpath\s*=\s*"[^"]+"',
                    f'git = "{source.as_uri()}", rev = "{revision}"', line)
        path.write_text('\n'.join(lines) + '\n')


def prepare_playback(dest, state):
    design_info = state['repositories']['design']
    design = Path(design_info['path'])
    if (design / 'crates/nixe-playback').exists():
        return
    history, groups = extract(dest, 'nixe-playback-history', ['crates/nixe-playback/'], [], [])
    run('git', 'fetch', '--no-tags', str(history), 'main', cwd=design)
    run('git', 'merge', '--allow-unrelated-histories', '--no-commit', 'FETCH_HEAD', cwd=design)
    core = state['repositories']['core']
    pin_dependencies(design, {'nixe-core': (Path(core['path']), core['revision'])})
    manifest = design / 'Cargo.toml'
    text = manifest.read_text().replace('"crates/nixe-icons"]', '"crates/nixe-icons", "crates/nixe-playback"]')
    manifest.write_text(text)
    write(design, 'docs/PLAYBACK.md', '''# Shared playback

The existing nixe-playback crate lives with GTK components because it depends on
nixe-ui. Media Player, Theater, and Pulse pin this same Design revision. Core stays
independent of Design, avoiding repository cycles and duplicate Git crate sources.
No playback API, controls, or application behavior changes are introduced.
''')
    run('cargo', 'metadata', '--format-version', '1', cwd=design, capture=True)
    design_info['revision'] = commit(design, 'Keep shared GTK playback with Design to avoid repository dependency cycles')


def packaging(root, app, directory, metadata, baseline_installer):
    # Retain application-specific legacy/default/plugin/native/helper integrations.
    install = baseline_installer
    install = re.sub(r'^ALL=\([^\n]+\)', f'ALL=({app})', install, flags=re.M)
    install = install.replace('apps=() make_default=false gear=false', '''# This standalone checkout installs only its owning application.
if [[ $# == 0 || ${1:-} == --* ]]; then set -- OWNER "$@"; fi
apps=() make_default=false gear=false'''.replace('OWNER', app))
    needle = 'command -v hyprctl >/dev/null || warn'
    guard = f'''for selected in "${{apps[@]}}"; do
  [[ $selected == {app} ]] || die "This repository installs only {app}."
done

'''
    install = install.replace(needle, guard + needle)
    install = install.replace('$src/target/release', '${CARGO_TARGET_DIR:-$src/target}/release')
    install = install.replace('install -m 755 "$src/bin/nixe" "$bin/nixe"',
                              '[[ -x $bin/nixe ]] || install -m 755 "$src/bin/nixe" "$bin/nixe"')
    # Respect the standing no-restart preference, including vault services.
    install = install.replace('    systemctl --user try-restart nixe-passwords.service 2>/dev/null || true',
                              '    # Leave the running vault untouched; the new binary is used at its next start.')
    start = install.index('    sudo install -d -m 755 /usr/local/lib/nixe-store')
    end = install.index('    # The privileged entry point', start)
    block = install[start:end]
    install = install[:start] + ('    if ! cmp -s "${CARGO_TARGET_DIR:-$src/target}/release/nixe-store-helper" /usr/local/lib/nixe-store/nixe-store-helper || ! cmp -s "$d/data/io.github.design_nexus.nixe.store.policy" /usr/share/polkit-1/actions/io.github.design_nexus.nixe.store.policy; then\n' + block + '    fi\n') + install[end:]
    write(root, 'install.sh', install, True)
    uninstall = subprocess.check_output(['git', 'show', f'{BASELINE}:uninstall.sh'], cwd=SOURCE, text=True)
    uninstall = re.sub(r'^ALL=\([^\n]+\)', f'ALL=({app})', uninstall, flags=re.M)
    uninstall = uninstall.replace('apps=() purge=false', f'if [[ $# == 0 || ${{1:-}} == --* ]]; then set -- {app} "$@"; fi\napps=() purge=false')
    uninstall = uninstall.replace('bin="$HOME/.local/bin"', f'''for selected in "${{apps[@]}}"; do
  [[ $selected == {app} ]] || die "This repository removes only {app}."
done
bin="$HOME/.local/bin"''')
    write(root, 'uninstall.sh', uninstall, True)
    write(root, 'tools/package.py', (SOURCE / 'tools/package-standalone.py').read_text(), True)
    spec = {'application': app, 'directory': directory,
            'packages': metadata['packages'], 'manifest': metadata['manifest'],
            'prepare': metadata.get('prepare', []), 'binaries': metadata.get('binaries', [])}
    write(root, 'packaging.json', json.dumps(spec, indent=2) + '\n')


def prepare_app(dest, app, state, app_info, dependencies):
    directory = 'gallery' if app == 'photos' else app
    prefixes = [f'apps/{directory}/']
    paths = COMMON + prefixes + EXTRA.get(app, []) + [f'crates/{c}/' for c in OWNED.get(app, [])]
    if app == 'assistant':
        paths = ['LICENSE', 'rustfmt.toml', 'install.sh', 'uninstall.sh', 'bin/nixe'] + prefixes
    else:
        paths += ['install.sh', 'uninstall.sh', 'bin/nixe']
    if app == 'settings':
        prefixes += ['extensions/']
        paths += ['extensions/']
    tags = [t for t in run('git', 'tag', '-l', cwd=SOURCE, capture=True).splitlines()
            if t.startswith(app + '-v') or (app == 'settings' and t.startswith('ext-'))]
    # Icon resources are packaged copies, versioned by their Design source revision.
    if app != 'assistant':
        desktop_files = [n for n in tracked(paths=[f'apps/{directory}/data/']) if n.endswith('.desktop')]
        for desktop in desktop_files:
            content = subprocess.check_output(['git', 'show', f'{BASELINE}:{desktop}'], cwd=SOURCE, text=True)
            icon = re.search(r'^Icon=(.+)$', content, re.M)
            if icon and icon[1].startswith('io.github.design_nexus.nixe.'):
                paths += [f'crates/nixe-icons/apps/{icon[1]}.svg']
    if app == 'assistant':
        app_info = dict(app_info, packages=['nixe-assistantd', 'assistant-tui', 'assistant-plugin-worker', 'assistant-privileged', 'assistant-asr'])
    root, groups = extract(dest, 'nixe-' + app, paths, prefixes, tags)
    if app != 'assistant':
        members = prefixes[:1] + EXTRA.get(app, []) + [f'crates/{c}' for c in OWNED.get(app, [])]
        pilot.workspace(root, [p.rstrip('/') for p in members], 'nixe-' + app)
        if app == 'settings':
            # Excluded independent extension workspaces keep their own lockfiles.
            p = root / 'Cargo.toml'
            p.write_text(p.read_text().replace('[workspace.package]', 'exclude = ["extensions"]\n\n[workspace.package]'))
        if app == 'glimpse':
            p = root / 'Cargo.toml'
            p.write_text(p.read_text().replace('[workspace.package]', 'exclude = ["apps/glimpse/inference", "apps/glimpse/examples/rust-plugin"]\n\n[workspace.package]'))
    else:
        write(root, '.gitignore', '/target/\n/dist/\n/apps/assistant/target/\n/apps/assistant/browser/node_modules/\n')
    # Preserve feature flags such as Passwords' client interface on Git dependencies.
    pin_dependencies(root, {name: value for name, value in dependencies.items() if name not in OWNED.get(app, [])})
    # Metadata of each crate now points at the owning repository, not the umbrella.
    for name in run('git', 'ls-files', '*Cargo.toml', cwd=root, capture=True).splitlines():
        p = root / name
        p.write_text(p.read_text().replace('repository = "https://github.com/design-nexus/nixe"',
                                         f'repository = "https://github.com/design-nexus/nixe-{app}"'))
    pilot.guidance(root, app.title(), f'Application source: apps/{directory}. Owned domain crates: '
        + (', '.join(OWNED.get(app, [])) or 'none') + '.\nKeep all existing runtime integration resources and public protocols.',
        f'`cargo build --release --locked --manifest-path {app_info["manifest"]}`; `./install.sh`')
    packaging(root, app, directory, app_info,
              subprocess.check_output(['git', 'show', f'{BASELINE}:install.sh'], cwd=SOURCE, text=True))
    if app == 'assistant':
        # Never restart, download a browser, or run inference merely to install this split.
        installer = root / 'apps/assistant/scripts/install.sh'
        text = installer.read_text()
        text = text.replace('start_after=0', 'start_after=0\n# Migration installs preserve stopped/running state without restarting.')
        text = text.replace('then start_after=1; fi', 'then :; fi')
        text = text.replace('npm ci --prefix "$root/browser" --ignore-scripts',
            '[[ -d "$root/browser/node_modules/playwright" ]] || npm ci --prefix "$root/browser" --ignore-scripts')
        text = text.replace('PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/nixe-assistant/chromium" "$node_bin" "$root/browser/node_modules/playwright/cli.js" install chromium',
            '# Browser download stays an explicit later runtime setup operation.')
        text = text.replace('$root/target/release', '${CARGO_TARGET_DIR:-$root/target}/release')
        text = text.replace('cargo build --release -p', 'cargo build --release --locked -p')
        text = text.replace('  systemctl --user stop nixe-assistantd.service nixe-assistant-hud.service || true',
                            '  # Restore files without stopping the running Assistant.')
        text = text.replace('  if [[ $(cat "$backup/daemon-state") == active ]]; then systemctl --user restart nixe-assistantd.service nixe-assistant-hud.service || true; fi',
                            '  # Keep the pre-install running process unchanged.')
        text = text.replace('systemctl --user disable nixe-assistant-stt.service nixe-assistant-hud.service', '# Preserve existing service enablement during migration.')
        text = text.replace('systemctl --user enable nixe-assistantd.service', '# Existing daemon enablement is retained.')
        text = text.replace('Installed (not started: it was stopped). Start it with: nixe-assistant start. Backup:', 'Installed without starting or restarting Assistant. Backup:')
        installer.write_text(text)
    manifest = root / app_info['manifest']
    run('cargo', 'metadata', '--format-version', '1', '--manifest-path', str(manifest), cwd=root, capture=True)
    for manifest in run('git', 'ls-files', '*Cargo.toml', cwd=root, capture=True).splitlines():
        if manifest == app_info['manifest']:
            continue
        # Verify independent plugin examples without building inference or extensions.
        if manifest == 'apps/glimpse/examples/rust-plugin/Cargo.toml':
            run('cargo', 'metadata', '--format-version', '1', '--manifest-path', str(root / manifest), cwd=root, capture=True)
    revision = commit(root, f'Prepare independent {app} repository with preserved integrations and pinned shared dependencies')
    record = {'path': str(root), 'revision': revision, 'history_groups': groups, 'tags': tags}
    state['repositories'][app] = record
    for name in OWNED.get(app, []):
        dependencies[name] = (root, revision)
    return record


def update_manifest(state):
    path = SOURCE / 'suite.toml'
    text = path.read_text()
    repo_end = text.index('[[applications]]')
    header, application_text = text[:repo_end], text[repo_end:]
    for id, record in state['repositories'].items():
        if id == 'monorepo':
            continue
        pattern = r'(\[\[repositories\]\]\nid = "' + re.escape(id) + r'"\n.*?\nrevision = ")[^"]+'
        if re.search(pattern, header, re.S):
            header = re.sub(pattern, lambda match: match[1] + record['revision'], header, count=1, flags=re.S)
        else:
            header += '\n[[repositories]]\n' + f'id = "{id}"\nname = "nixe-{id}"\nurl = "https://github.com/design-nexus/nixe-{id}.git"\nrevision = "{record["revision"]}"\nstatus = "prepared"\n'
    chunks = application_text.split('[[applications]]')
    for i in range(1, len(chunks)):
        id = re.search(r'id = "([^"]+)"', chunks[i])[1]
        if id in state['repositories']:
            chunks[i] = re.sub(r'^repository = "[^"]+"', f'repository = "{id}"', chunks[i], flags=re.M)
    path.write_text(header + '[[applications]]'.join(chunks))
    (SOURCE / '.nixe-local.json').write_text(json.dumps(state, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--apps', nargs='+', choices=ORDER, default=ORDER)
    parser.add_argument('--reprepare', action='store_true', help='Prepare new copies in a new destination; keep earlier repos intact')
    args = parser.parse_args()
    if run('git', 'rev-parse', 'HEAD', cwd=SOURCE, capture=True) != BASELINE:
        parser.error('Source HEAD differs from reviewed baseline')
    run('git', 'diff', '--exit-code', BASELINE, '--', 'Cargo.toml', 'Cargo.lock', 'apps', 'crates', 'extensions', 'STYLE.md', cwd=SOURCE)
    dest = args.destination.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    state = json.loads((SOURCE / '.nixe-local.json').read_text())
    info = tomllib.loads((SOURCE / 'suite.toml').read_text())
    apps = {entry['id']: entry for entry in info['applications']}
    prepare_playback(dest, state)
    update_manifest(state)
    core, design = state['repositories']['core'], state['repositories']['design']
    dependencies = {name: (Path(core['path']), core.get('dependency_revision', core['revision'])) for name in ['nixe-core', 'nixe-accounts', 'nixe-sync']}
    dependencies.update({name: (Path(design['path']), design.get('dependency_revision', design['revision'])) for name in ['nixe-ui', 'nixe-theme', 'nixe-playback']})
    for owner, names in OWNED.items():
        if owner in state['repositories']:
            record = state['repositories'][owner]
            dependencies.update({name: (Path(record['path']), record.get('dependency_revision', record['revision'])) for name in names})
    for app in ORDER:
        if app not in args.apps:
            continue
        if app in state['repositories'] and not args.reprepare:
            print(f'Keeping already prepared {app}', flush=True)
            continue
        print(f'Preparing {app}', flush=True)
        prepare_app(dest, app, state, apps[app], dependencies)
        update_manifest(state)
        write(dest, 'migration-state.json', json.dumps(state, indent=2) + '\n')
    print('Local splits prepared. No remote repositories created or pushed.')


if __name__ == '__main__':
    main()
