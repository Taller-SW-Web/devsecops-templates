#!/usr/bin/env bash
set -euo pipefail

test -n "${RAILWAY_TOKEN:-}" && test -n "${SERVICE_NAME:-}"
npm install -g @railway/cli
mkdir -p reports/deploy
railway up --service "$SERVICE_NAME" --detach | tee reports/deploy/railway-up.log
deploy_id="$(grep -Eo 'id=[a-zA-Z0-9_-]+' reports/deploy/railway-up.log | head -n1 | cut -d= -f2 || true)"
if [ -z "$deploy_id" ]; then
  deploy_id="railway-${GITHUB_RUN_ID:-0}-${GITHUB_RUN_ATTEMPT:-1}"
fi
node -e '
const fs = require("node:fs");
fs.writeFileSync("reports/deploy/deploy-meta.json", JSON.stringify({
  provider: "railway",
  service: process.env.SERVICE_NAME,
  id: process.env.DEPLOY_ID,
  sha: process.env.GITHUB_SHA || "",
  status: "success",
  identity: "provider-source",
  timestamp_utc: new Date().toISOString()
}, null, 2));
' DEPLOY_ID="$deploy_id"
