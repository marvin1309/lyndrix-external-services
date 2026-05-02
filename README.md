# lyndrix-external-services

A Lyndrix plugin that embeds external web services (Home Assistant, Grafana, Netdata, …) directly into the Lyndrix UI as full-screen iframes with their own sidebar navigation entries.

---

## Features

- **Automatic routing** — every service gets a dedicated page at `/external/<slug>`, registered at runtime without a restart
- **Sidebar integration** — each service appears in the Lyndrix sidebar under *Services*, indistinguishable from native plugins
- **REST API** — full CRUD at `/api/external-services/` so other services (e.g. lyndrix-iac-orchestrator) can register services programmatically
- **Event bus** — publish `external_services:register` from any plugin to register a service in-process
- **Settings UI** — manage services through the plugin settings modal (add / edit / delete with live preview)
- **Hub page** — `/external` lists all registered services as cards with open and new-tab buttons
- **Persistent** — service definitions survive restarts via the `external_services` MariaDB table

---

## Payload format

Both the REST API and the event bus accept the same fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `service` | string | yes | Internal identifier, used as slug fallback |
| `name` | string | yes | Display name shown in sidebar and card |
| `icon` | string | no | [Material Icon](https://fonts.google.com/icons) name (default: `open_in_browser`) |
| `url` | string | yes | Full URL of the external service |
| `type` | string | no | Integration type — currently `iframe` (default) |
| `route` | string | no | Explicit URL slug; falls back to `service` field |
| `show_in_nav` | bool | no | Whether to add a sidebar entry (default: `true`) |
| `description` | string | no | Short description shown on the hub card |
| `enabled` | bool | no | Whether to register the route (default: `true`) |

---

## REST API

Base path: `/api/external-services/`

### Register or update a service

```http
POST /api/external-services/
Content-Type: application/json

{
  "service":     "homeassistant",
  "name":        "Home-Assistant",
  "icon":        "home",
  "url":         "https://smart-home.int.fam-feser.de",
  "type":        "iframe",
  "route":       "smart-home",
  "show_in_nav": true
}
```

The call is **idempotent** — if a service with the same slug already exists it is updated in place.

### List all services

```http
GET /api/external-services/
```

### Update a service

```http
PUT /api/external-services/{id}
Content-Type: application/json

{
  "enabled": false
}
```

### Delete a service

```http
DELETE /api/external-services/{id}
```

### Force re-scan (after manual DB changes)

```http
POST /api/external-services/reload
```

---

## Event bus

Any Lyndrix plugin can register a service without HTTP by emitting on the bus.

**Topic:** `external_services:register`

The plugin's manifest must include this topic in `permissions.emit`:

```python
manifest = ModuleManifest(
    ...
    permissions={
        "emit": ["external_services:register"],
    },
)
```

Then emit from `setup()` or any bus handler:

```python
ctx.emit("external_services:register", {
    "service": "homeassistant",
    "name":    "Home-Assistant",
    "icon":    "home",
    "url":     "https://smart-home.int.fam-feser.de",
    "type":    "iframe",
    "route":   "smart-home",
})
```

The service is persisted to the DB and the route + sidebar entry are registered immediately.

---

## IAC Orchestrator integration example

In `lyndrix-iac-orchestrator`, after a deployment completes, post the service URL back to Lyndrix:

```python
import httpx

httpx.post("http://lyndrix-core:8081/api/external-services/", json={
    "service":     "homeassistant",
    "name":        "Home-Assistant",
    "icon":        "home",
    "url":         deployment.url,
    "type":        "iframe",
    "route":       "smart-home",
})
```

Or use the event bus directly if both run in the same process.

---

## File structure

```
lyndrix-external-services/
├── entrypoint.py      # Plugin manifest + setup() + bus subscriptions
├── models.py          # SQLAlchemy ExternalService ORM model
├── service.py         # CRUD manager (ext_service_manager singleton)
├── routing.py         # Dynamic NiceGUI page + sidebar injection
├── api.py             # FastAPI router (/api/external-services/)
├── ui_overview.py     # Hub page /external — service cards
└── ui_settings.py     # Settings modal — add / edit / delete
```

---

## Routes registered at runtime

| Path | Description |
|---|---|
| `/external` | Hub page — overview of all registered services |
| `/external/<slug>` | Full-screen iframe for the service |
| `/api/external-services/` | REST CRUD |

---

## Requirements

- lyndrix-core ≥ 0.0.1
- No additional Python dependencies — uses only packages already present in lyndrix-core (`nicegui`, `fastapi`, `sqlalchemy`, `pydantic`)
