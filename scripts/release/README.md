# Evidencias y release SemVer

workflow-deploy.yml descarga los artefactos del run actual, ejecuta collect_evidence.py
con la tecnologia del caller y pasa el manifiesto a bundle.py. No reutiliza reportes
historicos para rellenar categorias ausentes.

Estructura: manifest/, quality/, security/{sast,sca,secrets,dast}/,
tests/{unit,integration,e2e,performance}/, deployment/ y go-no-go.json.
Las categorias no aplicables se declaran en not_applicable; no reciben reportes ajenos.

Backend exige integracion, performance y DAST. Frontend exige E2E. Ambos exigen
unitarias, calidad, SAST, SCA, secretos, decision integral y despliegue saludable.
Se conservan todos los XML encontrados y sus rutas de origen. Los estados proceden
del gate-result.json del mismo SHA, repositorio, run y attempt, no de la existencia
del archivo. La recoleccion es posterior a los jobs y usa artefactos del run actual.
El timestamp del manifiesto es el de recoleccion; los reportes retienen su contenido
original. Cada entrada incluye origen, version, entorno, identidad y SHA-256.

bundle.py valida identidad, categorias, formatos, rutas y hashes, comprueba el ZIP
y rechaza sobrescribir un paquete existente. Mantiene manifiesto y SHA256SUMS.
provider-source acredita el SHA fuente del proveedor, no identidad binaria servida.

No se deben publicar estos cambios antes de sincronizar main y comprobar los tags.
VERSION sigue siendo la fuente SemVer; resolver una colision debe fallar, nunca
sobrescribir releases. La publicacion sigue condicionada a GO y healthcheck.

```sh
python -m unittest discover -s scripts/release -p 'test_*.py'
```
