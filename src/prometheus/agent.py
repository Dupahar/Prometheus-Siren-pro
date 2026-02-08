# src/prometheus/agent.py
"""
Prometheus Agent: The Main Orchestrator.
Connects all components into a self-healing system.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable
from loguru import logger

from src.core.config import settings
from src.prometheus.thought_signature import ThoughtSignature
from src.indexer.search import code_searcher, SearchResult
from .log_parser import log_parser, ParsedError
from .patch_generator import patch_generator, PatchResult
from .validator import patch_validator, ValidationResult


@dataclass
class PatchProposal:
    """A complete patch proposal ready for human review."""
    id: str
    timestamp: datetime
    error: ParsedError
    search_results: list[SearchResult]
    patch: PatchResult
    validation: ValidationResult
    status: str = "pending"  # pending, approved, rejected, applied
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage/display."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "error_type": self.error.error_type,
            "error_message": self.error.error_message,
            "file_path": self.patch.file_path,
            "confidence": self.patch.confidence,
            "explanation": self.patch.explanation,
            "status": self.status,
            "is_valid": self.validation.is_valid,
            "thought_signature": self.patch.thought_signature.signature_hash if self.patch.thought_signature else None
        }


class PrometheusAgent:
    """
    The Prometheus Agent: Self-healing immune system.
    
    Capabilities:
    1. Monitor logs for errors
    2. Semantically search codebase for relevant code
    3. Generate patches using Gemini
    4. Validate patches for safety
    5. Queue for human approval
    """
    
    def __init__(self):
        """Initialize the Prometheus Agent."""
        self.proposals: list[PatchProposal] = []
        self._proposal_counter = 0
        self._callbacks: list[Callable[[PatchProposal], None]] = []
    
    def on_proposal(self, callback: Callable[[PatchProposal], None]) -> None:
        """Register a callback for new proposals."""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self, proposal: PatchProposal) -> None:
        """Notify all registered callbacks of a new proposal."""
        for callback in self._callbacks:
            try:
                callback(proposal)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    def handle_error(self, error: ParsedError) -> Optional[PatchProposal]:
        """
        Handle a detected error: search, patch, validate, propose.
        
        This is the main entry point when an error is detected.
        
        Args:
            error: Parsed error from logs
            
        Returns:
            PatchProposal if generation succeeded, None otherwise
        """
        logger.info(f"Handling error: {error.full_error}")
        
        # Step 1: Search for relevant code
        search_results = code_searcher.search_by_error(
            error_type=error.error_type,
            error_message=error.error_message,
            stack_trace=error.raw_traceback,
            top_k=5,
        )
        
        if not search_results:
            logger.warning(f"No relevant code found for error: {error.error_type}")
            return None
        
        logger.debug(f"Found {len(search_results)} relevant code chunks")
        
        # Step 2: Get full code context
        top_result = search_results[0]
        full_code = code_searcher.get_full_code(top_result)
        
        # Step 3: Generate patch
        patch = patch_generator.generate_patch(
            error=error,
            search_results=search_results,
            full_code=full_code,
        )
        
        if not patch:
            logger.warning("Failed to generate patch")
            return None
        
        logger.info(f"Generated patch with {patch.confidence:.0%} confidence")
        
        # Step 4: Validate patch
        validation = patch_validator.validate(patch, run_tests=False)
        
        if not validation.syntax_valid:
            logger.error("Generated patch has syntax errors")
            return None
        
        # Step 5: Create proposal
        self._proposal_counter += 1
        proposal = PatchProposal(
            id=f"PROM-{self._proposal_counter:04d}",
            timestamp=datetime.now(),
            error=error,
            search_results=search_results,
            patch=patch,
            validation=validation,
        )
        
        self.proposals.append(proposal)
        self._notify_callbacks(proposal)
        
        logger.success(f"Created patch proposal: {proposal.id}")
        return proposal
    
    def approve_proposal(self, proposal_id: str) -> bool:
        """
        Approve a patch proposal.
        
        Args:
            proposal_id: ID of the proposal to approve
            
        Returns:
            True if approved successfully
        """
        proposal = self._find_proposal(proposal_id)
        if not proposal:
            logger.error(f"Proposal not found: {proposal_id}")
            return False
        
        if proposal.status != "pending":
            logger.warning(f"Proposal {proposal_id} is already {proposal.status}")
            return False
        
        proposal.status = "approved"
        logger.info(f"Approved proposal: {proposal_id}")
        return True
    
    def reject_proposal(self, proposal_id: str, reason: str = "") -> bool:
        """
        Reject a patch proposal.
        
        Args:
            proposal_id: ID of the proposal to reject
            reason: Optional rejection reason
            
        Returns:
            True if rejected successfully
        """
        proposal = self._find_proposal(proposal_id)
        if not proposal:
            logger.error(f"Proposal not found: {proposal_id}")
            return False
        
        proposal.status = "rejected"
        logger.info(f"Rejected proposal: {proposal_id} ({reason})")
        return True
    
    def apply_proposal(self, proposal_id: str) -> bool:
        """
        Apply an approved patch to the codebase.
        
        Args:
            proposal_id: ID of the proposal to apply
            
        Returns:
            True if applied successfully
        """
        proposal = self._find_proposal(proposal_id)
        if not proposal:
            logger.error(f"Proposal not found: {proposal_id}")
            return False
        
        if proposal.status != "approved":
            logger.error(f"Proposal {proposal_id} must be approved first")
            return False
        
        try:
            # Read original file
            file_path = Path(proposal.patch.file_path)
            original_content = file_path.read_text(encoding="utf-8")
            original_lines = original_content.splitlines(keepends=True)
            
            # Apply patch
            start = proposal.patch.start_line - 1
            end = proposal.patch.end_line
            
            new_lines = (
                original_lines[:start] +
                [proposal.patch.patched_code + "\n"] +
                original_lines[end:]
            )
            
            # Write back
            file_path.write_text("".join(new_lines), encoding="utf-8")
            
            proposal.status = "applied"
            logger.success(f"Applied patch {proposal_id} to {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to apply patch: {e}")
            return False
    
    def _find_proposal(self, proposal_id: str) -> Optional[PatchProposal]:
        """Find a proposal by ID."""
        for proposal in self.proposals:
            if proposal.id == proposal_id:
                return proposal
        return None
    
    def watch_logs(self, log_path: Optional[str] = None) -> None:
        """
        Watch a log file for errors and auto-generate proposals.
        
        Args:
            log_path: Path to log file (default: from settings)
        """
        log_path = log_path or settings.prometheus_log_path
        
        logger.info(f"Starting Prometheus Agent, watching: {log_path}")
        
        def on_error(error: ParsedError):
            """Handle detected errors."""
            proposal = self.handle_error(error)
            if proposal:
                self._print_proposal_summary(proposal)
        
        # Start watching
        log_parser.watch_file(log_path, on_error)
    
    def _print_proposal_summary(self, proposal: PatchProposal) -> None:
        """Print a summary of a new proposal."""
        print("\n" + "=" * 60)
        print(f"🔧 NEW PATCH PROPOSAL: {proposal.id}")
        print("=" * 60)
        print(f"Error: {proposal.error.full_error}")
        print(f"File: {proposal.patch.file_path}")
        print(f"Lines: {proposal.patch.start_line}-{proposal.patch.end_line}")
        print(f"Confidence: {proposal.patch.confidence:.0%}")
        print("-" * 60)
        if proposal.patch.thought_signature:
            sig = proposal.patch.thought_signature
            print(f"🧠 THOUGHT SIGNATURE: Verified")
            print(f"Hash: {sig.signature_hash[:16]}...")
            print(f"Trace: {sig.reasoning_trace[:100]}...")
            print("-" * 60)
        print("Explanation:")
        print(proposal.patch.explanation)
        print("-" * 60)
        print("Patch:")
        print(proposal.patch.unified_diff[:500])
        print("=" * 60)
        if settings.prometheus_approval_required:
            print("⚠️  Human approval required. Use approve_proposal() to apply.")
        print()
    
    def get_pending_proposals(self) -> list[PatchProposal]:
        """Get all pending proposals."""
        return [p for p in self.proposals if p.status == "pending"]
    
    def export_proposals(self, output_path: str) -> None:
        """Export all proposals to a JSON file."""
        data = [p.to_dict() for p in self.proposals]
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Exported {len(data)} proposals to {output_path}")


# Singleton instance
prometheus_agent = PrometheusAgent()
