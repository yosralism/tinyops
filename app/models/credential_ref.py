"""Credential Reference model for storing environment variable mappings."""

from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from app.db.base import Base


class CredentialReference(Base):
    """
    Reference to credentials stored in environment variables.
    
    Instead of storing actual credentials in the database, we store
    references to environment variable names. The actual secrets are
    retrieved from the environment at runtime.
    """
    
    __tablename__ = "credential_references"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    
    # Environment variable names (not the actual values!)
    username_env_var = Column(String(255), nullable=False)
    password_env_var = Column(String(255), nullable=True)
    ssh_key_env_var = Column(String(255), nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
