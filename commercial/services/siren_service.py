import sys
import os
import uvicorn
from fastapi import FastAPI, Request

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.siren.sandbox import SandboxManager

app = FastAPI(title="Prometheus Siren (Honeypot)")

sandbox = SandboxManager()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def honeypot(request: Request, path: str):
    # Provide a convincing fake response
    body = await request.body()
    payload = body.decode("utf-8", errors="ignore")
    
    # Identify attack type contextually or just return generic fake
    if "SELECT" in payload.upper():
        return {"data": [{"id": 1, "user": "admin", "role": "admin"}]}
    
    return {"message": "Login failed", "error": "Invalid credentials"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
