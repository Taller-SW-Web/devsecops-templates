#!/usr/bin/env bash
# Valida una ruta de script/configuracion entregada por el caller: relativa, sin '..',
# con caracteres seguros y existente en el checkout del repositorio llamador.
# Si la ruta es obligatoria para el perfil y falta, el job falla (NO-GO), nunca se omite.
set -euo pipefail

: "${QA_LABEL:?QA_LABEL requerido}"
value="${QA_PATH:-}"
if [ -z "$value" ]; then
  echo "::error::${QA_LABEL}: la politica exige este control y el caller no configuro la ruta."
  exit 1
fi
if [[ ! "$value" =~ ^[A-Za-z0-9._/-]+$ || "$value" == /* || "$value" == *..* ]]; then
  echo "::error::${QA_LABEL}: ruta no permitida '${value}' (solo rutas relativas del repositorio)."
  exit 1
fi
if [ ! -f "$value" ]; then
  echo "::error::${QA_LABEL}: no existe '${value}' en el repositorio llamador."
  exit 1
fi
echo "${QA_LABEL}: ${value}"
