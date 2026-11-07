#!/usr/bin/env bash
set -euo pipefail

test -n "${VERCEL_TOKEN:-}" && test -n "${VERCEL_ORG_ID:-}" && test -n "${VERCEL_PROJECT_ID:-}"
npm install -g vercel
vercel pull --yes --environment=production --token="$VERCEL_TOKEN"
vercel build --prod --token="$VERCEL_TOKEN"
vercel deploy --prebuilt --prod --token="$VERCEL_TOKEN"
