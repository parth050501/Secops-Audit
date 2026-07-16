from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Text, ForeignKey
from datetime import datetime
from app.core.database import Base

class Connector(Base):
    __tablename__ = "connectors"
    id           = Column(Integer, primary_key=True)
    tenant_id    = Column(Integer, ForeignKey("tenants.id"))
    name         = Column(String, nullable=False)
    # Category: network|server|cloud|identity|application|database|endpoint
    category     = Column(String, nullable=False)
    # Type: paloalto|fortinet|windows_server|linux|aws|azure|gcp|active_directory
    #        okta|splunk|sentinel|crowdstrike|custom_api|syslog|sql_server|postgres
    connector_type = Column(String, nullable=False)
    host         = Column(String)        # IP or hostname
    port         = Column(Integer)
    credentials  = Column(JSON)          # encrypted in prod; {api_key, username, token...}
    collection_mode = Column(String, default="polling")  # polling|webhook|agent|syslog
    poll_interval_sec = Column(Integer, default=300)     # for polling
    status       = Column(String, default="pending")     # pending|connected|error|disabled
    last_seen    = Column(DateTime)
    last_error   = Column(Text)
    metadata_    = Column("metadata", JSON, default=dict)  # vendor-specific extras
    realtime     = Column(Boolean, default=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
