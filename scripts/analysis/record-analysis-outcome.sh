#!/usr/bin/env bash
set -euo pipefail

printf 'value=%s\n' "$RAW_STATUS" >> "$GITHUB_OUTPUT"
printf '%s\n' "$SUMMARY_TEXT" >> "$GITHUB_STEP_SUMMARY"
