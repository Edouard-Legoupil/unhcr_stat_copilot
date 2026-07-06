from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import structlog

# Default log directory
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "unhcr_mcp.log"


def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
) -> None:
    """
    Configure application-wide logging.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file. If None, uses DEFAULT_LOG_FILE
        log_dir: Directory for log files. If None, uses DEFAULT_LOG_DIR
    """
    # Determine log file path
    if log_file:
        log_path = Path(log_file)
    else:
        if log_dir:
            log_path = Path(log_dir) / "unhcr_mcp.log"
        else:
            log_path = DEFAULT_LOG_FILE
    
    # Create log directory if it doesn't exist
    if log_path.parent.exists() is False:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            # If we can't create the directory, fall back to stdout
            print(f"Warning: Could not create log directory {log_path.parent}: {e}")
            log_path = None
    
    # Configure handlers
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_path:
        # Add file handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        handlers.append(file_handler)
    
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper()),
        handlers=handlers,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(
                fmt="iso",
                utc=True,
            ),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    return structlog.get_logger(name)