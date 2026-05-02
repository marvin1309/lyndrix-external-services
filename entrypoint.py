"""
entrypoint.py — lyndrix-external-services plugin entry point.

Integrates external web services into Lyndrix by:
  • Persisting service definitions in the DB (external_services table)
  • Registering a NiceGUI page per service at /external/<slug>
  • Injecting virtual manifest entries so each service appears in the sidebar
  • Exposing a REST API at /api/external-services/ for CRUD and remote registration
  • Listening on the event bus topic "external_services:register" for in-process
    registration (e.g. from lyndrix-iac-orchestrator)

Event bus payload format:
  {
    "service":     "homeassistant",          # used as slug if no 'route'
    "name":        "Home-Assistant",
    "icon":        "home",
    "url":         "https://example.com",
    "type":        "iframe",
    "route":       "smart-home",             # optional explicit slug
    "show_in_nav": true,
    "description": "",
    "enabled":     true
  }
"""
import asyncio

from nicegui import app as nicegui_app, ui

from core.components.plugins.logic.models import ModuleManifest

from .service import ext_service_manager
from .routing import set_context, register_all, register_service
from .ui_overview import render_overview_ui as _render_overview_ui
from .ui_settings import render_settings_ui as _render_settings_ui

try:
    from ui.layout import main_layout
except ImportError:
    def main_layout(title):  # type: ignore
        def decorator(fn):
            return fn
        return decorator


# ── Manifest ──────────────────────────────────────────────────────────────────

manifest = ModuleManifest(
    id="lyndrix.plugin.external_services",
    name="External Services",
    version="0.0.1",
    description="Embed external web services (Home Assistant, Grafana, …) via iframe.",
    author="Lyndrix",
    icon="public",
    type="PLUGIN",
    min_core_version="0.0.1",
    auto_enable_on_install=True,
    repo_url="https://github.com/lyndrix-dev/lyndrix-external-services",
    ui_route="/external",
    permissions={
        "subscribe": ["db:connected", "external_services:register"],
        "emit": [],
    },
)

# ── Plugin state ──────────────────────────────────────────────────────────────

plugin_state: dict = {"ready": False}


# ── Public plugin API ─────────────────────────────────────────────────────────

def render_overview_ui(ctx):
    _render_overview_ui(ctx)


def render_settings_ui(ctx):
    _render_settings_ui(ctx)


def render_dashboard_widget(ctx):
    """Compact widget for the dashboard — shows count + quick link."""
    services = ext_service_manager.get_enabled()
    with ui.row().classes("items-center gap-2"):
        ui.icon("public", size="16px").classes("text-sky-400")
        ui.label(f"{len(services)} externe Service(s) aktiv").classes(
            "text-xs text-zinc-400"
        )
        if services:
            ui.button(
                "Übersicht",
                icon="arrow_forward",
                on_click=lambda: ui.navigate.to("/external"),
            ).props("flat dense size=xs").classes("text-sky-400")


# ── Setup ─────────────────────────────────────────────────────────────────────

def setup(ctx):
    ctx.log.info("External Services: starting setup...")

    # 1. Create DB table
    ext_service_manager.ensure_table()

    # 2. Wire routing context
    set_context(ctx)

    # 3. Register routes + sidebar entries for all services already in DB
    services = ext_service_manager.get_enabled()
    register_all(services)
    ctx.log.info(f"External Services: registered {len(services)} service(s).")

    # 4. Register FastAPI routes
    from main import app as fastapi_app  # noqa: PLC0415 — late import like other plugins
    from .api import build_router
    fastapi_app.include_router(build_router())

    # 5. NiceGUI hub page (overview of all services)
    @ui.page("/external")
    @main_layout("External Services")
    async def _external_hub():
        render_overview_ui(ctx)

    # 6. Bus subscription: db:connected — re-register after reconnect
    @ctx.subscribe("db:connected")
    async def on_db_connected(payload):
        svcs = await asyncio.to_thread(ext_service_manager.get_enabled)
        register_all(svcs)
        ctx.log.info("External Services: re-registered routes after db:connected.")

    # 7. Bus subscription: external_services:register — remote/in-process registration
    @ctx.subscribe("external_services:register")
    async def on_register(payload):
        if not isinstance(payload, dict):
            ctx.log.warning("external_services:register received non-dict payload, ignoring.")
            return

        import re

        raw_slug = payload.get("route") or payload.get("service", "service")
        slug = re.sub(r"[^a-z0-9-]", "-", raw_slug.lower()).strip("-") or "service"

        try:
            svc = await asyncio.to_thread(
                ext_service_manager.upsert,
                slug=slug,
                name=payload.get("name", slug),
                url=payload.get("url", ""),
                icon=payload.get("icon", "open_in_browser"),
                service_type=payload.get("type", "iframe"),
                open_mode=payload.get("open_mode", "iframe"),
                show_in_nav=bool(payload.get("show_in_nav", True)),
                description=payload.get("description", ""),
                enabled=bool(payload.get("enabled", True)),
            )
            register_service(svc)
            ctx.log.info(
                f"External Services: registered '{svc.name}' via event bus."
            )
        except Exception as exc:
            ctx.log.error(
                f"External Services: failed to register '{slug}' from event: {exc}"
            )

    plugin_state["ready"] = True
    ctx.log.info("External Services: setup complete.")
