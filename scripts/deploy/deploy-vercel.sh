#!/usr/bin/env bash
set -euo pipefail

test -n "${VERCEL_TOKEN:-}" && test -n "${VERCEL_ORG_ID:-}" && test -n "${VERCEL_PROJECT_ID:-}"
npm install -g vercel
mkdir -p reports/deploy
vercel pull --yes --environment=production --token="$VERCEL_TOKEN"
vercel build --prod --token="$VERCEL_TOKEN"
deploy_url="$(vercel deploy --prebuilt --prod --token="$VERCEL_TOKEN" | tail -n1)"
DEPLOY_URL="$deploy_url" node -e '
const fs = require("node:fs");
const url = process.env.DEPLOY_URL || "";
fs.writeFileSync("reports/deploy/deploy-meta.json", JSON.stringify({
  provider: "vercel",
  id: url || `vercel-${process.env.GITHUB_RUN_ID || 0}-${process.env.GITHUB_RUN_ATTEMPT || 1}`,
  url,
  sha: process.env.GITHUB_SHA || "",
  status: "success",
  identity: "provider-source",
  timestamp_utc: new Date().toISOString()
}, null, 2));
'
