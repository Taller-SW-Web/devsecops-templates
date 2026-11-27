#!/usr/bin/env bash
set -euo pipefail
case "$EVENT_NAME" in pull_request|push|workflow_dispatch) ;; *) exit 1 ;; esac
test -n "$LANGUAGE"
