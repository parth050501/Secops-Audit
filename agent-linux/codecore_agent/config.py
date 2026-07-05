"""
Configuration for the CodeCore Linux Agent.

The agent runs on an internal Linux system, performs read-only compliance scans
locally, and submits raw results to the collector (CCE) on the internal network.

Deploy inputs:
  COLLECTOR_URL   the collector's agent endpoint, e.g. http://10.0.0.10:8514
  ENROLL_SECRET   the shared secret to enroll with that collector (one time)
  AGENT_NAME      a label for this agent (defaults to the hostname)

After first enrollment the agent stores its issued token locally so it does not
re-enroll on every run.
"""
import os
import socket
import json
from dataclasses import dataclass

CONFIG_PATH = os.environ.get("AGENT_CONFIG", "/etc/codecore/agent.conf")
STATE_PATH = os.environ.get("AGENT_STATE", "/var/lib/codecore-agent/state.json")
VERSION = "0.1.0"


@dataclass
class AgentConfig:
    collector_url: str
    enroll_secret: str
    agent_name: str
    verify_tls: bool = True
    scan_systems: str = "linux"     # comma list: linux,postgres
    framework: str = ""             # optional framework hint

    def masked_secret(self) -> str:
        if not self.enroll_secret or len(self.enroll_secret) < 6:
            return "****"
        return self.enroll_secret[:3] + "…"


def load_config() -> AgentConfig:
    import configparser
    collector_url = os.environ.get("COLLECTOR_URL")
    enroll_secret = os.environ.get("ENROLL_SECRET")
    agent_name = os.environ.get("AGENT_NAME")
    verify = os.environ.get("VERIFY_TLS")
    scan_systems = os.environ.get("SCAN_SYSTEMS")
    framework = os.environ.get("FRAMEWORK")

    if os.path.exists(CONFIG_PATH):
        parser = configparser.ConfigParser()
        parser.read(CONFIG_PATH)
        if parser.has_section("agent"):
            sec = parser["agent"]
            collector_url = collector_url or sec.get("collector_url")
            enroll_secret = enroll_secret or sec.get("enroll_secret")
            agent_name = agent_name or sec.get("agent_name")
            verify = verify or sec.get("verify_tls")
            scan_systems = scan_systems or sec.get("scan_systems")
            framework = framework or sec.get("framework")

    missing = []
    if not collector_url:
        missing.append("COLLECTOR_URL")
    if not enroll_secret:
        missing.append("ENROLL_SECRET")
    if missing:
        raise SystemExit(
            "Missing required configuration: " + ", ".join(missing) + ".\n"
            "Set them as environment variables or in " + CONFIG_PATH + " under [agent].\n"
            "COLLECTOR_URL is the collector's agent endpoint (e.g. http://10.0.0.10:8514); "
            "ENROLL_SECRET is the shared secret configured on that collector."
        )

    return AgentConfig(
        collector_url=collector_url.rstrip("/"),
        enroll_secret=enroll_secret,
        agent_name=agent_name or socket.gethostname(),
        verify_tls=(str(verify).lower() not in ("0", "false", "no")) if verify is not None else True,
        scan_systems=scan_systems or "linux",
        framework=framework or "",
    )


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                return json.load(f)
        except (ValueError, OSError):
            return {}
    return {}


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f)
    os.chmod(STATE_PATH, 0o600)   # token inside — restrict
