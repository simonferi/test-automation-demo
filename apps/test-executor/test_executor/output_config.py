"""Shared output format configuration for all applications."""

import os
from enum import Enum


class OutputFormat(str, Enum):
    """Output format options shared across all applications."""
    AUTO = "auto"
    RICH = "rich"
    PLAIN = "plain"
    JSON = "json"


ENV_VAR_NAME = "CONSOLE_OUTPUT_FORMAT"


def get_output_format(cli_override: str | None = None) -> OutputFormat:
    """
    Get the output format with priority: CLI parameter > Environment variable > Default (auto).
    
    Args:
        cli_override: Optional CLI parameter value that takes precedence
        
    Returns:
        OutputFormat enum value
    """
    # Priority 1: CLI parameter
    if cli_override:
        try:
            return OutputFormat(cli_override.lower())
        except ValueError:
            pass
    
    # Priority 2: Environment variable
    env_value = os.environ.get(ENV_VAR_NAME)
    if env_value:
        try:
            return OutputFormat(env_value.lower())
        except ValueError:
            pass
    
    # Priority 3: Default
    return OutputFormat.AUTO
