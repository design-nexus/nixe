"""Focused filesystem integration coverage; never touches the live desktop."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('icons', Path(__file__).resolve().parents[1] / 'tools/icons.py')
icons = importlib.util.module_from_spec(spec)
spec.loader.exec_module(icons)


class IconCommands(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.user, self.system = root / 'applications', root / 'system'
        self.user.mkdir()
        self.system.mkdir()
        self.state = root / 'nyx/icons'
        self.output = root / 'icons/hicolor/scalable/apps'
        self.patch = patch.multiple(icons, DATA=root, APPS=self.user, STATE=self.state, OUTPUT=self.output,
                                    roots=lambda: [self.user, self.system], refresh=lambda: None)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.firefox = '[Desktop Entry]\nType=Application\nName=Firefox\nExec=firefox %U\nIcon=firefox\n\n[Desktop Action Private]\nExec=firefox --private\nIcon=private\n'
        (self.system / 'firefox.desktop').write_text(self.firefox)
        logo = root / 'logo.svg'
        logo.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><circle cx="32" cy="32" r="25" fill="#dd8833"/></svg>')
        self.local = '[Desktop Entry]\nType=Application\nName=Custom\nExec=custom --flag\nIcon=' + str(logo) + '\n'
        (self.user / 'custom.desktop').write_text(self.local)
        (self.user / 'custom.desktop').chmod(0o750)
        (self.user / 'hidden.desktop').write_text('[Desktop Entry]\nHidden=true\n')
        (self.system / 'hidden.desktop').write_text(self.firefox)
        (self.system / 'io.github.design_nexus.nyx.Files.desktop').write_text(self.firefox)

    def run_command(self, action):
        result = io.StringIO()
        with contextlib.redirect_stdout(result):
            status = icons.run(action)
        return status, result.getvalue()

    def records(self):
        return json.loads((self.state / 'manifest.json').read_text())['entries']

    def test_generate_refresh_and_restore(self):
        before = sorted(str(p) for p in self.user.parent.rglob('*'))
        self.assertEqual(self.run_command('check')[0], 0)
        self.assertEqual(before, sorted(str(p) for p in self.user.parent.rglob('*')))
        status, output = self.run_command('generate')
        self.assertEqual(status, 0, output)
        self.assertEqual(set(self.records()), {'firefox.desktop', 'custom.desktop'})
        self.assertIn('generated (original logo)', output)
        self.assertIn('generated (curated)', output)
        managed = (self.user / 'firefox.desktop').read_text()
        self.assertIn('[Desktop Action Private]\nExec=firefox --private\nIcon=private', managed)
        self.assertEqual((self.user / 'custom.desktop').stat().st_mode & 0o777, 0o750)
        mtimes = {p: p.stat().st_mtime_ns for p in self.output.glob('*')}
        self.assertIn('2 current', self.run_command('generate')[1])
        self.assertEqual(mtimes, {p: p.stat().st_mtime_ns for p in self.output.glob('*')})
        (self.system / 'firefox.desktop').write_text(self.firefox.replace('firefox %U', 'firefox --new %U'))
        self.assertIn('outdated: Firefox', self.run_command('check')[1])
        self.assertEqual(self.run_command('generate')[0], 0)
        self.assertIn('Exec=firefox --new %U', (self.user / 'firefox.desktop').read_text())
        self.assertEqual(self.run_command('restore')[0], 0)
        self.assertFalse((self.user / 'firefox.desktop').exists())
        self.assertEqual((self.user / 'custom.desktop').read_text(), self.local)
        self.assertEqual(self.records(), {})
        self.assertFalse(list(self.output.glob('*')))

    def test_conflict_and_removed_upstream(self):
        self.run_command('generate')
        local = self.user / 'custom.desktop'
        edited = local.read_text() + '# user edit\n'
        local.write_text(edited)
        self.assertEqual(self.run_command('generate')[0], 1)
        self.assertEqual(local.read_text(), edited)
        (self.system / 'firefox.desktop').unlink()
        self.assertIn('obsolete', self.run_command('check')[1])
        self.run_command('generate')
        self.assertFalse((self.user / 'firefox.desktop').exists())
        self.assertEqual(self.run_command('restore')[0], 1)
        self.assertEqual(local.read_text(), edited)
        local.write_text(self.records()['custom.desktop']['managed'])
        self.assertEqual(self.run_command('restore')[0], 0)
        self.assertEqual(local.read_text(), self.local)


if __name__ == '__main__':
    unittest.main()
