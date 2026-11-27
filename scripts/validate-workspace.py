"""Validacion local de la arquitectura CI/CD centralizada (complementa a actionlint).

Comprueba en el workspace (repos hermanos de devsecops-templates):
- YAML valido y DAG de `needs` sin ciclos ni jobs inexistentes.
- Wrappers de aplicacion delgados: solo jobs `uses` hacia devsecops-templates (sin runs-on/steps/services).
- Cada `with`/`secrets` de un caller existe en `on.workflow_call` del template llamado, con inputs requeridos.
- Todo job del template controlado por politica consulta `needs.policy.outputs.<flag> == 'true'`.
- `pr-gate` corre con `if: always()` y depende de todos los jobs que la politica puede exigir.
- Ningun `continue-on-error` en los workflows.
- Escenarios del gate y de la politica: se ejecutan con `node --test` en github-actions.
"""
from pathlib import Path
import re
import subprocess
import sys

import yaml

root = Path(__file__).resolve().parents[2]
TEMPLATES = root / 'devsecops-templates' / '.github' / 'workflows'
APPS = ('G4-Retail-backend', 'G4-Retail-frontend')
POLICY_JOBS = {
    'build_test': 'run_build_test', 'sonar_analysis': 'run_sonar', 'sonar_gate': 'run_sonar_gate',
    'ghas_sast': 'run_codeql', 'ghas_sca': 'run_dependency_review', 'supply_chain': 'run_full_sca',
    'integration': 'run_integration', 'performance': 'run_performance', 'dast': 'run_dast', 'e2e': 'run_e2e',
}
REMOTE = re.compile(r'^Taller-SW-Web/devsecops-templates/\.github/workflows/([\w.-]+\.yml)@[\w./-]+$')
errors = []


def load(path):
    document = yaml.safe_load(path.read_text(encoding='utf-8'))
    # PyYAML interpreta la clave `on` como True.
    document['on'] = document.pop(True, document.get('on'))
    return document


def needs_of(job):
    needs = job.get('needs', [])
    return [needs] if isinstance(needs, str) else list(needs)


def check_dag(path, jobs):
    def visit(name, chain):
        if name in chain:
            errors.append(f'Ciclo en {path.name}: {" -> ".join(chain + [name])}')
            return
        for need in needs_of(jobs[name]):
            if need not in jobs:
                errors.append(f'{path.name}: job {name} necesita job inexistente {need}')
            else:
                visit(need, chain + [name])
    for job in jobs:
        visit(job, [])


def check_call(caller, job_id, job, target_path):
    contract = load(target_path)['on']['workflow_call']
    inputs = contract.get('inputs') or {}
    secrets = contract.get('secrets') or {}
    given = job.get('with') or {}
    for key in given:
        if key not in inputs:
            errors.append(f'{caller}:{job_id} pasa input inexistente `{key}` a {target_path.name}')
    for key, spec in inputs.items():
        if spec.get('required') and key not in given:
            errors.append(f'{caller}:{job_id} no pasa input requerido `{key}` a {target_path.name}')
    for key in (job.get('secrets') or {}):
        if key not in secrets:
            errors.append(f'{caller}:{job_id} pasa secreto inexistente `{key}` a {target_path.name}')


workflows = 0
for path in sorted([*TEMPLATES.glob('*.yml'), *(p for app in APPS for p in (root / app / '.github/workflows').glob('*.yml'))]):
    document = load(path)
    jobs = document['jobs']
    workflows += 1
    check_dag(path, jobs)
    if 'continue-on-error' in path.read_text(encoding='utf-8'):
        errors.append(f'{path}: contiene continue-on-error')
    is_app = path.parents[2].name in APPS
    for job_id, job in jobs.items():
        uses = job.get('uses')
        if is_app:
            if not uses or any(k in job for k in ('runs-on', 'steps', 'services', 'container')):
                errors.append(f'{path.parents[2].name}/{path.name}: job {job_id} debe ser solo un wrapper `uses`')
        if uses:
            match = REMOTE.match(uses)
            if not match:
                errors.append(f'{path.name}:{job_id} usa una referencia no permitida: {uses}')
                continue
            target = TEMPLATES / match.group(1)
            if not target.exists():
                errors.append(f'{path.name}:{job_id} referencia template inexistente {match.group(1)}')
            else:
                check_call(f'{path.parents[2].name}/{path.name}', job_id, job, target)

analysis = load(TEMPLATES / 'workflow-pr-analysis.yml')['jobs']
for job_id, flag in POLICY_JOBS.items():
    condition = str(analysis.get(job_id, {}).get('if', ''))
    if f"needs.policy.outputs.{flag} == 'true'" not in condition:
        errors.append(f'workflow-pr-analysis.yml:{job_id} no esta controlado por needs.policy.outputs.{flag}')
    if 'policy' not in needs_of(analysis.get(job_id, {})):
        errors.append(f'workflow-pr-analysis.yml:{job_id} no depende del job policy')
gate = analysis.get('pr-gate', {})
if str(gate.get('if')) != 'always()':
    errors.append('pr-gate debe ejecutarse con if: always()')
missing = {'policy', *POLICY_JOBS} - set(needs_of(gate))
if missing:
    errors.append(f'pr-gate no depende de: {sorted(missing)}')

deploy = load(TEMPLATES / 'workflow-deploy.yml')['jobs']
deployment_if = str(deploy['deployment'].get('if', ''))
for fragment in ("needs.quality.outputs.decision == 'GO'", "needs.authorize.result == 'success'", "allow_deploy == 'true'"):
    if fragment not in deployment_if:
        errors.append(f'workflow-deploy.yml: deployment no exige {fragment}')

if errors:
    print('\n'.join(f'FAIL: {e}' for e in errors))
    sys.exit(1)

actions_repo = root / 'github-actions'
tests = subprocess.run(['node', '--test', *sorted(str(p) for p in (actions_repo / 'tests').glob('*.test.cjs'))],
                       cwd=actions_repo, capture_output=True, text=True, encoding='utf-8', errors='replace')
summary = [line.lstrip('ℹ# ').strip() for line in tests.stdout.splitlines() if line.lstrip('ℹ# ').startswith(('tests ', 'pass ', 'fail '))]
if tests.returncode != 0:
    print(tests.stdout[-4000:], tests.stderr[-2000:])
    sys.exit(1)
print(f'PASS: {workflows} workflows (YAML, DAG, contratos caller->template, wrappers delgados, flags de politica, pr-gate).')
print('PASS: tests de politica y gate en github-actions ->', ', '.join(summary))
print('No sustituye actionlint.')
