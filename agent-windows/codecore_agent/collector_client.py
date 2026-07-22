"""
Client for talking to the collector (CCE) from the agent.

  POST /agent/enroll   {name, system_type, enroll_secret} -> {agent_token}
  POST /agent/results  (Bearer agent_token) {system_type, raw_data, ...} -> ok
"""
import logging
import requests

log = logging.getLogger("agent.collector")


class CollectorUnreachable(Exception):
    pass


class CollectorAuthError(Exception):
    pass


class CollectorClient:
    def __init__(self, base_url: str, verify_tls: bool = True, version: str = "0.1.0"):
        self.base_url = base_url.rstrip("/")
        self.verify_tls = verify_tls
        self.version = version
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": f"CodeCoreAgent/{version}"})

    def enroll(self, name: str, system_type: str, enroll_secret: str) -> str:
        try:
            r = self._session.post(
                f"{self.base_url}/agent/enroll",
                json={"name": name, "system_type": system_type, "enroll_secret": enroll_secret},
                timeout=30, verify=self.verify_tls,
            )
        except requests.RequestException as e:
            raise CollectorUnreachable(str(e))
        if r.status_code == 401:
            raise CollectorAuthError("Collector rejected the enroll secret")
        if r.status_code != 200:
            raise CollectorUnreachable(f"enroll failed: {r.status_code} {r.text[:200]}")
        return r.json()["agent_token"]

    def submit(self, agent_token: str, system_type: str, raw_data,
               target=None, framework=None):
        payload = {"system_type": system_type, "raw_data": raw_data}
        if target:
            payload["target"] = target
        if framework:
            payload["framework"] = framework
        try:
            r = self._session.post(
                f"{self.base_url}/agent/results",
                headers={"Authorization": f"Bearer {agent_token}"},
                json=payload, timeout=60, verify=self.verify_tls,
            )
        except requests.RequestException as e:
            raise CollectorUnreachable(str(e))
        if r.status_code == 401:
            raise CollectorAuthError("Collector rejected the agent token")
        if r.status_code != 200:
            raise CollectorUnreachable(f"submit failed: {r.status_code} {r.text[:200]}")
        return r.json()
