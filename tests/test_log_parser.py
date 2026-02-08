# tests/test_log_parser.py
"""Tests for Prometheus Log Parser - No external dependencies"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.prometheus.log_parser import LogParser, ParsedError, StackFrame


class TestLogParser:
    """Test the error log parser."""
    
    def setup_method(self):
        self.parser = LogParser()
    
    def test_parse_simple_traceback(self):
        """Test parsing a simple traceback."""
        traceback = '''Traceback (most recent call last):
  File "/app/main.py", line 42, in main
    result = calculate(a, b)
  File "/app/calc.py", line 10, in calculate
    return a / b
ZeroDivisionError: division by zero
'''
        errors = self.parser.parse(traceback)
        
        assert len(errors) == 1
        error = errors[0]
        assert error.error_type == "ZeroDivisionError"
        assert error.error_message == "division by zero"
        assert len(error.stack_frames) == 2
    
    def test_parse_stack_frames(self):
        """Test stack frame extraction."""
        traceback = '''Traceback (most recent call last):
  File "/app/auth.py", line 25, in login
    user = get_user(username)
  File "/app/db.py", line 50, in get_user
    cursor.execute(query)
sqlite3.OperationalError: no such table: users
'''
        errors = self.parser.parse(traceback)
        
        assert len(errors) == 1
        frames = errors[0].stack_frames
        
        assert frames[0].file_path == "/app/auth.py"
        assert frames[0].line_number == 25
        assert frames[0].function_name == "login"
        
        assert frames[1].file_path == "/app/db.py"
        assert frames[1].line_number == 50
    
    def test_origin_file_and_line(self):
        """Test origin file and line extraction."""
        traceback = '''Traceback (most recent call last):
  File "/app/outer.py", line 10, in outer
    inner()
  File "/app/inner.py", line 5, in inner
    raise ValueError("test")
ValueError: test
'''
        errors = self.parser.parse(traceback)
        error = errors[0]
        
        # Origin should be the innermost frame
        assert error.origin_file == "/app/inner.py"
        assert error.origin_line == 5
    
    def test_parse_attribute_error(self):
        """Test parsing AttributeError."""
        traceback = '''Traceback (most recent call last):
  File "/app/app.py", line 100, in handler
    return user.profile.name
AttributeError: 'NoneType' object has no attribute 'name'
'''
        errors = self.parser.parse(traceback)
        
        assert len(errors) == 1
        assert errors[0].error_type == "AttributeError"
    
    def test_full_error_property(self):
        """Test full_error property."""
        error = ParsedError(
            error_type="KeyError",
            error_message="'missing_key'",
            stack_frames=[],
            raw_traceback="",
        )
        
        assert error.full_error == "KeyError: 'missing_key'"
    
    def test_parse_multiple_tracebacks(self):
        """Test parsing multiple tracebacks in one log."""
        log_content = '''Application starting...
Traceback (most recent call last):
  File "/app/a.py", line 1, in a
    pass
TypeError: invalid

Some other log line...

Traceback (most recent call last):
  File "/app/b.py", line 2, in b
    pass
ValueError: bad value
'''
        errors = self.parser.parse(log_content)
        
        assert len(errors) == 2
        assert errors[0].error_type == "TypeError"
        assert errors[1].error_type == "ValueError"
    
    def test_parse_empty_content(self):
        """Test parsing empty content."""
        errors = self.parser.parse("")
        assert errors == []
    
    def test_parse_no_traceback(self):
        """Test parsing log without tracebacks."""
        log = "INFO: Application started\nDEBUG: Processing request"
        errors = self.parser.parse(log)
        assert errors == []


class TestStackFrame:
    """Test StackFrame dataclass."""
    
    def test_str_representation(self):
        """Test string representation."""
        frame = StackFrame(
            file_path="/app/test.py",
            line_number=42,
            function_name="test_function",
            code_context="result = func()"
        )
        
        str_repr = str(frame)
        assert "/app/test.py" in str_repr
        assert "42" in str_repr
        assert "test_function" in str_repr


class TestParsedError:
    """Test ParsedError dataclass."""
    
    def test_no_frames(self):
        """Test error with no frames."""
        error = ParsedError(
            error_type="RuntimeError",
            error_message="test",
            stack_frames=[],
            raw_traceback="",
        )
        
        assert error.top_frame is None
        assert error.origin_file is None
        assert error.origin_line is None
    
    def test_str_representation(self):
        """Test string representation."""
        error = ParsedError(
            error_type="ValueError",
            error_message="invalid input",
            stack_frames=[
                StackFrame("/app/main.py", 10, "main", "run()")
            ],
            raw_traceback="",
        )
        
        str_repr = str(error)
        assert "ValueError" in str_repr
        assert "invalid input" in str_repr
