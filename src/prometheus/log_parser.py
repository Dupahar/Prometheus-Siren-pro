# src/prometheus/log_parser.py
"""
Error Log Parser for Prometheus.
Extracts structured information from Python exceptions and stack traces.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from loguru import logger


@dataclass
class StackFrame:
    """A single frame in a stack trace."""
    file_path: str
    line_number: int
    function_name: str
    code_context: str
    
    def __str__(self) -> str:
        return f"  File \"{self.file_path}\", line {self.line_number}, in {self.function_name}"


@dataclass
class ParsedError:
    """Structured representation of a Python error."""
    error_type: str
    error_message: str
    stack_frames: list[StackFrame] = field(default_factory=list)
    raw_traceback: str = ""
    
    @property
    def full_error(self) -> str:
        """Full error string."""
        return f"{self.error_type}: {self.error_message}"
    
    @property
    def top_frame(self) -> Optional[StackFrame]:
        """Get the most recent (innermost) stack frame."""
        return self.stack_frames[-1] if self.stack_frames else None
    
    @property
    def origin_file(self) -> Optional[str]:
        """Get the file where the error originated."""
        frame = self.top_frame
        return frame.file_path if frame else None
    
    @property
    def origin_line(self) -> Optional[int]:
        """Get the line number where the error originated."""
        frame = self.top_frame
        return frame.line_number if frame else None
    
    def __str__(self) -> str:
        return f"{self.full_error} at {self.origin_file}:{self.origin_line}"


class LogParser:
    """
    Parses Python error logs and stack traces.
    
    Capabilities:
    - Parse standard Python tracebacks
    - Extract file, line, function, and context
    - Handle multi-line error messages
    """
    
    # Regex patterns for parsing
    TRACEBACK_START = re.compile(r"^Traceback \(most recent call last\):")
    FILE_LINE = re.compile(
        r'^\s*File "([^"]+)", line (\d+), in (.+)$'
    )
    ERROR_LINE = re.compile(r"^(\w+(?:\.\w+)*): (.+)$")
    
    def parse(self, log_content: str) -> list[ParsedError]:
        """
        Parse log content and extract all errors.
        
        Args:
            log_content: Raw log text containing tracebacks
            
        Returns:
            List of ParsedError objects
        """
        errors = []
        
        # Split into potential traceback sections
        sections = self._split_tracebacks(log_content)
        
        for section in sections:
            error = self._parse_traceback(section)
            if error:
                errors.append(error)
        
        logger.debug(f"Parsed {len(errors)} errors from log")
        return errors
    
    def parse_single(self, traceback_text: str) -> Optional[ParsedError]:
        """Parse a single traceback."""
        return self._parse_traceback(traceback_text)
    
    def _split_tracebacks(self, content: str) -> list[str]:
        """Split log content into individual tracebacks."""
        sections = []
        current_section = []
        in_traceback = False
        
        for line in content.splitlines():
            if self.TRACEBACK_START.match(line):
                # Start of new traceback
                if current_section:
                    sections.append("\n".join(current_section))
                current_section = [line]
                in_traceback = True
            elif in_traceback:
                current_section.append(line)
                # Check if this is the error line (end of traceback)
                if self.ERROR_LINE.match(line) and not line.startswith(" "):
                    sections.append("\n".join(current_section))
                    current_section = []
                    in_traceback = False
        
        if current_section:
            sections.append("\n".join(current_section))
        
        return sections
    
    def _parse_traceback(self, traceback_text: str) -> Optional[ParsedError]:
        """Parse a single traceback section."""
        lines = traceback_text.strip().splitlines()
        
        if not lines:
            return None
        
        stack_frames = []
        error_type = ""
        error_message = ""
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for file/line info
            file_match = self.FILE_LINE.match(line)
            if file_match:
                file_path = file_match.group(1)
                line_num = int(file_match.group(2))
                func_name = file_match.group(3)
                
                # Next line is usually the code context
                code_context = ""
                if i + 1 < len(lines) and lines[i + 1].startswith("    "):
                    code_context = lines[i + 1].strip()
                    i += 1
                
                stack_frames.append(StackFrame(
                    file_path=file_path,
                    line_number=line_num,
                    function_name=func_name,
                    code_context=code_context,
                ))
            
            # Check for error line
            error_match = self.ERROR_LINE.match(line)
            if error_match and not line.startswith(" "):
                error_type = error_match.group(1)
                error_message = error_match.group(2)
            
            i += 1
        
        if not error_type:
            return None
        
        return ParsedError(
            error_type=error_type,
            error_message=error_message,
            stack_frames=stack_frames,
            raw_traceback=traceback_text,
        )
    
    def watch_file(
        self,
        log_path: str | Path,
        callback,
    ):
        """
        Watch a log file for new errors (simple polling implementation).
        
        For production, consider using watchdog or inotify.
        
        Args:
            log_path: Path to log file
            callback: Function to call with ParsedError when errors are found
        """
        import time
        
        log_path = Path(log_path)
        last_position = 0
        
        if log_path.exists():
            last_position = log_path.stat().st_size
        
        logger.info(f"Watching {log_path} for errors...")
        
        while True:
            try:
                if log_path.exists():
                    current_size = log_path.stat().st_size
                    
                    if current_size > last_position:
                        with open(log_path, "r") as f:
                            f.seek(last_position)
                            new_content = f.read()
                        
                        errors = self.parse(new_content)
                        for error in errors:
                            callback(error)
                        
                        last_position = current_size
                
                time.sleep(1)
            
            except KeyboardInterrupt:
                logger.info("Stopped watching log file")
                break
            except Exception as e:
                logger.error(f"Error watching log: {e}")
                time.sleep(5)


# Singleton instance
log_parser = LogParser()
