# src/gateway/ingress.py
"""
Ingress Controller: FastAPI application for traffic handling.
The main entry point that ties everything together.
"""

from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn

from src.core.config import settings
from src.core.qdrant_client import qdrant_manager
from src.siren.sandbox import sandbox_manager
from src.siren.recorder import attack_recorder
from .router import traffic_router
from .threat_scorer import threat_scorer


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Prometheus-Siren Gateway...")
    qdrant_manager.ensure_collections()
    logger.success("Gateway ready!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down gateway...")
    await traffic_router.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Prometheus-Siren Gateway",
        description="Self-Evolving Cyber-Immune System Gateway",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ==========================================
    # Health & Status Endpoints
    # ==========================================
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "service": "prometheus-siren"}
    
    @app.get("/api/status")
    async def status():
        """Get system status."""
        return {
            "gateway": "running",
            "active_sessions": len(sandbox_manager.get_active_sessions()),
            "routing_stats": traffic_router.get_statistics(),
            "attack_stats": attack_recorder.get_attack_statistics(),
        }
    
    # ==========================================
    # Honeypot API Endpoints
    # ==========================================
    
    @app.get("/api/sessions")
    async def list_sessions():
        """List active honeypot sessions."""
        return sandbox_manager.get_active_sessions()
    
    @app.get("/api/attacks")
    async def list_attacks():
        """Get all recorded attacks."""
        return attack_recorder.get_attack_statistics()
    
    @app.post("/api/attacks/search")
    async def search_attacks(payload: dict):
        """Search for similar attacks in memory."""
        query = payload.get("query", "")
        return attack_recorder.find_similar_attacks(query, top_k=10)
    
    # ==========================================
    # Honeypot Interaction Endpoints
    # (These simulate vulnerable endpoints)
    # ==========================================
    
    @app.post("/api/honeypot/{session_id}/sql")
    async def honeypot_sql(session_id: str, request: Request):
        """Execute SQL in honeypot (fake)."""
        body = await request.json()
        query = body.get("query", "")
        
        result = traffic_router.handle_honeypot_request(
            session_id=session_id,
            request_type="sql",
            payload=query,
        )
        return result
    
    @app.post("/api/honeypot/{session_id}/file")
    async def honeypot_file(session_id: str, request: Request):
        """Read file in honeypot (fake)."""
        body = await request.json()
        path = body.get("path", "")
        operation = body.get("operation", "read")
        
        result = traffic_router.handle_honeypot_request(
            session_id=session_id,
            request_type=f"file_{operation}",
            payload=path,
        )
        return result
    
    # ==========================================
    # Main Proxy Endpoint
    # ==========================================
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def proxy_request(request: Request, path: str):
        """
        Main proxy endpoint - routes all traffic.
        
        This is where the magic happens:
        - Score incoming request
        - Route to app or honeypot
        - Return appropriate response
        """
        # Get request details
        method = request.method
        query_string = str(request.query_params)
        headers = dict(request.headers)
        client_ip = request.client.host if request.client else "unknown"
        
        # Get body
        try:
            body = await request.body()
            body_str = body.decode("utf-8", errors="ignore")
        except Exception:
            body = b""
            body_str = ""
        
        # Make routing decision
        decision = traffic_router.route(
            method=method,
            path=f"/{path}",
            query_string=query_string,
            body=body_str,
            headers=headers,
            client_ip=client_ip,
        )
        
        if decision.destination == "honeypot":
            # Redirect to honeypot session
            return {
                "status": "redirected",
                "session_id": decision.session_id,
                "message": "Your request is being processed",
                "_debug": {
                    "threat_score": decision.threat_assessment.score,
                    "attack_type": decision.threat_assessment.attack_type,
                },
            }
        
        elif decision.destination == "blocked":
            raise HTTPException(status_code=403, detail="Access denied")
        
        else:
            # Forward to real app
            try:
                response = await traffic_router.forward_to_app(
                    method=method,
                    path=f"/{path}",
                    headers={k: v for k, v in headers.items() if k.lower() != "host"},
                    body=body,
                )
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )
            except Exception as e:
                logger.error(f"Backend error: {e}")
                raise HTTPException(status_code=502, detail="Backend unavailable")
    
    return app


# Create app instance
app = create_app()


def run_gateway(host: Optional[str] = None, port: Optional[int] = None):
    """Run the gateway server."""
    host = host or settings.gateway_host
    port = port or settings.gateway_port
    
    logger.info(f"Starting gateway on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_gateway()
