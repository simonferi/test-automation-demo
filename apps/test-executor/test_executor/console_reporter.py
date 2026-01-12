"""Console reporter with intelligent environment detection for test execution output."""

import os
import sys
from typing import Optional, Any

from .output_config import OutputFormat

try:
    from rich.console import Console
    from rich.progress import (
        Progress,
        SpinnerColumn,
        BarColumn,
        TextColumn,
        TimeRemainingColumn,
        TaskID,
    )
    from rich.live import Live
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    TaskID = Any  # type: ignore


class ConsoleReporter:
    """
    Smart console reporter that adapts to environment.
    
    Automatically detects:
    - Interactive terminals (use rich with progress bars)
    - CI/CD environments (use plain text)
    - Pipe/redirect scenarios (use plain text)
    """
    
    def __init__(self, output_format: OutputFormat = OutputFormat.AUTO):
        self.output_format = output_format
        self._detect_environment()
        
        if self.use_rich:
            self.console = Console()
            self._setup_rich_components()
        else:
            self.console = None
            
    def _detect_environment(self) -> None:
        """Detect if we should use rich output or plain text."""
        if self.output_format == OutputFormat.RICH:
            self.use_rich = RICH_AVAILABLE
        elif self.output_format == OutputFormat.PLAIN:
            self.use_rich = False
        elif self.output_format == OutputFormat.JSON:
            self.use_rich = False
        else:  # AUTO
            # Use rich only if:
            # 1. Rich library is available
            # 2. stdout is a terminal (not redirected/piped)
            # 3. Not in CI environment (check common CI env vars)
            is_terminal = sys.stdout.isatty()
            is_ci = any([
                sys.platform == 'win32' and 'GITHUB_ACTIONS' in os.environ,
                'CI' in os.environ,
                'JENKINS_HOME' in os.environ,
                'GITLAB_CI' in os.environ,
                'TRAVIS' in os.environ,
            ])
            self.use_rich = RICH_AVAILABLE and is_terminal and not is_ci
            
    def _setup_rich_components(self) -> None:
        """Setup rich progress bar and live components."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console,
        )
        self.progress_task: Optional[TaskID] = None
        self.live: Optional[Live] = None
        self.results_table: Optional[Table] = None
        
    def start_test_suite(self, total_steps: int, scenario_name: str) -> None:
        """Initialize test suite execution display."""
        if self.use_rich:
            self.results_table = Table(show_header=True, header_style="bold cyan")
            self.results_table.add_column("Step", style="dim", width=12)
            self.results_table.add_column("Endpoint", width=40)
            self.results_table.add_column("Status", width=10)
            self.results_table.add_column("Duration", justify="right", width=12)
            
            self.progress_task = self.progress.add_task(
                f"[cyan]Running {scenario_name}",
                total=total_steps
            )
            
            # Start live display with simpler rendering
            from rich.console import Group
            
            self.live = Live(
                Group(self.progress, self.results_table),
                console=self.console,
                refresh_per_second=4
            )
            self.live.start()
        else:
            # Plain text mode
            print(f"Running test scenario: {scenario_name}")
            print(f"Total steps: {total_steps}")
            print("-" * 80)
            
    def report_step_start(self, step_num: int, endpoint: str, method: str) -> None:
        """Report that a test step is starting."""
        if not self.use_rich:
            # Plain text: show simple progress
            print(f"[{step_num}] {method} {endpoint} ... ", end="", flush=True)
            
    def report_step_result(
        self,
        step_num: int,
        endpoint: str,
        method: str,
        passed: bool,
        duration_ms: float,
        error_msg: Optional[str] = None
    ) -> None:
        """Report a test step result."""
        if self.use_rich:
            # Rich mode: update table and progress
            status_icon = "✓" if passed else "✗"
            status_color = "green" if passed else "red"
            status_text = Text(f"{status_icon} {'PASS' if passed else 'FAIL'}", style=status_color)
            
            step_label = f"Step {step_num}"
            endpoint_label = f"{method} {endpoint}"
            duration_label = f"{duration_ms:.0f}ms"
            
            self.results_table.add_row(
                step_label,
                endpoint_label,
                status_text,
                duration_label
            )
            
            if error_msg and not passed:
                self.results_table.add_row(
                    "",
                    Text(f"Error: {error_msg}", style="red"),
                    "",
                    ""
                )
            
            self.progress.update(self.progress_task, advance=1)
            # Update live display automatically
        else:
            # Plain text mode
            if passed:
                print(f"✓ PASS ({duration_ms:.0f}ms)")
            else:
                print(f"✗ FAIL ({duration_ms:.0f}ms)")
                if error_msg:
                    print(f"  Error: {error_msg}")
                    
    def finish_test_suite(
        self,
        total: int,
        passed: int,
        failed: int,
        duration_ms: float
    ) -> None:
        """Display final test suite summary."""
        if self.use_rich:
            # Stop live display
            if self.live:
                self.live.stop()
                
            # Print final summary panel
            from rich.panel import Panel
            
            summary_text = Text()
            summary_text.append(f"Total: {total}  ", style="bold")
            summary_text.append(f"Passed: {passed}  ", style="bold green")
            summary_text.append(f"Failed: {failed}  ", style="bold red" if failed > 0 else "bold green")
            summary_text.append(f"Duration: {duration_ms:.0f}ms", style="bold cyan")
            
            status = "✓ ALL TESTS PASSED" if failed == 0 else "✗ SOME TESTS FAILED"
            status_style = "bold green" if failed == 0 else "bold red"
            
            self.console.print()
            self.console.print(Panel(
                summary_text,
                title=Text(status, style=status_style),
                border_style="green" if failed == 0 else "red"
            ))
        else:
            # Plain text summary
            print("-" * 80)
            print(f"Total: {total} | Passed: {passed} | Failed: {failed} | Duration: {duration_ms:.0f}ms")
            if failed == 0:
                print("✓ ALL TESTS PASSED")
            else:
                print("✗ SOME TESTS FAILED")
                
    def print_error(self, message: str) -> None:
        """Print an error message."""
        if self.use_rich:
            self.console.print(f"[bold red]Error:[/] {message}")
        else:
            print(f"Error: {message}")
            
    def print_info(self, message: str) -> None:
        """Print an info message."""
        if self.use_rich:
            self.console.print(f"[cyan]{message}[/]")
        else:
            print(message)
