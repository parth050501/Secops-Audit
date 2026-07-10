"""
On-prem collector / agent foundation models.

Architecture (decided with the team):
  Agent (runs scanners on/near a system)  →  Collector/CCE (thin relay inside the
  customer network, the single outbound egress)  →  APE (this platform).

Security model: a Collector is bound to ONE tenant via a token issued at
registration. The platform DERIVES the tenant from the token on every request —
a collector can never *claim* a tenant. This is the same isolation principle as
tenant_guard: the boundary is enforced server-side from the credential, never
trusted from the caller. A collector for tenant A can therefore never submit
data, poll jobs, or appear for tenant B.

The collector is intentionally "dumb": it relays raw scan output tagged with a
type. ALL parsing/mapping lives in the APE (reusing the existing connector
parsers), so changing compliance logic never requires updating deployed
collectors.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from datetime import datetime, timedelta
from app.core.database import Base

# A collector is considered "disconnected" if it hasn't checked in within this
# window (matches the agreed ~5 minute heartbeat tolerance).
HEARTBEAT_TIMEOUT_SECONDS = 300


class Collector(Base):
    """A customer-side collection engine (CCE). One tenant may have several."""
    __tablename__ = "collectors"
    id           = Column(Integer, primary_key=True)
    tenant_id    = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name         = Column(String, nullable=False)          # e.g. "NTIPLCCE1" (display only)
    token_hash   = Column(String, nullable=False, index=True)  # bcrypt hash of the registration token
    token_prefix = Column(String)                          # first chars, for display/identification
    status       = Column(String, default="pending")       # pending | connected | disconnected
    last_seen    = Column(DateTime)
    version      = Column(String)                          # collector software version (reported)
    created_by   = Column(String)                          # which platform admin registered it
    created_at   = Column(DateTime, default=datetime.utcnow)

    def derived_status(self) -> str:
        """Status from last_seen — 'connected' only if seen within the timeout."""
        if not self.last_seen:
            return "pending"
        if (datetime.utcnow() - self.last_seen).total_seconds() <= HEARTBEAT_TIMEOUT_SECONDS:
            return "connected"
        return "disconnected"


class Agent(Base):
    """An agent reporting through a collector. Scans a specific target/system."""
    __tablename__ = "agents"
    id           = Column(Integer, primary_key=True)
    tenant_id    = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    collector_id = Column(Integer, ForeignKey("collectors.id"), nullable=False, index=True)
    name         = Column(String, nullable=False)          # e.g. "app-server-01"
    system_type  = Column(String, nullable=False)          # linux | windows_server | postgres | paloalto | ...
    target       = Column(String)                          # host/identifier it scans
    schedule     = Column(String, default="daily")         # daily | weekly | manual (agent-held schedule)
    status       = Column(String, default="pending")
    last_seen    = Column(DateTime)
    last_scan_at = Column(DateTime)                        # when it last submitted results
    last_result  = Column(String)                          # short summary e.g. "5 findings"
    created_at   = Column(DateTime, default=datetime.utcnow)

    def derived_status(self) -> str:
        if not self.last_seen:
            return "pending"
        if (datetime.utcnow() - self.last_seen).total_seconds() <= HEARTBEAT_TIMEOUT_SECONDS:
            return "connected"
        return "disconnected"


class ScanJob(Base):
    """A unit of work for the collector/agent to perform.

    Created either on-demand ("Scan Now") or by the scheduler. The collector
    polls for pending jobs for its tenant, the agent runs the scan, and results
    flow back via the ingestion endpoint referencing this job.
    """
    __tablename__ = "scan_jobs"
    id           = Column(Integer, primary_key=True)
    tenant_id    = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    collector_id = Column(Integer, ForeignKey("collectors.id"), index=True)
    agent_id     = Column(Integer, ForeignKey("agents.id"), index=True)
    system_type  = Column(String, nullable=False)          # what scanner to run
    target       = Column(String)                          # what to scan
    framework    = Column(String)                          # framework hint for mapping
    status       = Column(String, default="pending")       # pending | dispatched | running | done | error
    origin       = Column(String, default="on_demand")     # on_demand | scheduled
    created_at   = Column(DateTime, default=datetime.utcnow)
    dispatched_at= Column(DateTime)
    completed_at = Column(DateTime)
    error        = Column(Text)
    findings_count = Column(Integer)


class AssetGroup(Base):
    """A tenant-defined group of agents ("assets") the customer creates and names
    themselves — e.g. "Production Servers", "PCI Environment", "Mumbai DC".
    Used to schedule scans and run group-wide "Scan Now" across many agents at once.

    Membership is stored as a list of agent ids (JSON) — simple and flexible; an
    agent can belong to more than one group.
    """
    __tablename__ = "asset_groups"
    id           = Column(Integer, primary_key=True)
    tenant_id    = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name         = Column(String, nullable=False)          # customer-chosen, anything
    description  = Column(String)
    agent_ids    = Column(JSON, default=list)              # [agent_id, ...] membership

    # Schedule (stage two will act on these; stored now so the UI is real)
    schedule     = Column(String, default="manual")        # manual | daily | weekly | monthly
    schedule_time= Column(String, default="02:00")         # HH:MM (tenant local, informational)
    schedule_day = Column(String)                          # weekly: Mon..Sun ; monthly: 1..28
    last_run_at  = Column(DateTime)
    next_run_at  = Column(DateTime)

    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
