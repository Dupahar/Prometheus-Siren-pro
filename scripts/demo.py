# scripts/demo.py
"""
PROMETHEUS-SIREN DEMO SCRIPT
Demonstrates the complete attack detection and auto-patching flow.
Run with: python scripts/demo.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Fix Windows encoding for emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console(force_terminal=True, legacy_windows=False)


def banner():
    console.print(Panel.fit("""
[bold blue]🔥 PROMETHEUS-SIREN[/bold blue]
[dim]The Self-Evolving Cyber-Immune System[/dim]

[green]Autonomous Security Demonstration[/green]
""", title="Prometheus Security", box=box.ASCII))


def step(num: int, title: str):
    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
    console.print(f"[bold cyan]STEP {num}: {title}[/bold cyan]")
    console.print(f"[bold cyan]{'='*60}[/bold cyan]")


def demo_qdrant_connection():
    """Demo: Qdrant connection and collection setup."""
    step(1, "CONNECTING TO QDRANT")
    
    from src.core.qdrant_client import qdrant_manager
    from src.core.config import settings
    
    console.print("[dim]Connecting to Qdrant Cloud...[/dim]")
    qdrant_manager.ensure_collections()
    
    code_info = qdrant_manager.get_collection_info(settings.qdrant_code_collection)
    attack_info = qdrant_manager.get_collection_info(settings.qdrant_attack_collection)
    
    table = Table(title="Qdrant Collections")
    table.add_column("Collection", style="cyan")
    table.add_column("Points", style="green")
    table.add_column("Status", style="yellow")
    
    table.add_row("code_base", str(code_info["points_count"]), str(code_info["status"]))
    table.add_row("attack_memory", str(attack_info["points_count"]), str(attack_info["status"]))
    
    console.print(table)
    console.print("[bold green]✓ Qdrant connected and ready![/bold green]")


def demo_code_indexing():
    """Demo: Index the vulnerable app."""
    step(2, "INDEXING VULNERABLE APP")
    
    from src.indexer.indexer import code_indexer
    
    vuln_app = Path(__file__).parent.parent / "vulnerable_app"
    
    console.print(f"[dim]Scanning {vuln_app}...[/dim]")
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Indexing code...", total=None)
        stats = code_indexer.index_directory(vuln_app, incremental=False)
    
    console.print(f"[green]✓ Indexed {stats.files_indexed} files, {stats.chunks_created} code chunks[/green]")


def demo_semantic_search():
    """Demo: Semantic search for vulnerabilities."""
    step(3, "SEMANTIC VULNERABILITY SEARCH")
    
    from src.indexer.search import code_searcher
    
    queries = [
        "SQL injection vulnerability database query",
        "XSS cross-site scripting attack",
        "path traversal file read vulnerability",
    ]
    
    for query in queries:
        console.print(f"\n[yellow]Query:[/yellow] {query}")
        results = code_searcher.search(query, top_k=2)
        
        for r in results:
            console.print(f"  [green]→[/green] {r.function_name} (score: {r.score:.3f})")
            console.print(f"    [dim]{r.file_path}:{r.start_line}[/dim]")


def demo_attack_detection():
    """Demo: Real-time attack detection."""
    step(4, "ATTACK DETECTION")
    
    from src.gateway.threat_scorer import threat_scorer
    
    payloads = [
        ("Hello World", "Safe text"),
        ("admin' OR '1'='1' --", "SQL Injection"),
        ("<script>alert('XSS')</script>", "XSS Attack"),
        ("../../../etc/passwd", "Path Traversal"),
    ]
    
    table = Table(title="Threat Assessment")
    table.add_column("Payload", style="white", max_width=30)
    table.add_column("Type", style="cyan")
    table.add_column("Score", style="yellow")
    table.add_column("Action", style="red")
    
    for payload, expected_type in payloads:
        result = threat_scorer.score(payload)
        action_color = "green" if result.action == "allow" else "red"
        table.add_row(
            payload[:30] + "..." if len(payload) > 30 else payload,
            result.attack_type or "None",
            f"{result.score:.2f}",
            f"[{action_color}]{result.action.upper()}[/{action_color}]"
        )
    
    console.print(table)


def demo_honeypot():
    """Demo: Honeypot deception."""
    step(5, "HONEYPOT DECEPTION")
    
    from src.siren.sandbox import sandbox_manager
    
    console.print("[dim]Creating sandbox session for attacker...[/dim]")
    session = sandbox_manager.create_session("10.0.0.1")
    
    console.print(f"[green]✓ Session created: {session.session_id}[/green]")
    
    # Simulate SQL injection attack
    console.print("\n[yellow]Attacker executes:[/yellow] SELECT * FROM users WHERE '1'='1'")
    result = session.fake_sql.execute("SELECT * FROM users WHERE '1'='1'")
    
    console.print(f"[red]Honeypot returns {len(result.get('rows', []))} fake records![/red]")
    
    # Show fake data
    table = Table(title="Fake User Data (Honeypot)")
    table.add_column("ID")
    table.add_column("Username")
    table.add_column("Email")
    
    for row in result.get("rows", [])[:3]:
        table.add_row(str(row["id"]), row["username"], row["email"])
    
    console.print(table)
    
    # Simulate file read attack
    console.print("\n[yellow]Attacker reads:[/yellow] /etc/passwd")
    file_result = session.fake_fs.read_file("/etc/passwd")
    console.print(f"[red]Honeypot returns fake passwd file![/red]")
    console.print(f"[dim]{file_result['content'][:200]}...[/dim]")
    
    # Attack summary
    summary = session.fake_sql.get_attack_summary()
    console.print(f"\n[green]✓ Recorded {summary['malicious_queries']} malicious queries[/green]")


def demo_patch_generation():
    """Demo: AI-powered patch generation."""
    step(6, "AI PATCH GENERATION")
    
    from src.prometheus.patch_generator import patch_generator
    
    vulnerable_code = '''
def login(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    return cursor.fetchone()
'''
    
    console.print("[yellow]Vulnerable Code:[/yellow]")
    console.print(f"[red]{vulnerable_code}[/red]")
    
    console.print("\n[dim]Generating patch with Gemini...[/dim]")
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task("Thinking...", total=None)
        patch = patch_generator.generate_security_patch(
            vulnerability_type="sql_injection",
            vulnerable_code=vulnerable_code,
            context="Login function vulnerable to SQL injection",
        )
    
    if patch:
        console.print(f"\n[green]✓ Patch generated with {patch.confidence:.0%} confidence[/green]")
        console.print(f"\n[cyan]Explanation:[/cyan]\n{patch.explanation}")
        console.print(f"\n[cyan]Secure Code:[/cyan]")
        console.print(f"[green]{patch.patched_code}[/green]")
    else:
        console.print("[yellow]⚠ Patch generation paused (API Rate Limit)[/yellow]")


def demo_attack_memory():
    """Demo: Attack memory and learning."""
    step(7, "ATTACK MEMORY & LEARNING")
    
    from src.siren.recorder import attack_recorder
    
    # Record attack
    console.print("[dim]Recording attack pattern to Qdrant...[/dim]")
    record = attack_recorder.record_attack(
        session_id="demo-session",
        attacker_ip="10.0.0.1",
        attack_type="sql_injection",
        payload="' OR '1'='1' UNION SELECT password FROM users --",
        threat_level="critical",
    )
    console.print(f"[green]✓ Attack recorded: {record.id}[/green]")
    
    # Search for similar
    console.print("\n[dim]Searching for similar attacks...[/dim]")
    similar = attack_recorder.find_similar_attacks(
        payload="SELECT * FROM users WHERE 1=1",
        top_k=3,
    )
    
    console.print(f"[green]+ Found {len(similar)} similar patterns in memory[/green]")
    for s in similar:
        console.print(f"  [cyan]->[/cyan] {s['attack_type']} (similarity: {s['score']:.3f})")


def demo_evolution():
    """Demo: Evolution insights."""
    step(8, "EVOLUTION INSIGHTS")
    
    from src.evolution.feedback_loop import evolution_engine
    
    console.print("[dim]Analyzing attack patterns for evolution...[/dim]")
    
    insights = evolution_engine.get_evolution_insights()
    
    table = Table(title="Evolution Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Attacks Processed", str(insights["total_attacks_processed"]))
    table.add_row("Patterns in Memory", str(insights["patterns_in_memory"]))
    table.add_row("Vulnerabilities Found", str(insights["vulnerabilities_identified"]))
    
    console.print(table)
    
    # Priority patches
    suggestions = evolution_engine.suggest_priority_patches()
    if suggestions:
        console.print("\n[yellow]Priority Patches Suggested:[/yellow]")
        for s in suggestions[:3]:
            console.print(f"  [{s['priority']}] {s['attack_type']} - {s['attacks_seen']} attacks seen")
    else:
        console.print("\n[dim]No patch priorities yet - need more attack data[/dim]")
    
    console.print(f"\n[green]+ Evolution loop active - system improving continuously![/green]")


def summary():
    """Final summary."""
    console.print("\n")
    console.print(Panel.fit("""
[bold green]DEMONSTRATION COMPLETE[/bold green]

[cyan]Capabilities Demonstrated:[/cyan]
1. Qdrant Cloud integration with dual vector collections
2. AST-aware code indexing with Gemini embeddings  
3. Semantic vulnerability search by natural language
4. Real-time threat scoring (pattern + semantic)
5. Honeypot deception with realistic fake data
6. AI-powered security patch generation
7. Attack memory for instant pattern recognition
8. Continuous evolution from captured attacks

[dim]Prometheus-Siren: Detection + Deception + Evolution[/dim]
""", title="Summary", box=box.ASCII))


def main():
    banner()
    
    try:
        demo_qdrant_connection()
        demo_code_indexing()
        demo_semantic_search()
        demo_attack_detection()
        demo_honeypot()
        demo_patch_generation()
        demo_attack_memory()
        demo_evolution()
        summary()
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
