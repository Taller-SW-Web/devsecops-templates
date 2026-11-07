#!/usr/bin/env bash
set -euo pipefail

bash ./mvnw -B -Dmaven.test.skip=true clean package
