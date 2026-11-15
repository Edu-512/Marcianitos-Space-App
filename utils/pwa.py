"""Same-origin PWA routes without modifying installed Streamlit files."""

import re
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from components.navigation import PAGES

PWA_DIR = Path(__file__).resolve().parent.parent / "pwa"
NO_CACHE = {"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"}


@lru_cache(maxsize=1)
def app_shell() -> str:
    """Keep Streamlit's versioned frontend; add metadata to its real head."""
    shell = files("streamlit").joinpath("static", "index.html").read_text(encoding="utf-8")
    shell = re.sub(r"<title>.*?</title>", "<title>Field Shift</title>", shell)
    shell = re.sub(r'''<link\b[^>]*rel=["'](?:manifest|shortcut icon)["'][^>]*>''', "", shell)
    metadata = '''
    <link rel="manifest" href="./manifest.webmanifest" />
    <link rel="icon" type="image/png" href="./pwa/icons/icon-192.png" />
    <link rel="apple-touch-icon" href="./pwa/icons/apple-touch-icon.png" />
    <meta name="theme-color" content="#fff8f4" media="(prefers-color-scheme: light)" />
    <meta name="theme-color" content="#17110e" media="(prefers-color-scheme: dark)" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-title" content="Field Shift" />
    <meta name="description" content="Compare crop rotations, understand farm risk and plan with NASA data." />
    <script src="./pwa/register.js" defer></script>
    '''
    return shell.replace("</head>", metadata + "</head>", 1)


async def index(request: Request) -> HTMLResponse:
    return HTMLResponse(app_shell(), headers=NO_CACHE)


async def manifest(request: Request) -> FileResponse:
    return FileResponse(
        PWA_DIR / "manifest.webmanifest",
        media_type="application/manifest+json",
        headers=NO_CACHE,
    )


async def service_worker(request: Request) -> FileResponse:
    return FileResponse(
        PWA_DIR / "service-worker.js",
        media_type="text/javascript",
        headers={**NO_CACHE, "Service-Worker-Allowed": "/"},
    )


def pwa_routes() -> list[Route | Mount]:
    """Deploy this entrypoint at the domain root (Community Cloud)."""
    return [
        Route("/", index),
        Route("/index.html", index),
        *[Route(f"/{spec.url_path}", index) for spec in PAGES.values()],
        Route("/manifest.webmanifest", manifest),
        Route("/service-worker.js", service_worker),
        Mount("/pwa", app=StaticFiles(directory=PWA_DIR)),
    ]
