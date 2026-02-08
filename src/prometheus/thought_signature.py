# src/prometheus/thought_signature.py
"""
Thought Signatures: Cryptographic-ish proof of reasoning.
Ensures that every action taken by the agent is backed by a recorded reasoning trace.
"""

import hashlib
import json
import uuid
import typing
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class ThoughtSignature:
    """
    A signature attesting that an action was the result of a specific reasoning process.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    reasoning_trace: str = "" # The "thought" from Gemini Thinking API
    confidence: float = 0.0
    action_plan: str = ""
    signature_hash: str = ""
    
    def sign(self) -> 'ThoughtSignature':
        """Generate a hash signature for this thought process."""
        payload = f"{self.timestamp.isoformat()}|{self.reasoning_trace}|{self.action_plan}"
        self.signature_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        return self

    def verify(self) -> bool:
        """Verify the integrity of the signature."""
        if not self.signature_hash:
            return False
        payload = f"{self.timestamp.isoformat()}|{self.reasoning_trace}|{self.action_plan}"
        expected_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        return self.signature_hash == expected_hash

    def to_dict(self) -> typing.Dict[str, typing.Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "reasoning_trace": self.reasoning_trace[:200] + "..." if len(self.reasoning_trace) > 200 else self.reasoning_trace,
            "confidence": self.confidence,
            "signature_hash": self.signature_hash
        }

    @classmethod
    def from_gemini_response(cls, response_trace: str, plan: str, confidence: float) -> 'ThoughtSignature':
        """Create a signature from a Gemini response."""
        sig = cls(
            reasoning_trace=response_trace,
            action_plan=plan,
            confidence=confidence
        )
        return sig.sign()
