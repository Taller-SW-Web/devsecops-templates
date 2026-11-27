import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from bundle import assemble


class BundleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = dict(version='v1.2.3', sha='a'*40, repository='grupo/backend',
                             branch='main', decision='GO', run_id=123, attempt=1,
                             deployment=dict(sha='a'*40, id='deploy-1', status='success',
                                             smoke='success', identity='provider-source'))
        self.manifest['reports'] = []
        for kind in ['build', 'sast', 'sca', 'secrets', 'integration', 'performance', 'go-no-go']:
            (self.root / f'{kind}.json').write_text('{}')
            self.manifest['reports'].append(dict(kind=kind, path=f'{kind}.json',
                sha='a'*40, repository='grupo/backend', run_id=123, attempt=1, status='success'))

    def run_bundle(self, manifest=None):
        return assemble(manifest or self.manifest, self.root, self.root / 'out')

    def test_zip_verificable_y_sin_sobrescritura(self):
        archive = self.run_bundle()
        with zipfile.ZipFile(archive) as zipped:
            self.assertIsNone(zipped.testzip())
            self.assertEqual(len(json.loads(zipped.read('manifest/release-manifest.json'))['hashes']), 7)
        with self.assertRaises(ValueError): self.run_bundle()

    def test_identidad_decision_y_semver(self):
        for key, value in [('sha', 'wrong'), ('version', 'v01.2.3'), ('decision', 'NO-GO'),
                           ('branch', 'develop'), ('run_id', 0), ('attempt', 0)]:
            with self.subTest(key=key):
                candidate = copy.deepcopy(self.manifest); candidate[key] = value
                with self.assertRaises(ValueError): self.run_bundle(candidate)

    def test_reporte_de_otro_run_o_job_omitido(self):
        for key, value in [('sha', 'b'*40), ('run_id', 124), ('attempt', 2),
                           ('status', 'skipped'), ('status', 'cancelled'), ('status', 'failure')]:
            candidate = copy.deepcopy(self.manifest); candidate['reports'][0][key] = value
            with self.assertRaises(ValueError): self.run_bundle(candidate)

    def test_ausencia_reportes(self):
        self.manifest['reports'].pop()
        with self.assertRaises(ValueError): self.run_bundle()

    def test_ruta_maliciosa(self):
        for path in ['../secret.json', '.env', 'C:/secret.json', '/secret.json']:
            self.manifest['reports'][0]['path'] = path
            with self.assertRaises(ValueError): self.run_bundle()

    def test_reporte_invalido(self):
        (self.root / 'build.json').write_text('no json')
        with self.assertRaises(ValueError): self.run_bundle()

    def test_sin_smoke_no_release(self):
        self.manifest['deployment']['smoke'] = 'failure'
        with self.assertRaises(ValueError): self.run_bundle()


if __name__ == '__main__': unittest.main()
