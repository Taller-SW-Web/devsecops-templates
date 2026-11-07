#!/usr/bin/env bash
set -euo pipefail

curl --fail --silent --show-error --retry 12 --retry-all-errors --retry-delay 10 --max-time 20 "$HEALTHCHECK_URL"
