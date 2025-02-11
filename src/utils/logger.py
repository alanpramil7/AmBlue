import asyncio
import datetime
import functools
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable


class CustomFormatter(logging.Formatter):
	"""Custom formatter with colors for different log levels"""

	# Color codes for different log levels
	COLORS = {
		"DEBUG": "\033[94m",  # Blue
		"INFO": "\033[92m",  # Green
		"WARNING": "\033[93m",  # Yellow
		"ERROR": "\033[91m",  # Red
		"CRITICAL": "\033[91m\033[1m",  # Bold Red
		"RESET": "\033[0m",  # Reset colors
	}

	def format(self, record):
		# Add color to log level if it's a terminal output
		if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
			record.levelname = (
				f"{self.COLORS.get(record.levelname)}{record.levelname}{self.COLORS['RESET']}"
			)
		return super().format(record)


def setup_logger(
	name: str = __name__,
	log_level: str = "INFO",
	log_dir: str = "logs",
) -> logging.Logger:
	"""
	Setup logger with both file and console handlers

	Args:
	    name (str): Logger name (typically __name__)
	    log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
	    log_dir (str): Directory to store log files
	"""
	# Create logger
	logger = logging.getLogger(name)
	logger.setLevel(getattr(logging, log_level))

	# Create logs directory if it doesn't exist
	log_path = Path(log_dir)
	log_path.mkdir(exist_ok=True)

	# Generate log filename with timestamp
	timestamp = datetime.datetime.now().strftime("%Y%m%d")
	log_file = log_path / f"app_{timestamp}.log"

	# Create formatters
	file_formatter = logging.Formatter(
		fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
	)

	console_formatter = CustomFormatter(
		fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
		datefmt="%H:%M:%S",
	)

	# File handler (Rotating file handler to manage log size)
	file_handler = RotatingFileHandler(
		log_file,
		maxBytes=10485760,  # 10MB
		backupCount=5,  # Keep 5 backup files
		encoding="utf-8",
	)
	file_handler.setFormatter(file_formatter)

	# Console handler
	console_handler = logging.StreamHandler(sys.stdout)
	console_handler.setFormatter(console_formatter)

	# Add handlers to logger if they haven't been added
	if not logger.handlers:
		logger.addHandler(file_handler)
		logger.addHandler(console_handler)

	return logger


# Create default logger instance
logger = setup_logger()


def log_time(func: Callable) -> Callable:
	"""Decorator to log function execution time"""

	@functools.wraps(func)
	async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
		start = time.perf_counter()
		try:
			result = await func(*args, **kwargs)
			logger.info(f"{func.__name__} completed in {time.perf_counter() - start:.2f}s")
			return result
		except Exception as e:
			logger.error(f"{func.__name__} failed: {str(e)}")
			raise

	@functools.wraps(func)
	def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
		start = time.perf_counter()
		try:
			result = func(*args, **kwargs)
			logger.info(f"{func.__name__} completed in {time.perf_counter() - start:.2f}s")
			return result
		except Exception as e:
			logger.error(f"{func.__name__} failed: {str(e)}")
			raise

	# Return appropriate wrapper based on whether the function is async or not
	if asyncio.iscoroutinefunction(func):
		return async_wrapper
	return sync_wrapper