"""
ui_overview.py — Hub page at /external showing all registered external services
                 as clickable cards.  This is the "External Services" sidebar entry.
"""
from nicegui import ui

from .service import ext_service_manager


def render_overview_ui(ctx) -> None:
    services = ext_service_manager.get_all()

    if not services:
        with ui.column().classes("w-full items-center justify-center gap-4 py-16"):
            ui.icon("link_off", size="48px").classes("text-zinc-600")
            ui.label("Keine externen Services konfiguriert.").classes(
                "text-zinc-500 text-sm"
            )
            ui.label(
                "Füge Services über die Einstellungen → Plugins → External Services hinzu "
                "oder sende einen POST an /api/external-services/."
            ).classes("text-zinc-600 text-xs text-center max-w-md")
        return

    enabled = [s for s in services if s.enabled]
    disabled = [s for s in services if not s.enabled]

    if enabled:
        with ui.row().classes("flex-wrap gap-4 w-full"):
            for svc in enabled:
                _render_service_card(svc)

    if disabled:
        ui.label("Deaktiviert").classes(
            "text-[10px] font-bold uppercase tracking-wider text-zinc-600 mt-6 mb-2"
        )
        with ui.row().classes("flex-wrap gap-4 w-full opacity-50"):
            for svc in disabled:
                _render_service_card(svc, dimmed=True)


def _render_service_card(svc, dimmed: bool = False) -> None:
    """Render a card for one external service."""
    opacity = "opacity-50" if dimmed else ""

    with ui.card().classes(
        f"w-64 cursor-pointer hover:scale-[1.02] transition-transform "
        f"bg-zinc-800/50 border border-zinc-700/40 rounded-xl p-0 {opacity}"
    ):
        # Gradient header bar
        with ui.element("div").classes(
            "h-1 w-full bg-gradient-to-r from-sky-400 to-cyan-400 rounded-t-xl"
        ):
            pass

        with ui.column().classes("p-4 gap-3"):
            with ui.row().classes("items-center gap-3"):
                with ui.element("div").classes(
                    "w-10 h-10 rounded-lg bg-zinc-700/50 flex items-center justify-center shrink-0"
                ):
                    ui.icon(svc.icon or "open_in_browser", size="22px").classes("text-sky-400")

                with ui.column().classes("gap-0 min-w-0"):
                    ui.label(svc.name).classes(
                        "text-sm font-bold text-zinc-100 leading-tight truncate"
                    )
                    with ui.row().classes("items-center gap-1"):
                        ui.label(svc.service_type.upper()).classes(
                            "text-[10px] font-mono text-zinc-500 uppercase"
                        )
                        open_mode = getattr(svc, "open_mode", "iframe") or "iframe"
                        if open_mode == "new_tab":
                            ui.label("NEU TAB").classes(
                                "text-[9px] font-bold bg-amber-500/20 text-amber-400 "
                                "border border-amber-500/30 rounded px-1"
                            )

            if svc.description:
                ui.label(svc.description).classes(
                    "text-xs text-zinc-500 leading-relaxed line-clamp-2"
                )

            ui.label(svc.url).classes(
                "text-[10px] font-mono text-zinc-600 truncate w-full"
            )

            with ui.row().classes("w-full gap-2 mt-1"):
                open_mode = getattr(svc, "open_mode", "iframe") or "iframe"
                if open_mode == "new_tab":
                    ui.button(
                        "Öffnen",
                        icon="open_in_new",
                        on_click=lambda u=svc.url: ui.run_javascript(
                            f"window.open('{u}', '_blank')"
                        ),
                    ).props("unelevated size=sm color=amber").classes("flex-1")
                else:
                    ui.button(
                        "Öffnen",
                        icon="open_in_browser",
                        on_click=lambda u=f"/external/{svc.slug}": ui.navigate.to(u),
                    ).props("unelevated size=sm color=sky").classes("flex-1")

                # Always show direct link button
                ui.button(
                    icon="open_in_new",
                    on_click=lambda url=svc.url: ui.run_javascript(
                        f"window.open('{url}', '_blank')"
                    ),
                ).props("flat round dense").classes("text-zinc-500").tooltip(
                    "Im Browser öffnen"
                )
