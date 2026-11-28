"""Summarize actual JUnit and coverage files without converting failures to success."""
from html import escape
import argparse
import os
from pathlib import Path
import xml.etree.ElementTree as ET


def summarize(root, category):
    patterns = ('target/surefire-reports/*.xml', 'reports/vitest.xml') if category == 'unit' else (
        'target/integration-reports/*.xml', 'target/postgres-reports/*.xml')
    files = sorted({p for pattern in patterns for p in root.glob(pattern)})
    counts = dict(executed=0, passed=0, failed=0, skipped=0)
    details = []
    for path in files:
        tree = ET.parse(path).getroot()
        details.append(f'<details><summary>{escape(str(path.relative_to(root)))}</summary>\n<pre>')
        for case in tree.iter('testcase'):
            status = next((tag for tag in ('error', 'failure', 'skipped') if case.find(tag) is not None), 'passed')
            suite = case.get('classname', '')
            name = case.get('name', '(sin nombre)')
            duration = case.get('time')
            elapsed = f' · {duration} s' if duration else ''
            details.append(escape(f'  [{status}] {suite} · {name}{elapsed}'))
            if case.find('skipped') is not None:
                counts['skipped'] += 1
                continue
            counts['executed'] += 1
            counts['failed' if case.find('failure') is not None or case.find('error') is not None else 'passed'] += 1
        details.append('</pre></details>')
    lines = [f'### Pruebas — {category}', '',
             f"Reportes: {len(files)}; ejecutadas: {counts['executed']}; aprobadas: {counts['passed']}; fallidas: {counts['failed']}; omitidas: {counts['skipped']}."]
    if not files:
        lines.append('SIN EVIDENCIA: la ausencia de reportes no equivale a aprobación.')
        print('::warning::No se generaron reportes JUnit; revisar el paso de ejecución.')
    if category == 'integration':
        lines.append('BD: H2 y PostgreSQL efímero. G5/G6/G7: dobles HTTP locales; no valida servicios externos reales.')
    jacoco = root / 'target/site/jacoco/jacoco.xml'
    lcov = root / 'coverage/lcov.info'
    coverage = None
    if category == 'unit' and jacoco.exists():
        counter = next((c for c in ET.parse(jacoco).getroot().findall('counter') if c.get('type') == 'LINE'), None)
        if counter is not None:
            covered, missed = int(counter.get('covered')), int(counter.get('missed'))
            coverage = 100 * covered / (covered + missed) if covered + missed else None
    elif category == 'unit' and lcov.exists():
        values = lcov.read_text(encoding='utf-8').splitlines()
        found = sum(int(v[3:]) for v in values if v.startswith('LF:'))
        hit = sum(int(v[3:]) for v in values if v.startswith('LH:'))
        coverage = 100 * hit / found if found else None
    if category == 'unit':
        lines.append(f'Cobertura real de líneas: {coverage:.2f}%.' if coverage is not None else 'Cobertura: SIN EVIDENCIA.')
    return '\n'.join(lines + [''] + details) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--category', choices=['unit', 'integration'], required=True)
    args = parser.parse_args()
    result = summarize(Path.cwd(), args.category)
    print(result)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
            summary.write(result)
