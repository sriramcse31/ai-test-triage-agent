#!/usr/bin/env python3
"""
Main CLI interface for AI Test Triage Agent
Save as: cli.py (in project root)
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime

from agent.planner import TriageAgent, analyze_failure_file
from agent.memory import FailureMemory
from agent.models import HistoricalFailure, FailureType
from ingestion.log_parser import LogParser

console = Console()


@click.group()
def cli():
    """🤖 AI Test Triage Agent - Automated failure analysis"""
    pass


@cli.command()
@click.argument('log_file', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True, help='Show detailed reasoning steps')
@click.option('--no-llm', is_flag=True, help='Skip LLM explanation (faster)')
def analyze(log_file, verbose, no_llm):
    """Analyze a test failure log file"""
    
    console.print("\n[bold cyan]🤖 AI Test Triage Agent[/bold cyan]\n")
    console.print(f"📄 Analyzing: [yellow]{log_file}[/yellow]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task1 = progress.add_task("Parsing log file...", total=None)
        
        # Parse the log
        parser = LogParser()
        parsed = parser.parse_file(Path(log_file))
        progress.update(task1, completed=True)
        
        task2 = progress.add_task("Loading historical data...", total=None)
        
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
        progress.update(task2, completed=True)
        
        task3 = progress.add_task("Analyzing failure...", total=None)
        
        # Initialize agent and analyze
        memory = FailureMemory()
        agent = TriageAgent(memory)
        
        if no_llm:
            agent.llm = None
        
        result = agent.analyze(failure)
        progress.update(task3, completed=True)
    
    # Display results
    _display_result(result, verbose)


@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--limit', '-l', default=10, help='Max files to analyze')
def batch(directory, limit):
    """Analyze multiple log files in a directory"""
    
    console.print("\n[bold cyan]🤖 Batch Analysis Mode[/bold cyan]\n")
    
    log_files = list(Path(directory).glob("*.log"))[:limit]
    
    if not log_files:
        console.print("[red]No .log files found in directory[/red]")
        return
    
    console.print(f"Found {len(log_files)} log files\n")
    
    # Initialize agent once
    memory = FailureMemory()
    agent = TriageAgent(memory)
    
    results = []
    
    with Progress(console=console) as progress:
        task = progress.add_task("Analyzing...", total=len(log_files))
        
        for log_file in log_files:
            try:
                result = analyze_failure_file(str(log_file))
                results.append((log_file.name, result))
            except Exception as e:
                console.print(f"[red]Error analyzing {log_file.name}: {e}[/red]")
            
            progress.advance(task)
    
    # Display summary
    _display_batch_summary(results)


@cli.command()
def stats():
    """Show memory statistics"""
    
    console.print("\n[bold cyan]📊 Memory Statistics[/bold cyan]\n")
    
    memory = FailureMemory()
    stats = memory.get_stats()
    
    table = Table(show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Failures", str(stats.get('total_failures', 0)))
    table.add_row("Database Path", stats.get('db_path', 'N/A'))
    
    console.print(table)
    console.print()


@cli.command()
@click.option('--threshold', '-t', default=0.6, help='Flaky score threshold')
def flaky(threshold):
    """List tests with high flakiness scores"""
    
    console.print(f"\n[bold cyan]🔄 Flaky Tests (score > {threshold})[/bold cyan]\n")
    
    memory = FailureMemory()
    flaky_tests = memory.get_flaky_tests(threshold=threshold)
    
    if not flaky_tests:
        console.print("[green]No flaky tests found! 🎉[/green]\n")
        return
    
    table = Table(show_header=True)
    table.add_column("Test Name", style="cyan")
    table.add_column("Flaky Score", style="yellow")
    table.add_column("Error Type", style="red")
    
    for test in flaky_tests:
        table.add_row(
            test.test_name,
            f"{test.flaky_score:.1%}",
            test.error_type or "Unknown"
        )
    
    console.print(table)
    console.print()


def _display_result(result, verbose=False):
    """Display triage result in formatted output"""
    
    # Classification panel
    classification_text = f"""
[bold]Test:[/bold] {result.test_name}
[bold]Classification:[/bold] {result.classification.value}
[bold]Flaky Probability:[/bold] {result.flaky_probability:.1%}
[bold]Confidence:[/bold] {result.confidence_score:.1%}
"""
    
    console.print(Panel(
        classification_text.strip(),
        title="📋 Classification",
        border_style="cyan"
    ))
    console.print()
    
    # Root cause
    console.print(Panel(
        result.root_cause_explanation,
        title="🔍 Root Cause Analysis",
        border_style="yellow"
    ))
    console.print()
    
    # Suggested actions
    actions_text = "\n".join([f"{i}. {action}" for i, action in enumerate(result.suggested_actions, 1)])
    console.print(Panel(
        actions_text,
        title="✅ Suggested Actions",
        border_style="green"
    ))
    console.print()
    
    # Similar failures
    if result.similar_failures:
        console.print("[bold cyan]📚 Similar Past Failures:[/bold cyan]\n")
        
        for i, similar in enumerate(result.similar_failures, 1):
            console.print(f"  [cyan]{i}. {similar.test_name}[/cyan]")
            console.print(f"     Error: {similar.error_message[:80]}...")
            if similar.resolution:
                console.print(f"     [green]Fix: {similar.resolution.fix_applied}[/green]")
            console.print()
    
    # Reasoning steps (verbose mode)
    if verbose and result.reasoning_steps:
        console.print("[bold cyan]🧠 Reasoning Steps:[/bold cyan]\n")
        for i, step in enumerate(result.reasoning_steps, 1):
            console.print(f"  {i}. {step}")
        console.print()


def _display_batch_summary(results):
    """Display summary of batch analysis"""
    
    console.print("\n[bold cyan]📊 Batch Analysis Summary[/bold cyan]\n")
    
    table = Table(show_header=True)
    table.add_column("Log File", style="cyan")
    table.add_column("Test", style="white")
    table.add_column("Classification", style="yellow")
    table.add_column("Flaky", style="red")
    table.add_column("Confidence", style="green")
    
    for log_name, result in results:
        table.add_row(
            log_name,
            result.test_name[:30],
            result.classification.value,
            f"{result.flaky_probability:.0%}",
            f"{result.confidence_score:.0%}"
        )
    
    console.print(table)
    console.print()
    
    # Statistics
    classifications = {}
    for _, result in results:
        cls = result.classification.value
        classifications[cls] = classifications.get(cls, 0) + 1
    
    console.print("[bold]Classification Breakdown:[/bold]")
    for cls, count in classifications.items():
        console.print(f"  • {cls}: {count}")
    console.print()


if __name__ == "__main__":
    cli()