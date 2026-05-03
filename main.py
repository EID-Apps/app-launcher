"""App Platform — Hub Launcher.

Serves the main landing page with cards for each app.
Client portals are discovered dynamically from the client-webpage API.
"""

import logging
import sys
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from config_loader import tenant

import asyncio
import httpx
import json
import os
import time
from pathlib import Path as _Path

from storage_backend import get_storage_backend, StorageNotFoundError, StorageError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(f"{tenant.firm.service_prefix}-launcher")

app = FastAPI(title=f"{tenant.firm.short_name} App Platform", version="2.0")

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


# ── Registry config ────────────────────────────────────────────────────────────
_REGISTRY_DROPBOX_PATH = tenant.dropbox.registry_path
_ENV_FILE = _Path(tenant.deployment.base_path) / "plaud-control" / "engine" / ".env"
_registry_cache: list | None = None
_registry_cache_at: float = 0.0
_REGISTRY_TTL = 300  # 5 minutes

# Module-level storage backend — lazily initialised in _get_storage()
_storage = None
_storage_lock = __import__('threading').Lock()


def _read_env() -> dict:
    creds: dict = {}
    try:
        for line in _ENV_FILE.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip()
    except Exception:
        pass
    return creds


def _get_storage():
    """Return the module-level storage backend (synchronous, thread-safe)."""
    global _storage
    if _storage is not None:
        return _storage
    with _storage_lock:
        if _storage is not None:
            return _storage
        creds = _read_env()
        for k in ('DROPBOX_APP_KEY', 'DROPBOX_APP_SECRET', 'DROPBOX_REFRESH_TOKEN'):
            if creds.get(k) and not os.environ.get(k):
                os.environ[k] = creds[k]
        _storage = get_storage_backend()
        return _storage


def _download_registry() -> list[dict]:
    """Synchronous registry download - runs in executor."""
    raw = _get_storage().download(_REGISTRY_DROPBOX_PATH)
    data = json.loads(raw)
    return [p for p in data.get("projects", []) if p.get("status") == "Active"]


async def load_active_projects() -> list[dict]:
    """Download the Dropbox registry and return Active projects.
    Cached for 5 minutes. Never raises — returns [] on any error.
    """
    global _registry_cache, _registry_cache_at
    if _registry_cache is not None and (time.time() - _registry_cache_at) < _REGISTRY_TTL:
        return _registry_cache

    try:
        loop = asyncio.get_event_loop()
        active = await loop.run_in_executor(None, _download_registry)
        _registry_cache = active
        _registry_cache_at = time.time()
        logger.info("Registry loaded: %d active projects", len(active))
        return active
    except Exception as e:
        logger.warning("Registry load error: %s", e)
        return []


APPS = [
    {
        "name": "EBIF Schedules",
        "description": f"{tenant.firm.framework_name} — FF&E schedules extracted from Archicad with interactive dashboards.",
        "url": "https://eid-apps.github.io/ebif-calc/",
        "status": "live",
        "icon": "table",
    },
    {
        "name": "Shop Drawing QA",
        "description": "Automated shop drawing review with AI-powered markup, spec compliance checks, and approval workflows.",
        "url": "/shop-drawing-qa/",
        "status": "live",
        "icon": "drafting",
    },
    {
        "name": "Sample Library",
        "description": "Auto-files samples from your Dropbox inbox into the Digital Design Library.",
        "url": "/sample-library/",
        "status": "live",
        "icon": "swatch",
    },
    {
        "name": "Project Manager",
        "description": "Project setup, Archicad data sync, schedule dashboards, and export management.",
        "url": "/project-hub/",
        "status": "live",
        "icon": "table",
    },
    {
        "name": "Texture Studio",
        "description": "Convert sample photos to seamless tileable textures for 3D rendering.",
        "url": "/texture-studio/",
        "status": "live",
        "icon": "texture",
    },
    {
        "name": "Plaud to ClickUp",
        "description": "Automatically converts Plaud meeting recordings into Word meeting notes and ClickUp tasks.",
        "url": "/plaud-control/",
        "status": "live",
        "icon": "microphone",
    },
    {
        "name": "Material Viewer",
        "description": "Preview materials on 3D furniture models and share interactive links with clients.",
        "url": "/material-viewer/",
        "status": "live",
        "icon": "cube",
    },
]

# Internal URL for the eid-client-webpage API (same server)
CLIENT_WEBPAGE_API = f"http://127.0.0.1:{tenant.integrations.client_webpage_port}"


async def _load_portals() -> list[dict]:
    """Fetch discovered projects from eid-client-webpage API."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{CLIENT_WEBPAGE_API}/client/api/projects")
            resp.raise_for_status()
            data = resp.json()
            portals = []
            for p in data.get("projects", []):
                portals.append({
                    "name":      p.get("name", p["slug"]),
                    "subtitle":  p.get("address", ""),
                    "url":       p.get("url", f"/client/{p['slug']}"),
                    "admin_url": p.get("admin_url", f"/admin/{p['slug']}"),
                })
            portals.sort(key=lambda x: x["name"])
            return portals
    except Exception as e:
        logger.warning("Failed to fetch portals from client-webpage API: %s", e)
        return []



@app.get("/api/registry-projects")
async def api_registry_projects():
    """Return active projects from the central Dropbox registry."""
    projects = await load_active_projects()
    result = []
    for p in projects:
        slug = p.get("client_portal_slug", "").strip()
        result.append({
            "id":         p.get("id", ""),
            "name":       p.get("project_name", ""),
            "address":    p.get("project_address", ""),
            "owner":      (p.get("owner") or {}).get("last_name", ""),
            "status":     p.get("status", "Active"),
            "portal_url": f"https://{tenant.firm.domain}/client/{slug}" if slug else "",
            "has_portal": bool(slug),
        })
    return result


@app.get("/", response_class=HTMLResponse)
async def hub(request: Request):
    portals = await _load_portals()
    registry_projects = await load_active_projects()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "apps": APPS,
        "portals": portals,
        "registry_projects": registry_projects,
    })

@app.get("/health")
async def health():
    return {"status": "ok", "service": f"{tenant.firm.service_prefix}-app-platform", "version": "2.0"}
