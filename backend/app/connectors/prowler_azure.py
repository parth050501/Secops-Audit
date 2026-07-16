"""
Prowler Azure Connector Adapter.
Runs `prowler azure` against a real Azure subscription using service-principal
credentials (app registration), then reuses the shared OCSF parser to produce
GovernanceEvent dicts — same shape as the AWS connector.

Azure auth (read-only) uses a service principal:
  - tenant_id, client_id, client_secret, subscription_id
The app registration needs the "Reader" role + "Security Reader" on the subscription.
"""
import os
import glob
import tempfile
import subprocess
from typing import List

# Reuse the provider-agnostic OCSF parser from the AWS adapter
from app.connectors.prowler_aws import parse_prowler_ocsf


def run_prowler_azure_scan(credentials: dict, tenant_id: int, connector_id: int) -> List[dict]:
    """
    Run Prowler against an Azure subscription.
    credentials should contain:
      - tenant_id        (Azure AD tenant / directory ID)
      - client_id        (app registration application ID)
      - client_secret    (app registration secret)
      - subscription_id  (subscription to scan)
    """
    creds = credentials or {}
    env = os.environ.copy()

    # Prowler reads Azure SP creds from these standard env vars
    az_tenant = creds.get("tenant_id")
    client_id = creds.get("client_id")
    client_secret = creds.get("client_secret")
    subscription_id = creds.get("subscription_id")

    missing = [k for k in ("tenant_id", "client_id", "client_secret")
               if not creds.get(k)]
    if missing:
        raise RuntimeError(f"Missing Azure credentials: {', '.join(missing)}")

    env["AZURE_TENANT_ID"] = az_tenant
    env["AZURE_CLIENT_ID"] = client_id
    env["AZURE_CLIENT_SECRET"] = client_secret

    out_dir = tempfile.mkdtemp(prefix="prowler_azure_")
    cmd = ["prowler", "azure", "-M", "json-ocsf", "--output-directory", out_dir,
           "--ignore-exit-code-3", "--sp-env-auth"]
    # Scope to a subscription if provided (faster, more predictable)
    if subscription_id:
        cmd += ["--subscription-ids", subscription_id]

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, timeout=1800, check=False)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Prowler Azure scan timed out after 30 minutes")
    except FileNotFoundError:
        raise RuntimeError("Prowler is not installed in this environment")

    matches = glob.glob(os.path.join(out_dir, "*.ocsf.json"))
    if not matches:
        err = (result.stderr or b"").decode(errors="replace")[-500:]
        out = (result.stdout or b"").decode(errors="replace")[-300:]
        raise RuntimeError(
            f"Prowler Azure produced no output (exit {result.returncode}). "
            f"Check service-principal credentials and Reader/Security Reader roles. "
            f"Details: {err or out}"
        )

    return parse_prowler_ocsf(matches[0], tenant_id, connector_id)
