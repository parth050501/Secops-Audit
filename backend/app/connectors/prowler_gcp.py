"""
Prowler GCP Connector Adapter.
Runs `prowler gcp` against a real GCP project using a service-account JSON key,
then reuses the shared OCSF parser to produce GovernanceEvent dicts.

GCP auth (read-only) uses a service account key (JSON). The service account
needs read roles such as Viewer + Security Reviewer on the project/org.
"""
import os
import glob
import json
import tempfile
import subprocess
from typing import List

from app.connectors.prowler_aws import parse_prowler_ocsf


def run_prowler_gcp_scan(credentials: dict, tenant_id: int, connector_id: int) -> List[dict]:
    """
    Run Prowler against a GCP project.
    credentials should contain:
      - project_id            (GCP project to scan)
      - service_account_json  (the full JSON key, as a string)
    """
    creds = credentials or {}

    project_id = creds.get("project_id")
    sa_json = creds.get("service_account_json")

    if not sa_json:
        raise RuntimeError("Missing GCP service account JSON key")

    # Validate it's real JSON before writing it out
    try:
        if isinstance(sa_json, str):
            json.loads(sa_json)
            sa_content = sa_json
        else:
            sa_content = json.dumps(sa_json)
    except (ValueError, TypeError):
        raise RuntimeError("GCP service account key is not valid JSON")

    # Prowler reads the key from a file path via GOOGLE_APPLICATION_CREDENTIALS
    out_dir = tempfile.mkdtemp(prefix="prowler_gcp_")
    key_path = os.path.join(out_dir, "gcp_sa.json")
    with open(key_path, "w") as f:
        f.write(sa_content)
    os.chmod(key_path, 0o600)

    env = os.environ.copy()
    env["GOOGLE_APPLICATION_CREDENTIALS"] = key_path

    cmd = ["prowler", "gcp", "-M", "json-ocsf", "--output-directory", out_dir,
           "--ignore-exit-code-3", "--credentials-file", key_path]
    if project_id:
        cmd += ["--project-ids", project_id]

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, timeout=1800, check=False)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Prowler GCP scan timed out after 30 minutes")
    except FileNotFoundError:
        raise RuntimeError("Prowler is not installed in this environment")
    finally:
        # Remove the key file as soon as the scan is done — don't leave it on disk
        try:
            os.remove(key_path)
        except OSError:
            pass

    matches = glob.glob(os.path.join(out_dir, "*.ocsf.json"))
    if not matches:
        err = (result.stderr or b"").decode(errors="replace")[-500:]
        out = (result.stdout or b"").decode(errors="replace")[-300:]
        raise RuntimeError(
            f"Prowler GCP produced no output (exit {result.returncode}). "
            f"Check the service account key and its IAM roles (Viewer/Security Reviewer). "
            f"Details: {err or out}"
        )

    return parse_prowler_ocsf(matches[0], tenant_id, connector_id)
