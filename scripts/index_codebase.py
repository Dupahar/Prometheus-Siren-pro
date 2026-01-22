# scripts/index_codebase.py
"""
CLI: Index a Python codebase into Qdrant.
Usage: python scripts/index_codebase.py --path ./your_project
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from rich.console import Console
from rich.table import Table

from src.core.qdrant_client import qdrant_manager
from src.indexer.indexer import code_indexer


console = Console()


def main():
    parser = argparse.ArgumentParser(description="Index a Python codebase into Qdrant")
    parser.add_argument("--path", "-p", required=True, help="Path to directory to index")
    parser.add_argument("--incremental", "-i", action="store_true", help="Incremental indexing")
    parser.add_argument("--clear", "-c", action="store_true", help="Clear index before indexing")
    
    args = parser.parse_args()
    
    path = Path(args.path).resolve()
    
    if not path.exists():
        console.print(f"[red]Error:[/red] Path does not exist: {path}")
        sys.exit(1)
    
    console.print(f"\n[bold blue]🔍 Prometheus Code Indexer[/bold blue]")
    console.print(f"Indexing: [green]{path}[/green]\n")
    
    # Ensure collections exist
    console.print("Connecting to Qdrant...")
    qdrant_manager.ensure_collections()
    
    # Clear if requested
    if args.clear:
        console.print("[yellow]Clearing existing index...[/yellow]")
        code_indexer.clear_index()
    
    # Index
    console.print("Indexing codebase...")
    stats = code_indexer.index_directory(path, incremental=args.incremental)
    
    # Display results
    table = Table(title="Indexing Complete")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Files Scanned", str(stats.files_scanned))
    table.add_row("Files Indexed", str(stats.files_indexed))
    table.add_row("Files Skipped", str(stats.files_skipped))
    table.add_row("Chunks Created", str(stats.chunks_created))
    table.add_row("Errors", str(len(stats.errors)))
    
    console.print(table)
    
    if stats.errors:
        console.print("\n[red]Errors:[/red]")
        for error in stats.errors[:5]:
            console.print(f"  • {error}")
    
    console.print("\n[bold green]✓ Indexing complete![/bold green]")


if __name__ == "__main__":
    main()
