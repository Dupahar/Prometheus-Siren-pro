#!/usr/bin/env python3
"""
Training Script for Prometheus-Siren ML Models.

Usage:
    # Quick train (XGBoost only)
    python scripts/train_model.py
    
    # Full training with both models
    python scripts/train_model.py --full
    
    # Custom dataset size
    python scripts/train_model.py --samples 500 --safe 1000
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def main():
    parser = argparse.ArgumentParser(description="Train threat detection models")
    parser.add_argument("--full", action="store_true", help="Train both XGBoost and DistilBERT")
    parser.add_argument("--samples", type=int, default=200, help="Attack samples per type")
    parser.add_argument("--safe", type=int, default=1000, help="Safe traffic samples")
    parser.add_argument("--output", type=str, default=None, help="Output directory")
    parser.add_argument("--include-qdrant", action="store_true", help="Include real attacks from Qdrant")
    args = parser.parse_args()
    
    console.print(Panel.fit(
        "[bold cyan]🔥 Prometheus-Siren ML Training[/bold cyan]\n"
        "Training threat detection models...",
        border_style="cyan",
    ))
    
    # Build dataset
    from src.ml.dataset import DatasetBuilder
    
    console.print("\n[bold]📊 Building Dataset...[/bold]")
    builder = DatasetBuilder()
    dataset = builder.build_full_dataset(
        attacks_per_type=args.samples,
        safe_samples=args.safe,
        include_qdrant=args.include_qdrant,
    )
    
    # Show distribution
    stats = dataset.stats()
    table = Table(title="Dataset Distribution")
    table.add_column("Label", style="cyan")
    table.add_column("Count", style="green")
    for label, count in stats.items():
        table.add_row(label, str(count))
    console.print(table)
    
    # Split dataset
    train_data, test_data = dataset.split(train_ratio=0.8)
    console.print(f"\nTrain: {len(train_data)} | Test: {len(test_data)}")
    
    # Train models
    from src.ml.trainer import ModelTrainer
    
    output_dir = Path(args.output) if args.output else Path(__file__).parent.parent / "src" / "ml" / "models"
    trainer = ModelTrainer(output_dir)
    
    results = {}
    
    # XGBoost (always train)
    console.print("\n[bold]🚀 Training XGBoost...[/bold]")
    try:
        xgb_path, xgb_metrics = trainer.train_xgboost(train_data, test_data, binary=True)
        results["xgboost"] = xgb_metrics
        console.print(f"[green]✓ XGBoost trained: {xgb_metrics.accuracy:.2%} accuracy[/green]")
    except Exception as e:
        console.print(f"[red]✗ XGBoost failed: {e}[/red]")
    
    # DistilBERT (optional)
    if args.full:
        console.print("\n[bold]🧠 Training DistilBERT...[/bold]")
        try:
            bert_path, bert_metrics = trainer.train_distilbert(train_data, test_data, binary=True)
            results["distilbert"] = bert_metrics
            console.print(f"[green]✓ DistilBERT trained: {bert_metrics.accuracy:.2%} accuracy[/green]")
        except Exception as e:
            console.print(f"[yellow]⚠ DistilBERT failed (optional): {e}[/yellow]")
    
    # Final summary
    console.print("\n")
    summary = Table(title="Training Results")
    summary.add_column("Model", style="cyan")
    summary.add_column("Accuracy", style="green")
    summary.add_column("Precision", style="blue")
    summary.add_column("Recall", style="magenta")
    summary.add_column("F1 Score", style="yellow")
    summary.add_column("Time", style="white")
    
    for name, metrics in results.items():
        summary.add_row(
            name,
            f"{metrics.accuracy:.2%}",
            f"{metrics.precision:.2%}",
            f"{metrics.recall:.2%}",
            f"{metrics.f1_score:.2%}",
            f"{metrics.training_time_seconds:.1f}s",
        )
    
    console.print(summary)
    console.print(Panel.fit(
        f"[bold green]✓ Models saved to {output_dir}[/bold green]",
        border_style="green",
    ))


if __name__ == "__main__":
    main()
