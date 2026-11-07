#!/usr/bin/env bash
set -euo pipefail

npm ci
VITEST_VERSION="$(node -p "require('./node_modules/vitest/package.json').version")"
npm install --no-save --package-lock=false "@vitest/coverage-v8@${VITEST_VERSION}"
npm test -- --coverage --coverage.reporter=lcov '--coverage.include=src/**/*.{ts,tsx}'

test -s coverage/lcov.info || {
  echo '::error::Vitest did not produce coverage/lcov.info'
  exit 1
}
