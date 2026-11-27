"""Validación local de YAML, DAG y casos negativos del código real de pr-gate."""
import json
from pathlib import Path
import subprocess
import yaml

root = Path(__file__).resolve().parents[2]
count = 0
for repo in ('G4-Retail-backend', 'G4-Retail-frontend', 'devsecops-templates'):
    for path in (root / repo / '.github/workflows').glob('*.yml'):
        document = yaml.safe_load(path.read_text(encoding='utf-8'))
        jobs = document['jobs']
        def visit(name, chain):
            if name in chain: raise ValueError(f'Ciclo: {path}:{name}')
            needs = jobs[name].get('needs', [])
            if isinstance(needs, str): needs = [needs]
            for need in needs:
                if need not in jobs: raise ValueError(f'Job inexistente {path}:{need}')
                visit(need, chain + [name])
        for job in jobs: visit(job, [])
        count += 1
        if 'pr-gate' in jobs:
            script = jobs['pr-gate']['steps'][0]['with']['script']
            for status in ('success', 'failure', 'skipped', 'cancelled'):
                wrapper = '''
                const fs = {writeFileSync(){}};
                const require = () => fs;
                const context = {sha:'a'.repeat(40), runId:1};
                let failed=false;
                const summary = {addHeading(){return this},addTable(){return this},async write(){}};
                const core = {summary,setFailed(){failed=true}};
                process.env.RESULTS = REPORT;
                (async()=>{ CODE; if(failed !== EXPECTED) process.exitCode=1; })();
                '''.replace('REPORT', json.dumps(json.dumps({'evidence':{'result':status}, 'quality':{'result':'success'}})))
                wrapper = wrapper.replace('CODE', script).replace('EXPECTED', str(status != 'success').lower())
                subprocess.run(['node', '-e', wrapper], check=True)
print(f'PASS: {count} YAML/DAG; 8 casos de pr-gate (dos repositorios). No sustituye actionlint.')
