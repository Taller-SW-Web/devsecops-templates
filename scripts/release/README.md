# Herramientas de release

`bundle.py` valida SemVer, identidad de reportes, obligatoriedad, rutas, formatos y
checksums; reabre el ZIP para verificarlo. No descubre resultados ni convierte un
manifest escrito a mano en evidencia auténtica. Debe alimentarlo un colector de
artefactos del run, con revisión de privacidad y procedencia del proveedor.

`publish.py` consulta el run/attempt de producción y rechaza otro SHA, rama, evento,
workflow o conclusión. Una versión existente falla de forma segura sin sobrescribir.
Usa GitHub CLI con token de `contents:write` solo al publicar. No infiere SemVer.

```powershell
python -B -m unittest discover -s scripts/release -p test_*.py -v
python scripts/release/bundle.py --manifest candidato.json --root evidencia --output paquete
python scripts/release/publish.py --manifest candidato.json --root evidencia --output publicacion
```

El manifiesto exige: `version` (vX.Y.Z), `sha` completo, `repository`, `branch=main`,
`decision=GO`, `run_id`, `attempt`, `deployment` (id, sha, status, smoke, identity),
y `reports` (kind, path, sha, repository, run_id, attempt, status). Categorías
requeridas: build, sast, sca, secrets, integration, performance, go-no-go.
`provider-source` acredita origen de fuente, no igualdad binaria; `binary-digest`
solo debe usarse con comprobación independiente del digest servido por el proveedor.

Estado: utilidades locales verificables; **publicación automática no conectada aún**.
Faltan colector de reportes normalizados e identidad de Railway/Vercel. No se debe
conectar el publicador a un healthcheck HTTP 200 ni rellenar esos campos con supuestos.
No hay una release global: versiones independientes por componente y pareja de
SHAs explícita en specs cuando ambos despliegues estén acreditados.
