#!/usr/bin/env bash
set -euo pipefail
test -n "${SONAR_TOKEN:-}"
test -n "${SONAR_PROJECT_KEY:-}"
args=("-Dsonar.projectKey=$SONAR_PROJECT_KEY" "-Dsonar.qualitygate.wait=true" "-Dsonar.qualitygate.timeout=600")
if [[ -n "${SONAR_ORGANIZATION_ARGUMENT:-}" ]]; then
  [[ "$SONAR_ORGANIZATION_ARGUMENT" =~ ^-Dsonar.organization=[a-zA-Z0-9_.:-]+$ ]]
  args+=("$SONAR_ORGANIZATION_ARGUMENT")
fi
bash ./mvnw -B org.sonarsource.scanner.maven:sonar-maven-plugin:5.5.0.6356:sonar "${args[@]}"
test -s target/sonar/report-task.txt
