#!/usr/bin/env python3
"""Prepare the approved foundation/Archive pilot in new local repositories only."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

BASELINE = '97c1899499e52a42f6eaddca188aac4eca32b96e'
SOURCE = Path(__file__).resolve().parents[1]


def run(*args, cwd=None, capture=False):
    result = subprocess.run(args, cwd=cwd, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else None


def write(root, name, content, executable=False):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if executable:
        path.chmod(0o755)


def commit(root, message):
    run('git', 'add', '.', cwd=root)
    run('git', 'commit', '-m', message, cwd=root)
    return run('git', 'rev-parse', 'HEAD', cwd=root, capture=True)


def workspace(root, members, name):
    original = (root / 'Cargo.toml').read_text()
    package = original[original.index('[workspace.package]'):]
    package = package.replace('https://github.com/design-nexus/nixe"',
                              f'https://github.com/design-nexus/{name}"')
    write(root, 'Cargo.toml', '[workspace]\nresolver = "3"\nmembers = '
          + json.dumps(members) + '\n\n' + package)
    write(root, '.gitignore', '/target/\n/dist/\n')


def dependency(root, file, crate, repo, revision):
    path = root / file
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        if line.startswith(crate + ' = '):
            lines[i] = f'{crate} = {{ git = "{repo.as_uri()}", rev = "{revision}" }}'
            break
    else:
        raise RuntimeError(f'Missing dependency {crate} in {path}')
    path.write_text('\n'.join(lines) + '\n')


def guidance(root, name, architecture, commands):
    write(root, 'AGENTS.md', f'''# {name}

{architecture}

Commands: {commands}

Use the public, pinned shared crates; never import another application's internals.
Keep application names, IDs, paths, D-Bus interfaces, and data formats stable.
Use canonical STYLE.md from the pinned nixe-design dependency. Reuse existing
widgets, theme tokens, icons, and shortcuts. Media Player defines video controls.
Run essential targeted checks only. Do not download models or run inference for
routine verification. Install app updates without opening/restarting them.
Common guidance: https://github.com/design-nexus/nixe/blob/main/docs/AGENTS_COMMON.md
This file carries the essential common rules so offline work remains possible.

This is a local migration pilot. Dependencies use immutable local Git revisions.
Do not publish until file:// dependencies are replaced with approved remote URLs,
lockfiles are regenerated, and compatibility checks pass.
''')
    write(root, '.github/workflows/check.yml', '''name: Standalone check
# Enable PR/push events only after publication readiness passes.
on: workflow_dispatch
permissions:
  contents: read
jobs:
  check:
    runs-on: ubuntu-latest
    container: archlinux:latest
    steps:
      - uses: actions/checkout@v4
      - name: Publication prerequisite
        run: |
          if grep -R 'file://' --include='Cargo.toml' .; then
            echo 'Local pilot: replace dependencies before enabling hosted CI.'
            exit 1
          fi
      - name: Build prerequisites
        run: pacman -Syu --noconfirm --needed base-devel rust gtk4 pkgconf git
      - run: cargo check --locked --workspace
''')


def extract(destination, name, paths, tag=None):
    root = destination / name
    run('git', 'clone', '--no-local', '--single-branch', '--no-tags', '--branch',
        'main', str(SOURCE), str(root))
    if run('git', 'rev-parse', 'HEAD', cwd=root, capture=True) != BASELINE:
        raise RuntimeError('Source moved; review a new baseline before splitting')
    if tag:
        run('git', 'fetch', '--no-tags', str(SOURCE), f'refs/tags/{tag}:refs/tags/{tag}', cwd=root)
    args = ['git', 'filter-repo']
    for path in paths:
        args += ['--path', path]
    if name == 'nixe-archive':
        # Archive's pre-import branch has root-level src/data and five commits.
        # Scope renames to that ancestry so other imported apps are excluded.
        legacy_tip = '4d24026'
        legacy = run('git', 'rev-list', legacy_tip, cwd=SOURCE, capture=True).splitlines()
        old_paths = run('git', 'ls-tree', '--name-only', legacy_tip,
                        cwd=SOURCE, capture=True).splitlines()
        for path in old_paths:
            args += ['--path', path]
        callback = (
            'legacy = ' + repr({h.encode() for h in legacy}) + '\n'
            'if commit.original_id in legacy:\n'
            '    for change in commit.file_changes:\n'
            '        change.filename = b"apps/archive/" + change.filename\n'
            'else:\n'
            '    common = {b"Cargo.toml", b"Cargo.lock", b"LICENSE", b"rustfmt.toml"}\n'
            '    commit.file_changes = [c for c in commit.file_changes '
            'if c.filename.startswith(b"apps/archive/") or c.filename in common]\n'
        )
        args += ['--commit-callback', callback]
    run(*args, cwd=root)
    shutil.copy2(root / '.git/filter-repo/commit-map', destination / f'{name}-commit-map.txt')
    # Byte equality at the baseline, before intentional standalone adaptations.
    for path in paths:
        original = SOURCE / path
        files = original.rglob('*') if original.is_dir() else [original]
        for source in files:
            if source.is_file():
                relative = source.relative_to(SOURCE)
                expected = subprocess.run(['git', 'show', f'{BASELINE}:{relative}'], cwd=SOURCE,
                                          check=True, stdout=subprocess.PIPE).stdout
                if (root / relative).read_bytes() != expected:
                    raise RuntimeError(f'Extraction changed {relative}')
    return root


def prepare_archive(dest, core, core_rev, design, design_rev):
    common = ["Cargo.toml", "Cargo.lock", "LICENSE", "rustfmt.toml"]
    archive = extract(dest, 'nixe-archive', common + ['apps/archive/'], 'archive-v0.1.0')
    workspace(archive, ['apps/archive'], 'nixe-archive')
    dependency(archive, 'apps/archive/Cargo.toml', 'nixe-core', core, core_rev)
    for crate in ['nixe-theme', 'nixe-ui']:
        dependency(archive, 'apps/archive/Cargo.toml', crate, design, design_rev)
    manifest = archive / 'apps/archive/Cargo.toml'
    manifest.write_text(manifest.read_text().replace('repository = "https://github.com/design-nexus/nixe"',
                                                   'repository = "https://github.com/design-nexus/nixe-archive"'))
    icon = 'io.github.design_nexus.nixe.Archive.svg'
    write(archive, f'apps/archive/data/{icon}',
          (design / 'crates/nixe-icons/apps' / icon).read_text())
    write(archive, 'install.sh', '''#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ${1:-} != --no-build ]]; then
  cargo build --manifest-path "$root/Cargo.toml" --release --locked -p nixe-archive
fi
binary="${CARGO_TARGET_DIR:-$root/target}/release/nixe-archive"
share="${XDG_DATA_HOME:-$HOME/.local/share}"
bin="${NIXE_BIN_DIR:-$HOME/.local/bin}"
install -Dm755 "$binary" "$bin/nixe-archive"
install -Dm644 "$root/apps/archive/data/io.github.design_nexus.nixe.Archive.desktop" \
  "$share/applications/io.github.design_nexus.nixe.Archive.desktop"
install -Dm644 "$root/apps/archive/data/io.github.design_nexus.nixe.Archive.svg" \
  "$share/icons/hicolor/scalable/apps/io.github.design_nexus.nixe.Archive.svg"
command -v update-desktop-database >/dev/null && update-desktop-database "$share/applications" || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q "$share/icons/hicolor" || true
''', True)
    write(archive, 'uninstall.sh', '''#!/usr/bin/env bash
set -euo pipefail
share="${XDG_DATA_HOME:-$HOME/.local/share}"
bin="${NIXE_BIN_DIR:-$HOME/.local/bin}"
# Remove installed program resources only; never remove application data.
rm -f -- "$bin/nixe-archive" \
 "$share/applications/io.github.design_nexus.nixe.Archive.desktop" \
 "$share/icons/hicolor/scalable/apps/io.github.design_nexus.nixe.Archive.svg"
command -v update-desktop-database >/dev/null && update-desktop-database "$share/applications" || true
''', True)
    for action in ['install', 'uninstall']:
        write(archive, f'apps/archive/{action}.sh', f'''#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${{BASH_SOURCE[0]}}")/../.." && pwd)
exec "$root/{action}.sh" "$@"
''', True)
    guidance(archive, 'Archive', 'GTK4 archive manager backed by 7-Zip. The existing application remains\nin apps/archive; all shared dependencies use pinned Git sources.',
             '`cargo build --release --locked -p nixe-archive`; `./install.sh`')
    write(archive, 'README.md', '''# Archive

Standalone migration pilot of the existing Nixe Archive application.

Build: `cargo build --release --locked -p nixe-archive`.
Install: `./install.sh` (binary, launcher, icon; does not launch the app).
Requires Rust, GTK4 >= 4.18 development files, pkg-config, and 7-Zip at runtime.
Data, application identity, command-line behavior, and UI are unchanged.
Shared dependencies currently use local immutable Git sources. Publishing is gated.
The retained archive-v0.1.0 tag records historical source, not this new packaging.
''')
    write(archive, 'tools/package.sh', '''#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cargo build --manifest-path "$root/Cargo.toml" --release --locked -p nixe-archive
mkdir -p "$root/dist"
stage=$(mktemp -d "$root/dist/package.XXXXXX")
trap 'rm -rf -- "$stage"' EXIT
install -Dm755 "${CARGO_TARGET_DIR:-$root/target}/release/nixe-archive" "$stage/bin/nixe-archive"
install -Dm644 "$root/apps/archive/data/io.github.design_nexus.nixe.Archive.desktop" \
 "$stage/share/applications/io.github.design_nexus.nixe.Archive.desktop"
install -Dm644 "$root/apps/archive/data/io.github.design_nexus.nixe.Archive.svg" \
 "$stage/share/icons/hicolor/scalable/apps/io.github.design_nexus.nixe.Archive.svg"
cp "$root/LICENSE" "$stage/"
tar -C "$stage" -czf "$root/dist/archive-$(uname -m).tar.gz" .
sha256sum "$root/dist/archive-$(uname -m).tar.gz"
''', True)
    run('cargo', 'metadata', '--format-version', '1', cwd=archive, capture=True)
    archive_rev = commit(archive, 'Prepare standalone Archive pilot with pinned dependencies and installer')
    return archive, archive_rev


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    dest = args.destination.resolve()
    if dest.exists():
        parser.error('Destination already exists; choose a new directory. Nothing is overwritten.')
    if run('git', 'rev-parse', 'HEAD', cwd=SOURCE, capture=True) != BASELINE:
        parser.error('Source HEAD differs from the reviewed baseline')
    # Documentation/tooling additions are allowed; implementation source must match.
    run('git', 'diff', '--exit-code', BASELINE, '--', 'Cargo.toml', 'Cargo.lock', 'apps', 'crates',
        'extensions', 'STYLE.md', cwd=SOURCE)
    run('git', 'filter-repo', '--version')
    dest.mkdir(parents=True)
    run('git', 'bundle', 'create', str(dest / 'nixe-before.bundle'), '--all', cwd=SOURCE)
    run('git', 'bundle', 'verify', str(dest / 'nixe-before.bundle'), cwd=SOURCE)
    write(dest, 'source-refs.txt', run('git', 'show-ref', cwd=SOURCE, capture=True) + '\n')
    common = ['Cargo.toml', 'Cargo.lock', 'LICENSE', 'rustfmt.toml']

    core = extract(dest, 'nixe-core', common + ['crates/nixe-core/', 'crates/nixe-accounts/',
                                              'crates/nixe-sync/', 'docs/online-accounts/'])
    workspace(core, ['crates/nixe-core', 'crates/nixe-accounts', 'crates/nixe-sync'], 'nixe-core')
    guidance(core, 'Core', 'Three existing libraries: application foundation, GOA/EDS metadata discovery,\nand provider-independent WebDAV sync. No UI, helper binary, or application internals are extracted.',
             '`cargo check --locked --workspace`; `cargo check --locked -p nixe-core --no-default-features`')
    run('cargo', 'metadata', '--offline', '--format-version', '1', cwd=core, capture=True)
    core_rev = commit(core, 'Prepare standalone Core workspace from reviewed Nixe baseline')

    design = extract(dest, 'nixe-design', common + ['STYLE.md', 'crates/nixe-theme/',
        'crates/nixe-ui/', 'crates/nixe-icons/'])
    workspace(design, ['crates/nixe-theme', 'crates/nixe-ui', 'crates/nixe-icons'], 'nixe-design')
    for crate in ['nixe-theme', 'nixe-ui']:
        dependency(design, f'crates/{crate}/Cargo.toml', 'nixe-core', core, core_rev)
    guidance(design, 'Design', 'Canonical STYLE.md, GTK widgets, themes/base CSS, live Omarchy following,\nand application icons. Preserve current rendering and public APIs.',
             '`cargo check --locked --workspace`; `python3 tools/package-assets.py`')
    write(design, 'tools/package-assets.py',
          (SOURCE / 'tools/templates/package-design-assets.py').read_text(), True)
    run('cargo', 'metadata', '--format-version', '1', cwd=design, capture=True)
    design_rev = commit(design, 'Prepare standalone Design workspace pinned to Core')

    archive, archive_rev = prepare_archive(dest, core, core_rev, design, design_rev)
    result = {'baseline': BASELINE, 'destination': str(dest), 'repositories': {
        'core': {'path': str(core), 'revision': core_rev},
        'design': {'path': str(design), 'revision': design_rev},
        'archive': {'path': str(archive), 'revision': archive_rev}}}
    write(dest, 'pilot.json', json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
