# Backend Deployment (No Redis Required)

This guide deploys backend-only AfyaSync on:

- Domain: afyasync.dima.co.ke
- API base path: /api
- Server owner/user: tom
- Server workspace root: /home/afya-home
- Database: PostgreSQL
- Process manager: systemd
- Reverse proxy: nginx

This setup does not require Redis, Celery, or Channels. It runs Django + Gunicorn only.

## 1. Server layout

Recommended project path:

- /home/afya-home/health-supply-chain

Expected runtime user:

- tom (owner of /home/afya-home and project files)

## 2. Install dependencies

Ubuntu/Debian example:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx postgresql postgresql-contrib
```

## 3. Clone and setup backend

```bash
sudo -u tom -H bash -lc '
  cd /home/afya-home
  git clone <your-repo-url> health-supply-chain || true
  cd health-supply-chain
  chmod +x scripts/setup_backend.sh
  ./scripts/setup_backend.sh --skip-seed
'
```

If you want demo data on server:

```bash
sudo -u tom -H bash -lc 'cd /home/afya-home/health-supply-chain && ./scripts/setup_backend.sh'
```

## 4. PostgreSQL setup

Create DB and user:

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE afyaasync;
CREATE USER afyaasync_user WITH PASSWORD 'replace_with_strong_password';
GRANT ALL PRIVILEGES ON DATABASE afyaasync TO afyaasync_user;
\q
```

## 5. Configure environment

Create and edit:

- /home/afya-home/health-supply-chain/.env

Minimum production values:

```env
DJANGO_SECRET_KEY=replace_me
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=afyasync.dima.co.ke
CORS_ALLOWED_ORIGINS=https://afyasync.dima.co.ke

DATABASE_URL=postgresql://afyasync_user:replace_with_strong_password@127.0.0.1:5432/afyasync

JWT_ACCESS_LIFETIME_MIN=15
JWT_REFRESH_LIFETIME_DAYS=7

GEMMA_API_KEY=replace_me
GEMMA_MODEL_ASSISTANT=gemma-4-4b-it
GEMMA_MODEL_VISION=gemma-4-12b-it
GEMMA_CACHE_TTL_SECONDS=1200

PUBLIC_API_KEY=replace_me

NOTIFICATION_CHANNEL=email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=alerts@dima.co.ke
EMAIL_HOST_PASSWORD=replace_me
DEFAULT_FROM_EMAIL=alerts@dima.co.ke

# Optional for this stage; not used unless you run Celery
REDIS_URL=redis://127.0.0.1:6379/0
```

Note: Redis can stay unset if you never run Celery. The backend API will still run.

## 6. Install systemd service

Copy template:

- deploy/systemd/afyasync-backend.service

Install:

```bash
sudo cp /home/afya-home/health-supply-chain/deploy/systemd/afyasync-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now afyasync-backend
sudo systemctl status afyasync-backend --no-pager
```

If your path differs, update WorkingDirectory, EnvironmentFile, and ExecStart in the service file.

## 7. Install nginx config

Copy template:

- deploy/nginx/afyasync.dima.co.ke.conf

Install and enable:

```bash
sudo cp /home/afya-home/health-supply-chain/deploy/nginx/afyasync.dima.co.ke.conf /etc/nginx/sites-available/
sudo ln -sf /etc/nginx/sites-available/afyasync.dima.co.ke.conf /etc/nginx/sites-enabled/afyasync.dima.co.ke.conf
sudo nginx -t
sudo systemctl reload nginx
```

## 8. HTTPS certificate

If using Let's Encrypt:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d afyasync.dima.co.ke
```

Certbot usually updates ssl_certificate and ssl_certificate_key automatically.

## 9. Verify deployment

Health checks:

```bash
curl -I https://afyasync.dima.co.ke/api/
curl -I https://afyasync.dima.co.ke/api/v1/accounts/auth/login/
```

Service logs:

```bash
sudo journalctl -u afyasync-backend -f
```

Nginx logs:

```bash
sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
```

## 10. Update flow

On new code deploy:

```bash
sudo -u tom -H bash -lc '
  cd /home/afya-home/health-supply-chain
  git pull
  source .venv/bin/activate
  pip install -r requirements.txt
  python manage.py migrate
  python manage.py check
'
sudo systemctl restart afyasync-backend
```
