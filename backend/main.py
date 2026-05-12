import asyncio
import socket
import subprocess
import re
from typing import Optional
import httpx
import dns.resolver
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    ports: list[int] = [22, 80, 443, 3000, 3306, 5432, 8080, 8443]


class HttpRequest(BaseModel):
    url: str


def sanitize_host(host: str) -> str:
    host = host.strip()
    if not re.match(r'^[a-zA-Z0-9.\-_]+$', host):
        raise HTTPException(status_code=400, detail="Invalid host")
    return host


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/ping")
async def ping(req: HostRequest):
    host = sanitize_host(req.host)
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "4", "-W", "2", host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stdout.decode()
        lines = [l for l in output.splitlines() if l.strip()]
        return {"host": host, "output": lines, "success": proc.returncode == 0}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Timeout")


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


@app.post("/api/traceroute")
async def traceroute(req: HostRequest):
    host = sanitize_host(req.host)
    try:
        proc = await asyncio.create_subprocess_exec(
            "traceroute", "-m", "15", "-w", "1", host,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        lines = [l for l in stdout.decode().splitlines() if l.strip()]
        return {"host": host, "hops": lines}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=408, detail="Timeout")
