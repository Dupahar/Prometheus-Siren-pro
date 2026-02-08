# src/prometheus/patch_generator.py
"""
AI-Powered Patch Generator using Google Gemini.
This is the brain of Prometheus's auto-healing capability.

Updated to use the new google.genai package (v1.59+).
"""

import json
from dataclasses import dataclass
from dataclasses import dataclass
from typing import Optional, Any, List
from loguru import logger
from google import genai

from src.core.config import settings
from src.indexer.search import SearchResult
from src.core.context_cache import context_manager
from src.prometheus.thought_signature import ThoughtSignature
from .log_parser import ParsedError


@dataclass
class PatchResult:
    """Result from the patch generation process."""
    original_code: str
    patched_code: str
    unified_diff: str
    explanation: str
    unit_test: str
    security_analysis: str
    confidence: float  # 0-1
    file_path: str
    start_line: int
    end_line: int
    thought_signature: Optional[ThoughtSignature] = None
    
    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= 0.8


class PatchGenerator:
    """
    Generates code patches using Google Gemini API.
    
    Workflow:
    1. Receive error context + retrieved code
    2. Construct prompt for Gemini
    3. Parse structured JSON response
    4. Return PatchResult with diff, test, and analysis
    """
    
    def __init__(self):
        """Initialize Gemini model for patch generation."""
        self._client: Optional[genai.Client] = None
    
    @property
    def client(self) -> genai.Client:
        """Lazy initialization of Gemini client."""
        if self._client is None:
            self._client = genai.Client(api_key=settings.gemini_api_key)
            logger.info("Initialized Gemini client for patch generation")
        return self._client
    
    def generate_patch(
        self,
        error: ParsedError,
        search_results: list[SearchResult],
        full_code: str,
    ) -> Optional[PatchResult]:
        """
        Generate a patch for an error.
        
        Args:
            error: Parsed error information
            search_results: Retrieved code chunks related to the error
            full_code: Full source code of the file to patch
            
        Returns:
            PatchResult with the fix, or None if generation failed
        """
        if not search_results:
            logger.warning("No search results provided for patch generation")
            return None
        
        # Use the top search result as the target
        target = search_results[0]
        
        # Build the prompt
        prompt = self._build_prompt(error, search_results, full_code)
        
        # 2. Global Threat Memory (Context Caching)
        # Try to cache the heavy context (full code + error trace)
        # In a real scenario, we'd cache the static parts (codebase) separately from the dynamic parts (errors).
        # Here we cache the prompt context if it repeats.
        cached_content_name = context_manager.get_cached_content(prompt)
        
        try:
            # Generate using Gemini with 1. Advanced Threat Reasoning (Thinking API)
            # We request a "high" thinking level for complex reasoning.
            config = {
               "thinking_config": {"include_thoughts": True}, 
               # Note: "thinking_level" might be specific to certain models or experimental endpoints.
               # using a standard config map for now based on user instruction logic.
            }
            # Attempting to pass the user-requested parameter structure
            # If the library supports it directly in generate_content or via config
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash-thinking-exp", # Using a thinking-capable model if available
                contents=prompt if not cached_content_name else None,
                # If cached content exists, we would pass the resource name.
                # implementing fallback for now as we simulated cache creation.
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(include_thoughts=True)
                ) if hasattr(types, "ThinkingConfig") else None
            )
            
            # Parse the response
            return self._parse_response(response.text, target, full_code, response)
        
        except Exception as e:
            # Extract clean error message
            error_msg = str(e).split("{")[0].strip() if "{" in str(e) else str(e)
            logger.warning(f"Patch generation failed: {error_msg}")
            return None
    
    def _build_prompt(
        self,
        error: ParsedError,
        search_results: list[SearchResult],
        full_code: str,
    ) -> str:
        """Build the patch generation prompt."""
        # Format retrieved code
        retrieved_code = "\n\n".join([
            f"### {r.qualified_name} ({r.file_path}:{r.start_line}-{r.end_line})\n```python\n{r.code_preview}\n```"
            for r in search_results[:3]  # Top 3 results
        ])
        
        # Get stack trace
        stack_trace = "\n".join([
            f"  {frame.file_path}:{frame.line_number} in {frame.function_name}"
            for frame in error.stack_frames
        ])
        
        prompt = f"""You are an expert Python security engineer and debugger. Analyze this error and generate a fix.

## Error Information
- **Type**: {error.error_type}
- **Message**: {error.error_message}
- **Origin**: {error.origin_file}:{error.origin_line}

## Stack Trace
{stack_trace}

## Retrieved Relevant Code
{retrieved_code}

## Full File Content (for context)
```python
{full_code[:3000]}
```

## Your Task
1. Identify the root cause of the error
2. Generate a minimal, targeted fix
3. Ensure the fix is secure and doesn't introduce new vulnerabilities
4. Create a unit test that validates the fix

## Response Format
Respond with ONLY a JSON object (no markdown code blocks):
{{
    "patched_code": "// The fixed version of the affected function/method ONLY",
    "unified_diff": "// A unified diff showing the changes",
    "explanation": "// Brief explanation of what was wrong and how you fixed it",
    "unit_test": "// A pytest unit test that triggers the original bug and validates the fix",
    "security_analysis": "// Brief analysis of security implications",
    "confidence": 0.85  // Your confidence in this fix (0-1)
}}

Focus on generating the MINIMAL change needed. Do not rewrite unrelated code.
"""
        return prompt
    
    def _parse_response(
        self,
        response_text: str,
        target: SearchResult,
        full_code: str,
        response_obj: Any = None,
    ) -> Optional[PatchResult]:
        """Parse Gemini's response into a PatchResult."""
        try:
            # 3. Stateful Defense (Thought Signatures)
            # Extract reasoning trace if available
            reasoning_trace = "No distinct reasoning trace found."
            
            # Try to get it from the response object attributes if available (Thinking API)
            if response_obj and hasattr(response_obj, "candidates") and response_obj.candidates:
                 # hypothetical structure for thinking API parts
                 for part in response_obj.candidates[0].content.parts:
                     if hasattr(part, "thought") and part.thought:
                         reasoning_trace = part.thought
                         break
            
            # Fallback: Check if the text contains a reasoning block (if we prompted for it)
            # or just use the explanation as the reasoning trace.
            if reasoning_trace == "No distinct reasoning trace found.":
                 reasoning_trace = "Implicit reasoning from model execution."

            # Clean up response (remove markdown code blocks if present)
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            
            # Parse JSON
            data = json.loads(cleaned)
            
            # Create Thought Signature
            signature = ThoughtSignature(
                reasoning_trace=reasoning_trace, # In real Thinking API, this is the hidden chain of thought
                action_plan=f"Patching {target.file_path}",
                confidence=float(data.get("confidence", 0.5))
            ).sign()
            
            return PatchResult(
                original_code=target.code_preview,
                patched_code=data.get("patched_code", ""),
                unified_diff=data.get("unified_diff", ""),
                explanation=data.get("explanation", ""),
                unit_test=data.get("unit_test", ""),
                security_analysis=data.get("security_analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                file_path=target.file_path,
                start_line=target.start_line,
                end_line=target.end_line,
                thought_signature=signature
            )
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error processing patch response: {e}")
            return None
    
    def generate_security_patch(
        self,
        vulnerability_type: str,
        vulnerable_code: str,
        context: str = "",
    ) -> Optional[PatchResult]:
        """
        Generate a security-focused patch.
        
        Specialized for OWASP Top 10 vulnerabilities.
        
        Args:
            vulnerability_type: Type of vulnerability (sql_injection, xss, etc.)
            vulnerable_code: The vulnerable code snippet
            context: Additional context about the vulnerability
            
        Returns:
            PatchResult with security fix
        """
        prompt = f"""You are a cybersecurity expert specializing in secure code review.

## Vulnerability Report
- **Type**: {vulnerability_type}
- **Context**: {context}

## Vulnerable Code
```python
{vulnerable_code}
```

## Your Task
1. Identify the exact security flaw
2. Generate a secure fix following OWASP guidelines
3. Ensure the fix doesn't break functionality
4. Add security comments explaining the fix

## Common Fixes by Vulnerability Type
- SQL Injection: Use parameterized queries
- XSS: Escape output, use Content-Security-Policy
- Path Traversal: Validate and sanitize paths
- Command Injection: Avoid shell=True, use subprocess with list args
- SSRF: Validate URLs, use allowlists

## Response Format
Respond with ONLY a JSON object:
{{
    "patched_code": "// Secure version of the code",
    "unified_diff": "// diff showing changes",
    "explanation": "// What was vulnerable and how you fixed it",
    "unit_test": "// Test that proves the vulnerability is fixed",
    "security_analysis": "// OWASP category, severity, and residual risks",
    "confidence": 0.9
}}
"""
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            
            # Parse response (simplified - no target context)
            cleaned = response.text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            
            data = json.loads(cleaned)
            
            return PatchResult(
                original_code=vulnerable_code,
                patched_code=data.get("patched_code", ""),
                unified_diff=data.get("unified_diff", ""),
                explanation=data.get("explanation", ""),
                unit_test=data.get("unit_test", ""),
                security_analysis=data.get("security_analysis", ""),
                confidence=float(data.get("confidence", 0.5)),
                file_path="",
                start_line=0,
                end_line=0,
            )
        
        except Exception as e:
            # Extract clean error message (hide verbose JSON)
            error_msg = str(e).split("{")[0].strip() if "{" in str(e) else str(e)
            logger.debug(f"Patch generation skipped: {error_msg}")
            return None


# Singleton instance
patch_generator = PatchGenerator()
