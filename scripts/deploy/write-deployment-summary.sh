#!/usr/bin/env bash
set -euo pipefail

printf '### Production deployment\nCommit: `%s`\n\nRollback: %s\n\nSource tag: %s\n' \
  "$SOURCE_SHA" "$ROLLBACK" "$RELEASE_TAG" >> "$GITHUB_STEP_SUMMARY"
