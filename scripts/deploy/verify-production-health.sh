#!/usr/bin/env bash
set -euo pipefail

mkdir -p reports/deploy
http_code="$(curl --fail --silent --show-error --retry 12 --retry-all-errors --retry-delay 10 --max-time 20 -o reports/deploy/health-body.txt -w '%{http_code}' "$HEALTHCHECK_URL")"
HTTP_CODE="$http_code" node -e '
const fs = require("node:fs");
fs.writeFileSync("reports/deploy/health-check.json", JSON.stringify({
  url: process.env.HEALTHCHECK_URL,
  http_code: Number(process.env.HTTP_CODE || 0),
  status: "success",
  timestamp_utc: new Date().toISOString()
}, null, 2));
'
