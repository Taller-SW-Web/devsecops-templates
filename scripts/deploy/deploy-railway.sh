#!/usr/bin/env bash
set -euo pipefail

test -n "${RAILWAY_TOKEN:-}" && test -n "${SERVICE_NAME:-}"
npm install -g @railway/cli
railway up --service "$SERVICE_NAME"
