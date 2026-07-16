# Connecting a Real AWS Account (Prowler)

The AWS connector is now **real** — it runs Prowler against your AWS account and
ingests actual findings, mapped to your compliance frameworks. All other connector
types still use the simulator until built out.

## How it works
1. You add an AWS connector and enter read-only credentials (Access Key or IAM Role)
2. The backend runs `prowler aws` against that account
3. Prowler's findings (failed checks) are parsed from its OCSF JSON output
4. Each becomes a GovernanceEvent, mapped to PCI / SOC2 / ISO 27001 / HIPAA / NIST
   using Prowler's own compliance tags
5. Everything downstream — control mapping, tickets, reports — works unchanged

## Prerequisites
- A read-only AWS IAM user/role with `SecurityAudit` + `ViewOnlyAccess` policies
- An access key for that user

## Two ways to run

### Option A — Prowler inside the backend container (production-like)
Add Prowler to the image. It's already in requirements.txt. Rebuild:
```
docker compose up --build -d
```
Note: this makes the image larger and the build slower (~2-3 min extra).
Then add an AWS connector in the UI with your access key + secret.

### Option B — Prowler on the host (faster for dev)
If you'd rather not bloat the container, run the backend outside Docker for AWS
testing, with Prowler installed locally (you already have it):
```
cd backend
pip install -r requirements.txt
ENVIRONMENT=qc JWT_SECRET=dev uvicorn app.main:app --port 8000
```
The adapter calls the `prowler` CLI, which it finds on your PATH.

## Important behavior notes
- **A scan takes 5-7 minutes** (Prowler runs ~600 checks). The connector shows
  status "scanning" during this time, then flips to "connected" with events loaded.
- **Re-scanning** clears prior OPEN findings from that connector and replaces them
  with the current state. Findings you've already turned into tickets are preserved.
- If credentials are wrong or Prowler fails, the connector shows status "error"
  with the reason in last_error.
- Credentials are stored in the connector's `credentials` JSON field. **In production
  this must be encrypted at rest** (see production checklist) — right now it's plaintext,
  fine for local dev only.

## Scoping a scan (optional, faster)
Enter specific regions in the connector form (e.g. `us-east-1`) to limit the scan
scope and speed it up, instead of scanning all regions.

## Next connectors
The same pattern applies to the others:
- Azure / GCP → Prowler supports these too (`prowler azure`, `prowler gcp`)
- Linux servers → Lynis or OpenSCAP
- Kubernetes → Trivy / Kubescape
Each is a new adapter following `prowler_aws.py` as the template.
