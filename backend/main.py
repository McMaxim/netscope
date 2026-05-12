import asyncio
import re
import httpx
import dns.resolver
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

app = FastAPI(title="NetScope API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class HostRequest(BaseModel):
    host: str


class PortScanRequest(BaseModel):
    host: str
    ports: list[int] = [21, 22, 25, 80, 443, 3000, 3306, 5432, 8080, 8443]


class HttpRequest(BaseModel):
    url: str


def sanitize_host(host: str) -> str:
    host = host.strip()
    if not re.match(r'^[a-zA-Z0-9.\-_]+$', host):
        raise HTTPException(status_code=400, detail="Invalid host")
    return host


STATIC_DIR = Path(__file__).parent / "frontend"

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/docs.html")
def docs():
    return FileResponse(STATIC_DIR / "docs.html")


@app.post("/api/dns")
async def dns_lookup(req: HostRequest):
    host = sanitize_host(req.host)
    results = {}
    resolver = dns.resolver.Resolver()
    for rtype in ["A", "AAAA", "MX", "NS", "TXT"]:
        try:
            answers = resolver.resolve(host, rtype, lifetime=5)
            results[rtype] = [str(r) for r in answers]
        except Exception:
            results[rtype] = []
    return {"host": host, "records": results}


@app.post("/api/ports")
async def port_scan(req: PortScanRequest):
    host = sanitize_host(req.host)
    if len(req.ports) > 20:
        raise HTTPException(status_code=400, detail="Max 20 ports")

    async def check_port(port: int) -> dict:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=2
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            return {"port": port, "open": True}
        except Exception:
            return {"port": port, "open": False}

    tasks = [check_port(p) for p in req.ports]
    results = await asyncio.gather(*tasks)
    return {"host": host, "results": results}


@app.post("/api/headers")
async def http_headers(req: HttpRequest):
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            resp = await client.head(url)
            return {
                "url": str(resp.url),
                "status": resp.status_code,
                "headers": dict(resp.headers),
            }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# Serve frontend static files — must be last
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
