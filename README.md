# Retail CI/CD

Implementacion del patron caller -> reusable workflow -> acciones compartidas.
Los callers consumen las acciones y plantillas compartidas mediante commits inmutables. Los resultados efectivos de analisis y despliegue se consultan en GitHub Actions.

## Archivos por repositorio

| Repositorio | Archivos | Responsabilidad |
|---|---|---|
| G4-Retail-backend y G4-Retail-frontend | `.github/workflows/workflow-pr.yml` | Eventos de PR; un solo job que llama al template de seguridad |
| G4-Retail-backend y G4-Retail-frontend | `.github/workflows/workflow-main.yml` | Push main y dispatch con rollback/tag; un solo job que llama al template CD |
| G4-Retail-backend y G4-Retail-frontend | `.github/workflows/workflow-develop.yml` | Conserva CI de build/tests al hacer push a develop |
| devsecops-templates | `.github/workflows/workflow-pr-analysis.yml` | Validacion, Sonar scan/gate, GHAS SAST/SCA y reporte consolidado |
| devsecops-templates | `.github/workflows/workflow-ci.yml` | Validacion, compilacion, tests, SonarQube, dependencias y resultado |
| devsecops-templates | `.github/workflows/workflow-deploy.yml` | Autorizacion, CI, despliegue, salud HTTP y tag |
| github-actions | `analysis-validator/action.yml`, `policy.cjs` | Seleccion y obligatoriedad de analisis segun el evento real |
| github-actions | `deployment-validator/action.yml`, `validate.cjs` | Equipo GitHub, contexto, tag y procedencia del rollback |
| github-actions | `tests/policy.test.cjs` | Pruebas de autorizacion y politica |

Los cuatro templates anteriores se reemplazan por tres orquestadores (PR, CI y CD). Publicar los consumidores y plantillas coordinadamente: los callers antiguos referencian archivos eliminados.

## Politica

| Contexto | Build/tests | SonarQube | GHAS SAST / SCA |
|---|---|---|---|
| PR feature -> develop | No ejecuta unit tests; Java compila para los analizadores | Informativo | Informativos |
| PR develop -> main | No ejecuta unit tests; Java compila para los analizadores | Obligatorio | Obligatorios |
| Push develop | Obligatorios en workflow-develop | Informativo en CI | Se evaluan en el PR |
| Push main / dispatch normal desde main | Obligatorios en CD | Obligatorio en CI | Se exige revision en el PR protegido |
| Rollback autorizado desde main | Reconstruye la version seleccionada | No repite gate historico | No repite analisis de PR |

Los PR a main deben provenir de develop del mismo repositorio. Una rama de un fork llamada develop no puede promoverse a main. Los errores del analizador o la ausencia de reportes tambien bloquean main. Hacia develop se conserva el resultado real en summary/comentario y el check consolidado no bloquea por hallazgos. La validacion de contexto/lenguaje siempre es obligatoria.

## Analisis de PR: decisiones y alcance

Se mantienen analizadores independientes en paralelo despues de `validation`, con un solo escaneo SonarQube. Separar el mismo escaneo en supuestos jobs Sonar-SAST y Sonar-calidad duplicaria trabajo: seguridad, fiabilidad y mantenibilidad provienen del mismo analisis. El Quality Gate se evalua en un job propio ligado al **analysisId exacto** del compute task, evitando consultar el resultado de otro run concurrente.

| Job | Implementacion y reporte | Condicion |
|---|---|---|
| `validation` | Mapa tecnologia/lenguaje y politica de rama | Contexto valido y combinacion soportada |
| `sonar_analysis` | SonarQube SAST y calidad; bytecode Java o fuentes JS/TS | Escaneo y metadata generados |
| `sonar_gate` | Consulta tarea, espera computo y obtiene condiciones/metricas; JSON y tabla | Quality Gate exactamente `OK` |
| `ghas_sast` | CodeQL security-extended, SARIF, resumen de severidades y Code Scanning | Sin hallazgos high/critical (security-severity >= 7) en las fuentes analizadas |
| `ghas_sca` | Dependency Review, reporte de dependencias y versiones corregidas | Sin vulnerabilidades nuevas high/critical en cambios de dependencias |
| `status` | Actions summary, Markdown descargable y comentario actualizable en PR | Aplica la politica de develop/main |

CodeQL no falla simplemente por encontrar vulnerabilidades: la accion compartida lee el SARIF y aplica el umbral. Este gate cuenta todos los hallazgos de las fuentes analizadas, incluso deuda existente; no simula que sean todos nuevos. Los resultados tambien se publican en Code Scanning para ver localizaciones/anotaciones. Los errores de subida o falta de licencia no se cuentan como analisis limpio.

Dependency Review analiza la diferencia de dependencias del PR a partir de dependency graph. No es un escaneo completo de todas las dependencias desplegadas. Requiere dependency graph habilitado y manifiestos/lockfiles reconocidos. Para cubrir dependencias Maven resueltas/transitivas que no esten en el grafo, habilitar dependency submission y asegurar snapshots de base y head; este flujo no inventa esos snapshots ni ejecuta codigo de PR con un token elevado. No se ha impuesto una lista arbitraria de licencias prohibidas: eso requiere una politica del equipo.

SonarQube aporta SAST, fiabilidad, mantenibilidad, duplicacion y revision de security hotspots segun las reglas y el Quality Gate configurados. Un hotspot requiere revision humana; no equivale automaticamente a una vulnerabilidad confirmada. No se genera cobertura en el flujo PR, por lo que un gate que exija cobertura sin reportes fallara: configurar un gate de seguridad/calidad acorde o incorporar JaCoCo/LCOV posteriormente. No se elimina una condicion de cobertura automaticamente. No se duplica SCA en Sonar: la disponibilidad y licencia de esa funcion dependen del producto, y GHAS ya cubre el control definido aqui.

No se agrega DAST sin una aplicacion desplegada de prueba. Secret scanning/push protection se configuran en GitHub (GitHub Secret Protection cuando aplique), no se representan como un job que el YAML no puede ejecutar.

### Tecnologia y lenguaje declarados por el desarrollador

El caller de PR pasa `technology` y `language`; no hay comandos de build ni pipelines locales en el microservicio.

| Componente | technology | language | CodeQL | Extraccion |
|---|---|---|---|---|
| Backend | maven | java | java-kotlin | manual: Maven compila sin ejecutar tests |
| Frontend | node | typescript | javascript-typescript | none: analiza fuentes sin build |
| Otro proyecto Node admitido | node | javascript | javascript-typescript | none |

Solo se admiten estas combinaciones probadas. Kotlin, Python, .NET, etc. requieren ampliar explicitamente el contrato y preparar su build, sin tratarlos por defecto como Java/Node. SonarQube detecta lenguajes en las fuentes; la tecnologia determina preparacion y rutas. Java usa bytecode y dependencias, mientras JavaScript/TypeScript no necesita ejecutar unit tests para analizarse. Se conserva la clave Sonar derivada `<organizacion>_<repositorio>`.

### Reportes en Actions y PR

Cada job publica su resumen y los archivos disponibles: SARIF/JSON de CodeQL, JSON de Dependency Review, metadata del scanner, JSON del gate y Markdown consolidado. Los errores de configuracion aparecen como fallos/incompletos, nunca como cero hallazgos. `Security Policy Result` publica una tabla con estados, conteos disponibles y enlaces a Actions, Code Scanning y SonarQube. Usa un comentario identificado con marcador estable; lo actualiza en lugar de duplicarlo y evita reemplazar el reporte si el PR ya tiene un commit nuevo.

Los jobs analizadores tienen `continue-on-error` para centralizar la politica, pero exportan su **job.status real** antes de finalizar. El check requerido debe ser **Security Policy Result**, no un job de escaneo individual. Falta de output, cancelacion, skip o fallo de analisis bloquean main. No confundir el resultado tolerado del job individual con un escaneo aprobado.

El comentario usa unicamente GITHUB_TOKEN con `pull-requests: write` en el job de reporte. GH_TOKEN_G4 sigue limitado al control de equipos para deploy y no se pasa a PR. En forks el token normalmente es de lectura y no hay SONAR_TOKEN: se publica el reporte en Actions y se indica el fallo de Sonar. No se usa pull_request_target ni un PAT privilegiado para comentar desde codigo de un fork. Si GitHub impide comentar, el summary y los artefactos siguen disponibles y la politica mantiene su resultado.

## Configuracion pendiente en GitHub

Configurar en **cada repositorio de aplicacion**, Settings -> Secrets and variables -> Actions:

| Tipo | Nombre | Valor |
|---|---|---|
| Secret | `SONAR_TOKEN` | Token con permiso de analisis y lectura del Quality Gate del proyecto SonarQube |
| Variable | `SONAR_HOST_URL` | URL HTTPS del servidor SonarQube accesible desde ubuntu-latest |
| Variable | `PRODUCTION_HEALTHCHECK_URL` | Endpoint HTTPS publico que devuelve HTTP 2xx/3xx cuando la aplicacion esta saludable |
| Secret | `GH_TOKEN_G4` | Token con Members (read) de la organizacion y Contents/Actions (read) del repositorio; permite consultar la membresia del equipo y validar tags/runs |

La clave del proyecto SonarQube se deriva internamente del repositorio caller como `<organizacion>_<repositorio>`, conservando mayusculas: `Taller-SW-Web_G4-Retail-backend` y `Taller-SW-Web_G4-Retail-frontend`. No configurar `SONAR_PROJECT_KEY` ni pasar ese input en callers. `SONAR_HOST_URL` sigue siendo la URL del servidor y `PRODUCTION_HEALTHCHECK_URL` el endpoint de salud; esas URLs no se deducen del nombre del repositorio.

Backend conserva los secretos existentes `RAILWAY_TOKEN` y `RAILWAY_SERVICE` (este ultimo ya esta guardado como secreto). El token debe apuntar al proyecto/ambiente productivo. Frontend conserva `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.

La autorizacion se ejecuta como job visible `validation` (**Validate GitHub Team Membership**), antes de CI y deploy. No se usa GitHub Environments. Todos los secretos deben configurarse a nivel repositorio u organizacion.

Crear el equipo de organizacion **Taller-SW-Web/retail-operator** y agregar a los operadores. Se exige membresia activa tanto al actor original (`github.actor`) como a quien reejecuta (`github.triggering_actor`). La validacion aplica a todos los despliegues: push main, dispatch normal y rollback. No afecta a los PR de CI. Los usuarios o bots que disparan un push a main tambien deben pertenecer al equipo.

`GH_TOKEN_G4` debe poder leer miembros de la organizacion (fine-grained PAT con **Members: read**, autorizado para la organizacion, ademas de **Contents: read** y **Actions: read** en el repositorio). No pegar el token en codigo. GITHUB_TOKEN se usa como fallback, pero normalmente no puede leer miembros de la organizacion: si la consulta falla, el job deniega el acceso. La consulta se hace sobre el usuario que ejecuto el workflow, no sobre el propietario del token.

El summary muestra usuario, equipo requerido, estado y motivo. Invitaciones pendientes, usuarios fuera del equipo y errores de API (403/404/5xx) bloquean validation. CI, deploy y tag no avanzan. Un 404 no permite distinguir entre ausencia de membresia y un equipo oculto al token; el resumen indica ambas posibilidades. No se requiere un rol personalizado de repositorio ni aprobacion por environment.

Activar GitHub Code Security/GHAS cuando el repositorio privado lo requiera, dependency graph y CodeQL **Advanced setup**; desactivar Default setup si ya esta habilitado para evitar conflictos con el workflow. Permitir que GITHUB_TOKEN publique security-events y comentarios de PR. Los permisos se conceden por job y no se usa GH_TOKEN_G4 para subir SARIF.

SonarQube Server debe soportar analisis de PR y ramas (Developer Edition o superior). Vincular los proyectos con los repositorios y configurar el Quality Gate. Si el servidor no es accesible desde GitHub-hosted runners, configurar un runner con conectividad antes de ejecutar.

En **Rulesets/Branch protection**, exigir PR para main, bloquear pushes directos habituales y exigir el check del job **Security Policy Result** dentro de **Security Analysis**. Seleccionar su nombre exacto tras el primer run de GitHub. Exigir que la rama este actualizada. En develop se puede exigir ese mismo resultado: solo la validacion obligatoria lo hace fallar. No exigir separadamente los checks Sonar/CodeQL/dependencias en develop, pues deben ser informativos. Proteger tambien los workflows, templates y acciones con revision de propietarios.

Proteger `production-*` contra actualizacion y borrado mediante un tag ruleset y permitir su creacion al mecanismo del pipeline. Mantener los registros de runs usados como procedencia; si se elimina un run, ese tag deja de ser elegible. Desactivar despliegues automaticos independientes de las integraciones Git de Railway/Vercel si se pretende que este pipeline sea el unico gate de produccion.

## Despliegue y rollback

El flujo normal valida main, membresia del equipo y configuracion, ejecuta CI obligatorio, despliega Railway/Vercel, comprueba salud HTTP y crea un tag anotado `production-<run_id>-<attempt>` al SHA exacto desplegado. Un fallo de deploy/salud no crea tag. Un error al crear el tag deja el run fallido, aunque la aplicacion ya puede estar desplegada.

Para volver a una version anterior: Actions -> Production Deployment and Rollback -> Run workflow; seleccionar **main**, marcar **rollback** e ingresar un tag `production-...` generado por un run exitoso. El workflow siempre se ejecuta desde main; el tag solo selecciona el codigo a reconstruir. El validador revisa tanto al actor original como a quien reejecuta el run. Errores de API, tags arbitrarios, tags ligeros, runs fallidos y membresias no activas deniegan el despliegue antes de acceder al job deployment.

Se resuelve el tag a un SHA y ese SHA se usa en checkout; mover el tag despues de validar no cambia el checkout. El rollback reconstruye codigo con dependencias/configuracion actuales: no restaura una imagen inmutable ni una base de datos y no deshace migraciones. No crea otro tag de release. Los despliegues se serializan por repositorio y no se cancelan en curso; GitHub puede reemplazar ejecuciones pendientes del mismo grupo, por lo que no representa una cola FIFO de cada commit.

La comprobacion HTTP verifica disponibilidad, no identidad de la version; la confirmacion de version depende de que la CLI complete el deploy. Railway se ejecuta en modo adjunto, sin --ci (este ultimo puede terminar tras build). Configurar healthchecks tambien en el proveedor. Los CLIs se instalan desde npm; para reproducibilidad completa fijar sus versiones aprobadas.

## Publicacion cuando se autorice

1. Publicar github-actions en main y obtener el SHA real del commit.
2. Sustituir todas las referencias `Taller-SW-Web/github-actions/...@main` en templates por ese SHA; publicar templates en main y obtener su SHA.
3. Sustituir en los seis callers `devsecops-templates/...@main` por ese SHA real y publicar ambos consumidores en main. Esta ultima operacion inicia CD real.
4. Revisar los runs y seleccionar el required check en las reglas de main. Probar un PR hacia develop y otro desde develop hacia main, y luego un rollback autorizado y uno denegado.

Hasta publicar, las referencias @main mantienen el contrato previsto, pero el remoto aun contiene la version anterior. No inventar SHAs ni ejecutar callers nuevos contra templates viejos.

## Referencias

- [GitHub: membresia de equipos y permisos del token](https://docs.github.com/en/rest/teams/members)
- [SonarQube: analisis de pull requests](https://docs.sonarsource.com/sonarqube-server/discovering/code-analysis/pull-request-analysis.md)
- [Railway: comando up](https://docs.railway.com/cli/up)

- [GitHub: CodeQL por lenguaje y modos de build](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/manage-your-configuration/codeql-for-compiled-languages)
- [GitHub: alcance de Dependency Review](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependency-review)
- [Dependency Review: contrato oficial de inputs/outputs v4](https://github.com/actions/dependency-review-action/blob/v4/action.yml)
