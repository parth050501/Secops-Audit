# AWS EC2 Hosting Roadmap — Code Core Systems

A step-by-step path to host the platform on EC2 for real-data partner testing.
Items marked (YOU) happen in your AWS account; (CODE) is already prepared in the repo.

## Phase A — Before you launch the instance

1. (CODE) PostgreSQL support — done. Production compose uses Postgres.
2. (CODE) Credential encryption + bcrypt — done.
3. (CODE) HTTPS reverse-proxy config — pending (next code task: Caddy).
4. (YOU) Buy a domain (or use a subdomain you control), e.g. app.codecoresystems.com
5. (YOU) Generate production secrets and store them safely (password manager):
   ```
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"   # SECOPS_ENCRYPTION_KEY
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"                                  # JWT_SECRET
   python3 -c "import secrets; print(secrets.token_urlsafe(24))"                                  # POSTGRES_PASSWORD
   ```
   Losing SECOPS_ENCRYPTION_KEY = stored credentials become unrecoverable.

## Phase B — Launch & secure the instance

6. (YOU) Launch an EC2 instance:
   - AMI: Ubuntu 24.04 LTS
   - Size: t3.medium minimum (Prowler scans are memory-hungry); t3.large if scanning
     while serving traffic. Add a 30GB+ EBS volume.
7. (YOU) Security group (the firewall — critical):
   - Inbound 443 (HTTPS) from 0.0.0.0/0
   - Inbound 80 (HTTP) from 0.0.0.0/0  (only so the cert challenge + redirect works)
   - Inbound 22 (SSH) from YOUR IP ONLY — never 0.0.0.0/0
   - Do NOT open 8000, 3000, or 5432 to the internet. Only the reverse proxy is public.
8. (YOU) Point your domain's DNS A-record at the instance's public IP.

## Phase C — Install & deploy

9. (YOU) SSH in, install Docker + Docker Compose:
   ```
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
   sudo usermod -aG docker $USER   # re-login after this
   ```
10. (YOU) Copy the project to the instance (git clone, or scp the zip).
11. (YOU) Create a .env file next to docker-compose.yml with your secrets:
    ```
    JWT_SECRET=...
    SECOPS_ENCRYPTION_KEY=...
    POSTGRES_USER=secops
    POSTGRES_PASSWORD=...
    POSTGRES_DB=secops
    ANTHROPIC_API_KEY=...        # optional, only if using AI features
    ```
12. (CODE+YOU) Bring it up with the production override (Postgres + no reload + prod env):
    ```
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
    docker compose exec backend python seed.py    # first time only — creates demo/super admin
    ```
    For real use, after first login change/remove demo accounts.

## Phase D — HTTPS (once the reverse-proxy config is added)

13. (CODE) Add Caddy reverse-proxy service (pending). Caddy auto-obtains and renews
    a free TLS certificate for your domain — minimal config.
14. (YOU) Verify https://your-domain loads and http:// redirects to https.

## Phase E — Verify it's safe

15. (YOU) From a machine that is NOT you, confirm:
    - https://your-domain works
    - http://your-ip:8000 is NOT reachable (backend not exposed)
    - http://your-ip:3000 is NOT reachable (frontend not exposed)
    - port 5432 is NOT reachable (database not exposed)
16. (YOU) Log in over HTTPS, add an AWS connector with real read-only creds, run a scan,
    confirm findings appear and credentials show masked.

## Phase F — Operational safety

17. (YOU) Backups: schedule automated snapshots of the EBS volume AND/OR
    `pg_dump` the Postgres database on a cron to a separate location (e.g. S3).
    Test that you can actually restore — an untested backup is not a backup.
18. (YOU) Set up basic monitoring/alerting (even CloudWatch alarms on CPU/memory/disk).
19. (YOU) Document an incident process — who does what if something breaks.

## What's still pending in CODE before this is production-grade
- Caddy reverse-proxy + HTTPS config (Phase D)
- Job queue for scans (so concurrent Prowler runs don't tie up the app)
- Evidence-layer frontend (the API works; no UI yet)
- The login/navigation model + two-level user management
These don't block a careful single-or-few-partner pilot, but matter as you scale.

## Honest reminder
Hosting makes it reachable; it doesn't make it bug-free or compliant. Start with
ONE friendly partner on a sandbox/non-critical account, watch closely, and expand
only once it's behaving well.
