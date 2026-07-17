"""
Client for talking to the CodeCore platform (APE).

Wraps the collector-facing endpoints:
  POST /api/collector/heartbeat
  GET  /api/collector/jobs
  POST /api/collector/results

Auth is the bearer token. The token determines the tenant server-side; this
client never sends a tenant id. All calls go over HTTPS (TLS verified by
default). Network errors are surfaced as ApeUnreachable so callers can back off
and retry rather than crash.
"""
import logging
import requests

log = logging.getLogger("collector.ape")


class ApeUnreachable(Exception):
    pass


class ApeAuthError(Exception):
    pass


class ApeClient:
    def __init__(self, base_url: str, token: str, verify_tls: bool = True, version: str = "0.1.0"):
        self.base_url = base_url.rstrip("/")
        self._token = token
        self.verify_tls = verify_tls
        self.version = version
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {token}",
            "User-Agent": f"CodeCoreCollector/{version}",
        })

    def _post(self, path, json=None, timeout=30):
        url = f"{self.base_url}{path}"
        try:
            r = self._session.post(url, json=json, timeout=timeout, verify=self.verify_tls)
        except requests.RequestException as e:
            raise ApeUnreachable(str(e))
        if r.status_code == 401:
            raise ApeAuthError("Invalid or rejected collector token")
        return r

    def _get(self, path, timeout=30):
        url = f"{self.base_url}{path}"
        try:
            r = self._session.get(url, timeout=timeout, verify=self.verify_tls)
        except requests.RequestException as e:
            raise ApeUnreachable(str(e))
        if r.status_code == 401:
            raise ApeAuthError("Invalid or rejected collector token")
        return r

    def heartbeat(self):
        """Enroll/liveness. Returns the server response (which confirms tenant)."""
        r = self._post("/api/collector/heartbeat", json={"version": self.version})
        if r.status_code != 200:
            raise ApeUnreachable(f"heartbeat failed: {r.status_code}")
        return r.json()

    def poll_jobs(self):
        r = self._get("/api/collector/jobs")
        if r.status_code != 200:
            raise ApeUnreachable(f"poll failed: {r.status_code}")
        return r.json().get("jobs", [])

    def submit_result(self, system_type, raw_data, job_id=None, target=None, framework=None):
        import json as _json
        # raw_data may be a JSON string (from the queue) or a dict/str
        if isinstance(raw_data, str):
            try:
                parsed = _json.loads(raw_data)
            except ValueError:
                parsed = raw_data   # genuine raw string (e.g. XML config)
        else:
            parsed = raw_data
        payload = {"system_type": system_type, "raw_data": parsed}
        if job_id is not None:
            payload["job_id"] = job_id
        if target:
            payload["target"] = target
        if framework:
            payload["framework"] = framework
        r = self._post("/api/collector/results", json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            # job no longer valid — treat as a permanent failure for this item
            raise ValueError("job not found / not for this collector")
        raise ApeUnreachable(f"submit failed: {r.status_code} {r.text[:200]}")
