"""Recolecta evidencias reales del run de produccion y genera manifest.json para bundle.py."""
import argparse
import json
from pathlib import Path
import shutil
import hashlib
from datetime import datetime, timezone

def _copy_if_exists(src: Path, dst_root: Path, rel_path: str) -> str | None:
    if not src.is_file():
        return None
    target = dst_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, target)
    return rel_path


def _find_first(artifacts_dir: Path, patterns: tuple[str, ...]) -> Path | None:
    for pattern in patterns:
        matches = sorted(artifacts_dir.rglob(pattern))
        for m in matches:
            if m.is_file():
                return m
    return None


def collect(
    artifacts_dir: Path,
    evidence_root: Path,
    version: str,
    sha: str,
    repository: str,
    branch: str,
    run_id: int,
    attempt: int,
    technology: str | None = None,
) -> dict:
    artifacts_dir = artifacts_dir.resolve()
    evidence_root = evidence_root.resolve()
    evidence_root.mkdir(parents=True, exist_ok=True)

    reports = []
    missing = []

    technology = technology or ('node' if repository.endswith('frontend') else 'maven')
    if technology not in ('node', 'maven'):
        raise ValueError('Unsupported technology')
    gate_src = _find_first(artifacts_dir, ('gate-result.json',))
    gate = json.loads(gate_src.read_text(encoding='utf-8')) if gate_src else {}
    gate_valid = (gate.get('decision') == 'GO' and gate.get('sha') == sha
                  and gate.get('repository') == repository and str(gate.get('run_id')) == str(run_id)
                  and str(gate.get('run_attempt')) == str(attempt))
    if not gate_valid:
        missing.append('verified-gate')
    timestamp = datetime.now(timezone.utc).isoformat()

    def add_report(kind, destination, patterns, job, required=True):
        sources = sorted({p for pattern in patterns for p in artifacts_dir.rglob(pattern) if p.is_file()})
        if not sources and required:
            missing.append(kind)
        for src in sources:
            relative = src.relative_to(artifacts_dir).as_posix()
            copied = _copy_if_exists(src, evidence_root, destination + '/' + relative)
            status = gate.get('results', {}).get(job, 'unknown')
            if status != 'success':
                missing.append(kind + ':unverified-result')
            reports.append(dict(kind=kind, path=copied, source=relative, sha=sha,
                repository=repository, run_id=run_id, attempt=attempt, status=status,
                timestamp=timestamp, version=version, environment='ephemeral CI',
                checksum=hashlib.sha256(src.read_bytes()).hexdigest()))

    add_report('build', 'tests/unit', ('surefire-reports/*.xml', 'vitest.xml'), 'build_test')
    add_report('quality', 'quality', ('sonar-quality-gate.json', 'jacoco.xml', 'coverage-summary.json', 'lcov.info'), 'sonar_gate')
    add_report('sast', 'security/sast', ('*.sarif', 'ghas-sast-*/*.json'), 'ghas_sast')
    add_report('sca', 'security/sca', ('trivy-sca.json', 'npm-audit.json', 'dependency-review.json'), 'supply_chain')
    add_report('secrets', 'security/secrets', ('supply-chain-*/summary.json',), 'supply_chain')
    if technology == 'maven':
        add_report('integration', 'tests/integration', ('integration-reports/*.xml',), 'integration')
        add_report('integration', 'tests/integration', ('postgres-reports/*.xml',), 'integration')
        add_report('performance', 'tests/performance', ('performance-*/*.json', 'performance-*/*.md', 'target/performance/*.json'), 'performance')
        add_report('dast', 'security/dast', ('dast-zap-*/*.json', 'dast-zap-*/*.md'), 'dast')
    else:
        add_report('e2e', 'tests/e2e', ('e2e-pos-*/*.json', 'e2e-pos-*/*.xml', 'e2e-pos-*/*.md'), 'e2e')
    if gate_src:
        _copy_if_exists(gate_src, evidence_root, 'manifest/gate-result.json')
        reports.append(dict(kind='gate', path='manifest/gate-result.json', sha=sha,
            repository=repository, run_id=run_id, attempt=attempt,
            status='success' if gate_valid else 'failure'))

    # Deploy & health metadata
    deploy_meta_src = _find_first(artifacts_dir, ('deploy-meta.json',))
    health_src = _find_first(artifacts_dir, ('health-check.json',))
    deploy_meta = json.loads(deploy_meta_src.read_text(encoding='utf-8')) if deploy_meta_src else {}
    health_meta = json.loads(health_src.read_text(encoding='utf-8')) if health_src else {}

    if deploy_meta_src:
        _copy_if_exists(deploy_meta_src, evidence_root, 'deployment/deploy-meta.json')
    if health_src:
        _copy_if_exists(health_src, evidence_root, 'deployment/health-check.json')

    for name, source in [('deploy-meta.json', deploy_meta_src), ('health-check.json', health_src)]:
        if source:
            reports.append(dict(kind='deployment', path='deployment/' + name, sha=sha, repository=repository, run_id=run_id, attempt=attempt, status=json.loads(source.read_text(encoding='utf-8')).get('status', 'unknown')))

    decision = 'GO' if (not missing and deploy_meta.get('status') == 'success' and health_meta.get('status') == 'success' and deploy_meta.get('id')) else 'NO-GO'

    go_no_go = {
        'version': version,
        'sha': sha,
        'repository': repository,
        'branch': branch,
        'run_id': run_id,
        'attempt': attempt,
        'decision': decision,
        'missing_categories': missing,
        'deployment': {
            'id': deploy_meta.get('id', ''),
            'sha': sha,
            'status': deploy_meta.get('status', 'unknown'),
            'smoke': health_meta.get('status', 'unknown'),
            'identity': deploy_meta.get('identity', 'provider-source'),
        },
        'collected_reports': [r['kind'] for r in reports],
    }

    go_path = evidence_root / 'go-no-go.json'
    go_path.parent.mkdir(parents=True, exist_ok=True)
    go_path.write_text(json.dumps(go_no_go, indent=2), encoding='utf-8')
    reports.append({
        'kind': 'go-no-go',
        'path': 'go-no-go.json',
        'sha': sha,
        'repository': repository,
        'run_id': run_id,
        'attempt': attempt,
        'status': 'success' if decision == 'GO' else 'failure',
    })

    for report in reports:
        report.setdefault('source', report['path'])
        report.setdefault('timestamp', timestamp)
        report.setdefault('version', version)
        report.setdefault('environment', 'production' if report['kind'] == 'deployment' else 'ephemeral CI')
        report.setdefault('checksum', hashlib.sha256((evidence_root / report['path']).read_bytes()).hexdigest())

    manifest = {
        'version': version,
        'sha': sha,
        'repository': repository,
        'branch': branch,
        'run_id': run_id,
        'attempt': attempt,
        'decision': decision,
        'deployment': go_no_go['deployment'],
        'reports': reports,
        'technology': technology,
        'not_applicable': ['integration', 'performance', 'dast'] if technology == 'node' else ['e2e'],
    }
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifacts-dir', required=True)
    parser.add_argument('--evidence-root', required=True)
    parser.add_argument('--output-manifest', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--branch', default='main')
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--attempt', type=int, required=True)
    parser.add_argument('--technology', choices=['node', 'maven'])
    args = parser.parse_args()

    manifest = collect(
        Path(args.artifacts_dir),
        Path(args.evidence_root),
        args.version,
        args.sha,
        args.repository,
        args.branch,
        args.run_id,
        args.attempt,
        args.technology,
    )
    print(json.dumps({
        'decision': manifest['decision'],
        'branch': manifest['branch'],
        'deployment': manifest['deployment'],
        'reports': [r['kind'] for r in manifest['reports']],
    }, indent=2))
    out = Path(args.output_manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

