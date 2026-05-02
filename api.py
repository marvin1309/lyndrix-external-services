"""
api.py — FastAPI REST endpoints for External Services CRUD.

Endpoints:
  GET    /api/external-services/         — list all
  POST   /api/external-services/         — create / upsert by slug
  PUT    /api/external-services/{id}     — update fields
  DELETE /api/external-services/{id}     — remove
  POST   /api/external-services/reload   — re-scan DB and refresh nav/routes

Callers (e.g. lyndrix-iac-orchestrator) POST a payload like:
  {
    "service": "homeassistant",
    "name":    "Home-Assistant",
    "icon":    "home",
    "url":     "https://smart-home.int.example.com",
    "type":    "iframe",
    "route":   "smart-home"
  }
"""
import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .service import ext_service_manager


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9-]", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "service"


def _to_dict(svc) -> dict:
    return {
        "id": svc.id,
        "slug": svc.slug,
        "name": svc.name,
        "description": svc.description,
        "icon": svc.icon,
        "url": svc.url,
        "type": svc.service_type,
        "open_mode": getattr(svc, "open_mode", "iframe") or "iframe",
        "show_in_nav": svc.show_in_nav,
        "enabled": svc.enabled,
        "route": f"/external/{svc.slug}",
    }


class ServiceCreate(BaseModel):
    """Matches the payload format the IAC orchestrator (and others) send."""
    service: str                     # used as slug fallback
    name: str
    icon: str = "open_in_browser"
    url: str
    type: str = "iframe"
    route: Optional[str] = None      # explicit slug override
    # How to open the service:
    #   "iframe"   — embedded inside Lyndrix (default)
    #   "new_tab"  — opens in a new browser tab (for services that block embedding)
    open_mode: str = "iframe"
    show_in_nav: bool = True
    description: str = ""
    enabled: bool = True


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    url: Optional[str] = None
    type: Optional[str] = None
    open_mode: Optional[str] = None
    show_in_nav: Optional[bool] = None
    enabled: Optional[bool] = None


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/external-services", tags=["External Services"])

    @router.get("/")
    def list_services():
        return [_to_dict(s) for s in ext_service_manager.get_all()]

    @router.post("/", status_code=201)
    def create_service(data: ServiceCreate):
        slug = _slugify(data.route or data.service)
        try:
            svc = ext_service_manager.upsert(
                slug=slug,
                name=data.name,
                url=data.url,
                icon=data.icon,
                service_type=data.type,
                open_mode=data.open_mode,
                show_in_nav=data.show_in_nav,
                description=data.description,
                enabled=data.enabled,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        # Register route + sidebar entry immediately without restart
        _refresh_service(svc)
        return _to_dict(svc)

    @router.put("/{service_id}")
    def update_service(service_id: int, data: ServiceUpdate):
        updates = {k: v for k, v in data.dict().items() if v is not None}
        if not ext_service_manager.update(service_id, **updates):
            raise HTTPException(status_code=404, detail="Service not found")

        svc = ext_service_manager.get_by_id(service_id)
        if svc:
            _refresh_service(svc)
        return {"ok": True}

    @router.delete("/{service_id}")
    def delete_service(service_id: int):
        svc = ext_service_manager.get_by_id(service_id)
        if not svc:
            raise HTTPException(status_code=404, detail="Service not found")
        slug = svc.slug
        if not ext_service_manager.delete(service_id):
            raise HTTPException(status_code=404, detail="Service not found")
        _remove_service(slug)
        return {"ok": True}

    @router.post("/reload")
    def reload_services():
        """Re-scan DB and register any services that are not yet wired up."""
        services = ext_service_manager.get_enabled()
        from .routing import register_all
        register_all(services)
        return {"registered": len(services)}

    return router


def _refresh_service(svc) -> None:
    """Register (or re-register) route + nav for a service after create/update."""
    try:
        from .routing import register_service, remove_service, _registered_slugs
        # If slug already registered, remove first so it can be re-evaluated
        if svc.slug in _registered_slugs:
            remove_service(svc.slug)
        if svc.enabled:
            register_service(svc)
    except Exception:
        pass  # non-critical — takes effect on next startup


def _remove_service(slug: str) -> None:
    try:
        from .routing import remove_service
        remove_service(slug)
    except Exception:
        pass
