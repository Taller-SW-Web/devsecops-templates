"""Validación local de YAML, DAG y casos negativos/positivos del código real de pr-gate."""
import json
from pathlib import Path
import subprocess
import yaml

root = Path(__file__).resolve().parents[2]
count = 0
gate_cases = 0

for repo in ('G4-Retail-backend', 'G4-Retail-frontend', 'devsecops-templates'):
    for path in (root / repo / '.github/workflows').glob('*.yml'):
        document = yaml.safe_load(path.read_text(encoding='utf-8'))
        jobs = document['jobs']

        def visit(name, chain):
            if name in chain:
                raise ValueError(f'Ciclo: {path}:{name}')
            needs = jobs[name].get('needs', [])
            if isinstance(needs, str):
                needs = [needs]
            for need in needs:
                if need not in jobs:
                    raise ValueError(f'Job inexistente {path}:{need}')
                visit(need, chain + [name])

        for job in jobs:
            visit(job, [])
        count += 1

        if 'pr-gate' in jobs:
            script = jobs['pr-gate']['steps'][0]['with']['script']
            is_backend = repo == 'G4-Retail-backend'
            base_jobs = ['quality', 'integration'] if is_backend else ['quality']
            main_only = ['performance', 'dast'] if is_backend else ['e2e']

            scenarios = [
                # (base_ref, results_dict, expected_failed)
                ('develop', {**{j: {'result': 'success'} for j in base_jobs}, **{j: {'result': 'skipped'} for j in main_only}}, False),
                ('main', {j: {'result': 'success'} for j in base_jobs + main_only}, False),
            ]
            for j in base_jobs:
                for bad in ('failure', 'skipped', 'cancelled'):
                    res = {k: {'result': 'success'} for k in base_jobs + main_only}
                    res[j] = {'result': bad}
                    scenarios.append(('develop', res, True))
                    scenarios.append(('main', res, True))
            for j in main_only:
                for bad in ('failure', 'skipped', 'cancelled'):
                    res = {k: {'result': 'success'} for k in base_jobs + main_only}
                    res[j] = {'result': bad}
                    scenarios.append(('main', res, True))

            for base_ref, results, expected_failed in scenarios:
                wrapper = (
                    "const fs = {writeFileSync(){}};\n"
                    "const require = () => fs;\n"
                    "const context = {sha:'a'.repeat(40), runId:1};\n"
                    "let failed=false;\n"
                    "const summary = {addHeading(){return this},addRaw(){return this},addTable(){return this},async write(){}};\n"
                    "const core = {summary,setFailed(){failed=true}};\n"
                    f"process.env.RESULTS = {json.dumps(json.dumps(results))};\n"
                    f"process.env.BASE_REF = {json.dumps(base_ref)};\n"
                    f"(async()=>{{\n{script}\nif(failed !== {str(expected_failed).lower()}) process.exitCode=1;\n}})();"
                )
                subprocess.run(['node', '-e', wrapper], check=True)
                gate_cases += 1

print(f'PASS: {count} YAML/DAG; {gate_cases} casos de pr-gate (develop y main, positivos y negativos). No sustituye actionlint.')
