import logging
import os
import sys
from datetime import datetime


class Logger:
    def __init__(self, name="app", log_level=logging.INFO):
        """Initialize logger with name and log level.

        Args:
            name (str): Logger name
            log_level (int): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        # Create logs directory if it doesn't exist
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Generate log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        log_filename = os.path.join(log_dir, f"{name}_{timestamp}.log")

        # Create handlers
        self._setup_file_handler(log_filename, log_level)
        self._setup_console_handler(log_level)

        # Prevent logging from propagating to the root logger
        self.logger.propagate = False

    def _setup_file_handler(self, filename, level):
        """Set up file handler for logging to file."""
        file_handler = logging.FileHandler(filename)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def _setup_console_handler(self, level):
        """Set up console handler for logging to console."""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def debug(self, message):
        """Log debug message."""
        self.logger.debug(message)

    def info(self, message):
        """Log info message."""
        self.logger.info(message)

    def warning(self, message):
        """Log warning message."""
        self.logger.warning(message)

    def error(self, message):
        """Log error message."""
        self.logger.error(message)

    def critical(self, message):
        """Log critical message."""
        self.logger.critical(message)

    def exception(self, message):
        """Log exception message with traceback."""
        self.logger.exception(message)


def get_logger(name="app", log_level=logging.INFO):
    """Factory function to create and return a Logger instance.

    Args:
        name (str): Logger name
        log_level (int): Logging level

    Returns:
        Logger: Configured logger instance
    """
    return Logger(name, log_level)
