"""Structured logging helpers for cli-mock-runtime."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from .output_config import LogFormat, get_log_format, ENV_VAR_NAME

try:
    from rich.console import Console
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class RichConsoleRenderer:
    """Custom structlog renderer using Rich library for beautiful console output."""
    
    def __init__(self) -> None:
        if not RICH_AVAILABLE:
            raise ImportError("rich library is required for RichConsoleRenderer")
        self.console = Console(force_terminal=True, width=200)
        
        # Custom color scheme - pleasant colors without purple/magenta
        self.level_styles = {
            "debug": "dim cyan",
            "info": "cyan",
            "warning": "yellow",
            "error": "bold red",
            "critical": "bold white on red",
        }
    
    def __call__(self, logger: Any, name: str, event_dict: dict[str, Any]) -> str:
        """Render a log entry with Rich formatting."""
        # Extract main components
        timestamp = event_dict.pop("timestamp", "")
        level = event_dict.pop("level", "info")
        event = event_dict.pop("event", "")
        
        # Build styled text
        text = Text()
        
        # Timestamp in dim white
        text.append(timestamp, style="dim white")
        text.append(" ")
        
        # Log level with appropriate color
        level_style = self.level_styles.get(level, "white")
        text.append(f"[{level:<8}]", style=level_style)
        text.append(" ")
        
        # Event message in bold white
        text.append(event, style="bold white")
        
        # Calculate padding to align key-value pairs
        padding = max(0, 32 - len(event))
        if padding > 0 and event_dict:
            text.append(" " * padding)
        
        # Key-value pairs with pleasant colors
        items = sorted(event_dict.items())
        for i, (key, value) in enumerate(items):
            if key not in ("color_message", "stack", "exception"):
                text.append(f"{key}=", style="dim white")
                # Values in bright cyan instead of purple/magenta
                text.append(str(value), style="bright_cyan")
                if i < len(items) - 1:
                    text.append(" ")
        
        # Use console to render with ANSI codes
        from io import StringIO
        string_buffer = StringIO()
        temp_console = Console(file=string_buffer, force_terminal=True, width=200, legacy_windows=False)
        temp_console.print(text, end="")
        return string_buffer.getvalue()


def configure_logging(log_level: str, log_format: LogFormat = "console") -> structlog.stdlib.BoundLogger:
    """Configure structlog to emit JSON events compatible with the smoke runtime."""

    normalized_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=normalized_level,
        stream=sys.stdout,
        format="%(message)s",
        force=True,
    )

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
        structlog.processors.format_exc_info,
    ]

    if log_format == "console":
        if RICH_AVAILABLE:
            processors.append(RichConsoleRenderer())
        else:
            # Fallback to standard console renderer if rich is not available
            processors.append(structlog.dev.ConsoleRenderer(colors=True))
    elif log_format == "plain":
        # Plain text without colors - for CI/CD and non-interactive environments
        processors.append(structlog.dev.ConsoleRenderer(colors=False))
    else:  # json
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(normalized_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger("cli_mock_runtime")
