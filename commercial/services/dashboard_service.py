import os
import random
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Prometheus Hive Mind Dashboard")

# CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock Data Generator (Simulating connection to Brain/Qdrant)
def get_mock_stats():
    return {
        "active_sidecars": 12,
        "total_attacks_blocked": 14502,
        "global_immunity_score": 98.4,
        "vectors_learned": 850
    }

def get_recent_attacks():
    attack_types = ["SQL Injection", "XSS", "Path Traversal", "RCE"]
    locations = [
        {"lat": 37.7749, "lng": -122.4194, "city": "San Francisco"},
        {"lat": 51.5074, "lng": -0.1278, "city": "London"},
        {"lat": 35.6762, "lng": 139.6503, "city": "Tokyo"},
        {"lat": 40.7128, "lng": -74.0060, "city": "New York"},
        {"lat": 19.0760, "lng": 72.8777, "city": "Mumbai"},
    ]
    
    attacks = []
    for _ in range(5):
        loc = random.choice(locations)
        attacks.append({
            "timestamp": "Just now",
            "type": random.choice(attack_types),
            "source": loc["city"],
            "lat": loc["lat"], 
            "lng": loc["lng"],
            "status": "BLOCKED"
        })
    return attacks

@app.get("/api/stats")
async def stats():
    return {
        "metrics": get_mock_stats(),
        "live_feed": get_recent_attacks()
    }

# Serve SPA
# In docker, static files are at /app/dashboard
static_path = os.path.join(os.path.dirname(__file__), "..", "dashboard")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

@app.get("/")
async def read_index():
    index_path = os.path.join(static_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Dashboard UI not built yet"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
