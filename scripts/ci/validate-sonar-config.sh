#!/usr/bin/env bash
set -euo pipefail

test -n "${SONAR_TOKEN:-}" || { echo '::error::Missing SONAR_TOKEN'; exit 1; }
test -n "${SONAR_HOST_URL:-}" || { echo '::error::Missing SONAR_HOST_URL'; exit 1; }
test -n "${SONAR_PROJECT_KEY:-}" || { echo '::error::Missing SONAR_PROJECT_KEY'; exit 1; }
