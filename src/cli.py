# src/cli.py
"""
Prometheus-Siren: Unified Command Line Interface.
One command to rule them all.
"""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
<<<<<<< HEAD
=======
import asyncio
>>>>>>> fresh_submission

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

<<<<<<< HEAD
=======
from src.prometheus.researcher import researcher as deep_researcher

>>>>>>> fresh_submission
app = typer.Typer(
    name="prometheus-siren",
    help="🔥 Self-Evolving Cyber-Immune System",
    add_completion=False,
)
console = Console()


def banner():
    """Display the banner."""
    console.print(Panel.fit("""
[bold red]🔥 PROMETHEUS-SIREN[/bold red]
[dim]The Self-Evolving Cyber-Immune System[/dim]
[cyan]Detection • Deception • Evolution[/cyan]
""", border_style="red"))


@app.command()
def demo():
    """Run the full demonstration."""
    banner()
    console.print("\n[yellow]Running full demo...[/yellow]\n")
    
    # Import and run demo
    from scripts.demo import main as demo_main
    demo_main()


@app.command()
def index(
    path: str = typer.Argument(..., help="Path to codebase to index"),
    incremental: bool = typer.Option(False, "--incremental", "-i", help="Incremental indexing"),
    clear: bool = typer.Option(False, "--clear", "-c", help="Clear existing index"),
):
    """Index a codebase into Qdrant."""
    banner()
    
    from src.core.qdrant_client import qdrant_manager
    from src.indexer.indexer import code_indexer
    
    path = Path(path).resolve()
    console.print(f"\n[cyan]Indexing:[/cyan] {path}")
    
    qdrant_manager.ensure_collections()
    
    if clear:
        console.print("[yellow]Clearing existing index...[/yellow]")
        code_indexer.clear_index()
    
    stats = code_indexer.index_directory(path, incremental=incremental)
    
    table = Table(title="Indexing Complete")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Files Indexed", str(stats.files_indexed))
    table.add_row("Chunks Created", str(stats.chunks_created))
    
    console.print(table)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(5, "--top", "-k", help="Number of results"),
):
    """Semantic search in indexed codebase."""
    banner()
    
    from src.indexer.search import code_searcher
    
    console.print(f"\n[cyan]Searching:[/cyan] {query}\n")
    
    results = code_searcher.search(query, top_k=top_k)
    
    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return
    
    for r in results:
        console.print(f"[green]→[/green] {r.function_name} [dim](score: {r.score:.3f})[/dim]")
        console.print(f"   [dim]{r.file_path}:{r.start_line}[/dim]")


@app.command()
def gateway(
    host: str = typer.Option("0.0.0.0", "--host", "-H", help="Host to bind"),
    port: int = typer.Option(8080, "--port", "-p", help="Port to bind"),
    backend: str = typer.Option("http://localhost:5000", "--backend", "-b", help="Backend URL"),
):
    """Start the Siren Gateway."""
    banner()
    
    from src.gateway.router import traffic_router
    from src.gateway.ingress import run_gateway
    
    console.print(f"\n[green]Starting Gateway[/green]")
    console.print(f"  Gateway: http://{host}:{port}")
    console.print(f"  Backend: {backend}")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    traffic_router.app_backend_url = backend
    run_gateway(host=host, port=port)


@app.command()
def watch(
    log_path: str = typer.Argument(..., help="Log file to watch"),
):
    """Watch logs and auto-generate patches."""
    banner()
    
    from src.prometheus.agent import prometheus_agent
    
    console.print(f"\n[cyan]Watching:[/cyan] {log_path}")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    prometheus_agent.watch_logs(log_path)


@app.command()
def status():
    """Show system status."""
    banner()
    
    from src.core.qdrant_client import qdrant_manager
    from src.core.config import settings
    from src.siren.sandbox import sandbox_manager
    from src.siren.recorder import attack_recorder
    
    console.print("\n[bold]System Status[/bold]\n")
    
    # Qdrant
    try:
        qdrant_manager.ensure_collections()
        code_info = qdrant_manager.get_collection_info(settings.qdrant_code_collection)
        attack_info = qdrant_manager.get_collection_info(settings.qdrant_attack_collection)
        
        table = Table(title="Qdrant Collections")
        table.add_column("Collection")
        table.add_column("Points")
        table.add_row("code_base", str(code_info["points_count"]))
        table.add_row("attack_memory", str(attack_info["points_count"]))
        console.print(table)
    except Exception as e:
        console.print(f"[red]Qdrant: {e}[/red]")
    
    # Sessions
    sessions = sandbox_manager.get_active_sessions()
    console.print(f"\n[cyan]Active Honeypot Sessions:[/cyan] {len(sessions)}")
    
    # Attack stats
    stats = attack_recorder.get_attack_statistics()
    console.print(f"[cyan]Total Attacks Recorded:[/cyan] {stats.get('total', 0)}")


@app.command()
def evolve():
    """Show evolution insights."""
    banner()
    
    from src.evolution.feedback_loop import evolution_engine
    
    console.print("\n[bold]Evolution Insights[/bold]\n")
    
    insights = evolution_engine.get_evolution_insights()
    
    table = Table()
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Attacks Processed", str(insights["total_attacks_processed"]))
    table.add_row("Patterns in Memory", str(insights["patterns_in_memory"]))
    table.add_row("Vulnerabilities Found", str(insights["vulnerabilities_identified"]))
    
    console.print(table)
    
    # Priority patches
    console.print("\n[bold]Priority Patches[/bold]")
    suggestions = evolution_engine.suggest_priority_patches()
    
    if suggestions:
        for s in suggestions[:5]:
            console.print(f"  [{s['priority']}] {s['attack_type']} - {s['attacks_seen']} attacks")
            for f in s.get("suggested_files", []):
                console.print(f"    → {f['function']} in {f['file']}")
    else:
        console.print("  [dim]No suggestions yet. Run some attacks through the honeypot![/dim]")


@app.command()
def train(
    full: bool = typer.Option(False, "--full", "-f", help="Train both XGBoost and DistilBERT"),
    samples: int = typer.Option(200, "--samples", "-s", help="Attack samples per type"),
    safe: int = typer.Option(1000, "--safe", help="Safe traffic samples"),
):
    """Train threat detection ML models."""
    banner()
    
    from src.ml.dataset import DatasetBuilder
    from src.ml.trainer import ModelTrainer
    
    console.print("\n[bold]🧠 Training ML Models[/bold]\n")
    
    # Build dataset
    console.print("[cyan]Building dataset...[/cyan]")
    builder = DatasetBuilder()
    dataset = builder.build_full_dataset(
        attacks_per_type=samples,
        safe_samples=safe,
        include_qdrant=False,
    )
    
    # Show stats
    stats = dataset.stats()
    table = Table(title="Dataset Distribution")
    table.add_column("Label", style="cyan")
    table.add_column("Count", style="green")
    for label, count in stats.items():
        table.add_row(label, str(count))
    console.print(table)
    
    # Split and train
    train_data, test_data = dataset.split(train_ratio=0.8)
    console.print(f"\nTrain: {len(train_data)} | Test: {len(test_data)}")
    
    trainer = ModelTrainer()
    
    # XGBoost
    console.print("\n[cyan]Training XGBoost...[/cyan]")
    try:
        xgb_path, xgb_metrics = trainer.train_xgboost(train_data, test_data, binary=True)
        console.print(f"[green]✓ XGBoost: {xgb_metrics.accuracy:.2%} accuracy[/green]")
    except Exception as e:
        console.print(f"[red]✗ XGBoost failed: {e}[/red]")
    
    # DistilBERT (optional)
    if full:
        console.print("\n[cyan]Training DistilBERT...[/cyan]")
        try:
            bert_path, bert_metrics = trainer.train_distilbert(train_data, test_data, binary=True)
            console.print(f"[green]✓ DistilBERT: {bert_metrics.accuracy:.2%} accuracy[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ DistilBERT failed: {e}[/yellow]")
    
    console.print("\n[green]Training complete![/green]")


@app.command()
def classify(
    payload: str = typer.Argument(..., help="Payload to classify"),
    mode: str = typer.Option("adaptive", "--mode", "-m", help="Mode: fast/accurate/adaptive/ensemble"),
):
    """Classify a payload using local ML."""
    banner()
    
    from src.ml.classifier import ThreatClassifier
    
    classifier = ThreatClassifier(mode=mode)
    result = classifier.classify(payload)
    
    console.print("\n[bold]Classification Result[/bold]\n")
    
    color = "red" if result.prediction == "attack" else "green"
    console.print(f"Prediction: [{color}]{result.prediction.upper()}[/{color}]")
    console.print(f"Confidence: {result.confidence:.2%}")
    if result.attack_type:
        console.print(f"Attack Type: {result.attack_type}")
    console.print(f"Expert Used: {result.expert_used}")
    console.print(f"Time: {result.inference_time_ms:.2f}ms")


@app.command(name="ml-status")
def ml_status():
    """Show ML model status and statistics."""
    banner()
    
    from pathlib import Path
    
    console.print("\n[bold]ML Model Status[/bold]\n")
    
    model_dir = Path(__file__).parent / "ml" / "models"
    
    table = Table()
    table.add_column("Model", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Size")
    
    # Check XGBoost
    xgb_path = model_dir / "xgboost_threat.pkl"
    if xgb_path.exists():
        size_kb = xgb_path.stat().st_size / 1024
        table.add_row("XGBoost", "✓ Loaded", f"{size_kb:.1f} KB")
    else:
        table.add_row("XGBoost", "✗ Not trained", "-")
    
    # Check DistilBERT
    bert_path = model_dir / "distilbert_threat"
    if bert_path.exists():
        size_mb = sum(f.stat().st_size for f in bert_path.rglob("*") if f.is_file()) / (1024 * 1024)
        table.add_row("DistilBERT", "✓ Loaded", f"{size_mb:.1f} MB")
    else:
        table.add_row("DistilBERT", "✗ Not trained", "-")
    
    console.print(table)
    
    # Show hybrid scorer stats
    try:
        from src.ml.hybrid_scorer import hybrid_scorer
        stats = hybrid_scorer.get_stats()
        
        if stats["total_requests"] > 0:
            console.print("\n[bold]Hybrid Scorer Statistics[/bold]")
            console.print(f"  Total Requests: {stats['total_requests']}")
            console.print(f"  ML-Only Decisions: {stats['ml_only_decisions']} ({stats.get('ml_only_ratio', 0):.1%})")
            console.print(f"  Gemini Escalations: {stats['gemini_escalations']} ({stats.get('escalation_ratio', 0):.1%})")
    except Exception:
        pass


@app.command()
<<<<<<< HEAD
=======
def research(
    target: str = typer.Argument(..., help="Threat signature or topic to investigate"),
):
    """
    🕵️ Launch a Deep Research mission on a specific threat.
    """
    banner()
    console.print(f"[bold cyan]🚀 Launching Deep Research Agent for:[/bold cyan] {target}")
    
    with console.status("[bold green]Agent is Planning & Searching...[/bold green]"):
        report = deep_researcher.investigate(target)
    
    console.print("\n[bold yellow]📋 Mission Report[/bold yellow]")
    console.print(Panel(report.findings, title="Findings", border_style="green"))
    
    table = Table(title="Sources")
    table.add_column("URL/Source", style="cyan")
    for source in report.sources:
        table.add_row(source)
    console.print(table)
    
    console.print(Panel(report.suggested_action, title="RECOMMENDED ACTION", border_style="bold red"))
    console.print(f"[dim]Confidence: {report.confidence:.0%}[/dim]\n")

@app.command()
>>>>>>> fresh_submission
def test():
    """Run the test suite."""
    banner()
    import subprocess
    console.print("\n[yellow]Running tests...[/yellow]\n")
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"])


if __name__ == "__main__":
    app()
