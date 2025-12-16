"""
Unit tests for agent components
Save as: tests/test_agent.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(str(project_root))  # Ensure correct working directory

import pytest
from datetime import datetime
from agent.models import (
    HistoricalFailure, 
    Resolution, 
    FailureType,
    TriageResult
)
from agent.tools import AgentTools
from agent.memory import FailureMemory
from ingestion.log_parser import LogParser


class TestLogParser:
    """Test log parsing functionality"""
    
    def test_parse_timeout_log(self):
        """Test parsing timeout error"""
        parser = LogParser()
        log_file = Path("demo/sample_ci_failures/test_login_timeout.log")
        
        if not log_file.exists():
            pytest.skip("Sample log file not found")
        
        result = parser.parse_file(log_file)
        
        assert result.test_name == "test_user_login"
        assert result.error_type == "TimeoutError"
        assert result.duration_seconds == 32.0
        assert len(result.error_lines) > 0
    
    def test_parse_selector_log(self):
        """Test parsing selector error"""
        parser = LogParser()
        log_file = Path("demo/sample_ci_failures/test_selector_changed.log")
        
        if not log_file.exists():
            pytest.skip("Sample log file not found")
        
        result = parser.parse_file(log_file)
        
        assert result.test_name == "test_add_to_cart"
        assert "selector" in result.failure_message.lower()
        assert result.duration_seconds == 31.0


class TestAgentTools:
    """Test agent tools"""
    
    @pytest.fixture
    def sample_failure(self):
        """Create a sample failure for testing"""
        return HistoricalFailure(
            test_name="test_example",
            error_message="TimeoutError: Element not visible",
            error_type="TimeoutError",
            log_snippet="waiting for element #button",
            timestamp=datetime.now(),
            duration_seconds=30.0,
            retry_count=0,
            artifacts=[],
            resolution=None
        )
    
    def test_classify_timeout(self, sample_failure):
        """Test timeout classification"""
        memory = FailureMemory()
        tools = AgentTools(memory)
        
        classification = tools.classify_error_type(sample_failure)
        
        assert classification == FailureType.TIMEOUT
    
    def test_classify_selector(self):
        """Test selector classification"""
        failure = HistoricalFailure(
            test_name="test_example",
            error_message="Element not found: button[id='submit']",
            error_type="SelectorError",
            log_snippet="selector not found on page",
            timestamp=datetime.now(),
            duration_seconds=5.0,
            retry_count=0,
            artifacts=[],
            resolution=None
        )
        
        memory = FailureMemory()
        tools = AgentTools(memory)
        classification = tools.classify_error_type(failure)
        
        assert classification == FailureType.SELECTOR
    
    def test_flaky_score_with_retries(self, sample_failure):
        """Test flaky score calculation with retries"""
        sample_failure.retry_count = 2
        
        memory = FailureMemory()
        tools = AgentTools(memory)
        score = tools.calculate_flaky_score(sample_failure, [])
        
        assert score >= 0.4  # Should be flaky if retries succeeded
    
    def test_suggest_actions_timeout(self, sample_failure):
        """Test action suggestions for timeout"""
        memory = FailureMemory()
        tools = AgentTools(memory)
        
        actions = tools.suggest_actions(
            FailureType.TIMEOUT,
            flaky_score=0.2,
            similar_failures=[]
        )
        
        assert len(actions) > 0
        assert any("timeout" in action.lower() for action in actions)


class TestModels:
    """Test data models"""
    
    def test_historical_failure_to_dict(self):
        """Test serialization"""
        failure = HistoricalFailure(
            test_name="test_example",
            error_message="Error message",
            error_type="TimeoutError",
            log_snippet="log content",
            timestamp=datetime.now(),
            duration_seconds=10.0,
            retry_count=0,
            artifacts=["screenshot.png"],
            resolution=None
        )
        
        data = failure.to_dict()
        
        assert data['test_name'] == "test_example"
        assert data['error_type'] == "TimeoutError"
        assert isinstance(data['timestamp'], str)
    
    def test_historical_failure_from_dict(self):
        """Test deserialization"""
        data = {
            'test_name': "test_example",
            'error_message': "Error",
            'error_type': "TimeoutError",
            'log_snippet': "log",
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': 10.0,
            'retry_count': 0,
            'artifacts': [],
            'resolution': None
        }
        
        failure = HistoricalFailure.from_dict(data)
        
        assert failure.test_name == "test_example"
        assert isinstance(failure.timestamp, datetime)
    
    def test_triage_result_report(self):
        """Test report generation"""
        result = TriageResult(
            test_name="test_example",
            classification=FailureType.TIMEOUT,
            flaky_probability=0.3,
            root_cause_explanation="Element loading timeout",
            suggested_actions=["Increase timeout", "Check network"],
            confidence_score=0.8,
            similar_failures=[],
            reasoning_steps=["Step 1", "Step 2"]
        )
        
        report = result.to_report()
        
        assert "test_example" in report
        assert "timeout" in report.lower()
        assert "30.0%" in report or "30%" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])