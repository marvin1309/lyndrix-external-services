"""
models.py — SQLAlchemy persistence model for external service registrations.
"""
from sqlalchemy import Column, Integer, String, Boolean

from core.components.database.logic.db_service import Base


class ExternalService(Base):
    __tablename__ = "external_services"

    id = Column(Integer, primary_key=True, index=True)
    # URL-safe path segment used for /external/<slug>
    slug = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500), default="")
    icon = Column(String(100), default="open_in_browser")
    url = Column(String(1000), nullable=False)
    # Type of integration: "iframe" | future: "embed", "proxy", ...
    service_type = Column(String(50), default="iframe")
    # How the service is opened:
    #   "iframe"   — embedded full-screen inside Lyndrix (default)
    #   "new_tab"  — clicking opens the URL directly in a new browser tab
    #                (use this for services that block embedding via X-Frame-Options / CSP)
    open_mode = Column(String(20), default="iframe")
    # Whether this service gets its own sidebar entry
    show_in_nav = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)
