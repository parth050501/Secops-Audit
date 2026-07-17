# DEPLOY — Complete Step-by-Step (AWS EC2 + Ubuntu + HTTPS)

Follow these in order on your fresh Ubuntu EC2 instance.

## Prerequisites (do these in AWS console first)
- [ ] EC2 instance running (Ubuntu 24.04, c7i.large/m_i.large recommended, 30GB disk)
- [ ] Elastic IP allocated AND associated with the instance (stable IP)
- [ ] Security group: 22 (SSH) from YOUR IP only; 80 + 443 from anywhere;
      NOTHING else public (not 8000, 3000, 5432)
- [ ] GoDaddy A record: your subdomain → the Elastic IP
- [ ] DNS resolves: run `nslookup YOUR_SUBDOMAIN` from your laptop and confirm
      it returns the Elastic IP BEFORE deploying (HTTPS cert needs this)

---

## Step 1 — Install Docker + Compose on the instance
```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
# log out and back in (or run: newgrp docker) so the group applies
newgrp docker
docker --version && docker compose version
```

## Step 2 — Get the code onto the server
Option A (recommended) — clone from your GitHub repo:
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```
Option B — scp the zip from your laptop, then unzip on the server.

## Step 3 — Generate secrets
```bash
echo "JWT_SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
echo "SECOPS_ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' 2>/dev/null || docker run --rm python:3.11-slim sh -c 'pip install cryptography -q && python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')"
echo "POSTGRES_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
```
Copy these values. **Save them in a password manager** — especially
SECOPS_ENCRYPTION_KEY (lose it = stored credentials unrecoverable).

## Step 4 — Create the .env file
In the project root (same folder as docker-compose.yml):
```bash
cat > .env << 'ENVEOF'
SITE_DOMAIN=YOUR_SUBDOMAIN              # e.g. app.codecoresystems.com (no https://)
ENVIRONMENT=production
JWT_SECRET=<paste from step 3>
SECOPS_ENCRYPTION_KEY=<paste from step 3>
POSTGRES_USER=secops
POSTGRES_PASSWORD=<paste from step 3>
POSTGRES_DB=secops
ANTHROPIC_API_KEY=                       # optional, only if using AI features
ENVEOF
chmod 600 .env
```
The .env is gitignored — it will NOT be committed. Good.

## Step 5 — Launch (production stack with HTTPS)
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```
First build takes several minutes (Prowler + OpenSCAP are large). Watch logs:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```
Caddy will automatically obtain the HTTPS certificate from Let's Encrypt for
SITE_DOMAIN. If DNS is resolving correctly, this takes under a minute.

## Step 6 — Create the first super-admin (one time)
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python seed.py
```
NOTE: in production the seed refuses to create demo accounts unless ALLOW_PROD_SEED=1.
For a clean prod start where you ONLY want the super-admin (super@secops.ai), see
"Production seed" below — you likely want to create just the super-admin and then
change its password immediately, NOT the full demo dataset.

## Step 7 — Verify it's up and SAFE
```bash
# From your LAPTOP (not the server):
curl -I https://YOUR_SUBDOMAIN/health        # should return 200 over HTTPS
nc -zv YOUR_ELASTIC_IP 8000                   # should FAIL/timeout (backend not public)
nc -zv YOUR_ELASTIC_IP 5432                   # should FAIL/timeout (db not public)
```
Open https://YOUR_SUBDOMAIN in a browser — you should get the app over HTTPS with
a valid certificate (no warning).

## Step 8 — Log in and harden
- Log in as super@secops.ai (platform console) → change the password immediately.
- Onboard your first real tenant from the platform console.
- Remove/disable any demo accounts you don't want.

---

## Updating later (the GitHub workflow)
```bash
cd YOUR_REPO
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
# only the changed services rebuild
```

## Backups (do this before real customer data)
```bash
# Postgres dump (cron this daily, ship to S3):
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec postgres \
  pg_dump -U secops secops > backup_$(date +%F).sql
```
Also snapshot the EBS volume periodically. Test a restore once — an untested
backup is not a backup.

## Production seed (super-admin only, no demo data)
If you want ONLY the super-admin on a production box (recommended), the simplest
path: run the seed with ALLOW_PROD_SEED=1 to create accounts, then immediately
delete the demo tenant + demo users from the platform console and change the
super-admin password. (A dedicated prod-seed script is a good future addition.)

## Troubleshooting
- Cert not issued → check DNS resolves to the Elastic IP, and ports 80+443 open.
- 502 from Caddy → backend/frontend still starting; check `docker compose ... logs`.
- Scan crashes / OOM → instance too small; size up (need 4GB+; 8GB comfortable).
- Backend can't reach DB → confirm POSTGRES_* in .env match; check postgres health.
