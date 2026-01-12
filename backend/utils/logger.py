import logging
import sys
import colorama
from logging.handlers import RotatingFileHandler
from datetime import datetime
import os

# Initialize colorama for Windows support
colorama.init()


class SymbolFormatter(logging.Formatter):
    """Custom formatter with symbols and colors for different log levels."""

    COLORS = {
        'DEBUG': colorama.Fore.CYAN,
        'INFO': colorama.Fore.GREEN,
        'WARNING': colorama.Fore.YELLOW,
        'ERROR': colorama.Fore.RED,
        'CRITICAL': colorama.Fore.RED + colorama.Style.BRIGHT,
    }

    SYMBOLS = {
        'DEBUG': '🐛',
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🔥',
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, colorama.Fore.WHITE)
        symbol = self.SYMBOLS.get(record.levelname, '')
        reset = colorama.Style.RESET_ALL

        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')

        # Create the log message
        # [TIME] SYMBOL MESSAGE
        formatted_msg = f"{color}[{timestamp}] {symbol} {record.msg}{reset}"

        # Add exception info if present
        if record.exc_info:
            formatted_msg += f"\n{colorama.Fore.RED}{self.formatException(record.exc_info)}{reset}"

        return formatted_msg


def setup_logger(name="BinanceCore", log_file="backend/logs/system.log", level=logging.INFO):
    """Sets up a robust logger with both console and file output."""

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console Handler (Pretty output)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(SymbolFormatter())
    logger.addHandler(console_handler)

    # File Handler (Detailed, rotation)
    try:
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to setup file logging: {e}")

    return logger


# Global logger instance
logger = setup_logger()
