# scripts/run_prometheus.py
"""
CLI: Run the Prometheus Agent.
Usage: python scripts/run_prometheus.py --watch ./logs/app.log
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from rich.console import Console

from src.core.qdrant_client import qdrant_manager
from src.prometheus.agent import prometheus_agent


console = Console()


def main():
    parser = argparse.ArgumentParser(description="Run the Prometheus Auto-Healing Agent")
    parser.add_argument("--watch", "-w", help="Log file to watch for errors")
    parser.add_argument("--demo", "-d", action="store_true", help="Run demo mode with sample error")
    
    args = parser.parse_args()
    
    console.print("\n[bold blue]🔥 Prometheus Agent[/bold blue]")
    console.print("The Self-Healing Immune System\n")
    
    # Ensure collections exist
    qdrant_manager.ensure_collections()
    
    if args.demo:
        # Demo mode: simulate an error
        console.print("[yellow]Running in demo mode...[/yellow]\n")
        
        from src.prometheus.log_parser import ParsedError, StackFrame
        
        demo_error = ParsedError(
            error_type="ZeroDivisionError",
            error_message="division by zero",
            stack_frames=[
                StackFrame(
                    file_path="/app/calculator.py",
                    line_number=42,
                    function_name="divide",
                    code_context="result = a / b",
                ),
            ],
            raw_traceback="""Traceback (most recent call last):
  File "/app/calculator.py", line 42, in divide
    result = a / b
ZeroDivisionError: division by zero
""",
        )
        
        console.print(f"[dim]Simulating error: {demo_error.full_error}[/dim]")
        
        proposal = prometheus_agent.handle_error(demo_error)
        
        if proposal:
            console.print(f"\n[green]✓ Generated patch proposal: {proposal.id}[/green]")
            console.print(f"  Confidence: {proposal.patch.confidence:.0%}")
            console.print(f"  File: {proposal.patch.file_path}")
        else:
            console.print("[red]No patch generated (codebase may not be indexed)[/red]")
    
    elif args.watch:
        # Watch mode
        log_path = Path(args.watch)
        console.print(f"[green]Watching:[/green] {log_path}")
        console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        
        prometheus_agent.watch_logs(str(log_path))
    
    else:
        console.print("[yellow]Use --watch <log_path> or --demo[/yellow]")
        parser.print_help()


if __name__ == "__main__":
    main()
