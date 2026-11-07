#!/usr/bin/env bash
set -euo pipefail

[[ "${TECHNOLOGY:-}" == maven || "${TECHNOLOGY:-}" == node ]] || {
  echo '::error::TECHNOLOGY must be maven or node'
  exit 1
}
[[ "${HEALTHCHECK_URL:-}" == https://* ]] || {
  echo '::error::Configure an HTTPS PRODUCTION_HEALTHCHECK_URL'
  exit 1
}
