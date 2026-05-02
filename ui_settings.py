"""
ui_settings.py — Settings card for managing external services.
                 Rendered inside the plugin settings modal from the header bar.
"""
from nicegui import ui

from core.logger import get_logger

log = get_logger("Plugin:ExternalServices:UI")


def render_settings_ui(ctx) -> None:
    from .service import ext_service_manager

    _state = {"editing": None}  # id of service currently being edited, or None

    def _reload():
        container.clear()
        with container:
            _render_list(container, _state)

    with ui.column().classes("w-full gap-4"):
        # ── Header ────────────────────────────────────────────────────────────
        with ui.row().classes("w-full items-center justify-between"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("public", size="20px").classes("text-sky-400")
                ui.label("External Services").classes(
                    "text-base font-bold text-zinc-100"
                )
            ui.button(
                "Service hinzufügen",
                icon="add",
                on_click=lambda: _open_form_dialog(None, _reload),
            ).props("unelevated size=sm color=sky")

        # ── Info banner ───────────────────────────────────────────────────────
        with ui.row().classes(
            "w-full items-start gap-3 p-3 "
            "bg-zinc-800/30 border border-zinc-700/30 rounded-xl"
        ):
            ui.icon("info_outline", size="16px").classes("text-zinc-500 shrink-0 mt-0.5")
            ui.label(
                "Externe Services werden über /external/<slug> eingebettet. "
                "Andere Plugins (z.B. IAC Orchestrator) können Services automatisch via "
                "POST /api/external-services/ registrieren. "
                "Neue Services erscheinen sofort in der Navigation ohne Neustart."
            ).classes("text-xs text-zinc-500")

        # ── Service list ──────────────────────────────────────────────────────
        container = ui.column().classes("w-full gap-2")
        with container:
            _render_list(container, _state)


def _render_list(container, _state) -> None:
    from .service import ext_service_manager

    services = ext_service_manager.get_all()

    if not services:
        ui.label("Noch keine Services konfiguriert.").classes(
            "text-sm text-zinc-600 italic py-4"
        )
        return

    for svc in services:
        _render_service_row(svc, container, _state)


def _render_service_row(svc, container, _state) -> None:
    with ui.card().classes(
        "w-full bg-zinc-800/40 border border-zinc-700/30 rounded-xl p-0"
    ):
        with ui.row().classes("w-full items-center gap-3 p-3"):
            # Status dot
            dot_color = "bg-emerald-500" if svc.enabled else "bg-zinc-600"
            ui.element("div").classes(
                f"w-2 h-2 rounded-full {dot_color} shrink-0"
            )

            # Icon
            ui.icon(svc.icon or "open_in_browser", size="20px").classes("text-sky-400 shrink-0")

            # Info
            with ui.column().classes("gap-0 flex-1 min-w-0"):
                ui.label(svc.name).classes("text-sm font-semibold text-zinc-200 truncate")
                with ui.row().classes("items-center gap-2"):
                    ui.label(f"/external/{svc.slug}").classes(
                        "text-[10px] font-mono text-zinc-500"
                    )
                    ui.label("•").classes("text-zinc-700 text-[10px]")
                    ui.label(svc.url).classes(
                        "text-[10px] font-mono text-zinc-600 truncate"
                    )

            # Action buttons
            with ui.row().classes("items-center gap-1 shrink-0"):
                ui.button(
                    icon="open_in_new",
                    on_click=lambda u=svc.url: ui.run_javascript(
                        f"window.open('{u}', '_blank')"
                    ),
                ).props("flat round dense").classes("text-zinc-500").tooltip("Im Browser öffnen")

                ui.button(
                    icon="edit",
                    on_click=lambda s=svc: _open_form_dialog(
                        s,
                        lambda: (container.clear(), _render_list.__wrapped__(container, _state))
                        if hasattr(_render_list, '__wrapped__')
                        else _refresh_container(container, _state),
                    ),
                ).props("flat round dense").classes("text-zinc-400").tooltip("Bearbeiten")

                ui.button(
                    icon="delete",
                    on_click=lambda s=svc: _confirm_delete(s, container, _state),
                ).props("flat round dense").classes("text-red-500/70").tooltip("Löschen")


def _refresh_container(container, _state) -> None:
    container.clear()
    with container:
        _render_list(container, _state)


def _open_form_dialog(svc, on_save) -> None:
    """Open a dialog for create / edit."""
    is_edit = svc is not None

    with ui.dialog() as dlg, ui.card().classes(
        "w-[500px] max-w-full bg-zinc-900 border border-zinc-700 rounded-2xl p-6"
    ):
        ui.label("Service bearbeiten" if is_edit else "Neuen Service hinzufügen").classes(
            "text-base font-bold text-zinc-100 mb-4"
        )

        name_in = ui.input(
            "Name",
            value=svc.name if is_edit else "",
            placeholder="Home-Assistant",
        ).props("outlined dark").classes("w-full")

        slug_in = ui.input(
            "Route (Slug)",
            value=svc.slug if is_edit else "",
            placeholder="smart-home",
        ).props("outlined dark").classes("w-full")
        ui.label(
            "URL-sicherer Pfad, wird zu /external/<slug>"
        ).classes("text-[10px] text-zinc-600 -mt-2 mb-1")

        url_in = ui.input(
            "URL",
            value=svc.url if is_edit else "",
            placeholder="https://smart-home.int.example.com",
        ).props("outlined dark").classes("w-full")

        icon_in = ui.input(
            "Material Icon",
            value=svc.icon if is_edit else "open_in_browser",
        ).props("outlined dark").classes("w-full")

        desc_in = ui.input(
            "Beschreibung (optional)",
            value=svc.description if is_edit else "",
        ).props("outlined dark").classes("w-full")

        # ── Open mode ─────────────────────────────────────────────────────
        current_mode = (getattr(svc, "open_mode", "iframe") or "iframe") if is_edit else "iframe"
        with ui.column().classes("w-full gap-1 mt-1"):
            ui.label("Anzeigemodus").classes(
                "text-[10px] font-bold uppercase tracking-wider text-zinc-500"
            )
            open_mode_sel = ui.select(
                options={
                    "iframe":   "In Lyndrix einbetten (iframe)",
                    "new_tab":  "Direkt im neuen Tab öffnen",
                },
                value=current_mode,
            ).props("outlined dark").classes("w-full")
            ui.label(
                "Wähle \u201eNeuer Tab\u201c für Services, die das Einbetten via "
                "X-Frame-Options oder CSP blockieren (z. B. manche Proxmox / "
                "pfSense Instanzen)."
            ).classes("text-[10px] text-zinc-600")

        with ui.row().classes("w-full items-center gap-4 mt-1"):
            show_nav = ui.checkbox(
                "In Navigation anzeigen",
                value=svc.show_in_nav if is_edit else True,
            )
            enabled_cb = ui.checkbox(
                "Aktiviert",
                value=svc.enabled if is_edit else True,
            )

        def _save():
            from .service import ext_service_manager
            from .routing import register_service, remove_service, _registered_slugs

            n = name_in.value.strip()
            s = slug_in.value.strip()
            u = url_in.value.strip()
            if not n or not u:
                ui.notify("Name und URL sind Pflichtfelder.", type="negative")
                return

            # Derive slug from name if empty
            import re
            if not s:
                s = re.sub(r"[^a-z0-9-]", "-", n.lower()).strip("-") or "service"

            saved_svc = ext_service_manager.upsert(
                slug=s,
                name=n,
                url=u,
                icon=icon_in.value.strip() or "open_in_browser",
                description=desc_in.value.strip(),
                open_mode=open_mode_sel.value or "iframe",
                show_in_nav=show_nav.value,
                enabled=enabled_cb.value,
            )
            # Refresh routing / nav
            if s in _registered_slugs:
                remove_service(s)
            if saved_svc.enabled:
                register_service(saved_svc)

            ui.notify(f"Service '{n}' gespeichert.", type="positive")
            dlg.close()
            on_save()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Abbrechen", on_click=dlg.close).props("flat").classes(
                "text-zinc-400"
            )
            ui.button("Speichern", icon="save", on_click=_save).props(
                "unelevated color=sky"
            )

    dlg.open()


def _confirm_delete(svc, container, _state) -> None:
    with ui.dialog() as dlg, ui.card().classes(
        "bg-zinc-900 border border-zinc-700 rounded-2xl p-6 gap-4"
    ):
        ui.label(f"Service '{svc.name}' wirklich löschen?").classes(
            "text-sm font-semibold text-zinc-200"
        )
        ui.label(
            "Die Route /external/" + svc.slug + " wird deaktiviert (Neustart erforderlich "
            "für vollständige Entfernung)."
        ).classes("text-xs text-zinc-500")

        with ui.row().classes("w-full justify-end gap-2"):
            ui.button("Abbrechen", on_click=dlg.close).props("flat").classes(
                "text-zinc-400"
            )

            def _do_delete(s=svc):
                from .service import ext_service_manager
                from .routing import remove_service
                ext_service_manager.delete(s.id)
                remove_service(s.slug)
                ui.notify(f"Service '{s.name}' gelöscht.", type="positive")
                dlg.close()
                _refresh_container(container, _state)

            ui.button("Löschen", icon="delete", on_click=_do_delete).props(
                "unelevated color=negative"
            )

    dlg.open()
