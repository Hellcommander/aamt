#!/usr/bin/env python3
"""
Centralized logging system for ToME Asset Generators.
All generators should use this module for consistent logging and issue tracking.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import traceback


class ToMEAssetGeneratorLogger:
    """Centralized logger for ToME asset generators."""
    
    _instance: Optional['ToMEAssetGeneratorLogger'] = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.log_dir = Path(__file__).parent / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"tome_asset_generator_{timestamp}.log"
        
        # Also maintain a "latest.log" for easy access
        self.latest_log = self.log_dir / "latest.log"
        
        # Configure root logger
        self.logger = logging.getLogger("ToMEAssetGenerator")
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler (detailed)
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(file_handler)
        
        # Latest log handler (detailed)
        latest_handler = logging.FileHandler(self.latest_log, encoding='utf-8', mode='w')
        latest_handler.setLevel(logging.DEBUG)
        latest_handler.setFormatter(detailed_formatter)
        self.logger.addHandler(latest_handler)
        
        # Console handler (simpler, INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        self.logger.addHandler(console_handler)
        
        # Log initialization
        self.logger.info("=" * 80)
        self.logger.info("ToME Asset Generator Logger Initialized")
        self.logger.info(f"Log file: {self.log_file}")
        self.logger.info(f"Latest log: {self.latest_log}")
        self.logger.info("=" * 80)
        
        self._initialized = True
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """Get a logger instance, optionally with a specific name."""
        if name:
            return logging.getLogger(f"ToMEAssetGenerator.{name}")
        return self.logger
    
    def log_exception(self, exception: Exception, context: str = ""):
        """Log an exception with full traceback."""
        self.logger.error(f"Exception occurred{f' in {context}' if context else ''}: {type(exception).__name__}: {exception}")
        self.logger.debug(f"Traceback:\n{traceback.format_exc()}")
    
    def log_generation_start(self, generator_name: str, mod_name: str, config: dict = None):
        """Log the start of asset generation."""
        self.logger.info("=" * 80)
        self.logger.info(f"Starting Asset Generation")
        self.logger.info(f"Generator: {generator_name}")
        self.logger.info(f"Mod: {mod_name}")
        if config:
            self.logger.info(f"Configuration: {config}")
        self.logger.info("=" * 80)
    
    def log_generation_end(self, generator_name: str, results: dict = None):
        """Log the end of asset generation."""
        self.logger.info("=" * 80)
        self.logger.info(f"Asset Generation Complete")
        self.logger.info(f"Generator: {generator_name}")
        if results:
            self.logger.info(f"Results: {len(results)} assets generated")
            for key, value in results.items():
                if isinstance(value, dict):
                    self.logger.info(f"  {key}: {value.get('path', 'N/A')} (score: {value.get('score', 0):.2f})")
                else:
                    self.logger.info(f"  {key}: {value}")
        self.logger.info("=" * 80)
    
    def log_asset_generation(self, asset_name: str, variation: int, total: int, score: float = None):
        """Log individual asset generation."""
        msg = f"Generating {asset_name} - Variation {variation}/{total}"
        if score is not None:
            msg += f" (score: {score:.2f})"
        self.logger.debug(msg)
    
    def log_ai_request(self, task_type: str, prompt: str, model: str = None):
        """Log AI model requests."""
        self.logger.debug(f"AI Request - Type: {task_type}, Model: {model or 'auto'}")
        self.logger.debug(f"Prompt: {prompt[:200]}..." if len(prompt) > 200 else f"Prompt: {prompt}")
    
    def log_ai_response(self, task_type: str, response: str, model: str = None):
        """Log AI model responses."""
        self.logger.debug(f"AI Response - Type: {task_type}, Model: {model or 'auto'}")
        self.logger.debug(f"Response: {response[:200]}..." if len(response) > 200 else f"Response: {response}")
    
    def log_file_operation(self, operation: str, source: Path, dest: Path = None):
        """Log file operations."""
        if dest:
            self.logger.debug(f"File {operation}: {source} -> {dest}")
        else:
            self.logger.debug(f"File {operation}: {source}")
    
    def log_performance(self, operation: str, duration: float, details: dict = None):
        """Log performance metrics."""
        self.logger.info(f"Performance - {operation}: {duration:.2f}s")
        if details:
            for key, value in details.items():
                self.logger.debug(f"  {key}: {value}")


# Global instance
_logger_instance: Optional[ToMEAssetGeneratorLogger] = None


def get_logger(name: str = None) -> logging.Logger:
    """Get the global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ToMEAssetGeneratorLogger()
    return _logger_instance.get_logger(name)


def log_exception(exception: Exception, context: str = ""):
    """Log an exception with full traceback."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ToMEAssetGeneratorLogger()
    _logger_instance.log_exception(exception, context)


def log_generation_start(generator_name: str, mod_name: str, config: dict = None):
    """Log the start of asset generation."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ToMEAssetGeneratorLogger()
    _logger_instance.log_generation_start(generator_name, mod_name, config)


def log_generation_end(generator_name: str, results: dict = None):
    """Log the end of asset generation."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ToMEAssetGeneratorLogger()
    _logger_instance.log_generation_end(generator_name, results)


def log_asset_generation(asset_name: str, variation: int, total: int, score: float = None):
    """Log individual asset generation."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ToMEAssetGeneratorLogger()
    _logger_instance.log_asset_generation(asset_name, variation, total, score)


def log_ai_request(task_type: str, prompt: str, model: str = None):
    """Log AI model requests."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ToMEAssetGeneratorLogger()
    _logger_instance.log_ai_request(task_type, prompt, model)


def log_ai_response(task_type: str, response: str, model: str = None):
    """Log AI model responses."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ToMEAssetGeneratorLogger()
    _logger_instance.log_ai_response(task_type, response, model)


def log_file_operation(operation: str, source: Path, dest: Path = None):
    """Log file operations."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ToMEAssetGeneratorLogger()
    _logger_instance.log_file_operation(operation, source, dest)


def log_performance(operation: str, duration: float, details: dict = None):
    """Log performance metrics."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = ToMEAssetGeneratorLogger()
    _logger_instance.log_performance(operation, duration, details)


# Convenience functions for common operations
def debug(msg: str, *args, **kwargs):
    """Log a debug message."""
    get_logger().debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Log an info message."""
    get_logger().info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Log a warning message."""
    get_logger().warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Log an error message."""
    get_logger().error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    """Log a critical message."""
    get_logger().critical(msg, *args, **kwargs)


if __name__ == '__main__':
    # Test the logger
    logger = get_logger("test")
    logger.info("Testing ToME Asset Generator Logger")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    try:
        raise ValueError("Test exception")
    except Exception as e:
        log_exception(e, "test context")
    
    log_generation_start("TestGenerator", "test-mod", {"variations": 10})
    log_asset_generation("test_asset", 1, 10, 85.5)
    log_generation_end("TestGenerator", {"test_asset": {"path": "test.png", "score": 85.5}})
    
    print(f"\nLog files created:")
    print(f"  - {ToMEAssetGeneratorLogger().log_file}")
    print(f"  - {ToMEAssetGeneratorLogger().latest_log}")

