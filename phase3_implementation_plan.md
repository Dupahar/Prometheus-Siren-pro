# Implementation Plan - Phase 3: The Hive Mind Dashboard

## 🥅 Goal
Create a visual "Command Center" that demonstrates the global immunity network.
The dashboard will connect to the `Brain` to visualize real-time attacks layout and the "Evolution" status.

## 🏗️ Architecture
- **Service Name:** `P-Dashboard`
- **Tech Stack:**
    - **Backend:** Python (FastAPI) [Lightweight, same stack as others]
    - **Frontend:** HTML5 + Vue.js (CDN) + TailwindCSS (CDN) [No build step needed, fast iteration]
    - **Visualization:** Mapbox / Leaflet for "Global Map", Chart.js for stats.

## 📋 Features
1.  **Global Attack Map:** Blip on the map when an attack is reported (Source IP geolocation).
2.  **Live Log Feed:** Streaming list of blocked requests.
3.  **Immunity Status:** Count of "Patched Vulnerabilities" and "Vectors Learned".

## 🚀 Implementation Steps

### 1. `services/dashboard_service.py`
A simple FastAPI app that:
- Serves static files from `commercial/dashboard/`.
- Proxies `/api/stats` -> `Brain`/stats.

### 2. The Frontend (`dashboard/index.html`)
A Single Page App (SPA) containing:
- **Hero Section:** "Prometheus-Siren Global Immunity System".
- **Real-Time Map:** (Mocked for demo with random lat/longs if geo-ip missing).
- **Attack Terminal:** A cyberpunk-style log viewer.

### 3. Orchestration
Add `dashboard` service to `docker-compose.yml` exposed on port `8080`.

---
> [!TIP]
> This is what sells the product. Executives don't read logs; they watch dashboards.
