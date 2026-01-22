# scripts/run_siren.py
"""
CLI: Run the Siren Gateway.
Usage: python scripts/run_siren.py --port 8080
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console

console = Console()


def main():
    parser = argparse.ArgumentParser(description="Run the Siren Gateway & Honeypot")
    parser.add_argument("--host", "-H", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", "-p", type=int, default=8080, help="Port to bind to")
    parser.add_argument("--backend", "-b", default="http://localhost:5000", 
                        help="Backend app URL to proxy safe traffic to")
    
    args = parser.parse_args()
    
    console.print("\n[bold blue]🧜 Siren Gateway[/bold blue]")
    console.print("The Infinite Honeypot\n")
    console.print(f"[green]Gateway:[/green] http://{args.host}:{args.port}")
    console.print(f"[green]Backend:[/green] {args.backend}")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    from src.gateway.router import traffic_router
    from src.gateway.ingress import run_gateway
    
    # Configure router
    traffic_router.app_backend_url = args.backend
    
    # Run gateway
    run_gateway(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
