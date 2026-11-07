# devsecops-templates

Repositorio central para gobernar CI/CD. Contiene workflows reutilizables (reusable workflows) de GitHub Actions que los repos de producto llaman con `workflow_call`.

## Templates disponibles

### `cd-railway.yml` — Deploy a Railway

Dispara un redeploy en Railway via deploy hook (webhook).

**Secrets requeridos en el repo que llama:**

| Secret | Descripcion |
|--------|-------------|
| `RAILWAY_DEPLOY_HOOK_URL` | URL del deploy hook del servicio en Railway (Settings > Deploy Hooks) |

**Inputs opcionales:**

| Input | Default | Descripcion |
|-------|---------|-------------|
| `environment` | `production` | Nombre del environment de GitHub |
| `wait-for-healthy` | `120` | Segundos de espera antes de verificar health check |
| `health-url` | `""` | URL del health check (vacia = no verificar) |

**Ejemplo de uso:**

```yaml
deploy:
  uses: Taller-SW-Web/devsecops-templates/.github/workflows/cd-railway.yml@main
  with:
    environment: production
  secrets:
    RAILWAY_DEPLOY_HOOK_URL: ${{ secrets.RAILWAY_DEPLOY_HOOK_URL }}
```

---

### `cd-vercel.yml` — Deploy a Vercel

Despliega a Vercel produccion usando la CLI oficial.

**Secrets requeridos en el repo que llama:**

| Secret | Descripcion |
|--------|-------------|
| `VERCEL_TOKEN` | Token de la API de Vercel (vercel.com > Settings > Tokens) |
| `VERCEL_ORG_ID` | ID de la organizacion/equipo en Vercel |
| `VERCEL_PROJECT_ID` | ID del proyecto en Vercel |

**Inputs opcionales:**

| Input | Default | Descripcion |
|-------|---------|-------------|
| `environment` | `production` | Nombre del environment de GitHub |
| `node-version` | `22` | Version de Node.js |
| `build-env` | `{}` | Variables de entorno extra para el build (JSON) |

**Ejemplo de uso:**

```yaml
deploy:
  uses: Taller-SW-Web/devsecops-templates/.github/workflows/cd-vercel.yml@main
  with:
    environment: production
    node-version: "22"
  secrets:
    VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
    VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
    VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
```

## Configuracion de secrets

Los secrets se configuran en cada repo de producto: **Settings > Secrets and variables > Actions > New repository secret**.

### Para el backend (Railway)

1. En Railway, ir al servicio > Settings > Deploy Hooks > crear un hook.
2. Copiar la URL y guardarla como `RAILWAY_DEPLOY_HOOK_URL` en los secrets del repo de backend.

### Para el frontend (Vercel)

1. En vercel.com > Settings > Tokens > crear un token.
2. Guardar como `VERCEL_TOKEN` en los secrets del repo de frontend.
3. Obtener `VERCEL_ORG_ID` y `VERCEL_PROJECT_ID` de la carpeta `.vercel/project.json` local (se genera al hacer `vercel link`) o desde Settings del proyecto en Vercel.
4. Guardarlos como `VERCEL_ORG_ID` y `VERCEL_PROJECT_ID` en los secrets del repo de frontend.
