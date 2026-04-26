# DIVSYSTEM · Painel Django

Reescrita em Django 5.2 + DRF + PostgreSQL + Tailwind v4 + Iconify do
DIVSYSTEM (originalmente Laravel 12 / Livewire). SaaS B2G multi-tenant
single-database para gestão de TI municipal.

> Todos acessam pela mesma URL (ex.: `ti.divsystem.com.br`); o tenant é
> identificado automaticamente pelo usuário autenticado.

## Stack

- Python 3.12 · Django 5.2 · DRF 3.17
- PostgreSQL (JSONB) · Redis (cache, sessions, Celery)
- Tailwind CSS v4 (CLI) · Iconify (web component) · HTMX + Alpine.js
- WhiteNoise (estáticos) · Celery (tasks) · drf-spectacular (OpenAPI)

## Apps

| App | Responsabilidade |
|---|---|
| `apps.core` | Tenant, middleware, RBAC (`UserRole`), thread-local, mixins |
| `apps.accounts` | User customizado (email login), perfil, CRUD usuários |
| `apps.organizacoes` | Secretaria + Setor (multi-tenant scoped) |
| `apps.configuracoes` | Setting (chave-valor por tenant) |
| `apps.agentes` | AgentToken, AgentHeartbeat, RemoteCommand + API REST |
| `apps.dashboard` | Home/landing |

## RBAC

Hierarquia (igual ao Laravel original):
`Operador (1) < Tecnico (2) < Gestor (3) < Admin (4)`.

`is_global_admin` é o "superadmin SABIO" — vê e altera entre todos os tenants
via `/contas/tenant/selecionar/`.

## Multi-tenant single-DB

- `apps.core.models.Tenant` — uma prefeitura.
- `apps.core.models.TenantOwnedModel` — base abstrata com `tenant` FK.
- `apps.core.threadlocal` — guarda tenant ativo por request.
- `apps.core.middleware.ResolveTenantMiddleware` — preenche thread-local pelo
  `request.user.tenant`.
- Manager `objects` filtra automaticamente por tenant. `all_tenants` ignora.

## Setup local

```bash
# 1. Banco
sudo -u postgres createdb divsystem_django -O divsystem_user

# 2. Python deps
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Tailwind
npm install
npm run build  # ou npm run dev em outro terminal

# 4. .env (copie .env.example e ajuste)
cp .env.example .env

# 5. Migrate + seed
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo

# 6. Run
.venv/bin/python manage.py runserver 0.0.0.0:8011
```

Login do seed:
- `admin@divsystem.com.br` / `divsystem2026` — admin global SABIO
- `gestor@divinesia.mg.gov.br` / `divsystem2026` — Gestor da Prefeitura de Divinésia

## Endpoints da API do agente

- `GET  /api/v1/agent/ping`
- `POST /api/v1/agent/ping/`           (Bearer)
- `POST /api/v1/agent/heartbeat`       (Bearer)
- `POST /api/v1/agent/enroll`
- `GET  /api/v1/agent/commands/pending` (Bearer)
- `POST /api/v1/agent/command-result`   (Bearer)
- `POST /api/v1/agent/setup/resolve-master-key`
- `GET  /api/v1/agent/setup/validate/{code}`
- `GET  /api/v1/agent/setup/{code}/secretarias`
- `GET  /api/v1/agent/setup/{code}/secretaria/{id}/setores`

Alias legado (compat com agentes antigos): `/api/agente/...`

OpenAPI/Swagger: `/api/docs/` (precisa estar autenticado).
