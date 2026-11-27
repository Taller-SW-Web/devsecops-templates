#!/usr/bin/env bash
# Arranca el JAR compilado en build_test como instancia local efimera (loopback) y espera salud.
# HEALTH_OUTPUT (opcional) guarda la respuesta de salud. Deja el PID en $OUT_DIR/aplicacion.pid para que stop-app.sh lo detenga al final del job.
set -euo pipefail

: "${OUT_DIR:?OUT_DIR requerido}"
: "${APP_JAR_PATTERN:?APP_JAR_PATTERN requerido}"
: "${APP_HEALTH_PATH:?APP_HEALTH_PATH requerido}"
if [[ ! "$APP_HEALTH_PATH" =~ ^/[A-Za-z0-9._/-]*$ ]]; then
  echo "::error::APP_HEALTH_PATH invalido"
  exit 1
fi
mkdir -p "$OUT_DIR"
application_jar="$(find target -maxdepth 2 -type f -name "$APP_JAR_PATTERN" ! -name '*.original' | head -n 1)"
if [ -z "$application_jar" ]; then
  echo "::error::No se encontro un JAR '${APP_JAR_PATTERN}' en el artefacto build-coverage."
  exit 1
fi
# Argumentos de la aplicacion separados por espacios o saltos de linea (sin comillas).
read -r -a boot_args <<< "$(printf '%s' "${APP_BOOT_ARGS:-}" | tr '\n' ' ')"
java -jar "$application_jar" \
  --server.address=127.0.0.1 \
  --server.port=8080 \
  "${boot_args[@]}" \
  > "$OUT_DIR/servidor.log" 2>&1 &
application_pid=$!
printf '%s\n' "$application_pid" > "$OUT_DIR/aplicacion.pid"
for _ in $(seq 1 60); do
  if curl --fail --silent "http://127.0.0.1:8080${APP_HEALTH_PATH}" > "${HEALTH_OUTPUT:-/dev/null}"; then
    exit 0
  fi
  kill -0 "$application_pid"
  sleep 2
done
cat "$OUT_DIR/servidor.log"
exit 1
