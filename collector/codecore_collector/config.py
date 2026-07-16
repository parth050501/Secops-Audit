"""
Configuration for the CodeCore Collector Engine.

Two required inputs at deploy time:
  - APE_URL          : where the platform lives (e.g. https://qc.codecoresystems.in)
  - COLLECTOR_TOKEN  : the secret enrollment token (issued when the collector was
                       registered in the platform console for a specific tenant).
                       The token determines the tenant — the collector never
                       asserts a tenant id itself.

Config is read from environment variables first (clean for Docker), falling back
to a config file at CONFIG_PATH (default /etc/codecore/collector.conf, an
INI-style file). The token is treated as a secret: it is never logged.
"""
import os
import configparser
from dataclasses import dataclass

CONFIG_PATH = os.environ.get("COLLECTOR_CONFIG", "/etc/codecore/collector.conf")
DEFAULT_POLL_INTERVAL = 60        # seconds between job polls
DEFAULT_HEARTBEAT_INTERVAL = 60   # seconds between heartbeats
VERSION = "0.1.0"


@dataclass
class CollectorConfig:
    ape_url: str
    token: str
    poll_interval: int = DEFAULT_POLL_INTERVAL
    heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL
    verify_tls: bool = True          # verify the APE's TLS cert (keep True in prod)
    queue_path: str = "/var/lib/codecore/queue.db"
    agent_db_path: str = "/var/lib/codecore/agents.db"   # agent registry
    inbound_host: str = "0.0.0.0"    # agent-facing server bind (internal network)
    inbound_port: int = 8514
    enroll_secret: str = ""          # shared secret agents present to enroll

    def masked_token(self) -> str:
        """For safe display/logging — never log the full token."""
        if not self.token or len(self.token) < 12:
            return "****"
        return self.token[:8] + "…" + self.token[-2:]


def load_config() -> CollectorConfig:
    ape_url = os.environ.get("APE_URL")
    token = os.environ.get("COLLECTOR_TOKEN")
    poll = os.environ.get("POLL_INTERVAL")
    hb = os.environ.get("HEARTBEAT_INTERVAL")
    verify = os.environ.get("VERIFY_TLS")
    queue = os.environ.get("QUEUE_PATH")
    agent_db = os.environ.get("AGENT_DB_PATH")
    inbound_host = os.environ.get("INBOUND_HOST")
    inbound_port = os.environ.get("INBOUND_PORT")
    enroll_secret = os.environ.get("ENROLL_SECRET")

    # Fall back to config file for anything not set via env
    if os.path.exists(CONFIG_PATH):
        parser = configparser.ConfigParser()
        parser.read(CONFIG_PATH)
        if parser.has_section("collector"):
            sec = parser["collector"]
            ape_url = ape_url or sec.get("ape_url")
            token = token or sec.get("token")
            poll = poll or sec.get("poll_interval")
            hb = hb or sec.get("heartbeat_interval")
            verify = verify or sec.get("verify_tls")
            queue = queue or sec.get("queue_path")
            agent_db = agent_db or sec.get("agent_db_path")
            inbound_host = inbound_host or sec.get("inbound_host")
            inbound_port = inbound_port or sec.get("inbound_port")
            enroll_secret = enroll_secret or sec.get("enroll_secret")

    missing = []
    if not ape_url:
        missing.append("APE_URL")
    if not token:
        missing.append("COLLECTOR_TOKEN")
    if missing:
        raise SystemExit(
            "Missing required configuration: " + ", ".join(missing) + ".\n"
            "Set them as environment variables, or in " + CONFIG_PATH + " under [collector].\n"
            "Get the token from the CodeCore platform console when you register this collector."
        )

    ape_url = ape_url.rstrip("/")
    return CollectorConfig(
        ape_url=ape_url,
        token=token,
        poll_interval=int(poll) if poll else DEFAULT_POLL_INTERVAL,
        heartbeat_interval=int(hb) if hb else DEFAULT_HEARTBEAT_INTERVAL,
        verify_tls=(str(verify).lower() not in ("0", "false", "no")) if verify is not None else True,
        queue_path=queue or "/var/lib/codecore/queue.db",
        agent_db_path=agent_db or "/var/lib/codecore/agents.db",
        inbound_host=inbound_host or "0.0.0.0",
        inbound_port=int(inbound_port) if inbound_port else 8514,
        enroll_secret=enroll_secret or "",
    )
