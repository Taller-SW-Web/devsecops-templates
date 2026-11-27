"""Publica un paquete validado tras verificar el run de producción en GitHub.

No sustituye la obtención de identidad del proveedor ni la revisión de privacidad.
Nunca mueve tags ni reemplaza assets. Una colisión requiere revisión, no force.
"""
import argparse
import json
from pathlib import Path
import subprocess
from bundle import assemble


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)


def publish(manifest, root, output):
    if manifest.get('synthetic'):
        raise ValueError('Un ejemplo sintetico no se publica')
    repo, sha = manifest['repository'], manifest['sha']
    run = json.loads(gh('api', f'repos/{repo}/actions/runs/{manifest["run_id"]}/attempts/{manifest["attempt"]}'))
    if (run['head_sha'] != sha or run['head_branch'] != 'main'
            or run['conclusion'] != 'success'
            or run['path'] != '.github/workflows/workflow-main.yml'
            or run['event'] not in ('push', 'workflow_dispatch')):
        raise ValueError('El run no acredita producción del SHA solicitado')
    # La consulta paginada debe completar; un error de permisos/red no significa tag libre.
    refs = json.loads(gh('api', '--paginate', '--slurp', f'repos/{repo}/git/matching-refs/tags/{manifest["version"]}'))
    if any(ref['ref'] == f'refs/tags/{manifest["version"]}' for page in refs for ref in page):
        raise ValueError('Version existente: no sobrescribir ni reparar automáticamente')
    archive = assemble(manifest, root, output)
    notes = Path(output) / 'release-notes.md'
    notes.write_text(f'# {manifest["version"]}\n\nSHA: `{sha}`\n\n'
                     f'Run: https://github.com/{repo}/actions/runs/{manifest["run_id"]}\n\n'
                     f'Identidad: {manifest["deployment"]["identity"]}. '
                     'Consultar límites y riesgos en el paquete.\n', encoding='utf-8')
    # gh crea draft, sube todos los assets y publica; compatible con releases inmutables.
    gh('release', 'create', manifest['version'], str(archive),
       str(Path(output) / 'release-manifest.json'), str(Path(output) / 'SHA256SUMS'),
       '--repo', repo, '--target', sha, '--notes-file', str(notes), '--latest=false')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('manifest', 'root', 'output'): parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    publish(json.loads(Path(args.manifest).read_text(encoding='utf-8')), args.root, args.output)
