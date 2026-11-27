"""Recolecta evidencias reales del run de produccion y genera manifest.json para bundle.py."""
import argparse
import json
from pathlib import Path
import shutil

REQUIRED_CATEGORIES = ('build', 'sast', 'sca', 'secrets', 'integration', 'performance', 'go-no-go')


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
) -> dict:
    artifacts_dir = artifacts_dir.resolve()
    evidence_root = evidence_root.resolve()
    evidence_root.mkdir(parents=True, exist_ok=True)

    reports = []
    missing = []

    def add_report(kind: str, rel_dst: str, patterns: tuple[str, ...]):
        src = _find_first(artifacts_dir, patterns)
        if not src:
            missing.append(kind)
            return
        copied = _copy_if_exists(src, evidence_root, rel_dst)
        if copied:
            reports.append({
                'kind': kind,
                'path': copied,
                'sha': sha,
                'repository': repository,
                'run_id': run_id,
                'attempt': attempt,
                'status': 'success',
            })

    add_report('build', 'ci/build-report.xml', ('surefire-reports/*.xml', 'reports/vitest.xml', 'coverage/lcov.info'))
    add_report('sast', 'security/sast/sonar-quality-gate.json', ('sonar-quality-gate.json',))
    add_report('sca', 'security/sca/sca-report.json', ('dependency-check-report.json', 'npm-audit.json', 'dependency-review.json'))
    add_report('secrets', 'security/secrets/summary.json', ('summary.json',))
    add_report('integration', 'integration/integration-report.xml', ('integration-reports/*.xml', 'postgres-reports/*.xml', 'reports/vitest.xml'))
    add_report('performance', 'performance/perf-summary.json', ('target/performance/*.json', 'e2e-pos.json', 'reports/e2e/*.json'))

    # Deploy & health metadata
    deploy_meta_src = _find_first(artifacts_dir, ('deploy-meta.json',))
    health_src = _find_first(artifacts_dir, ('health-check.json',))
    deploy_meta = json.loads(deploy_meta_src.read_text(encoding='utf-8')) if deploy_meta_src else {}
    health_meta = json.loads(health_src.read_text(encoding='utf-8')) if health_src else {}

    if deploy_meta_src:
        _copy_if_exists(deploy_meta_src, evidence_root, 'deploy/deploy-meta.json')
    if health_src:
        _copy_if_exists(health_src, evidence_root, 'deploy/health-check.json')

    decision = 'GO' if (not missing and health_meta.get('status') == 'success' and deploy_meta.get('id')) else 'NO-GO'

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

    go_path = evidence_root / 'release-decision/go-no-go.json'
    go_path.parent.mkdir(parents=True, exist_ok=True)
    go_path.write_text(json.dumps(go_no_go, indent=2), encoding='utf-8')
    reports.append({
        'kind': 'go-no-go',
        'path': 'release-decision/go-no-go.json',
        'sha': sha,
        'repository': repository,
        'run_id': run_id,
        'attempt': attempt,
        'status': 'success' if decision == 'GO' else 'failure',
    })

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
    )
    out = Path(args.output_manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

