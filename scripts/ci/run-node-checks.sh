#!/usr/bin/env bash
set -euo pipefail

npm ci
npm test
npm run build
