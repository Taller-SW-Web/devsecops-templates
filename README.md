# devsecops-templates

Repositorio central de gobernanza CI/CD para la organizacion Taller-SW-Web.
Contiene workflows reutilizables (reusable workflows) de GitHub Actions que los
repositorios de producto invocan mediante `workflow_call`.

## Arquitectura

```
mic (caller)                    devsecops-templates (templates)
┌──────────────────────┐        ┌──────────────────────────────────────┐
│ workflow-pr.yml      │───────>│ workflow-ci-maven.yml                │
│   - evento: PR/push  │        │   - validation                      │
│   - with: datos      │        │   - build-and-test                  │
│   - secrets          │        │   - status-check                    │
└──────────────────────┘        ├──────────────────────────────────────┤
┌──────────────────────┐        │ workflow-ci-node.yml                 │
│ workflow-main.yml    │───────>│   - validation                      │
│   - evento: push main│        │   - install                         │
│   - with: datos      │        │   - test                            │
│   - secrets          │        │   - build                           │
│   - needs: ci→deploy │        │   - status-check                    │
└──────────────────────┘        ├──────────────────────────────────────┤
                                │ workflow-deploy-railway.yml          │
                                │   - pre-deploy-validation           │
                                │   - deploy (Railway CLI)            │
                                │   - post-deploy-verification        │
                                ├──────────────────────────────────────┤
                                │ workflow-deploy-vercel.yml           │
                                │   - pre-deploy-validation           │
                                │   - deploy (Vercel CLI)             │
                                │   - post-deploy-verification        │
                                └──────────────────────────────────────┘
```

**Regla principal:** el repositorio del microservicio no implementa el pipeline.
Solo declara cuando se ejecuta y llama al template, pasando datos con `with` y
secretos con `secrets`. La orquestacion, runners y steps viven en los templates.

## Templates disponibles

### `workflow-ci-maven.yml` — CI para Java + Maven

Jobs: `validation` → `build-and-test` → `status-check`

| Input | Requerido | Default | Descripcion |
|-------|-----------|---------|-------------|
| `component_name` | Si | — | Nombre del componente |
| `java_version` | No | `21` | Version de Java |
| `maven_goals` | No | `verify` | Goals de Maven |

### `workflow-ci-node.yml` — CI para Node.js + Vite

Jobs: `validation` → `install` → `test` + `build` (paralelo) → `status-check`

| Input | Requerido | Default | Descripcion |
|-------|-----------|---------|-------------|
| `component_name` | Si | — | Nombre del componente |
| `node_version` | No | `22` | Version de Node.js |
| `build_env_vars` | No | `{}` | Variables de entorno para build |

### `workflow-deploy-railway.yml` — Deploy a Railway

Jobs: `pre-deploy-validation` → `deploy` → `post-deploy-verification`

| Input | Requerido | Default | Descripcion |
|-------|-----------|---------|-------------|
| `component_name` | Si | — | Nombre del componente |
| `environment_name` | No | `production` | Environment de GitHub |
| `service_name` | No | `""` | Nombre del servicio en Railway |
| `java_version` | No | `21` | Version de Java |

| Secret | Requerido | Descripcion |
|--------|-----------|-------------|
| `RAILWAY_TOKEN` | Si | Project Token de Railway |

### `workflow-deploy-vercel.yml` — Deploy a Vercel

Jobs: `pre-deploy-validation` → `deploy` → `post-deploy-verification`

| Input | Requerido | Default | Descripcion |
|-------|-----------|---------|-------------|
| `component_name` | Si | — | Nombre del componente |
| `environment_name` | No | `production` | Environment de GitHub |
| `node_version` | No | `22` | Version de Node.js |

| Secret | Requerido | Descripcion |
|--------|-----------|-------------|
| `VERCEL_TOKEN` | Si | Token de la API de Vercel |
| `VERCEL_ORG_ID` | Si | ID de la organizacion en Vercel |
| `VERCEL_PROJECT_ID` | Si | ID del proyecto en Vercel |

## Configuracion de secrets por repositorio

### G4-Retail-backend

| Tipo | Nombre | Origen |
|------|--------|--------|
| Secret | `RAILWAY_TOKEN` | Railway > Proyecto > Settings > Tokens |
| Variable | `RAILWAY_SERVICE` | Nombre del servicio en el dashboard de Railway |

### G4-Retail-frontend

| Tipo | Nombre | Origen |
|------|--------|--------|
| Secret | `VERCEL_TOKEN` | vercel.com > Settings > Tokens |
| Secret | `VERCEL_ORG_ID` | `.vercel/project.json` o Settings del proyecto |
| Secret | `VERCEL_PROJECT_ID` | `.vercel/project.json` o Settings del proyecto |
