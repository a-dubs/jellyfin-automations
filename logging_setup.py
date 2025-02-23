import logging
import logging.config
from logging.handlers import RotatingFileHandler
import os

# create log directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Setup logging
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler = RotatingFileHandler('logs/jellyfin-automations.log', maxBytes=1000000, backupCount=5)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.DEBUG)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(log_handler)
    return logger
