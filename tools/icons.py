#!/usr/bin/python3
"""Generate opt-in Nyx launcher icons. Runs only when explicitly invoked."""
import argparse
import colorsys
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

DATA = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
APPS = DATA / 'applications'
STATE = DATA / 'nyx/icons'
OUTPUT = DATA / 'icons/hicolor/scalable/apps'
# A read-only check must not create bytecode next to the bundled renderer.
sys.dont_write_bytecode = True


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def atomic(path, content, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.nyx-tmp')
    tmp.write_text(content)
    if mode is not None:
        tmp.chmod(mode)
    tmp.replace(path)


def fields(text):
    section = ''
    result = {}
    for line in text.splitlines():
        if line.startswith('['):
            section = line.strip()
        elif section == '[Desktop Entry]' and '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            result[key] = value
    return result


def replace_icon(text, icon):
    lines = text.splitlines(keepends=True)
    section = False
    for index, line in enumerate(lines):
        if line.startswith('['):
            if section:
                lines.insert(index, 'Icon=' + icon + '\n')
                return ''.join(lines)
            section = line.strip() == '[Desktop Entry]'
        elif section and line.startswith('Icon='):
            lines[index] = 'Icon=' + icon + '\n'
            return ''.join(lines)
    if section:
        return ''.join(lines).rstrip('\n') + '\nIcon=' + icon + '\n'
    raise ValueError('Missing [Desktop Entry]')


def roots():
    values = [APPS]
    values += [Path(p) / 'applications' for p in os.environ.get(
        'XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if p]
    values += [DATA / 'flatpak/exports/share/applications',
               Path('/var/lib/flatpak/exports/share/applications')]
    return list(dict.fromkeys(values))


def discover(records):
    found = {}
    for root in roots():
        if not root.is_dir():
            continue
        for path in sorted(root.rglob('*.desktop')):
            identity = '-'.join(path.relative_to(root).parts)
            if identity in found:
                continue
            record = records.get(identity)
            # Our local override must not hide upstream changes, hiding or removal.
            if record and not record['local'] and path == APPS / identity:
                continue
            found[identity] = path
    # Keep local originals available even while their Icon points at a managed asset.
    return found


def assets():
    candidates = [Path(__file__).resolve().parent / 'assets',
                  Path(__file__).resolve().parents[1] / 'assets/icons']
    for path in candidates:
        if (path / 'third-party-glyphs.json').is_file():
            spec = importlib.util.spec_from_file_location('nyx_icon_renderer', path / 'make_icons.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return path, module, json.loads((path / 'third-party-glyphs.json').read_text())
    raise ValueError('Icon assets are missing; reinstall the Nyx CLI icon tools.')


class Logos:
    def __init__(self):
        try:
            os.environ.setdefault('NO_AT_BRIDGE', '1')
            import gi
            gi.require_version('Gtk', '3.0')
            from gi.repository import Gtk, GdkPixbuf
        except (ImportError, ValueError) as error:
            raise ValueError('Icon lookup requires python-gobject and gtk3.') from error
        self.theme = Gtk.IconTheme.get_default()
        if self.theme is None:
            self.theme = Gtk.IconTheme.new()
            self.theme.set_custom_theme('hicolor')
        self.pixbuf = GdkPixbuf.Pixbuf

    def resolve(self, name):
        if not name:
            return None
        if name.startswith('/'):
            path = Path(name)
            return path if path.is_file() else None
        info = self.theme.lookup_icon(name, 128, 0)
        if info and info.get_filename():
            path = Path(info.get_filename())
            if path.is_file():
                return path
        for root in [DATA, *[Path(p) for p in os.environ.get(
                'XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if p]]:
            for suffix in ['', '.svg', '.png', '.xpm']:
                path = root / 'pixmaps' / (name + suffix)
                if path.is_file():
                    return path
        return None

    def render(self, path, renderer):
        # Decode to pixels first: arbitrary source SVG content is never embedded.
        image = self.pixbuf.new_from_file_at_scale(str(path), 128, 128, True)
        pixels, channels, stride = image.get_pixels(), image.get_n_channels(), image.get_rowstride()
        accents = []
        for y in range(0, image.get_height(), 3):
            for x in range(0, image.get_width(), 3):
                i = y * stride + x * channels
                if channels == 4 and pixels[i + 3] < 160:
                    continue
                rgb = tuple(value / 255 for value in pixels[i:i + 3])
                h, s, v = colorsys.rgb_to_hsv(*rgb)
                if s > .25 and v > .3:
                    accents.append((s * v, h))
        hue = sorted(accents)[len(accents) // 2][1] if accents else .62
        def color(s, v):
            return '#' + ''.join(f'{round(c * 255):02x}' for c in colorsys.hsv_to_rgb(hue, s, v))
        ok, png = image.save_to_bufferv('png', [], [])
        if not ok:
            raise ValueError('Could not rasterize logo')
        return renderer.render_logo(png, color(.38, .95), color(.65, .78))


def refresh():
    for executable, args in [('gtk-update-icon-cache', ['-f', '-t', '-q', str(DATA / 'icons/hicolor')]),
                             ('update-desktop-database', [str(APPS)])]:
        if shutil.which(executable):
            result = subprocess.run([executable, *args], capture_output=True, text=True)
            if result.returncode:
                print(f'Warning: {executable}: {result.stderr.strip()}', file=sys.stderr)


def save(records):
    atomic(STATE / 'manifest.json', json.dumps({'version': 1, 'entries': records}, indent=2) + '\n')


def unchanged_override(identity, record):
    path = APPS / identity
    return path.is_file() and path.read_text() == record['managed']


def restore_one(identity, record):
    target = APPS / identity
    if not unchanged_override(identity, record):
        # Already removed/restored files can safely release their assets.
        if target.exists() and (not record['local'] or target.read_text() != record['original']):
            return False
    elif record['local']:
        atomic(target, record['original'], record['mode'])
    else:
        target.unlink()
    icon = OUTPUT / record['asset']
    if icon.is_file() and digest(icon.read_bytes()) == record['output_hash']:
        icon.unlink()
    return True


def run(action):
    manifest = STATE / 'manifest.json'
    state = json.loads(manifest.read_text()) if manifest.exists() else {'version': 1, 'entries': {}}
    if state.get('version') != 1:
        raise ValueError('Unsupported icon manifest version')
    records = state['entries']
    counts = {}
    def report(status, name):
        counts[status] = counts.get(status, 0) + 1
        if status != 'current':
            print(f'{status}: {name}')
    if action == 'restore':
        for identity, record in list(records.items()):
            if restore_one(identity, record):
                del records[identity]
                save(records)
                report('restored', identity)
            else:
                report('conflict (launcher edited; left intact)', identity)
        refresh()
    else:
        asset_dir, renderer, registry = assets()
        curated = {identity: value['glyph'] for value in registry.values() for identity in value['desktop_ids']}
        renderer_hash = digest((asset_dir / 'make_icons.py').read_bytes())
        logos = None
        eligible = set()
        for identity, source in discover(records).items():
            record = records.get(identity)
            try:
                raw = source.read_text()
                if record:
                    if not unchanged_override(identity, record):
                        eligible.add(identity)
                        report('conflict (launcher edited; left intact)', identity)
                        continue
                    if record['local']:
                        raw = record['original']
                entry = fields(raw)
                if entry.get('Type') != 'Application' or entry.get('Hidden') == 'true' or entry.get('NoDisplay') == 'true':
                    continue
                if identity.startswith(('io.github.design_nexus.nyx.', 'io.github.design_nexus.nixe.')) or re.match(r'^(?:\S*/)?(?:nyx|nixe)-', entry.get('Exec', '')):
                    continue
                eligible.add(identity)
                label = entry.get('Name', identity)
                glyph = curated.get(identity)
                logo = None
                if glyph is None:
                    if logos is None:
                        logos = Logos()
                    logo = logos.resolve(entry.get('Icon', ''))
                    if logo is None:
                        report('unavailable (source icon missing)', label)
                        continue
                fingerprint = digest(raw + renderer_hash + (json.dumps(glyph, sort_keys=True) if glyph else digest(logo.read_bytes())))
                if record and record['fingerprint'] == fingerprint:
                    output = OUTPUT / record['asset']
                    if output.is_file() and digest(output.read_bytes()) == record['output_hash']:
                        report('current', label)
                        continue
                if action == 'check':
                    report('outdated' if record else 'missing', label)
                    continue
                svg = renderer.render_glyph(glyph) if glyph else logos.render(logo, renderer)
                asset = 'nyx-third-party-' + digest(identity)[:24] + '.svg'
                managed = replace_icon(raw, str(OUTPUT / asset))
                original = record['original'] if record else raw
                local = record['local'] if record else source == APPS / identity
                mode = record['mode'] if record and local else source.stat().st_mode & 0o777
                atomic(OUTPUT / asset, svg)
                records[identity] = dict(original=original, local=local, mode=mode,
                    managed=managed, fingerprint=fingerprint, asset=asset, output_hash=digest(svg))
                # Record ownership before changing the launcher so interruption is recoverable.
                save(records)
                atomic(APPS / identity, managed, mode)
                report('generated (curated)' if glyph else 'generated (original logo)', label)
            except Exception as error:
                eligible.add(identity)
                report('error', f'{identity}: {error}')
        for identity in set(records) - eligible:
            if action == 'check':
                report('obsolete', identity)
            elif restore_one(identity, records[identity]):
                del records[identity]
                save(records)
                report('cleaned', identity)
            else:
                report('conflict (launcher edited; left intact)', identity)
        if action == 'generate':
            refresh()
    print(', '.join(f'{value} {key}' for key, value in counts.items()) or 'No matching applications.')
    return 1 if any(key == 'error' or key.startswith('conflict') for key in counts) else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'generate', 'restore'])
    args = parser.parse_args()
    try:
        if args.action == 'check':
            return run(args.action)
        STATE.mkdir(parents=True, exist_ok=True)
        with (STATE / 'lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return run(args.action)
    except (OSError, ValueError) as error:
        print(f'nyx icons: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
