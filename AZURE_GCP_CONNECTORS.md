# Azure & GCP Connectors — Testing Guide

Both follow the proven AWS/Prowler pattern. Build the app (Prowler is in the
container), then add each connector with the right read-only credentials.

## Azure
Prowler needs a service principal (app registration) with read access.

Setup in Azure (your side):
1. Azure AD → App registrations → New registration → note the Application (client) ID
   and Directory (tenant) ID
2. Certificates & secrets → New client secret → copy the secret value
3. Subscriptions → your subscription → Access control (IAM) → add role assignments:
   - "Reader"
   - "Security Reader"
   assigned to the app registration
4. Note your Subscription ID

In the app: Connectors → Add → Azure, enter:
- tenant_id, client_id, client_secret, subscription_id

## GCP
Prowler needs a service account key (JSON) with read roles.

Setup in GCP (your side):
1. IAM & Admin → Service Accounts → Create service account
2. Grant roles: "Viewer" and "Security Reviewer" (project or org level)
3. Keys → Add key → JSON → download the key file
4. Note your Project ID

In the app: Connectors → Add → GCP, enter:
- project_id
- service_account_json  (paste the FULL contents of the JSON key file)

## Notes
- First scans take longer than AWS (Azure/GCP have many checks). Be patient.
- If a scan fails, the connector shows status "error" with the reason — usually
  missing roles or wrong credentials. The error text comes straight from Prowler.
- The GCP service-account key is written to a temp file only for the scan duration
  and deleted immediately after — it's never persisted to disk beyond the scan.
- Credentials are encrypted at rest (same as AWS).

## Dedup improvement (this build)
Findings are now deduplicated by check + resource, with framework mappings MERGED
across duplicates. The same finding no longer appears multiple times — it shows once
with all its framework control IDs combined and the highest severity kept.
