#!/usr/bin/env bash
set -euo pipefail

test -n "${SONAR_TOKEN:-}" || { echo '::error::Missing SONAR_TOKEN'; exit 1; }
[[ "${SONAR_HOST_URL:-}" == https://* ]] || {
  echo '::error::Configure HTTPS SONAR_HOST_URL'
  exit 1
}
