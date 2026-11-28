"""Paquete de evidencia cerrado: valida identidad, archivos y hashes antes de publicar."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def assemble(manifest, root, destination):
    root = Path(root).resolve()
    destination = Path(destination)
    version = manifest.get('version', '')
    if not re.fullmatch(r'v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', version):
        raise ValueError('Version SemVer estable invalida')
    sha = manifest.get('sha', '')
    if not re.fullmatch('[0-9a-f]{40}', sha):
        raise ValueError('SHA invalido')
    if manifest.get('branch') != 'main' or manifest.get('decision') != 'GO':
        raise ValueError('Release requiere main y GO')
    if not re.fullmatch(r'[\w.-]+/[\w.-]+', manifest.get('repository', '')):
        raise ValueError('Repositorio invalido')
    deploy = manifest.get('deployment', {})
    if (deploy.get('sha') != sha or deploy.get('status') != 'success'
            or deploy.get('smoke') != 'success' or not deploy.get('id')
            or deploy.get('identity') not in ('provider-source', 'binary-digest')):
        raise ValueError('Falta identidad y smoke del despliegue')
    required = {'build', 'sast', 'sca', 'secrets', 'integration', 'performance', 'go-no-go'}
    if manifest.get('technology') in ('node', 'maven'):
        required = {'build', 'quality', 'sast', 'sca', 'secrets', 'gate', 'deployment', 'go-no-go'} | ({'e2e'} if manifest['technology'] == 'node' else {'integration', 'performance', 'dast'})
    reports = manifest.get('reports', [])
    if not required.issubset({r.get('kind') for r in reports}):
        raise ValueError('Faltan categorias obligatorias')
    payload = {}
    for report in reports:
        if (report.get('sha') != sha or report.get('repository') != manifest['repository']
                or report.get('run_id') != manifest.get('run_id')
                or report.get('attempt') != manifest.get('attempt')
                or report.get('status') != 'success'):
            raise ValueError('Reporte de otra identidad o no aprobado')
        name = report.get('path', '')
        relative = PurePosixPath(name)
        if (not name or relative.is_absolute() or '..' in relative.parts or '\\' in name
                or ':' in name or any(p.startswith('.') for p in relative.parts)
                or relative.suffix.lower() not in ('.json', '.xml', '.md', '.csv', '.txt', '.sarif', '.info')):
            raise ValueError('Ruta de reporte no permitida')
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError('Reporte fuera del directorio')
        data = path.read_bytes()
        if report.get('checksum') and report['checksum'] != digest(data):
            raise ValueError('Checksum del reporte no coincide')
        if not data or len(data) > 20_000_000:
            raise ValueError('Reporte vacio o demasiado grande')
        content = data.decode('utf-8-sig')
        if re.search(r'-----BEGIN .*PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{20,}', content):
            raise ValueError('Posible secreto en reporte')
        if relative.suffix == '.json':
            json.loads(content)
        if relative.suffix == '.xml':
            import xml.etree.ElementTree as ET
            ET.fromstring(content)
        if name in payload:
            raise ValueError('Reporte duplicado')
        payload[name] = data
    if not isinstance(manifest.get('run_id'), int) or manifest['run_id'] <= 0:
        raise ValueError('Run invalido')
    if not isinstance(manifest.get('attempt'), int) or manifest['attempt'] <= 0:
        raise ValueError('Attempt invalido')
    result = dict(manifest, hashes={name: digest(data) for name, data in payload.items()})
    payload['manifest/release-manifest.json'] = json.dumps(result, indent=2).encode()
    payload['manifest/SHA256SUMS'] = ''.join(f'{digest(data)}  {name}\n' for name, data in sorted(payload.items())).encode()
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / f'release-evidence-{version}.zip'
    if archive.exists():
        raise ValueError('No sobrescribir paquete existente')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as zipped:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            zipped.writestr(info, data)
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() or any(zipped.read(name) != data for name, data in payload.items()):
            raise ValueError('ZIP no integro')
    (destination / 'release-manifest.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (destination / 'SHA256SUMS').write_text(f'{digest(archive.read_bytes())}  {archive.name}\n', encoding='utf-8')
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    assemble(json.loads(Path(args.manifest).read_text(encoding='utf-8')), args.root, args.output)
