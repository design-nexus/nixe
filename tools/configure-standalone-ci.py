#!/usr/bin/env python3
"""Add app-specific, publication-gated CI to prepared local repositories."""
import json
from pathlib import Path
import subprocess
import tomllib
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('migration', ROOT / 'tools/continue-migration.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)
CI = '''#!/usr/bin/env python3
"""Hosted checks: require published dependency sources; never fetch/run models."""
import json
from pathlib import Path
import subprocess
root = Path(__file__).resolve().parents[1]
names = subprocess.check_output(['git', 'ls-files', '*Cargo.toml'], cwd=root, text=True).splitlines()
if any('file://' in (root / name).read_text() for name in names):
    raise SystemExit('Publish immutable shared dependency sources before enabling hosted CI.')
spec = json.loads((root / 'packaging.json').read_text())
for command in spec.get('prepare', []):
    subprocess.run(command, cwd=root, check=True)
command = ['cargo', 'build', '--release', '--locked', '--manifest-path', spec['manifest']]
for package in spec['packages']:
    command += ['-p', package]
subprocess.run(command, cwd=root, check=True)
for command in spec['test_commands']:
    subprocess.run(command, cwd=root, check=True)
subprocess.run(['python3', 'tools/package.py', '--no-build'], cwd=root, check=True)
subprocess.run(['python3', 'tools/release-notes.py'], cwd=root, check=True)
'''


def main():
    state = json.loads((ROOT / '.nixe-local.json').read_text())
    apps = {a['id']: a for a in tomllib.loads((ROOT / 'suite.toml').read_text())['applications']}
    for owner in ['core', 'design', 'passwords', 'glimpse']:
        state['repositories'][owner].setdefault('dependency_revision', state['repositories'][owner]['revision'])
    for id, app in apps.items():
        record = state['repositories'][id]
        root = Path(record['path'])
        info = root / 'packaging.json'
        data = json.loads(info.read_text())
        if data.get('test_commands'):
            continue
        if id == 'assistant':
            data['test_commands'] = [['cargo', 'test', '--locked', '--manifest-path', app['manifest'],
                                      '-p', 'assistant-core', '-p', 'assistant-policy', '--lib']]
        elif id == 'passwords':
            data['test_commands'] = [['cargo', 'test', '--locked', '-p', 'nixe-passwords-core',
                                      '-p', 'nixe-passwords-proto', '--lib']]
        else:
            binary = app['packages'][0]
            data['test_commands'] = [['cargo', 'test', '--locked', '-p', binary, '--bin', binary]]
        info.write_text(json.dumps(data, indent=2) + '\n')
        (root / 'tools/release-notes.py').write_text((ROOT / 'tools/release-notes.py').read_text())
        if id != 'archive':
            directory = data['directory']
            display = {'photos': 'Photos', 'media-player': 'Media Player', 'pdf': 'PDF', 'git': 'Git'}.get(id, id.title())
            (root / 'README.md').write_text(f"# {display}\n\nApplication source: [apps/{directory}](apps/{directory}).\n\nBuild with `cargo build --release --locked --manifest-path {app['manifest']}`.\nInstall with `./install.sh`; package with `python3 tools/package.py`.\nGenerate notes with `python3 tools/release-notes.py`.\n\nRead AGENTS.md for public dependency and design boundaries. Publication remains gated.\n")
        (root / 'tools/ci.py').write_text(CI)
        workflow = '''name: Independent application checks
# Remains manual until approved immutable remote dependencies are published.
on: workflow_dispatch
permissions:
  contents: read
jobs:
  application:
    runs-on: ubuntu-latest
    container: archlinux:latest
    steps:
      - uses: actions/checkout@v4
      - name: Dependency publication gate
        run: |
          if grep -R 'file://' --include='Cargo.toml' .; then
            echo 'Local split: publish pinned dependency sources first.'
            exit 1
          fi
      - name: Build prerequisites
        run: |
          source <(sed -n '/^app_info()/,/^}/p' install.sh)
          app_info APP
          pacman -Syu --noconfirm --needed base-devel rust python git gtk4 pkgconf cmake ninja clang $deps
      - name: Locked build, targeted tests and package
        run: python3 tools/ci.py
'''.replace('app_info APP', 'app_info ' + id)
        (root / '.github/workflows/check.yml').write_text(workflow)
        subprocess.run(['git', 'add', '.'], cwd=root, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git', 'commit', '-m', 'Add independent locked build, targeted test and package pipeline'], cwd=root, check=True, stdout=subprocess.DEVNULL)
        record['revision'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    migration.update_manifest(state)
    # Different checkout and public-interface revisions are intentional. CI-only
    # commits do not require rewriting every consumer's already pinned source.
    p = ROOT / 'suite.toml'
    text = p.read_text()
    for owner in ['core', 'design', 'passwords', 'glimpse']:
        needle = f'id = "{owner}"\nname = "nixe-{owner}"\n'
        declaration = f'dependency_revision = "{state["repositories"][owner]["dependency_revision"]}"\n'
        text = text.replace(needle, needle + declaration)
    p.write_text(text)
    (ROOT / 'docs/migration/repositories.json').write_text(json.dumps(state, indent=2) + '\n')


if __name__ == '__main__':
    main()
