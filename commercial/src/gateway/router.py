# src/gateway/router.py
"""
Traffic Router: Routes requests to real app or honeypot.
The decision engine at the heart of the gateway.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import httpx
from loguru import logger

from src.siren.sandbox import sandbox_manager, SandboxSession
from .threat_scorer import threat_scorer, ThreatAssessment


@dataclass
class RouteDecision:
    """Result of routing decision."""
    destination: str  # "app", "honeypot", "blocked"
    session_id: Optional[str]
    threat_assessment: ThreatAssessment
    timestamp: datetime


class TrafficRouter:
    """
    Routes traffic based on threat assessment.
    
    Safe traffic → Real application
    Malicious traffic → Siren honeypot
    """
    
    def __init__(self, app_backend_url: str = "http://localhost:5000"):
        """
        Initialize the router.
        
        Args:
            app_backend_url: URL of the real application backend
        """
        self.app_backend_url = app_backend_url
        self.decisions: list[RouteDecision] = []
        self._http_client: Optional[httpx.AsyncClient] = None
    
    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client
    
    def route(
        self,
        method: str,
        path: str,
        query_string: str,
        body: str,
        headers: dict,
        client_ip: str,
    ) -> RouteDecision:
        """
        Decide where to route a request.
        
        Args:
            method: HTTP method
            path: Request path
            query_string: Query string
            body: Request body
            headers: Request headers
            client_ip: Client IP address
            
        Returns:
            RouteDecision with destination and threat info
        """
        # Score the request
        assessment = threat_scorer.score_request(
            method=method,
            path=path,
            query_string=query_string,
            body=body,
            headers=headers,
        )
        
        # Make routing decision
        if assessment.action == "honeypot":
            # Create or get honeypot session
            session = sandbox_manager.create_session(client_ip)
            destination = "honeypot"
            session_id = session.session_id
            
            logger.warning(
                f"Routing {client_ip} to honeypot | "
                f"Attack: {assessment.attack_type} | "
                f"Score: {assessment.score:.2f}"
            )
        
        elif assessment.action == "block":
            destination = "blocked"
            session_id = None
            logger.warning(f"Blocking request from {client_ip}")
        
        else:
            destination = "app"
            session_id = None
            logger.debug(f"Allowing request from {client_ip} to pass through")
        
        decision = RouteDecision(
            destination=destination,
            session_id=session_id,
            threat_assessment=assessment,
            timestamp=datetime.now(),
        )
        
        self.decisions.append(decision)
        return decision
    
    async def forward_to_app(
        self,
        method: str,
        path: str,
        headers: dict,
        body: bytes,
    ) -> httpx.Response:
        """
        Forward a safe request to the real application.
        
        Args:
            method: HTTP method
            path: Request path
            headers: Request headers
            body: Request body
            
        Returns:
            Response from the real application
        """
        url = f"{self.app_backend_url}{path}"
        
        try:
            response = await self.http_client.request(
                method=method,
                url=url,
                headers=headers,
                content=body,
            )
            return response
        
        except httpx.RequestError as e:
            logger.error(f"Failed to forward request: {e}")
            raise
    
    def handle_honeypot_request(
        self,
        session_id: str,
        request_type: str,
        payload: str,
    ) -> dict:
        """
        Handle a request in the honeypot.
        
        Routes to appropriate fake service (SQL, filesystem, etc.)
        
        Args:
            session_id: Honeypot session ID
            request_type: Type of request (sql, file, command)
            payload: The request payload
            
        Returns:
            Fake response from honeypot
        """
        session = sandbox_manager.get_session(session_id)
        
        if not session:
            return {"error": "Session expired"}
        
        if request_type == "sql":
            return session.fake_sql.execute(payload)
        
        elif request_type == "file_read":
            return session.fake_fs.read_file(payload)
        
        elif request_type == "file_list":
            return session.fake_fs.list_directory(payload)
        
        elif request_type == "file_write":
            path, content = payload.split("|||", 1) if "|||" in payload else (payload, "")
            return session.fake_fs.write_file(path, content)
        
        else:
            return {"error": "Unknown request type"}
    
    def get_statistics(self) -> dict:
        """Get routing statistics."""
        total = len(self.decisions)
        if total == 0:
            return {"total": 0}
        
        destinations = {"app": 0, "honeypot": 0, "blocked": 0}
        attack_types = {}
        
        for decision in self.decisions:
            destinations[decision.destination] = destinations.get(decision.destination, 0) + 1
            
            if decision.threat_assessment.attack_type:
                attack_types[decision.threat_assessment.attack_type] = \
                    attack_types.get(decision.threat_assessment.attack_type, 0) + 1
        
        return {
            "total": total,
            "destinations": destinations,
            "attack_types": attack_types,
            "honeypot_rate": destinations["honeypot"] / total * 100,
        }
    
    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
traffic_router = TrafficRouter()
