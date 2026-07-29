# Deploy de producao com Nginx e PM2

Este guia publica a aplicacao em tres enderecos:

| Endereco | Conteudo |
| --- | --- |
| `https://seudominio.com.br` | Site publico Astro |
| `https://app.seudominio.com.br` | Aplicacao React |
| `https://api.seudominio.com.br` | API FastAPI, health check e OpenAPI |

O Nginx serve os builds estaticos do React e do Astro. O PM2 gerencia apenas a
API, o worker Celery e o Celery Beat. PostgreSQL/PostGIS e Redis devem executar
como servicos de infraestrutura, não como processos do PM2.

Antes de executar os comandos, substitua:

- `seudominio.com.br` pelo dominio real;
- `URL_DO_REPOSITORIO` pela URL Git do projeto;
- senhas e segredos de exemplo por valores exclusivos de producao.

## 1. Preparar DNS e firewall

Crie registros `A` (e `AAAA`, se houver IPv6) apontando para o servidor:

```text
seudominio.com.br
www.seudominio.com.br
app.seudominio.com.br
api.seudominio.com.br
```

Libere somente SSH, HTTP e HTTPS externamente. As portas `8000`, `5173`, `4321`,
`5432` e `6379` não devem ficar publicas.

Em Ubuntu com UFW:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

## 2. Instalar os pacotes

Exemplo para Ubuntu 24.04:

```bash
sudo apt update
sudo apt install -y \
  nginx certbot python3-certbot-nginx \
  python3 python3-venv python3-dev \
  build-essential libpq-dev git redis-server

curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
sudo corepack enable
sudo corepack prepare pnpm@11.7.0 --activate
sudo npm install -g pm2
sudo systemctl enable --now nginx redis-server
```

Confirme as versoes:

```bash
python3 --version
node --version
pnpm --version
pm2 --version
nginx -v
```

O PostgreSQL 16 com PostGIS pode estar no mesmo servidor ou em um servico
gerenciado. Em ambos os casos, restrinja a conexao ao servidor da aplicacao.

## 3. Criar o usuario e os diretorios

```bash
sudo adduser --disabled-password --gecos '' poliorama
sudo mkdir -p /var/www/poliorama /var/lib/poliorama/arquivos
sudo chown -R poliorama:poliorama /var/www/poliorama /var/lib/poliorama

sudo -u poliorama git clone URL_DO_REPOSITORIO /var/www/poliorama/current
cd /var/www/poliorama/current
```

## 4. Instalar as dependencias da aplicacao

Backend:

```bash
sudo -u poliorama python3 -m venv backend_core/.venv
sudo -u poliorama backend_core/.venv/bin/python -m pip install --upgrade pip
sudo -u poliorama backend_core/.venv/bin/python -m pip install ./backend_core
```

Worker:

```bash
sudo -u poliorama python3 -m venv backend_jobs_celery/.venv
sudo -u poliorama backend_jobs_celery/.venv/bin/python -m pip install --upgrade pip
sudo -u poliorama backend_jobs_celery/.venv/bin/python -m pip install ./backend_jobs_celery
```

Frontends:

```bash
sudo -u poliorama pnpm --dir frontend_core install --frozen-lockfile
sudo -u poliorama pnpm --dir site_publico install --frozen-lockfile
```

## 5. Configurar as variaveis de ambiente

Crie `backend_core/.env`:

```dotenv
APP_NAME=Poliorama API
APP_VERSION=0.1.0
ENVIRONMENT=production
LOG_LEVEL=INFO
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql+asyncpg://app_inteligencia:SENHA_FORTE@127.0.0.1:5432/inteligencia_politica
DATABASE_ECHO=false

JWT_SECRET=SEGREDO_ALEATORIO_COM_PELO_MENOS_32_CARACTERES
MFA_ENCRYPTION_KEY=OUTRO_SEGREDO_ALEATORIO_COM_PELO_MENOS_32_CARACTERES
CORS_ORIGINS=https://seudominio.com.br,https://www.seudominio.com.br,https://app.seudominio.com.br

STORAGE_PROVIDER=local
STORAGE_LOCAL_PATH=/var/lib/poliorama/arquivos
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
```

Crie `backend_jobs_celery/.env`:

```dotenv
ENVIRONMENT=production
LOG_LEVEL=INFO
JOBS_DATABASE_URL=postgresql://app_inteligencia:SENHA_FORTE@127.0.0.1:5432/inteligencia_politica
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
STORAGE_PROVIDER=local
STORAGE_LOCAL_PATH=/var/lib/poliorama/arquivos
```

Crie `frontend_core/.env.production`:

```dotenv
VITE_API_URL=https://app.seudominio.com.br
VITE_APP_NAME=Poliorama
VITE_ENABLE_DEVTOOLS=false
```

Crie `site_publico/.env.production`:

```dotenv
PUBLIC_SITE_URL=https://seudominio.com.br
PUBLIC_APP_LOGIN_URL=https://app.seudominio.com.br/login
PUBLIC_API_BASE_URL=https://seudominio.com.br
PUBLIC_ENVIRONMENT=production
PUBLIC_PLANS_SOURCE=api
PUBLIC_ANALYTICS_PROVIDER=none
```

Gere os segredos sem reutilizar a mesma sequencia:

```bash
openssl rand -hex 32
openssl rand -hex 32
```

Proteja os arquivos:

```bash
sudo chown poliorama:poliorama backend_core/.env backend_jobs_celery/.env
sudo chmod 600 backend_core/.env backend_jobs_celery/.env
```

## 6. Aplicar as migrations

O usuário administrativo do banco é necessário para criar extensoes, schemas,
roles e politicas RLS. A API não deve usar esse usuário.

```bash
read -s -p 'DATABASE_ADMIN_URL: ' DATABASE_ADMIN_URL
echo
export DATABASE_ADMIN_URL

sudo -E -u poliorama backend_core/.venv/bin/python \
  database/scripts/run_migrations.py --dry-run
sudo -E -u poliorama backend_core/.venv/bin/python \
  database/scripts/run_migrations.py

unset DATABASE_ADMIN_URL
```

Depois das migrations, execute o bootstrap do primeiro `gestor_saas`, se ainda
for necessário:

```bash
sudo -iu poliorama bash -lc '
  cd /var/www/poliorama/current/backend_core
  .venv/bin/python -m app.auth.bootstrap \
    --tenant-slug vurix-admin \
    --name "Administrador SaaS" \
    --email admin@seudominio.com.br \
    --profile gestor_saas
'
```

O comando solicita a senha sem gravá-la no historico do terminal.

## 7. Gerar os builds estaticos

O `PUBLIC_SITE_URL` também é exportado porque o arquivo de configuracao do Astro
o utiliza para gerar URLs canonicas e o sitemap.

```bash
sudo -u poliorama pnpm --dir frontend_core build

sudo -u poliorama env \
  PUBLIC_SITE_URL=https://seudominio.com.br \
  PUBLIC_APP_LOGIN_URL=https://app.seudominio.com.br/login \
  PUBLIC_API_BASE_URL=https://seudominio.com.br \
  pnpm --dir site_publico build

test -f frontend_core/dist/index.html
test -f site_publico/dist/index.html
```

## 8. Obter o certificado TLS

O virtual host final referencia o certificado e, por isso, só deve ser ativado
depois desta etapa.

Crie temporariamente `/etc/nginx/sites-available/poliorama-bootstrap`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name seudominio.com.br www.seudominio.com.br
                app.seudominio.com.br api.seudominio.com.br;

    location / {
        return 200 "TLS bootstrap\n";
        add_header Content-Type text/plain;
    }
}
```

Ative o host temporario e solicite um certificado SAN:

```bash
sudo ln -s /etc/nginx/sites-available/poliorama-bootstrap \
  /etc/nginx/sites-enabled/poliorama-bootstrap
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

sudo certbot certonly --nginx \
  -d seudominio.com.br \
  -d www.seudominio.com.br \
  -d app.seudominio.com.br \
  -d api.seudominio.com.br
```

Confira se os arquivos foram criados:

```bash
sudo test -f /etc/letsencrypt/live/seudominio.com.br/fullchain.pem
sudo test -f /etc/letsencrypt/live/seudominio.com.br/privkey.pem
```

## 9. Instalar o virtual host definitivo

O arquivo versionado está em `deploy/nginx/poliorama.conf`.

```bash
cd /var/www/poliorama/current

sed 's/seudominio\\.com\\.br/DOMINIO_REAL.com.br/g' \
  deploy/nginx/poliorama.conf | \
  sudo tee /etc/nginx/sites-available/poliorama >/dev/null

sudo rm -f /etc/nginx/sites-enabled/poliorama-bootstrap
sudo ln -sfn /etc/nginx/sites-available/poliorama \
  /etc/nginx/sites-enabled/poliorama

sudo nginx -t
sudo systemctl reload nginx
```

No comando acima, troque `DOMINIO_REAL.com.br` pelo dominio real. Se o caminho
da aplicacao não for `/var/www/poliorama/current`, altere as duas diretivas
`root` do virtual host.

Teste a renovacao automatica:

```bash
sudo certbot renew --dry-run
systemctl list-timers | grep certbot
```

## 10. Iniciar os processos com PM2

Como os frontends estaticos são entregues diretamente pelo Nginx, inicie no PM2
somente os processos persistentes:

```bash
cd /var/www/poliorama/current

sudo -iu poliorama bash -lc '
  cd /var/www/poliorama/current
  pm2 start ecosystem.config.cjs \
    --only poliorama-api,poliorama-worker,poliorama-scheduler
  pm2 save
'
```

Configure a inicializacao automática:

```bash
sudo env PATH="$PATH:/usr/bin" \
  pm2 startup systemd -u poliorama --hp /home/poliorama
sudo -iu poliorama pm2 save
```

## 11. Validar o deploy

```bash
sudo nginx -t
sudo -iu poliorama pm2 status
sudo -iu poliorama pm2 logs --lines 100

curl -I https://seudominio.com.br
curl -I https://app.seudominio.com.br/login
curl -fsS https://api.seudominio.com.br/health
curl -fsS \
  'https://api.seudominio.com.br/internal/health?check_database=true'
```

Também valide no navegador:

- login e troca de senha;
- cadastro de tenant e usuário;
- upload e download de arquivo;
- formulário comercial do site;
- documentação em `https://api.seudominio.com.br/docs`.

## 12. Atualizacoes futuras

```bash
cd /var/www/poliorama/current
sudo -u poliorama git pull --ff-only

sudo -u poliorama backend_core/.venv/bin/python -m pip install ./backend_core
sudo -u poliorama backend_jobs_celery/.venv/bin/python \
  -m pip install ./backend_jobs_celery

sudo -u poliorama pnpm --dir frontend_core install --frozen-lockfile
sudo -u poliorama pnpm --dir site_publico install --frozen-lockfile
sudo -u poliorama pnpm --dir frontend_core build
sudo -u poliorama env PUBLIC_SITE_URL=https://seudominio.com.br \
  pnpm --dir site_publico build

sudo -iu poliorama pm2 restart \
  poliorama-api poliorama-worker poliorama-scheduler --update-env
sudo nginx -t && sudo systemctl reload nginx
```

Antes de cada atualizacao do banco, execute primeiro:

```bash
python3 database/scripts/run_migrations.py --dry-run
```

Mantenha backup testado do PostgreSQL e do armazenamento de arquivos antes de
aplicar migrations em producao.
