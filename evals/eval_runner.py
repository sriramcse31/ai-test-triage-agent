#!/usr/bin/env python3
"""
Evaluation suite for testing agent accuracy
Run from project root: python evals/eval_runner.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
from typing import List, Dict
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from agent.planner import analyze_failure_file
from agent.models import FailureType

console = Console()


@dataclass
class EvalResult:
    """Result of evaluating one test case"""
    case_id: str
    case_name: str
    passed: bool
    errors: List[str]
    classification_correct: bool
    flaky_score_correct: bool
    keywords_found: bool
    actions_found: bool
    confidence_ok: bool


class EvaluationSuite:
    """Runs evaluation tests and generates reports"""
    
    def __init__(self, golden_cases_path: str = "evals/golden_cases.json"):
        self.golden_cases_path = Path(golden_cases_path)
        self.results: List[EvalResult] = []
    
    def load_golden_cases(self) -> List[Dict]:
        """Load golden test cases"""
        with open(self.golden_cases_path, 'r') as f:
            return json.load(f)
    
    def run_evaluation(self) -> List[EvalResult]:
        """Run all evaluation tests"""
        
        console.print("\n[bold cyan]🧪 Running Evaluation Suite[/bold cyan]\n")
        
        golden_cases = self.load_golden_cases()
        
        for case in golden_cases:
            console.print(f"Testing: [yellow]{case['name']}[/yellow]")
            result = self._evaluate_case(case)
            self.results.append(result)
            
            if result.passed:
                console.print("  ✅ PASSED\n")
            else:
                console.print(f"  ❌ FAILED: {', '.join(result.errors)}\n")
        
        return self.results
    
    def _evaluate_case(self, case: Dict) -> EvalResult:
        """Evaluate a single test case"""
        errors = []
        
        try:
            # Run agent analysis
            result = analyze_failure_file(case['log_file'])
            expected = case['expected']
            
            # Check 1: Classification
            classification_correct = result.classification.value == expected['classification']
            if not classification_correct:
                errors.append(
                    f"Classification: got {result.classification.value}, "
                    f"expected {expected['classification']}"
                )
            
            # Check 2: Flaky probability range
            flaky_min, flaky_max = expected['flaky_probability_range']
            flaky_score_correct = flaky_min <= result.flaky_probability <= flaky_max
            if not flaky_score_correct:
                errors.append(
                    f"Flaky score: {result.flaky_probability:.2f} "
                    f"not in range [{flaky_min}, {flaky_max}]"
                )
            
            # Check 3: Keywords in explanation
            explanation_lower = result.root_cause_explanation.lower()
            keywords_found = all(
                kw.lower() in explanation_lower 
                for kw in expected.get('should_contain_keywords', [])
            )
            if not keywords_found:
                missing = [
                    kw for kw in expected['should_contain_keywords']
                    if kw.lower() not in explanation_lower
                ]
                errors.append(f"Missing keywords in explanation: {missing}")
            
            # Check 4: Suggested actions
            actions_text = ' '.join(result.suggested_actions).lower()
            actions_found = any(
                phrase.lower() in actions_text
                for phrase in expected.get('suggested_actions_should_include', [])
            )
            if not actions_found:
                errors.append(
                    f"Expected action phrases not found: "
                    f"{expected['suggested_actions_should_include']}"
                )
            
            # Check 5: Confidence threshold
            confidence_ok = result.confidence_score >= expected.get('min_confidence', 0.5)
            if not confidence_ok:
                errors.append(
                    f"Confidence too low: {result.confidence_score:.2f} < "
                    f"{expected['min_confidence']}"
                )
            
            return EvalResult(
                case_id=case['id'],
                case_name=case['name'],
                passed=len(errors) == 0,
                errors=errors,
                classification_correct=classification_correct,
                flaky_score_correct=flaky_score_correct,
                keywords_found=keywords_found,
                actions_found=actions_found,
                confidence_ok=confidence_ok
            )
            
        except Exception as e:
            return EvalResult(
                case_id=case['id'],
                case_name=case['name'],
                passed=False,
                errors=[f"Exception: {str(e)}"],
                classification_correct=False,
                flaky_score_correct=False,
                keywords_found=False,
                actions_found=False,
                confidence_ok=False
            )
    
    def generate_report(self):
        """Generate evaluation report"""
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        # Summary table
        console.print("\n[bold cyan]📊 Evaluation Summary[/bold cyan]\n")
        
        summary_table = Table(show_header=True)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green")
        summary_table.add_column("Percentage", style="yellow")
        
        summary_table.add_row(
            "Total Cases",
            str(total),
            "100%"
        )
        summary_table.add_row(
            "Passed",
            str(passed),
            f"{(passed/total*100):.1f}%"
        )
        summary_table.add_row(
            "Failed",
            str(failed),
            f"{(failed/total*100):.1f}%" if failed > 0 else "0%"
        )
        
        console.print(summary_table)
        console.print()
        
        # Detailed results
        console.print("[bold cyan]📋 Detailed Results[/bold cyan]\n")
        
        results_table = Table(show_header=True)
        results_table.add_column("Case ID", style="cyan")
        results_table.add_column("Name", style="white")
        results_table.add_column("Classification", style="yellow")
        results_table.add_column("Flaky Score", style="magenta")
        results_table.add_column("Keywords", style="blue")
        results_table.add_column("Actions", style="green")
        results_table.add_column("Confidence", style="red")
        results_table.add_column("Overall", style="bold")
        
        for r in self.results:
            results_table.add_row(
                r.case_id,
                r.case_name[:30],
                "✅" if r.classification_correct else "❌",
                "✅" if r.flaky_score_correct else "❌",
                "✅" if r.keywords_found else "❌",
                "✅" if r.actions_found else "❌",
                "✅" if r.confidence_ok else "❌",
                "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
            )
        
        console.print(results_table)
        console.print()
        
        # Failed cases details
        failed_cases = [r for r in self.results if not r.passed]
        if failed_cases:
            console.print("[bold red]❌ Failed Cases Details[/bold red]\n")
            
            for result in failed_cases:
                error_text = "\n".join([f"  • {err}" for err in result.errors])
                console.print(Panel(
                    error_text,
                    title=f"{result.case_id}: {result.case_name}",
                    border_style="red"
                ))
                console.print()
        
        # Accuracy breakdown
        console.print("[bold cyan]📈 Accuracy Breakdown[/bold cyan]\n")
        
        accuracy_table = Table(show_header=True)
        accuracy_table.add_column("Check", style="cyan")
        accuracy_table.add_column("Correct", style="green")
        accuracy_table.add_column("Accuracy", style="yellow")
        
        checks = [
            ("Classification", sum(1 for r in self.results if r.classification_correct)),
            ("Flaky Score", sum(1 for r in self.results if r.flaky_score_correct)),
            ("Keywords", sum(1 for r in self.results if r.keywords_found)),
            ("Actions", sum(1 for r in self.results if r.actions_found)),
            ("Confidence", sum(1 for r in self.results if r.confidence_ok))
        ]
        
        for check_name, correct in checks:
            accuracy_table.add_row(
                check_name,
                f"{correct}/{total}",
                f"{(correct/total*100):.1f}%"
            )
        
        console.print(accuracy_table)
        console.print()
        
        # Overall score
        if passed == total:
            console.print("[bold green]🎉 All tests passed![/bold green]\n")
        else:
            console.print(f"[bold yellow]⚠️  {failed} test(s) failed[/bold yellow]\n")


def main():
    """Run evaluation suite"""
    suite = EvaluationSuite()
    suite.run_evaluation()
    suite.generate_report()


if __name__ == "__main__":
    main()