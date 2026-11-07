#!/usr/bin/env bash
set -euo pipefail

test "$EVENT_NAME" = pull_request
test -n "$LANGUAGE"
