#!/usr/bin/env bash
set -euo pipefail

printf 'value=%s\n' "$RAW_STATUS" >> "$GITHUB_OUTPUT"
