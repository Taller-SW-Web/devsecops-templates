"""Resuelve y valida la version SemVer estable vX.Y.Z desde VERSION o entrada explicita."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

SEMVER_RE = re.compile(r'^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$')


def normalize_version(raw: str) -> str:
    value = raw.strip()
    match = SEMVER_RE.fullmatch(value)
    if not match:
        raise ValueError(f'Version SemVer invalida: {raw!r}. Se esperaba X.Y.Z o vX.Y.Z')
    return f'v{match.group(1)}.{match.group(2)}.{match.group(3)}'


def resolve_version(version_file: Path, override: str = '', existing_tags: list[str] | None = None) -> str:
    if override and override.strip():
        version = normalize_version(override)
    elif version_file.is_file():
        version = normalize_version(version_file.read_text(encoding='utf-8'))
    else:
        raise FileNotFoundError(f'No existe archivo VERSION en {version_file} ni override explicito')

    if existing_tags is not None and version in existing_tags:
        raise ValueError(f'La etiqueta {version} ya existe en este repositorio. Incrementa VERSION (por ejemplo, 0.1.0 a 0.1.1) o proporciona version_override con una version libre.')
    return version


def fetch_git_tags(repo_dir: Path) -> list[str]:
    resolved_repo = repo_dir.resolve()
    out = subprocess.check_output(['git', '-c', f'safe.directory={resolved_repo.as_posix()}', '-C', str(resolved_repo), 'tag', '-l', 'v*'], text=True)
    return [line.strip() for line in out.splitlines() if line.strip()]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version-file', default='VERSION')
    parser.add_argument('--override', default='')
    parser.add_argument('--repo-dir', default='.')
    parser.add_argument('--check-tags', action='store_true')
    args = parser.parse_args()

    try:
        tags = fetch_git_tags(Path(args.repo_dir)) if args.check_tags else None
        resolved = resolve_version(Path(args.version_file), args.override, tags)
    except (ValueError, FileNotFoundError, subprocess.CalledProcessError) as error:
        print(f'::error title=Resolucion SemVer::{error}', file=sys.stderr)
        raise SystemExit(1) from error
    print(json.dumps({'version': resolved}))

