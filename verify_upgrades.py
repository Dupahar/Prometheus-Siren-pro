import sys
import os
from pathlib import Path
from rich.console import Console

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.prometheus.thought_signature import ThoughtSignature
# from src.prometheus.researcher import DeepResearchAgent 
# (Cannot easily import DeepResearchAgent if it needs API key at init and env is not loaded, 
# but let's try assuming env is loaded or we mock it)

console = Console()

def test_thought_signature():
    console.print("[bold cyan]Testing Thought Signatures...[/bold cyan]")
    sig = ThoughtSignature(
        reasoning_trace="Evaluated IP 192.168.1.5 against threat intel. Pattern matches CVE-2023-XXXX.",
        action_plan="Block IP and rotate validation key.",
        confidence=0.95
    )
    sig.sign()
    
    console.print(f"Generated Signature Hash: {sig.signature_hash}")
    
    # Verify
    if sig.verify():
        console.print("[bold green]✅ Signature Verification Passed[/bold green]")
    else:
        console.print("[bold red]❌ Signature Verification Failed[/bold red]")
        
    # Tamper
    sig.reasoning_trace = "Hacked trace"
    if not sig.verify():
        console.print("[bold green]✅ Tamper Detection Passed[/bold green]")
    else:
        console.print("[bold red]❌ Tamper Detection Failed[/bold red]")

if __name__ == "__main__":
    test_thought_signature()
