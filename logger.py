#!/usr/bin/env python3
"""
Logging Configuration for Excel Source-Target Mapping Comparison Tool

This module provides centralized logging configuration with different levels,
output formats, and destinations.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds color to console output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Get the original formatted message
        formatted = super().format(record)
        
        # Add color if we're outputting to a terminal
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, '')
            reset = self.COLORS['RESET']
            return f"{color}{formatted}{reset}"
        
        return formatted


class ExcelComparisonLogger:
    """Centralized logger configuration for the Excel comparison tool."""
    
    def __init__(self, name: str = "excel_comparison"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.log_dir = Path("logs")
        self._setup_log_directory()
        self._configured = False
    
    def _setup_log_directory(self):
        """Create logs directory if it doesn't exist."""
        self.log_dir.mkdir(exist_ok=True)
    
    def setup_logging(self, 
                     level: str = "INFO",
                     console_output: bool = True,
                     file_output: bool = True,
                     debug_mode: bool = False) -> logging.Logger:
        """
        Set up logging configuration.
        
        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console_output: Whether to output to console
            file_output: Whether to output to file
            debug_mode: Enable debug mode with verbose output
            
        Returns:
            Configured logger instance
        """
        
        if self._configured:
            return self.logger
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Set logging level
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level if not debug_mode else logging.DEBUG)
        
        # Prevent duplicate messages from parent loggers
        self.logger.propagate = False
        
        # Create formatters
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        debug_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            
            if debug_mode:
                console_handler.setFormatter(debug_formatter)
            else:
                console_handler.setFormatter(console_formatter)
            
            self.logger.addHandler(console_handler)
        
        # Add file handler
        if file_output:
            timestamp = datetime.now().strftime("%Y%m%d")
            log_file = self.log_dir / f"excel_comparison_{timestamp}.log"
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)  # Always log everything to file
            
            if debug_mode:
                file_handler.setFormatter(debug_formatter)
            else:
                file_handler.setFormatter(file_formatter)
            
            self.logger.addHandler(file_handler)
        
        # Add rotating file handler for error logs
        if file_output:
            error_log_file = self.log_dir / "errors.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            self.logger.addHandler(error_handler)
        
        self._configured = True
        
        # Log initial setup message
        self.logger.info(f"Logging initialized - Level: {level}, Console: {console_output}, File: {file_output}, Debug: {debug_mode}")
        
        return self.logger
    
    def get_logger(self, module_name: Optional[str] = None) -> logging.Logger:
        """
        Get a logger instance for a specific module.
        
        Args:
            module_name: Name of the module requesting the logger
            
        Returns:
            Logger instance
        """
        if module_name:
            return logging.getLogger(f"{self.name}.{module_name}")
        return self.logger
    
    def set_level(self, level: str):
        """Change the logging level dynamically."""
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        # Update all handlers
        for handler in self.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                handler.setLevel(log_level)
    
    def log_performance(self, operation: str, duration: float, details: Optional[str] = None):
        """Log performance metrics."""
        message = f"Performance: {operation} completed in {duration:.3f}s"
        if details:
            message += f" - {details}"
        self.logger.info(message)
    
    def log_comparison_summary(self, file1: str, file2: str, summary: dict):
        """Log comparison operation summary."""
        self.logger.info(f"Comparison Summary: {file1} vs {file2}")
        self.logger.info(f"  Tabs: +{summary.get('tabs_added', 0)} -{summary.get('tabs_deleted', 0)} ~{summary.get('tabs_modified', 0)}")
        self.logger.info(f"  Mappings: +{summary.get('total_mappings_added', 0)} -{summary.get('total_mappings_deleted', 0)} ~{summary.get('total_mappings_modified', 0)}")
    
    def log_file_operation(self, operation: str, file_path: str, success: bool = True, error: Optional[str] = None):
        """Log file operations."""
        if success:
            self.logger.info(f"File {operation} successful: {file_path}")
        else:
            self.logger.error(f"File {operation} failed: {file_path} - {error}")
    
    def close_handlers(self):
        """Close all file handlers properly."""
        for handler in self.logger.handlers:
            if isinstance(handler, (logging.FileHandler, logging.handlers.RotatingFileHandler)):
                handler.close()


# Global logger instance
_global_logger = None


def get_logger(module_name: Optional[str] = None, 
               level: str = "INFO",
               console_output: bool = True,
               file_output: bool = True,
               debug_mode: bool = False) -> logging.Logger:
    """
    Get a configured logger instance.
    
    This is the main function to use for getting loggers throughout the application.
    
    Args:
        module_name: Name of the module requesting the logger
        level: Logging level (only used for initial setup)
        console_output: Whether to output to console (only used for initial setup)
        file_output: Whether to output to file (only used for initial setup)
        debug_mode: Enable debug mode (only used for initial setup)
        
    Returns:
        Configured logger instance
    """
    global _global_logger
    
    if _global_logger is None:
        _global_logger = ExcelComparisonLogger()
        _global_logger.setup_logging(level, console_output, file_output, debug_mode)
    
    return _global_logger.get_logger(module_name)


def setup_debug_logging():
    """Quick setup for debug logging."""
    return get_logger(debug_mode=True, level="DEBUG")


def setup_production_logging():
    """Quick setup for production logging."""
    return get_logger(level="INFO", console_output=False, file_output=True)


def setup_testing_logging():
    """Quick setup for testing (console only)."""
    return get_logger(level="WARNING", console_output=True, file_output=False)


def log_exception(logger: logging.Logger, operation: str, error: Exception):
    """Log exceptions with full context."""
    logger.error(f"Exception in {operation}: {type(error).__name__}: {str(error)}", exc_info=True)


def log_user_action(logger: logging.Logger, action: str, details: Optional[str] = None):
    """Log user actions for audit purposes."""
    message = f"User Action: {action}"
    if details:
        message += f" - {details}"
    logger.info(message)


# Context manager for performance logging
class PerformanceTimer:
    """Context manager to log operation performance."""
    
    def __init__(self, logger: logging.Logger, operation: str, details: Optional[str] = None):
        self.logger = logger
        self.operation = operation
        self.details = details
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting {self.operation}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            if exc_type is None:
                message = f"Performance: {self.operation} completed in {duration:.3f}s"
                if self.details:
                    message += f" - {self.details}"
                self.logger.info(message)
            else:
                self.logger.error(f"Performance: {self.operation} failed after {duration:.3f}s")


# Example usage
if __name__ == "__main__":
    # Demo of different logging configurations
    
    # Standard logging
    logger = get_logger("demo", level="INFO")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Debug logging
    debug_logger = setup_debug_logging()
    debug_logger.debug("This is a debug message")
    
    # Performance logging example
    with PerformanceTimer(logger, "example operation", "processing 100 items"):
        import time
        time.sleep(0.1)  # Simulate work
    
    print(f"Logs written to: {Path('logs').absolute()}")