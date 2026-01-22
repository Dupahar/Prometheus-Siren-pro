# tests/test_ast_parser.py
"""Tests for AST Parser - No external dependencies"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.ast_parser import ASTParser, CodeChunk


class TestASTParser:
    """Test the AST-based code parser."""
    
    def setup_method(self):
        self.parser = ASTParser()
    
    def test_parse_simple_function(self):
        """Test parsing a simple function."""
        source = '''
def hello(name):
    """Say hello."""
    return f"Hello, {name}!"
'''
        chunks = self.parser.parse_source(source)
        
        assert len(chunks) == 1
        assert chunks[0].name == "hello"
        assert chunks[0].chunk_type == "function"
        assert chunks[0].docstring == "Say hello."
    
    def test_parse_class(self):
        """Test parsing a class."""
        source = '''
class Calculator:
    """A simple calculator."""
    
    def add(self, a, b):
        return a + b
    
    def subtract(self, a, b):
        return a - b
'''
        chunks = self.parser.parse_source(source)
        
        # Should find the class
        assert any(c.name == "Calculator" and c.chunk_type == "class" for c in chunks)
    
    def test_parse_with_methods(self):
        """Test parsing with method extraction."""
        source = '''
class User:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}"
'''
        chunks = self.parser.parse_source(source)
        
        # Find class
        user_class = [c for c in chunks if c.name == "User"]
        assert len(user_class) == 1
    
    def test_content_hash(self):
        """Test content hashing for change detection."""
        source = '''
def foo():
    return 1
'''
        chunks = self.parser.parse_source(source)
        
        assert len(chunks) == 1
        assert chunks[0].content_hash
        assert len(chunks[0].content_hash) == 16
    
    def test_qualified_name_method(self):
        """Test qualified name for methods."""
        chunk = CodeChunk(
            name="greet",
            code="def greet(self): pass",
            start_line=5,
            end_line=6,
            chunk_type="method",
            parent="User",
        )
        
        assert chunk.qualified_name == "User.greet"
    
    def test_qualified_name_function(self):
        """Test qualified name for standalone functions."""
        chunk = CodeChunk(
            name="hello",
            code="def hello(): pass",
            start_line=1,
            end_line=2,
            chunk_type="function",
        )
        
        assert chunk.qualified_name == "hello"
    
    def test_empty_source(self):
        """Test parsing empty source."""
        chunks = self.parser.parse_source("")
        assert chunks == []
    
    def test_syntax_error_handling(self):
        """Test graceful handling of syntax errors."""
        source = "def broken("  # Invalid syntax
        chunks = self.parser.parse_source(source)
        assert chunks == []


class TestCodeChunk:
    """Test CodeChunk dataclass."""
    
    def test_context_string(self):
        """Test context string generation."""
        chunk = CodeChunk(
            name="login",
            code="def login(user, pwd): pass",
            start_line=10,
            end_line=15,
            chunk_type="function",
            docstring="Authenticate a user",
            file_path="/app/auth.py",
        )
        
        context = chunk.context_string
        assert "function: login" in context
        assert "Authenticate a user" in context
    
    def test_location(self):
        """Test chunk location."""
        chunk = CodeChunk(
            name="test",
            code="pass",
            start_line=5,
            end_line=10,
            chunk_type="function",
            file_path="/app/test.py",
        )
        
        # Test line properties
        assert chunk.start_line == 5
        assert chunk.end_line == 10
