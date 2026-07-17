from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    id         = Column(Integer, primary_key=True)
    email      = Column(String, unique=True, nullable=False)
    name       = Column(String, nullable=False)
    role       = Column(String, default="engineer")  # admin|engineer|manager|auditor
    hashed_pw  = Column(String, nullable=False)
    tenant_id  = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
