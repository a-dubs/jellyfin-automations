import logging
import logging.config
from logging.handlers import RotatingFileHandler
import os
import time  # Import time for timezone conversion

# Create log directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Custom formatter that uses local time instead of UTC
class LocalTimeFormatter(logging.Formatter):
    def converter(self, timestamp):
        return time.localtime(timestamp)  # Convert timestamp to local time

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            return time.strftime(datefmt, ct)
        else:
            return time.strftime("%Y-%m-%d %H:%M:%S", ct)

# Setup logging with local timezone
log_formatter = LocalTimeFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('logs/jellyfin-automations.log', maxBytes=1000000, backupCount=5)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.DEBUG)

# Function to get logger
def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    if not logger.hasHandlers():  # Prevent adding multiple handlers
        logger.addHandler(log_handler)
    return logger
