# CLAUDE.md — divsystem-ti

Projeto Django de **gestão de TI** (org municipal + setores + agentes). Deployed em produção no servidor `sabio-srv` (Magalu Cloud, São Paulo).

> 🔐 **Credenciais não estão aqui.** Ver `~/arquivos/acessos-v2/acessos-v2.md` no servidor (chmod 600) para senha do Postgres, Redis, Django secret key, tokens R2/Mailgun/Anthropic/Stripe, login admin, e creds da Magalu/Cloudflare.

---

## URLs

| | |
|---|---|
| Site público | https://ti.divsystem.com.br |
| Admin Django | https://ti.divsystem.com.br/admin/django/ |
| Login | https://ti.divsystem.com.br/contas/login/ |
| Health check | https://ti.divsystem.com.br/healthz |

## Stack

- **Python 3.12.3** + **Django 5.2** (custom user `accounts.User` autenticado por email)
- **PostgreSQL 17.10** (PGDG, role `divsystem_ti`, db `divsystem_ti_prod`)
- **Redis 7** (cache em DB 3, Celery broker em DB 4 — Celery sem tasks definidas ainda)
- **Gunicorn** (3 sync workers, unix socket) atrás de **Nginx** (TLS termination, /static + /media)
- **Tailwind v4** + Node 20 (build via `npm run build`)
- **Whitenoise** + R2 storage (Cloudflare) para media

## Layout

```
divsystem-ti/
├── divsystem/              # settings, urls, wsgi/asgi
├── apps/                   # Django apps
│   ├── accounts/           # custom User (email-based), Tenant
│   ├── agentes/            # WinSysMon (cliente C#) endpoints
│   ├── configuracoes/      # wallpaper, system config
│   ├── mikrotik/           # WireGuard/Mikrotik hub
│   ├── organizacoes/       # secretarias/setores
│   └── core/               # Tenant model
├── theme/                  # Tailwind input.css
├── static/                 # CSS compilada (entrada do collectstatic)
├── staticfiles/            # collectstatic output (servido por Nginx /static/)
├── media/                  # uploads (servido por Nginx /media/)
├── logs/                   # gunicorn-{access,error,stdout,stderr}.log
├── .env                    # chmod 600 — não commitar
└── .venv/                  # virtualenv local (gitignored)
```

## Comandos comuns (no servidor)

```bash
# Sempre dentro do projeto
cd ~/projetos/divsystem-ti
source .venv/bin/activate

# Operações Django
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py shell
python manage.py check --deploy

# Tailwind (no root do projeto, fora do venv)
npm install
npm run build           # build minified
npm run dev             # watch mode

# Reload da app sem downtime
sudo systemctl reload divsystem-gunicorn
sudo systemctl status divsystem-gunicorn --no-pager

# Logs
tail -f logs/gunicorn-error.log
sudo journalctl -u divsystem-gunicorn -f
sudo tail -f /var/log/nginx/divsystem-ti-{access,error}.log
```

## Workflow de deploy

```bash
cd ~/projetos/divsystem-ti
git pull
source .venv/bin/activate
pip install -r requirements.txt
npm install && npm run build
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl reload divsystem-gunicorn
```

## Rotas com peculiaridades

- `/admin/django/` — Django admin (**não** é `/admin/` — esse path é da app `mikrotik`/`configuracoes`)
- `/contas/login/` — Login do `django-allauth` (campo do form: `name="email"`, **não** `username`)
- `/healthz` — respondido pelo **Nginx** direto, não passa pelo gunicorn (200 "ok")

## User model

```python
AUTH_USER_MODEL = "accounts.User"
USERNAME_FIELD = "email"
REQUIRED_FIELDS = ["name"]
```

Campos extras: `tenant` (FK `core.Tenant` nullable), `role` (`operador|tecnico|gestor|admin`), `is_global_admin`, `email_verified_at`, `avatar_url`, `two_factor_secret`, `two_factor_recovery_codes`.

## Infra

| | |
|---|---|
| Provedor | Magalu Cloud (br-se1) |
| Servidor | `sabio-srv` (Ubuntu 24.04, kernel 6.8) |
| IP público | `201.23.73.251` |
| SSH alias (do Windows) | `sabio` |
| Firewall | Magalu SG (22/80/443/ICMP) + UFW + fail2ban |
| SSL | Let's Encrypt via DNS-01 Cloudflare (auto-renova) |
| DNS | Cloudflare (proxy off, A → IP direto) |

## systemd units instaladas

```
/etc/systemd/system/divsystem-gunicorn.socket
/etc/systemd/system/divsystem-gunicorn.service
```

Hardening do unit: `NoNewPrivileges=true`, `PrivateTmp=true`, `User=ubuntu`, `Group=www-data`.

## Variáveis de ambiente importantes (`.env`)

Ver `.env.example` para template completo. Categorias:

- `DJANGO_*` — secret key, debug, allowed hosts, CSRF origins
- `DATABASE_URL` — Postgres
- `REDIS_URL` / `CACHE_REDIS_URL` / `CELERY_BROKER_URL`
- `EMAIL_*` — Mailgun SMTP (⚠️ HOST_USER/HOST_PASSWORD ainda pendentes)
- `CLOUDFLARE_R2_*` — storage de media
- `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL_VISION` — Claude vision
- `AGENT_LATEST_VERSION` + `AGENT_UPDATE_URL` + `AGENT_UPDATE_SHA256` — auto-update do WinSysMon

## Cliente do backend

O **agente C# Windows (WinSysMon)** é o principal consumidor das APIs em `apps/agentes/`. Repo separado (não neste). Endpoints relevantes:

- `POST /api/agente/ping` / `/api/v1/agent/ping`
- `POST /api/v1/agent/heartbeat`
- `POST /api/v1/agent/screenshot/upload`
- `POST /api/v1/agent/setup/{resolve-master-key,validate-code,secretarias,setores}`
- `GET /api/v1/agent/policies` + `GET /api/v1/agent/commands/pending` + `POST /api/v1/agent/command/result`
- `GET /api/v1/agent/download/latest` (responde com `AGENT_UPDATE_URL` do `.env`)

Autenticação via `apps.agentes.authentication.AgentTokenAuthentication`.

## Migração histórica

Origem: **Railway** (artefatos `railway.json`, `nixpacks.toml`, `Procfile` removidos no commit `0baf818`). Backup pré-migração em S3 (`ec2-backups-984365596673`, sa-east-1).

## Schema OpenAPI

`drf-spectacular` gera schema automático em `/api/schema/` (ver `urls.py`). Algumas views custom em `apps/agentes/api_views.py` aparecem como warnings no `check --deploy` (sem serializer_class) — não impeditivo, melhorável.
