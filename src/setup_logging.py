import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',   # Blue
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',   # Red
        'CRITICAL': '\033[95m' # Purple
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')

        asctime = self.formatTime(record, self.datefmt)
        name = record.name
        levelname = f"{color}{record.levelname}{self.RESET}"
        message = f"{color}{record.getMessage()}{self.RESET}"

        return f"{asctime} [{levelname}] {name}: {message}"

def setup_logging():
    # Console (with color)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColorFormatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    ))

    # File (no color)
    log_name = datetime.now().strftime("camera_%Y%m%d_%H%M%S.log")
    file_handler = RotatingFileHandler(
        log_name, maxBytes=5 * 1024 * 1024, backupCount=5
    )

    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S'
    ))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler]
    )
