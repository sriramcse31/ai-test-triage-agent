"""
Data models for storing failures and resolutions
Save as: agent/models.py
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, List, Dict
from enum import Enum
import json


class FailureType(Enum):
    """Classification of failure types"""
    TIMEOUT = "timeout"
    SELECTOR = "selector_issue"
    NETWORK = "network_instability"
    DATA_SETUP = "data_setup_issue"
    ENVIRONMENT = "environment_issue"
    GENUINE_BUG = "genuine_regression"
    UNKNOWN = "unknown"


class FlakyScore(Enum):
    """Flakiness probability"""
    NOT_FLAKY = 0.0
    LOW = 0.3
    MEDIUM = 0.6
    HIGH = 0.9


@dataclass
class Resolution:
    """How a failure was resolved"""
    root_cause: str
    classification: FailureType
    fix_applied: str
    fixed_by: Optional[str] = None
    fixed_at: Optional[datetime] = None
    ticket_reference: Optional[str] = None
    confidence: float = 0.8
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['classification'] = self.classification.value
        if self.fixed_at:
            d['fixed_at'] = self.fixed_at.isoformat()
        return d
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Resolution':
        if 'fixed_at' in data and data['fixed_at']:
            data['fixed_at'] = datetime.fromisoformat(data['fixed_at'])
        if 'classification' in data:
            data['classification'] = FailureType(data['classification'])
        return cls(**data)


@dataclass
class HistoricalFailure:
    """Complete failure record with resolution"""
    
    # Failure details
    test_name: str
    error_message: str
    error_type: Optional[str]
    log_snippet: str
    timestamp: datetime
    duration_seconds: Optional[float]
    retry_count: int
    artifacts: List[str]
    
    # Resolution (may be None for unresolved)
    resolution: Optional[Resolution]
    
    # Metadata
    ci_run_id: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    flaky_score: float = 0.0
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        if self.resolution:
            d['resolution'] = self.resolution.to_dict()
        return d
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'HistoricalFailure':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        if data.get('resolution'):
            # Only convert if it's a dict (not already a Resolution object)
            if isinstance(data['resolution'], dict):
                data['resolution'] = Resolution.from_dict(data['resolution'])
        return cls(**data)
    
    def to_embedding_text(self) -> str:
        """Generate text for embedding - combines all relevant context"""
        parts = [
            f"Test: {self.test_name}",
            f"Error: {self.error_message}",
            f"Type: {self.error_type or 'unknown'}",
            f"Log: {self.log_snippet}",
        ]
        
        if self.resolution:
            parts.extend([
                f"Root Cause: {self.resolution.root_cause}",
                f"Classification: {self.resolution.classification.value}",
                f"Fix: {self.resolution.fix_applied}"
            ])
        
        return " | ".join(parts)
    
    def get_summary(self) -> str:
        """Human-readable summary"""
        summary = f"{self.test_name}: {self.error_message}"
        if self.resolution:
            summary += f"\n  → Fixed: {self.resolution.fix_applied}"
        return summary


@dataclass
class TriageResult:
    """Agent's analysis output"""
    test_name: str
    classification: FailureType
    flaky_probability: float
    root_cause_explanation: str
    suggested_actions: List[str]
    confidence_score: float
    similar_failures: List[HistoricalFailure]
    reasoning_steps: List[str]
    
    def to_report(self) -> str:
        """Generate human-readable report"""
        report = f"""
╔══════════════════════════════════════════════════════════════
║ TEST FAILURE TRIAGE REPORT
╠══════════════════════════════════════════════════════════════
║ Test: {self.test_name}
║ Classification: {self.classification.value}
║ Flaky Probability: {self.flaky_probability:.1%}
║ Confidence: {self.confidence_score:.1%}
╠══════════════════════════════════════════════════════════════
║ ROOT CAUSE
╠══════════════════════════════════════════════════════════════
{self.root_cause_explanation}

╔══════════════════════════════════════════════════════════════
║ SUGGESTED ACTIONS
╠══════════════════════════════════════════════════════════════
"""
        for i, action in enumerate(self.suggested_actions, 1):
            report += f"{i}. {action}\n"
        
        if self.similar_failures:
            report += f"""
╔══════════════════════════════════════════════════════════════
║ SIMILAR PAST FAILURES ({len(self.similar_failures)})
╠══════════════════════════════════════════════════════════════
"""
            for failure in self.similar_failures[:3]:
                report += f"  • {failure.get_summary()}\n"
        
        return report


# Sample historical data for testing
SAMPLE_HISTORICAL_FAILURES = [
    {
        "test_name": "test_user_login",
        "error_message": "TimeoutError: selector '#user-dashboard' not visible",
        "error_type": "TimeoutError",
        "log_snippet": "waiting for selector '#user-dashboard' to be visible. Element is hidden.",
        "timestamp": "2024-01-10T10:00:00",
        "duration_seconds": 32.0,
        "retry_count": 0,
        "artifacts": ["login_fail.png"],
        "resolution": {
            "root_cause": "Dashboard renders with display:none initially, needs animation time",
            "classification": "timeout",
            "fix_applied": "Increased wait timeout to 60s and added waitForLoadState('networkidle')",
            "fixed_by": "engineer@example.com",
            "fixed_at": "2024-01-10T14:00:00",
            "confidence": 0.95
        },
        "flaky_score": 0.2
    },
    {
        "test_name": "test_add_to_cart",
        "error_message": "Element with selector button[data-test-id='add-cart'] not found",
        "error_type": "SelectorError",
        "log_snippet": "Available buttons: .btn-primary.add-to-cart. Test selector no longer matches.",
        "timestamp": "2024-01-12T15:30:00",
        "duration_seconds": 31.0,
        "retry_count": 0,
        "artifacts": [],
        "resolution": {
            "root_cause": "UI refactor changed data-test-id to class-based selector",
            "classification": "selector_issue",
            "fix_applied": "Updated selector to .btn-primary.add-to-cart",
            "fixed_by": "qa@example.com",
            "ticket_reference": "JIRA-1234",
            "confidence": 1.0
        },
        "flaky_score": 0.0
    },
    {
        "test_name": "test_api_search",
        "error_message": "RequestError: connect ETIMEDOUT",
        "error_type": "NetworkError",
        "log_snippet": "Failed to connect to API. Succeeded on retry 2/3.",
        "timestamp": "2024-01-13T09:15:00",
        "duration_seconds": 15.0,
        "retry_count": 2,
        "artifacts": [],
        "resolution": {
            "root_cause": "Intermittent network latency in CI environment",
            "classification": "network_instability",
            "fix_applied": "Added retry logic with exponential backoff",
            "confidence": 0.7
        },
        "flaky_score": 0.85
    }
]


def save_sample_data(filepath: str = "demo/sample_historical_data.json"):
    """Save sample historical failures for testing"""
    import json
    from pathlib import Path
    
    Path(filepath).parent.mkdir(exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(SAMPLE_HISTORICAL_FAILURES, f, indent=2)
    
    print(f"✓ Saved sample historical data to {filepath}")


if __name__ == "__main__":
    save_sample_data()