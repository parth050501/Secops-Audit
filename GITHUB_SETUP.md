# GitHub Setup & Workflow

A single monorepo containing both backend and frontend. Recommended for a
project this size — one place to version everything together.

## First-time setup (today)

From the project root (the folder containing `backend/`, `frontend/`, `.gitignore`):

```bash
git init
git add .
git status            # REVIEW before committing — confirm no .env or *.db listed
git commit -m "Initial commit: Code Core Systems compliance platform + security fixes"
git branch -M main
git remote add origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Before that very first commit — verify nothing secret is staged
```bash
git status
```
You should NOT see: `.env`, any `*.db`, `node_modules/`, `.next/`, service-account
JSON, or `*.ocsf.json`. The `.gitignore` excludes all of these. If you see a `.env`
listed, STOP and check — never commit real secrets.

## Ongoing workflow (each phase)

When I deliver a set of changes, I'll give you the changed files + notes. Then:
```bash
# apply the changed files into your local repo, then:
git add .
git commit -m "Phase: <what changed>"
git push
```

On the server, to deploy updates without rebuilding everything from scratch:
```bash
git pull
# rebuild only what changed:
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d backend
# or 'frontend', or both
```

## Important rules

1. **Never commit `.env`.** Only `.env.example` (no real values) belongs in git.
2. **Never commit secrets** — the encryption key, JWT secret, DB password,
   cloud credentials, service-account JSON. All are gitignored, but double-check.
3. If you ever accidentally commit a secret, rotate it immediately — removing it
   from a later commit does NOT remove it from git history.
4. Keep `.env.example` updated when new env vars are introduced, so anyone
   cloning knows what to set.

## Branching (optional, recommended as you grow)
- `main` — stable, deployable
- feature branches per phase (`feature/job-queue`, `feature/user-mgmt-ui`),
  merged into main when tested. Lets you keep main always-deployable.
