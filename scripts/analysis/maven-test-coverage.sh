#!/usr/bin/env bash
set -euo pipefail

JACOCO_VERSION=0.8.13
if command -v mvn >/dev/null 2>&1; then
  mvn -B clean \
    "org.jacoco:jacoco-maven-plugin:${JACOCO_VERSION}:prepare-agent" \
    verify \
    "org.jacoco:jacoco-maven-plugin:${JACOCO_VERSION}:report"
else
  bash ./mvnw -B clean \
    "org.jacoco:jacoco-maven-plugin:${JACOCO_VERSION}:prepare-agent" \
    verify \
    "org.jacoco:jacoco-maven-plugin:${JACOCO_VERSION}:report"
fi

test -s target/site/jacoco/jacoco.xml || {
  echo '::error::JaCoCo did not produce target/site/jacoco/jacoco.xml'
  exit 1
}
