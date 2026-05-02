"""
routing.py — Dynamic NiceGUI page registration and sidebar-nav injection
             for ExternalService entries.

Each service gets:
  • A NiceGUI page at /external/<slug>  (registered once, idempotent)
  • A virtual manifest entry in module_manager.registry so the service
    shows up in the main sidebar under "Services"
"""
from core.logger import get_logger

log = get_logger("Plugin:ExternalServices:Routing")

# Tracks slugs that have already had a route + nav entry registered
# so we never double-register even if the function is called twice.
_registered_slugs: set = set()

# Shared ModuleContext for all virtual manifests (set by entrypoint)
_ctx = None


def set_context(ctx) -> None:
    global _ctx
    _ctx = ctx


def register_all(services) -> None:
    """Register routes + nav for every enabled service (called at startup)."""
    for svc in services:
        if svc.enabled:
            register_service(svc)


def register_service(svc) -> None:
    """Register a single service's route and inject its sidebar entry."""
    if svc.slug in _registered_slugs:
        return
    open_mode = getattr(svc, "open_mode", "iframe") or "iframe"
    _register_nicegui_page(svc.slug, svc.name, svc.icon, svc.url, open_mode)
    if svc.show_in_nav:
        _inject_nav_entry(svc)
    _registered_slugs.add(svc.slug)
    log.info(f"ROUTE: Registered /external/{svc.slug} for '{svc.name}' (mode={open_mode}).")


def remove_service(slug: str) -> None:
    """Remove a service's sidebar nav entry (route stays until restart)."""
    virtual_id = f"external.service.{slug}"
    try:
        from core.components.plugins.logic.manager import module_manager
        if virtual_id in module_manager.registry:
            del module_manager.registry[virtual_id]
            log.info(f"NAV: Removed sidebar entry for '{slug}'.")
    except Exception as exc:
        log.warning(f"NAV: Could not remove entry for '{slug}': {exc}")
    _registered_slugs.discard(slug)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _register_nicegui_page(slug: str, name: str, icon: str, url: str, open_mode: str) -> None:
    """Register a NiceGUI page at /external/<slug> using the standard main_layout."""
    from nicegui import ui

    try:
        from ui.layout import main_layout
    except ImportError:
        def main_layout(title):  # type: ignore
            def decorator(fn):
                return fn
            return decorator

    if open_mode == "new_tab":
        @ui.page(f"/external/{slug}")
        @main_layout(name)
        async def _new_tab_page(_name=name, _icon=icon, _url=url):
            _render_new_tab_landing(_name, _icon, _url)
    else:
        @ui.page(f"/external/{slug}")
        @main_layout(name)
        async def _iframe_page(_name=name, _icon=icon, _url=url):
            _render_iframe(_name, _icon, _url)


def _render_iframe(name: str, icon: str, url: str) -> None:
    from nicegui import ui

    ui.element('iframe').props(
        f'src="{url}" allowfullscreen'
    ).style(
        'width: 100%; '
        'flex: 1 1 auto; '
        'min-height: 0; '
        'border: none; '
        'display: block;'
    )

    # Strip all padding/margin/max-width from every container between
    # .q-page and the iframe so it fills edge-to-edge top-to-bottom.
    # .q-page-container already accounts for the 48px header via padding-top,
    # so inside .q-page we just need flex:1 on every wrapper.
    ui.run_javascript('''
        (function() {
            var qpage = document.querySelector(".q-page");
            if (!qpage) return;
            qpage.style.padding    = "0";
            qpage.style.display    = "flex";
            qpage.style.flexDirection = "column";

            var content = qpage.querySelector(".nicegui-content");
            if (content) {
                content.style.padding       = "0";
                content.style.margin        = "0";
                content.style.width         = "100%";
                content.style.flex          = "1 1 auto";
                content.style.display       = "flex";
                content.style.flexDirection = "column";
                content.style.minHeight     = "0";
            }

            var col = content ? content.querySelector(":scope > .nicegui-column") : null;
            if (col) {
                col.style.maxWidth      = "none";
                col.style.padding       = "0";
                col.style.margin        = "0";
                col.style.width         = "100%";
                col.style.flex          = "1 1 auto";
                col.style.display       = "flex";
                col.style.flexDirection = "column";
                col.style.minHeight     = "0";
            }
        })();
    ''')


def _render_new_tab_landing(name: str, icon: str, url: str) -> None:
    """
    Landing page for services configured with open_mode='new_tab'.
    Opens the URL in a new browser tab immediately via JS, and shows a
    small card as confirmation so the page isn't blank.
    """
    from nicegui import ui

    # Auto-open on page load
    ui.run_javascript(f"window.open('{url}', '_blank');")

    with ui.column().classes("w-full items-center justify-center gap-6 py-24"):
        with ui.card().classes(
            "items-center gap-4 p-8 bg-zinc-800/40 border border-zinc-700/30 rounded-2xl"
        ):
            ui.icon(icon or "open_in_browser", size="48px").classes("text-sky-400")
            ui.label(name).classes("text-xl font-bold text-zinc-100")
            ui.label(
                "Dieser Service wird in einem neuen Tab geöffnet."
            ).classes("text-sm text-zinc-400 text-center")
            ui.label(url).classes("text-[11px] font-mono text-zinc-600")
            ui.button(
                "Erneut öffnen",
                icon="open_in_new",
                on_click=lambda u=url: ui.run_javascript(f"window.open('{u}', '_blank')"),
            ).props("unelevated color=sky").classes("mt-2")


def _inject_nav_entry(svc) -> None:
    """Add a virtual manifest entry to the module_manager so the sidebar shows this service."""
    try:
        from core.components.plugins.logic.manager import module_manager
        from core.components.plugins.logic.models import ModuleManifest, ModulePermissions

        virtual_id = f"external.service.{svc.slug}"
        if virtual_id in module_manager.registry:
            return

        virtual_manifest = ModuleManifest(
            id=virtual_id,
            name=svc.name,
            icon=svc.icon or "open_in_browser",
            type="PLUGIN",
            ui_route=f"/external/{svc.slug}",
            version="1.0.0",
            description=svc.description or f"External service: {svc.name}",
            permissions=ModulePermissions(),
        )
        module_manager.registry[virtual_id] = {
            "manifest": virtual_manifest,
            "module": None,
            "context": _ctx,
            "status": "active",
        }
    except Exception as exc:
        log.warning(f"NAV: Could not inject sidebar entry for '{svc.slug}': {exc}")
