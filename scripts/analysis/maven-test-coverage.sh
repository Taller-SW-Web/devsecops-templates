#!/usr/bin/env bash
set -euo pipefail

JACOCO_VERSION=0.8.13
bash ./mvnw -B clean \
  "org.jacoco:jacoco-maven-plugin:${JACOCO_VERSION}:prepare-agent" \
  verify \
  "org.jacoco:jacoco-maven-plugin:${JACOCO_VERSION}:report"

test -s target/site/jacoco/jacoco.xml || {
  echo '::error::JaCoCo did not produce target/site/jacoco/jacoco.xml'
  exit 1
}
