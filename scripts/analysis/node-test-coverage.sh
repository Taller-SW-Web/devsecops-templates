#!/usr/bin/env bash
set -euo pipefail

npm ci
VITEST_VERSION="$(node -p "require('./node_modules/vitest/package.json').version")"
CURRENT_TEMP="${RUNNER_TEMP:-${TMPDIR:-/tmp}}"
COVERAGE_PREFIX="${CURRENT_TEMP%/}/vitest-coverage-provider"
mkdir -p "$COVERAGE_PREFIX"
printf '{"name":"vitest-coverage-provider","version":"1.0.0","private":true}\n' > "$COVERAGE_PREFIX/package.json"
npm install --prefix "$COVERAGE_PREFIX" --save-exact --legacy-peer-deps \
  "@vitest/coverage-v8@${VITEST_VERSION}"
mkdir -p node_modules/@vitest
ln -s "$COVERAGE_PREFIX/node_modules/@vitest/coverage-v8" node_modules/@vitest/coverage-v8
if [ ! -e "$COVERAGE_PREFIX/node_modules/vitest" ]; then
  ln -s "$PWD/node_modules/vitest" "$COVERAGE_PREFIX/node_modules/vitest"
fi
npm test -- --coverage --coverage.reporter=lcov '--coverage.include=src/**/*.{ts,tsx}'

test -s coverage/lcov.info || {
  echo '::error::Vitest did not produce coverage/lcov.info'
  exit 1
}
