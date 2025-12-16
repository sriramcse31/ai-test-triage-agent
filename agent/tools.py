"""
Tools that the agent can use during reasoning
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import List, Dict, Optional
from agent.models import HistoricalFailure, FailureType
from agent.memory import FailureMemory
import re


class AgentTools:
    """Collection of tools for failure analysis"""
    
    def __init__(self, memory: FailureMemory):
        self.memory = memory
    
    def search_similar_failures(
        self, 
        current_failure: HistoricalFailure,
        top_k: int = 5
    ) -> List[HistoricalFailure]:
        """Search for similar past failures"""
        return self.memory.search_similar(current_failure, top_k=top_k)
    
    def get_test_history(self, test_name: str) -> List[HistoricalFailure]:
        """Get all historical failures for a specific test"""
        return self.memory.get_by_test_name(test_name)
    
    def calculate_flaky_score(
        self, 
        current_failure: HistoricalFailure,
        history: List[HistoricalFailure]
    ) -> float:
        """Calculate flakiness probability based on patterns"""
        score = 0.0
        
        # Factor 1: Retry success in current run
        if current_failure.retry_count > 0:
            score += 0.4
        
        # Factor 2: Historical pattern
        if len(history) >= 3:
            score += 0.3
        
        # Factor 3: Network/timeout errors are often flaky
        if current_failure.error_type in ['NetworkError', 'TimeoutError']:
            score += 0.2
        
        # Factor 4: Same error appears and disappears
        resolved_count = sum(1 for h in history if h.resolution is not None)
        if resolved_count > 0 and len(history) > resolved_count:
            score += 0.1
        
        return min(score, 1.0)
    
    def extract_selector_from_error(self, error_message: str) -> Optional[str]:
        """Extract CSS/XPath selector from error message"""
        patterns = [
            r'selector ["\']([^"\']+)["\']',
            r'element ["\']([^"\']+)["\']',
            r'locator ["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_message)
            if match:
                return match.group(1)
        return None
    
    def classify_error_type(self, failure: HistoricalFailure) -> FailureType:
        """Classify failure into predefined types"""
        error_text = (failure.error_message + " " + failure.log_snippet).lower()
        
        # Timeout issues
        if any(word in error_text for word in ['timeout', 'timed out', 'exceeded']):
            return FailureType.TIMEOUT
        
        # Selector issues
        if any(word in error_text for word in ['selector', 'not found', 'element', 'locator']):
            return FailureType.SELECTOR
        
        # Network issues
        if any(word in error_text for word in ['network', 'connection', 'etimedout', 'econnrefused']):
            return FailureType.NETWORK
        
        # Data setup issues
        if any(word in error_text for word in ['database', 'duplicate key', 'constraint', 'data']):
            return FailureType.DATA_SETUP
        
        # Environment issues
        if any(word in error_text for word in ['environment', 'config', 'permission']):
            return FailureType.ENVIRONMENT
        
        return FailureType.UNKNOWN
    
    def suggest_actions(
        self, 
        failure_type: FailureType,
        flaky_score: float,
        similar_failures: List[HistoricalFailure]
    ) -> List[str]:
        """Generate actionable suggestions based on analysis"""
        actions = []
        
        # Learn from similar failures
        for similar in similar_failures[:2]:
            if similar.resolution and similar.resolution.confidence > 0.7:
                actions.append(
                    f"Apply similar fix: {similar.resolution.fix_applied}"
                )
        
        # Type-specific actions
        if failure_type == FailureType.TIMEOUT:
            actions.append("Increase wait timeout (consider animation/loading time)")
            actions.append("Add explicit wait for element state (visible/stable)")
            if flaky_score > 0.6:
                actions.append("Test is flaky - add retry logic or investigate root cause")
        
        elif failure_type == FailureType.SELECTOR:
            actions.append("Update selector - UI may have changed")
            actions.append("Check recent deployments for UI changes")
            actions.append("Use more stable selectors (data-testid, aria-label)")
        
        elif failure_type == FailureType.NETWORK:
            actions.append("Add retry logic with exponential backoff")
            actions.append("Check CI environment network stability")
            if flaky_score > 0.7:
                actions.append("Highly flaky - investigate environment or mock network calls")
        
        elif failure_type == FailureType.DATA_SETUP:
            actions.append("Review test data setup - ensure cleanup between runs")
            actions.append("Use unique identifiers to prevent conflicts")
            actions.append("Add database reset in test teardown")
        
        elif failure_type == FailureType.ENVIRONMENT:
            actions.append("Check environment configuration")
            actions.append("Verify dependencies and services are running")
        
        # Flakiness-specific actions
        if flaky_score > 0.75:
            actions.append("🚨 HIGH FLAKINESS - Consider quarantining test")
        
        # Generic fallback
        if not actions:
            actions.append("Re-run test to confirm failure is reproducible")
            actions.append("Review recent code changes")
            actions.append("Check CI logs for environment issues")
        
        return actions[:5]  # Limit to top 5 actions
    
    def build_evidence_summary(
        self,
        current_failure: HistoricalFailure,
        similar_failures: List[HistoricalFailure],
        history: List[HistoricalFailure]
    ) -> str:
        """Build evidence summary for LLM context"""
        evidence = []
        
        evidence.append(f"CURRENT FAILURE:")
        evidence.append(f"Test: {current_failure.test_name}")
        evidence.append(f"Error: {current_failure.error_message}")
        evidence.append(f"Type: {current_failure.error_type}")
        evidence.append(f"Log snippet: {current_failure.log_snippet}")
        evidence.append(f"Retries: {current_failure.retry_count}")
        
        if similar_failures:
            evidence.append(f"\nSIMILAR PAST FAILURES ({len(similar_failures)}):")
            for i, similar in enumerate(similar_failures[:3], 1):
                evidence.append(f"{i}. {similar.test_name}")
                evidence.append(f"   Error: {similar.error_message}")
                if similar.resolution:
                    evidence.append(f"   Root cause: {similar.resolution.root_cause}")
                    evidence.append(f"   Fix applied: {similar.resolution.fix_applied}")
        
        if history:
            evidence.append(f"\nTEST HISTORY ({len(history)} past failures)")
            resolved = sum(1 for h in history if h.resolution is not None)
            evidence.append(f"Resolved: {resolved}/{len(history)}")
        
        return "\n".join(evidence)