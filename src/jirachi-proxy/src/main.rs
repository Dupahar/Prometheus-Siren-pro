
use axum::{
    body::Body,
    extract::{Request, State},
    response::{Response, IntoResponse},
    routing::{any, post, get}, // Added get/post for trap
    Router, Json, // Added Json
};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tracing::{info, warn, error};
use std::net::SocketAddr;
use serde_json::json; // Added json macro

// --- JSON Artifact Schemas ---

#[derive(Serialize, Deserialize, Debug)]
struct ThreatJudgment {
    artifact_type: String,
    threat_level: String,
    command: Command,
}

#[derive(Serialize, Deserialize, Debug)]
struct Command {
    action: String, // "BLOCK", "ALLOW", "DECEIVE"
    redirect_target: Option<String>,
}

// --- App State ---

struct AppState {
    brain_url: String,
    upstream_url: String,
    http_client: Client,
}

// --- THE HONEYPOT HANDLER (SIREN) ---
async fn honeypot_handler(req: Request<Body>) -> impl IntoResponse {
    warn!("!! [SIREN] ALERT: Attacker trapped in Honeypot!");
    warn!("!! [SIREN] Headers: {:?}", req.headers());
    
    (
        axum::http::StatusCode::OK, 
        Json(json!({
            "error": "Fatal DB Error",
            "debug_trace": "SELECT * FROM users WHERE admin = 1 failed.", // Fake info
            "suggestion": "Please contact sysadmin."
        }))
    )
}

// --- The Proxy Handler ---

async fn proxy_handler(
    State(state): State<Arc<AppState>>,
    mut req: Request<Body>,
) -> impl IntoResponse {
    let uri = req.uri().to_string();
    let method = req.method().to_string();
    
    // 1. The Sentinel (Local Triage)
    // Adding 'siren_test' for the demo
    let is_suspicious = uri.contains("admin") || uri.contains("UNION") || uri.contains("%27") || uri.contains("siren_test");
    
    if is_suspicious {
        info!("Sentinel: Detected suspicious pattern: {}", uri);
        
        // 2. The General (Escalation)
        let trace = format!("{} {}", method, uri);
        let payload = serde_json::json!({
            "trace": trace,
            "slm_score": 0.9
        });

        match state.http_client.post(&state.brain_url).json(&payload).send().await {
            Ok(resp) => {
                if let Ok(judgment) = resp.json::<ThreatJudgment>().await {
                    info!("General's Judgment: {:?}", judgment);
                    
                    if judgment.command.action == "BLOCK" {
                        return Response::builder()
                            .status(403)
                            .body(Body::from("Jirachi Shield: Request Blocked by Command."))
                            .unwrap();
                    }
                    
                    // --- SIREN DECEPTION LOGIC ---
                    if judgment.command.action == "DECEIVE" {
                        info!("<< COMMAND: DECEIVE. Rerouting to Siren.");
                        return Response::builder()
                            .status(axum::http::StatusCode::TEMPORARY_REDIRECT)
                            .header("Location", "/trap") // Send them to the trap
                            .body(Body::from("Redirecting for debug..."))
                            .unwrap();
                    }
                }
            }
            Err(e) => error!("Failed to reach General: {}", e),
        }
    }

    // 3. Forward to Consumer (Upstream)
    let path = req.uri().path();
    let query = req.uri().query().unwrap_or("");
    let target_url = format!("{}{}{}", state.upstream_url, path, if query.is_empty() { "".to_string() } else { format!("?{}", query) });

    match state.http_client.get(&target_url).send().await {
        Ok(upstream_resp) => {
             let status_u16 = upstream_resp.status().as_u16();
             let status = axum::http::StatusCode::from_u16(status_u16).unwrap_or(axum::http::StatusCode::INTERNAL_SERVER_ERROR);
             let bytes = upstream_resp.bytes().await.unwrap_or_default();
             
             Response::builder()
                .status(status)
                .body(Body::from(bytes))
                .unwrap()
        }
        Err(e) => {
             Response::builder()
                .status(502)
                .body(Body::from(format!("Upstream Error: {}", e)))
                .unwrap()
        }
    }
}

// --- Main Entry Point ---

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();
    
    let state = Arc::new(AppState {
        brain_url: "http://127.0.0.1:8000/analyze_threat".to_string(),
        upstream_url: "http://127.0.0.1:5000".to_string(),
        http_client: Client::new(),
    });

    let app = Router::new()
        .route("/trap", any(honeypot_handler)) // The Siren Trap
        .route("/*path", any(proxy_handler))   // The Shield
        .with_state(state);

    let addr = SocketAddr::from(([0, 0, 0, 0], 6161));
    info!("Jirachi Proxy (Axum) listening on {}", addr);
    
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
