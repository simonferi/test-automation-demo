"""Shared output format configuration for mock server."""

import os
from typing import Literal


OutputFormat = Literal["auto", "rich", "plain", "json"]
LogFormat = Literal["json", "console", "plain"]

ENV_VAR_NAME = "CONSOLE_OUTPUT_FORMAT"


def get_log_format(cli_override: str | None = None) -> LogFormat:
    """
    Get the log format with priority: CLI parameter > Environment variable > Default (console).
    
    Maps output format to log format:
    - auto/rich -> console (with colors)
    - plain -> plain (no colors, simple text)
    - json -> json
    
    Args:
        cli_override: Optional CLI parameter value that takes precedence
        
    Returns:
        LogFormat value
    """
    # Priority 1: CLI parameter
    if cli_override:
        format_lower = cli_override.lower()
        if format_lower in ("json", "console", "plain"):
            return format_lower  # type: ignore
    
    # Priority 2: Environment variable
    env_value = os.environ.get(ENV_VAR_NAME)
    if env_value:
        format_lower = env_value.lower()
        # Map output formats to log formats
        if format_lower == "json":
            return "json"
        elif format_lower == "plain":
            return "plain"  # No colors
        elif format_lower in ("auto", "rich"):
            return "console"  # With colors
    
    # Priority 3: Default - console with auto-detection
    return "console"
