"""EID App Platform — Hub Launcher.

Serves the main landing page at apps.ellisid.com with cards for each app.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

app = FastAPI(title="EID App Platform", version="1.0")

BASE = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

APPS = [
    # {
    #     "name": "RENCO CALC",
    #     "description": "Renco block quantities, container packing, and shipping logistics from Archicad BIM models.",
    #     "url": "/renco/",
    #     "status": "live",
    #     "icon": "cube",
    # },
    {
        "name": "Meeting Notes",
        "description": "AI-powered meeting transcription, action items, and client communication summaries.",
        "url": "/meeting-notes/",
        "status": "live",
        "icon": "clipboard",
    },
    {
        "name": "EBIF Schedules",
        "description": "Ellis Building Intelligence Framework — FF&E schedules extracted from Archicad with interactive dashboards.",
        "url": "https://sprtic1.github.io/ebif-calc/",
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
        "description": "Photograph a material sample, let Claude read the label, and file it instantly to the correct Dropbox folder — no renaming, no manual filing.",
        "url": "/sample-library/",
        "status": "live",
        "icon": "swatch",
    },
]

PORTALS_FILE = Path("/opt/eid-apps/client-portal/data/projects.json")


def _load_portals() -> list[dict]:
    """Load client portal cards from the shared projects.json."""
    import json
    try:
        data = json.load(open(PORTALS_FILE))
        portals = []
        for slug, p in data.get("projects", {}).items():
            portals.append({
                "name": p.get("name", slug),
                "subtitle": p.get("address", ""),
                "url": f"/client/{slug}",
                "categories": p.get("active_schedules", 0),
            })
        portals.sort(key=lambda x: x["name"])
        return portals
    except Exception:
        return []


@app.get("/", response_class=HTMLResponse)
async def hub(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "apps": APPS,
        "portals": _load_portals(),
    })


@app.get("/health")
async def health():
    return {"status": "ok", "service": "eid-app-platform"}
