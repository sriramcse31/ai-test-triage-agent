"""
CI Log Parser - Extracts structured data from test failure logs
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from pathlib import Path


@dataclass
class LogEntry:
    """Single log line with metadata"""
    timestamp: Optional[datetime]
    level: str  # INFO, ERROR, FAIL, etc.
    message: str
    raw_line: str


@dataclass
class TestFailure:
    """Structured representation of a test failure"""
    test_name: str
    failure_message: str
    error_type: Optional[str]
    duration_seconds: Optional[float]
    log_entries: List[LogEntry]
    error_lines: List[str]
    artifacts: List[str]  # screenshots, traces, etc.
    retry_count: int = 0
    
    def get_context_window(self, around_errors: int = 3) -> List[LogEntry]:
        """Get log entries around error lines for context"""
        error_indices = [i for i, entry in enumerate(self.log_entries) 
                        if entry.level in ['ERROR', 'FAIL']]
        
        context_indices = set()
        for idx in error_indices:
            start = max(0, idx - around_errors)
            end = min(len(self.log_entries), idx + around_errors + 1)
            context_indices.update(range(start, end))
        
        return [self.log_entries[i] for i in sorted(context_indices)]


class LogParser:
    """Parse CI test logs into structured format"""
    
    # Common log patterns
    TIMESTAMP_PATTERN = r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]'
    LEVEL_PATTERN = r'(INFO|ERROR|FAIL|PASS|WARNING|NOTE)'
    TEST_NAME_PATTERN = r'test[_\w]+'
    TIMEOUT_PATTERN = r'Timeout (\d+)ms exceeded'
    SELECTOR_PATTERN = r'selector ["\']([^"\']+)["\']'
    DURATION_PATTERN = r'after (\d+)s'
    
    def parse_file(self, filepath: Path) -> TestFailure:
        """Parse a log file into TestFailure object"""
        with open(filepath, 'r') as f:
            content = f.read()
        
        log_entries = self._parse_log_lines(content)
        test_name = self._extract_test_name(log_entries)
        error_lines = [e.message for e in log_entries if e.level in ['ERROR', 'FAIL']]
        failure_message = self._extract_failure_message(log_entries)
        error_type = self._classify_error_type(error_lines)
        duration = self._extract_duration(log_entries)
        artifacts = self._extract_artifacts(log_entries)
        retry_count = self._count_retries(log_entries)
        
        return TestFailure(
            test_name=test_name,
            failure_message=failure_message,
            error_type=error_type,
            duration_seconds=duration,
            log_entries=log_entries,
            error_lines=error_lines,
            artifacts=artifacts,
            retry_count=retry_count
        )
    
    def _parse_log_lines(self, content: str) -> List[LogEntry]:
        """Parse individual log lines"""
        entries = []
        for line in content.split('\n'):
            if not line.strip():
                continue
            
            timestamp = self._extract_timestamp(line)
            level = self._extract_level(line)
            message = self._extract_message(line)
            
            entries.append(LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                raw_line=line
            ))
        
        return entries
    
    def _extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp from log line"""
        match = re.search(self.TIMESTAMP_PATTERN, line)
        if match:
            try:
                return datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        return None
    
    def _extract_level(self, line: str) -> str:
        """Extract log level"""
        match = re.search(self.LEVEL_PATTERN, line)
        return match.group(1) if match else 'INFO'
    
    def _extract_message(self, line: str) -> str:
        """Extract message content"""
        # Remove timestamp and level prefix
        msg = re.sub(self.TIMESTAMP_PATTERN, '', line)
        msg = re.sub(f'{self.LEVEL_PATTERN}:', '', msg)
        return msg.strip()
    
    def _extract_test_name(self, entries: List[LogEntry]) -> str:
        """Find test name from log entries"""
        for entry in entries:
            if 'Starting test:' in entry.message:
                match = re.search(self.TEST_NAME_PATTERN, entry.message)
                if match:
                    return match.group(0)
        return "unknown_test"
    
    def _extract_failure_message(self, entries: List[LogEntry]) -> str:
        """Get primary failure message"""
        fail_entries = [e for e in entries if e.level in ['FAIL', 'ERROR']]
        if fail_entries:
            return fail_entries[0].message
        return "Unknown failure"
    
    def _classify_error_type(self, error_lines: List[str]) -> Optional[str]:
        """Classify error type from error messages"""
        error_text = ' '.join(error_lines).lower()
        
        if 'timeout' in error_text:
            return 'TimeoutError'
        elif 'selector' in error_text or 'element not found' in error_text:
            return 'SelectorError'
        elif 'connection' in error_text or 'network' in error_text:
            return 'NetworkError'
        elif 'database' in error_text or 'duplicate key' in error_text:
            return 'DatabaseError'
        
        return None
    
    def _extract_duration(self, entries: List[LogEntry]) -> Optional[float]:
        """Extract test duration in seconds"""
        for entry in entries:
            match = re.search(self.DURATION_PATTERN, entry.message)
            if match:
                return float(match.group(1))
        return None
    
    def _extract_artifacts(self, entries: List[LogEntry]) -> List[str]:
        """Find artifact references (screenshots, traces)"""
        artifacts = []
        for entry in entries:
            if 'screenshot' in entry.message.lower():
                # Extract filename from message
                words = entry.message.split()
                for word in words:
                    if word.endswith(('.png', '.jpg', '.jpeg')):
                        artifacts.append(word)
        return artifacts
    
    def _count_retries(self, entries: List[LogEntry]) -> int:
        """Count retry attempts"""
        retry_count = 0
        for entry in entries:
            if 'retry attempt' in entry.message.lower():
                retry_count += 1
        return retry_count


# CLI usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python log_parser.py <log_file>")
        print("\nExample:")
        print("  python ingestion/log_parser.py demo/sample_ci_failures/test_login_timeout.log")
        sys.exit(1)
    
    log_file = sys.argv[1]
    
    # Check if file exists
    if not Path(log_file).exists():
        print(f"❌ File not found: {log_file}")
        sys.exit(1)
    
    print(f"\n🔍 Parsing log file: {log_file}\n")
    
    parser = LogParser()
    failure = parser.parse_file(Path(log_file))
    
    print(f"📋 Test: {failure.test_name}")
    print(f"❌ Error: {failure.failure_message}")
    print(f"🔧 Type: {failure.error_type or 'Unknown'}")
    print(f"⏱️  Duration: {failure.duration_seconds}s" if failure.duration_seconds else "⏱️  Duration: Unknown")
    print(f"🔁 Retries: {failure.retry_count}")
    
    if failure.artifacts:
        print(f"📸 Artifacts: {', '.join(failure.artifacts)}")
    
    print(f"\n🔍 Error lines ({len(failure.error_lines)}):")
    for line in failure.error_lines:
        print(f"  • {line}")
    
    print(f"\n✅ Successfully parsed {len(failure.log_entries)} log entries")