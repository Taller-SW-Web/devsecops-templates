"""Pruebas para resolve_version.py y collect_evidence.py."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_evidence import collect
from resolve_version import resolve_version


class ResolveVersionTest(unittest.TestCase):
    def test_reads_version_file_and_rejects_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            vf = Path(tmp) / 'VERSION'
            vf.write_text('1.2.3\n', encoding='utf-8')
            self.assertEqual(resolve_version(vf, '', ['v1.2.2']), 'v1.2.3')
            with self.assertRaises(ValueError):
                resolve_version(vf, '', ['v1.2.3'])

    def test_cli_collision_fails_without_emitting_partial_json(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            vf = Path(tmp) / 'VERSION'
            vf.write_text('0.1.0\n', encoding='utf-8')
            result = subprocess.run([
                sys.executable, str(Path(__file__).with_name('resolve_version.py')),
                '--version-file', str(vf), '--repo-dir', tmp, '--check-tags'
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, '')
            self.assertIn('::error title=Resolucion SemVer::', result.stderr)

    def test_rejects_malformed_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            vf = Path(tmp) / 'VERSION'
            vf.write_text('01.2.3', encoding='utf-8')
            with self.assertRaises(ValueError):
                resolve_version(vf)


class CollectEvidenceTest(unittest.TestCase):
    def complete_security(self, art):
        (art / 'postgres-reports').mkdir(exist_ok=True)
        (art / 'postgres-reports/TEST-postgres.xml').write_text('<testsuite tests="1"/>')
        (art / 'supply-chain-1').mkdir(exist_ok=True)
        (art / 'supply-chain-1/summary.json').write_text('{"secrets":"success"}')
        (art / 'supply-chain-1/trivy-sca.json').write_text('{"Results":[]}')
        (art / 'scan.sarif').write_text('{"runs":[]}')
        (art / 'dast-zap-1').mkdir(exist_ok=True)
        (art / 'dast-zap-1/report_json.json').write_text('{}')
        (art / 'gate-result.json').write_text(json.dumps(dict(decision='GO', sha='a'*40,
            repository='Taller-SW-Web/G4-Retail-backend', run_id=10, run_attempt='1',
            results={job:'success' for job in ['build_test','sonar_gate','ghas_sast','supply_chain','integration','performance','dast']})))

    def test_missing_reports_produce_nogo(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / 'artifacts'
            art.mkdir()
            self.complete_security(art)
            ev = Path(tmp) / 'evidence'
            manifest = collect(art, ev, 'v0.1.0', 'a' * 40, 'Taller-SW-Web/G4-Retail-backend', 'main', 10, 1)
            self.assertEqual(manifest['decision'], 'NO-GO')

    def test_complete_artifacts_produce_go_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / 'artifacts'
            (art / 'surefire-reports').mkdir(parents=True)
            (art / 'surefire-reports/TEST-pos.xml').write_text('<testsuite tests="1"/>', encoding='utf-8')
            (art / 'sonar-quality-gate.json').write_text('{"status":"OK"}', encoding='utf-8')
            (art / 'dependency-check-report.json').write_text('{"dependencies":[]}', encoding='utf-8')
            (art / 'summary.json').write_text('{"secrets":"success"}', encoding='utf-8')
            (art / 'integration-reports').mkdir(parents=True)
            (art / 'integration-reports/TEST-int.xml').write_text('<testsuite tests="1"/>', encoding='utf-8')
            (art / 'target/performance').mkdir(parents=True)
            (art / 'target/performance/resumen.json').write_text('{"p95":120}', encoding='utf-8')
            (art / 'deploy-meta.json').write_text(json.dumps({'id': 'dep-1', 'status': 'success', 'identity': 'provider-source'}), encoding='utf-8')
            (art / 'health-check.json').write_text(json.dumps({'status': 'success'}), encoding='utf-8')

            self.complete_security(art)
            ev = Path(tmp) / 'evidence'
            manifest = collect(art, ev, 'v0.1.0', 'a' * 40, 'Taller-SW-Web/G4-Retail-backend', 'main', 10, 1)
            self.assertEqual(manifest['decision'], 'GO')
            self.assertTrue({'build', 'sast', 'dast', 'gate', 'deployment'}.issubset({r['kind'] for r in manifest['reports']}))

    def test_upload_artifact_flattened_performance_and_e2e_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = Path(tmp) / 'artifacts'
            (art / 'build-coverage-1/target/surefire-reports').mkdir(parents=True)
            (art / 'build-coverage-1/target/surefire-reports/TEST-pos.xml').write_text('<testsuite tests="1"/>', encoding='utf-8')
            (art / 'sonar-quality-gate-1').mkdir(parents=True)
            (art / 'sonar-quality-gate-1/sonar-quality-gate.json').write_text('{"status":"OK"}', encoding='utf-8')
            (art / 'supply-chain-1').mkdir(parents=True)
            (art / 'supply-chain-1/trivy-sca.json').write_text('{"Results":[]}', encoding='utf-8')
            (art / 'supply-chain-1/summary.json').write_text('{"secrets":"success"}', encoding='utf-8')
            (art / 'integration-reports-1/integration-reports').mkdir(parents=True)
            (art / 'integration-reports-1/integration-reports/TEST-int.xml').write_text('<testsuite tests="1"/>', encoding='utf-8')
            (art / 'performance-1').mkdir(parents=True)
            (art / 'performance-1/resultados.json').write_text('{"p95":120}', encoding='utf-8')
            (art / 'deploy-meta-1').mkdir(parents=True)
            (art / 'deploy-meta-1/deploy-meta.json').write_text(json.dumps({'id': 'dep-1', 'status': 'success', 'identity': 'provider-source'}), encoding='utf-8')
            (art / 'deploy-meta-1/health-check.json').write_text(json.dumps({'status': 'success'}), encoding='utf-8')

            self.complete_security(art)
            ev = Path(tmp) / 'evidence'
            manifest = collect(art, ev, 'v0.1.0', 'a' * 40, 'Taller-SW-Web/G4-Retail-backend', 'main', 10, 1)
            self.assertEqual(manifest['decision'], 'GO')
            self.assertTrue({'build', 'sast', 'dast', 'gate', 'deployment'}.issubset({r['kind'] for r in manifest['reports']}))


if __name__ == '__main__':
    unittest.main()

