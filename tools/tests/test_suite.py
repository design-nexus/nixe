import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('suite', Path(__file__).parents[1] / 'suite.py')
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)


class SuiteTests(unittest.TestCase):
    def test_real_manifest_boundaries(self):
        repos, apps, _ = suite.load()
        self.assertEqual(apps['archive']['repository'], 'archive')
        self.assertEqual(apps['photos']['packages'], ['nyx-photos'])
        self.assertFalse(apps['assistant']['default'])
        self.assertEqual(repos['monorepo']['revision'],
                         '97c1899499e52a42f6eaddca188aac4eca32b96e')

    def test_unknown_application_has_actionable_error(self):
        with self.assertRaisesRegex(ValueError, 'Unknown app'):
            suite.selected({'archive': {}}, 'mail')

    def test_setup_never_changes_existing_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / 'work.txt'
            marker.write_text('uncommitted work')
            with patch.object(suite, 'checkout', return_value=root), \
                    patch.object(suite, 'status'), patch.object(suite, 'run') as run:
                suite.setup({'core': {'id': 'core'}}, {})
                run.assert_not_called()
            self.assertEqual(marker.read_text(), 'uncommitted work')

    def test_unpinned_revision_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'suite.toml'
            manifest.write_text('schema_version = 1\napplications = []\n'
                                '[[repositories]]\nid = "bad"\nrevision = "main"\n')
            with patch.dict(os.environ, {'NYX_SUITE_MANIFEST': str(manifest)}):
                with self.assertRaisesRegex(ValueError, 'Unpinned repository'):
                    suite.load()


    def test_stale_shared_dependency_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Cargo.lock').write_text(
                'version = 4\n[[package]]\nname = "nyx-ui"\nversion = "0.1.0"\n'
                'source = "git+file:///design?rev=' + 'a' * 40 + '#' + 'a' * 40 + '"\n')
            repos = {'app': {'id': 'app'}, 'design': {'revision': 'b' * 40}}
            apps = {'app': {'id': 'app', 'repository': 'app', 'manifest': 'Cargo.toml'}}
            with patch.object(suite, 'checkout', return_value=root):
                errors = suite.compatibility_errors(repos, apps, {})
            self.assertEqual(errors, ['app: incompatible nyx-ui Git revision'])


    def test_older_shared_dependency_in_history_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git = lambda *args: suite.subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-q')
            commits = []
            for n in range(3):
                git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', str(n))
                commits.append(git('rev-parse', 'HEAD'))
            older, shared, newer = commits
            repos = {'app': {'id': 'app'}, 'design': {'revision': shared}}
            apps = {'app': {'id': 'app', 'repository': 'app', 'manifest': 'Cargo.toml'}}
            def lock(rev):
                (root / 'Cargo.lock').write_text(
                    'version = 4\n[[package]]\nname = "nyx-ui"\nversion = "0.1.0"\n'
                    'source = "git+https://github.com/design-nexus/nyx-design.git?rev=' + rev + '#' + rev + '"\n')
            with patch.object(suite, 'checkout', return_value=root):
                for rev, expected in [(older, []), (shared, []), (newer, ['app: incompatible nyx-ui Git revision'])]:
                    lock(rev)
                    self.assertEqual(suite.compatibility_errors(repos, apps, {}), expected)

if __name__ == '__main__':
    unittest.main()
