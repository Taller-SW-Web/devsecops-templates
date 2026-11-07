#!/usr/bin/env bash
set -euo pipefail

./mvnw -B -Dmaven.test.skip=true clean package
