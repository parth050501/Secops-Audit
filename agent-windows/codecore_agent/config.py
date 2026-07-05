"""
Configuration for the CodeCore Windows Agent.

Runs on an internal Windows system, performs the read-only PowerShell compliance
assessment locally, and submits raw results to the collector (CCE).

Deploy inputs (environment variables or C:\ProgramData\CodeCore\agent.conf):
  COLLECTOR_URL   the collector's agent endpoint, e.g. http://10.0.0.10:8514
  ENROLL_SECRET   the shared secret to enroll with that collector
  AGENT_NAME      label for this agent (defaults to the hostname)
"""
import os
import socket
import json
from dataclasses import dataclass

CONFIG_PATH = os.environ.get("AGENT_CONFIG", r"C:\ProgramData\CodeCore\agent.conf")
STATE_PATH = os.environ.get("AGENT_STATE", r"C:\ProgramData\CodeCore\state.json")
VERSION = "0.1.0"


@dataclass
class AgentConfig:
    collector_url: str
    enroll_secret: str
    agent_name: str
    verify_tls: bool = True
    framework: str = ""
    ps_script: str = "secops-win-assess.ps1"


def load_config() -> AgentConfig:
    import configparser
    collector_url = os.environ.get("COLLECTOR_URL")
    enroll_secret = os.environ.get("ENROLL_SECRET")
    agent_name = os.environ.get("AGENT_NAME")
    verify = os.environ.get("VERIFY_TLS")
    framework = os.environ.get("FRAMEWORK")
    ps_script = os.environ.get("PS_SCRIPT")

    if os.path.exists(CONFIG_PATH):
        parser = configparser.ConfigParser()
        parser.read(CONFIG_PATH)
        if parser.has_section("agent"):
            sec = parser["agent"]
            collector_url = collector_url or sec.get("collector_url")
            enroll_secret = enroll_secret or sec.get("enroll_secret")
            agent_name = agent_name or sec.get("agent_name")
            verify = verify or sec.get("verify_tls")
            framework = framework or sec.get("framework")
            ps_script = ps_script or sec.get("ps_script")

    missing = []
    if not collector_url: missing.append("COLLECTOR_URL")
    if not enroll_secret: missing.append("ENROLL_SECRET")
    if missing:
        raise SystemExit("Missing required configuration: " + ", ".join(missing) +
                         ". Set as environment variables or in " + CONFIG_PATH + " under [agent].")

    return AgentConfig(
        collector_url=collector_url.rstrip("/"),
        enroll_secret=enroll_secret,
        agent_name=agent_name or socket.gethostname(),
        verify_tls=(str(verify).lower() not in ("0","false","no")) if verify is not None else True,
        framework=framework or "",
        ps_script=ps_script or "secops-win-assess.ps1",
    )


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f: return json.load(f)
        except (ValueError, OSError): return {}
    return {}


def save_state(state: dict):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f: json.dump(state, f)
