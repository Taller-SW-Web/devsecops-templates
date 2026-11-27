#!/usr/bin/env bash
# Detiene la instancia efimera iniciada por boot-app.sh (si sigue viva).
set -uo pipefail
pid_file="${OUT_DIR:?OUT_DIR requerido}/aplicacion.pid"
if [ -f "$pid_file" ]; then
  kill "$(cat "$pid_file")" 2>/dev/null || true
fi
