import sys
import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
import httpx

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.gateway.threat_scorer import ThreatScorer
from src.ml.hybrid_scorer import HybridThreatScorer

app = FastAPI(title="Prometheus Agent (Sidecar)")

# Initialize Local Analyzers
threat_scorer = ThreatScorer()
# In a real sidecar, HybridScorer would be lightweight or offloaded
hybrid_scorer = HybridThreatScorer() 

BRAIN_URL = os.getenv("BRAIN_URL", "http://localhost:8001")
SIREN_URL = os.getenv("SIREN_URL", "http://localhost:8002")
APP_URL = os.getenv("APP_URL", "http://localhost:5000")

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy(request: Request, path: str):
    # 1. Capture Request
    body = await request.body()
    payload = body.decode("utf-8", errors="ignore")
    
    # 2. Fast Analysis (Local) - <1ms
    assessment = threat_scorer.score(payload)
    if assessment.score > 0.9:
        # Fast Block -> Redirect to Honeypot
        return await tunnel_to_siren(request, path, payload)
        
    # 3. Decision
    # Ideally, Hybrid analysis happens here or async. 
    # For MVP, we'll allow traffic and report async to Brain if suspicious.
    
    # Async Telemetry (Fire & Forget)
    # asyncio.create_task(report_to_brain(payload))
    
    # 4. Proxy to App (Allow)
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.request(
                method=request.method,
                url=f"{APP_URL}/{path}",
                headers=request.headers,
                content=body
            )
            return Response(content=resp.content, status_code=resp.status_code, headers=resp.headers)
        except Exception as e:
            return JSONResponse({"error": "Upstream application unreachable"}, status_code=502)

async def tunnel_to_siren(request: Request, path: str, payload: str):
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method=request.method,
            url=f"{SIREN_URL}/{path}",
            headers=request.headers,
            content=payload
        )
        return Response(content=resp.content, status_code=resp.status_code, headers=resp.headers)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
