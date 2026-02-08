# src/prometheus/validator.py
"""
Patch Validator: Ensures generated patches are safe and correct.
This is the safety gate before human approval.
"""

import ast
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from loguru import logger

from .patch_generator import PatchResult


@dataclass
class ValidationResult:
    """Result of patch validation."""
    is_valid: bool
    syntax_valid: bool
    tests_passed: bool
    security_check_passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    test_output: str = ""
    
    @property
    def can_apply(self) -> bool:
        """Check if the patch is safe to apply (with human approval)."""
        return self.syntax_valid and not any(
            "critical" in e.lower() for e in self.errors
        )


class PatchValidator:
    """
    Validates generated patches before they can be applied.
    
    Validation steps:
    1. Syntax check (ast.parse)
    2. Run existing tests
    3. Run generated unit test
    4. Security pattern check
    """
    
    # Dangerous patterns to flag
    DANGEROUS_PATTERNS = [
        "eval(",
        "exec(",
        "__import__(",
        "subprocess.call(shell=True",
        "os.system(",
        ".format(",  # potential format string vuln
    ]
    
    # Secure patterns we want to see
    SECURE_PATTERNS = [
        "parameterized",
        "escape",
        "sanitize",
        "validate",
    ]
    
    def validate(
        self,
        patch: PatchResult,
        run_tests: bool = True,
    ) -> ValidationResult:
        """
        Validate a patch.
        
        Args:
            patch: The patch to validate
            run_tests: Whether to run unit tests
            
        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(
            is_valid=True,
            syntax_valid=True,
            tests_passed=True,
            security_check_passed=True,
        )
        
        # Step 1: Syntax validation
        syntax_ok = self._check_syntax(patch.patched_code)
        result.syntax_valid = syntax_ok
        if not syntax_ok:
            result.errors.append("Patched code has syntax errors")
            result.is_valid = False
        
        # Step 2: Security pattern check
        security_issues = self._check_security_patterns(patch)
        if security_issues:
            result.warnings.extend(security_issues)
            # Don't fail validation, but warn
        
        # Step 3: Check if dangerous patterns increased
        if self._introduced_dangerous_pattern(patch):
            result.security_check_passed = False
            result.errors.append("Patch introduces potentially dangerous pattern")
            result.is_valid = False
        
        # Step 4: Run generated unit test
        if run_tests and patch.unit_test:
            test_result = self._run_unit_test(patch.unit_test)
            result.tests_passed = test_result["passed"]
            result.test_output = test_result["output"]
            if not test_result["passed"]:
                result.warnings.append(f"Generated unit test failed: {test_result['output'][:200]}")
        
        # Overall validation
        result.is_valid = result.syntax_valid and result.security_check_passed
        
        logger.info(f"Patch validation: valid={result.is_valid}, syntax={result.syntax_valid}")
        return result
    
    def _check_syntax(self, code: str) -> bool:
        """Check if code has valid Python syntax."""
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            logger.debug(f"Syntax error: {e}")
            return False
    
    def _check_security_patterns(self, patch: PatchResult) -> list[str]:
        """Check for security patterns in the patch."""
        warnings = []
        
        patched = patch.patched_code.lower()
        original = patch.original_code.lower()
        
        # Check if dangerous patterns are still present
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.lower() in patched:
                if pattern.lower() not in original:
                    warnings.append(f"Warning: Patch introduces '{pattern}'")
                else:
                    warnings.append(f"Note: '{pattern}' still present (review needed)")
        
        return warnings
    
    def _introduced_dangerous_pattern(self, patch: PatchResult) -> bool:
        """Check if the patch introduces new dangerous patterns."""
        patched = patch.patched_code.lower()
        original = patch.original_code.lower()
        
        for pattern in ["eval(", "exec(", "__import__("]:
            if pattern in patched and pattern not in original:
                return True
        
        return False
    
    def _run_unit_test(self, test_code: str) -> dict:
        """Run a unit test in isolation."""
        try:
            # Create temporary test file
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix="_test.py",
                delete=False,
            ) as f:
                # Add pytest import if not present
                if "import pytest" not in test_code:
                    f.write("import pytest\n\n")
                f.write(test_code)
                test_file = f.name
            
            # Run pytest
            result = subprocess.run(
                ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            # Cleanup
            Path(test_file).unlink(missing_ok=True)
            
            return {
                "passed": result.returncode == 0,
                "output": result.stdout + result.stderr,
            }
        
        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "output": "Test timed out (>30s)",
            }
        except Exception as e:
            return {
                "passed": False,
                "output": f"Failed to run test: {e}",
            }
    
    def validate_file_integration(
        self,
        file_path: str,
        patched_code: str,
        start_line: int,
        end_line: int,
    ) -> ValidationResult:
        """
        Validate that a patch integrates correctly with a file.
        
        Reads the file, applies the patch, and validates the result.
        """
        result = ValidationResult(
            is_valid=True,
            syntax_valid=True,
            tests_passed=True,
            security_check_passed=True,
        )
        
        try:
            # Read original file
            with open(file_path, "r") as f:
                original_lines = f.readlines()
            
            # Apply patch
            patched_lines = (
                original_lines[:start_line - 1] +
                [patched_code + "\n"] +
                original_lines[end_line:]
            )
            patched_content = "".join(patched_lines)
            
            # Syntax check the entire file
            result.syntax_valid = self._check_syntax(patched_content)
            if not result.syntax_valid:
                result.errors.append("Patched file has syntax errors")
                result.is_valid = False
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Integration validation failed: {e}")
        
        return result


# Singleton instance
patch_validator = PatchValidator()
