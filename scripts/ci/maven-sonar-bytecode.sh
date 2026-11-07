#!/usr/bin/env bash
set -euo pipefail

bash ./mvnw -B -DskipTests package
