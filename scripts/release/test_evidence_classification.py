import json
from pathlib import Path
import tempfile
import unittest
from collect_evidence import collect
from bundle import assemble


class ClassificationTest(unittest.TestCase):
    def test_frontend_has_e2e_without_fake_integration_or_performance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / 'artifacts'
            repository = 'Taller-SW-Web/G4-Retail-frontend'
            files = {
                'build-coverage-1/reports/vitest.xml': '<testsuites><testsuite><testcase name="a"/></testsuite></testsuites>',
                'sonar-quality-gate-1/sonar-quality-gate.json': '{}',
                'ghas-sast-typescript-1/javascript.sarif': '{"runs":[]}',
                'supply-chain-1/npm-audit.json': '{}',
                'supply-chain-1/summary.json': '{"secrets":"success"}',
                'e2e-pos-1/resultados.json': '{"mode":"API simulada"}',
                'deploy-evidence-1/deploy-meta.json': '{"status":"success","id":"deployment"}',
                'deploy-evidence-1/health-check.json': '{"status":"success"}',
                'pr-gate-1/gate-result.json': json.dumps(dict(repository=repository, sha='a'*40,
                    decision='GO', run_id=10, run_attempt='1', results={
                        job:'success' for job in ['build_test','sonar_gate','ghas_sast','supply_chain','e2e']})),
            }
            for name, content in files.items():
                path = artifacts / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
            evidence = root / 'evidence'
            manifest = collect(artifacts, evidence, 'v0.2.1', 'a'*40, repository, 'main', 10, 1)
            self.assertEqual(manifest['decision'], 'GO')
            kinds = {r['kind'] for r in manifest['reports']}
            self.assertIn('e2e', kinds)
            self.assertFalse({'integration','performance','dast'} & kinds)
            self.assertTrue(assemble(manifest, evidence, root / 'release').exists())
            # A gate from a different commit cannot authorize this evidence.
            gate = artifacts / 'pr-gate-1/gate-result.json'
            gate.write_text(gate.read_text().replace('a'*40, 'b'*40))
            self.assertEqual(collect(artifacts, root / 'invalid', 'v0.2.1', 'a'*40,
                repository, 'main', 10, 1)['decision'], 'NO-GO')

    def test_all_unit_xml_files_are_retained(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / 'artifacts'
            reports = artifacts / 'build-coverage-1/target/surefire-reports'
            reports.mkdir(parents=True)
            for name in ['TEST-a.xml', 'TEST-b.xml']:
                (reports / name).write_text('<testsuite/>')
            manifest = collect(artifacts, root / 'evidence', 'v0.1.3', 'a'*40,
                'Taller-SW-Web/G4-Retail-backend', 'main', 10, 1)
            self.assertEqual(len([r for r in manifest['reports'] if r['kind']=='build']), 2)
            self.assertEqual(manifest['decision'], 'NO-GO')
