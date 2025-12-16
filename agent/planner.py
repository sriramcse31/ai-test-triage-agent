"""
Core agent reasoning loop - analyzes failures and produces triage results
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from typing import List, Optional
from agent.models import (
    HistoricalFailure, 
    TriageResult, 
    FailureType,
    Resolution
)
from agent.memory import FailureMemory
from agent.tools import AgentTools
import config

try:
    from llama_index.llms.ollama import Ollama
except ImportError:
    print("⚠️  LlamaIndex not installed")
    Ollama = None


class TriageAgent:
    """AI agent that triages test failures"""
    
    def __init__(self, memory: FailureMemory):
        self.memory = memory
        self.tools = AgentTools(memory)
        
        # Initialize local LLM (Ollama)
        if Ollama:
            self.llm = Ollama(
                model=config.LLM_MODEL,
                base_url=config.LLM_BASE_URL,
                temperature=config.LLM_TEMPERATURE,
                request_timeout=120.0
            )
        else:
            self.llm = None
    
    def analyze(self, failure: HistoricalFailure) -> TriageResult:
        """
        Main analysis loop:
        1. Gather evidence
        2. Search similar failures
        3. Calculate flakiness
        4. Classify failure
        5. Generate explanation
        6. Suggest actions
        """
        reasoning_steps = []
        
        # Step 1: Gather evidence
        reasoning_steps.append("Gathering evidence from logs and error messages")
        
        # Step 2: Search for similar failures
        reasoning_steps.append("Searching for similar past failures in memory")
        similar_failures = self.tools.search_similar_failures(failure, top_k=5)
        
        # Step 3: Get test history
        reasoning_steps.append(f"Retrieving history for test: {failure.test_name}")
        history = self.tools.get_test_history(failure.test_name)
        
        # Step 4: Calculate flakiness
        reasoning_steps.append("Calculating flakiness probability")
        flaky_score = self.tools.calculate_flaky_score(failure, history)
        
        # Step 5: Classify failure type
        reasoning_steps.append("Classifying failure type")
        failure_type = self.tools.classify_error_type(failure)
        
        # Step 6: Generate root cause explanation with LLM
        reasoning_steps.append("Generating root cause explanation")
        root_cause = self._generate_root_cause_explanation(
            failure, similar_failures, history, failure_type
        )
        
        # Step 7: Suggest actions
        reasoning_steps.append("Determining actionable next steps")
        actions = self.tools.suggest_actions(
            failure_type, flaky_score, similar_failures
        )
        
        # Step 8: Calculate confidence
        confidence = self._calculate_confidence(
            failure_type, similar_failures, flaky_score
        )
        
        return TriageResult(
            test_name=failure.test_name,
            classification=failure_type,
            flaky_probability=flaky_score,
            root_cause_explanation=root_cause,
            suggested_actions=actions,
            confidence_score=confidence,
            similar_failures=similar_failures[:3],
            reasoning_steps=reasoning_steps
        )
    
    def _generate_root_cause_explanation(
        self,
        failure: HistoricalFailure,
        similar_failures: List[HistoricalFailure],
        history: List[HistoricalFailure],
        failure_type: FailureType
    ) -> str:
        """Generate natural language explanation of root cause"""
        
        # Build evidence for LLM
        evidence = self.tools.build_evidence_summary(
            failure, similar_failures, history
        )
        
        # If LLM available, use it for detailed explanation
        if self.llm:
            prompt = f"""You are a test automation expert analyzing a test failure.

{evidence}

Based on this evidence, provide a clear, concise root cause explanation (2-3 sentences).
Focus on:
1. What specifically went wrong
2. Why it likely happened
3. Reference similar past failures if relevant

Root cause explanation:"""
            
            try:
                response = self.llm.complete(prompt)
                return response.text.strip()
            except Exception as e:
                print(f"⚠️  LLM error: {e}")
                # Fallback to rule-based
        
        # Fallback: Rule-based explanation
        return self._rule_based_explanation(
            failure, similar_failures, failure_type
        )
    
    def _rule_based_explanation(
        self,
        failure: HistoricalFailure,
        similar_failures: List[HistoricalFailure],
        failure_type: FailureType
    ) -> str:
        """Generate explanation without LLM (fallback)"""
        
        explanations = {
            FailureType.TIMEOUT: (
                f"The test '{failure.test_name}' timed out waiting for an element. "
                f"This typically occurs when the page takes longer than expected to render, "
                f"or when elements are hidden/delayed by animations."
            ),
            FailureType.SELECTOR: (
                f"The test cannot find the expected element using the specified selector. "
                f"This usually indicates that the UI structure has changed, requiring "
                f"an update to the test's element locators."
            ),
            FailureType.NETWORK: (
                f"Network connectivity issues prevented the test from completing. "
                f"This may be due to temporary network instability in the CI environment "
                f"or issues with external dependencies."
            ),
            FailureType.DATA_SETUP: (
                f"Test data setup failed, likely due to database constraint violations "
                f"or leftover data from previous test runs. Proper test isolation and "
                f"cleanup is needed."
            ),
            FailureType.ENVIRONMENT: (
                f"The test failed due to environment configuration issues. "
                f"This could involve missing dependencies, incorrect settings, or "
                f"service availability problems."
            ),
        }
        
        base_explanation = explanations.get(
            failure_type,
            f"The test '{failure.test_name}' failed with error: {failure.error_message}"
        )
        
        # Add context from similar failures
        if similar_failures and similar_failures[0].resolution:
            resolution = similar_failures[0].resolution
            base_explanation += (
                f" A similar failure was previously resolved by: "
                f"{resolution.fix_applied}"
            )
        
        return base_explanation
    
    def _calculate_confidence(
        self,
        failure_type: FailureType,
        similar_failures: List[HistoricalFailure],
        flaky_score: float
    ) -> float:
        """Calculate confidence score for the analysis"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence if we have resolved similar failures
        resolved_similar = [
            f for f in similar_failures 
            if f.resolution and f.resolution.confidence > 0.7
        ]
        if resolved_similar:
            confidence += 0.3
        
        # Lower confidence for unknown failure types
        if failure_type == FailureType.UNKNOWN:
            confidence -= 0.2
        
        # Adjust for flakiness (flaky tests are harder to diagnose)
        if flaky_score > 0.7:
            confidence -= 0.1
        
        return max(0.1, min(1.0, confidence))


def analyze_failure_file(log_file: str) -> TriageResult:
    """Convenience function to analyze a log file"""
    from pathlib import Path
    from ingestion.log_parser import LogParser
    from datetime import datetime
    
    # Parse log file
    parser = LogParser()
    parsed = parser.parse_file(Path(log_file))
    
    # Convert to HistoricalFailure
    failure = HistoricalFailure(
        test_name=parsed.test_name,
        error_message=parsed.failure_message,
        error_type=parsed.error_type,
        log_snippet="\n".join(parsed.error_lines[:5]),
        timestamp=datetime.now(),
        duration_seconds=parsed.duration_seconds,
        retry_count=parsed.retry_count,
        artifacts=parsed.artifacts,
        resolution=None
    )
    
    # Initialize agent and analyze
    memory = FailureMemory()
    agent = TriageAgent(memory)
    
    return agent.analyze(failure)


if __name__ == "__main__":
    import sys
    from rich.console import Console
    
    console = Console()
    
    if len(sys.argv) < 2:
        console.print("[red]Usage: python agent/planner.py <log_file>[/red]")
        console.print("\nExample:")
        console.print("  python agent/planner.py demo/sample_ci_failures/test_login_timeout.log")
        sys.exit(1)
    
    console.print("\n[bold cyan]🤖 AI Test Triage Agent[/bold cyan]\n")
    console.print(f"Analyzing: {sys.argv[1]}\n")
    
    # Analyze the failure
    result = analyze_failure_file(sys.argv[1])
    
    # Print results
    console.print(result.to_report())