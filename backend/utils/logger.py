import logging
import sys
from backend.config import settings

def setup_logger(name: str = "jarvis") -> logging.Logger:
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times if logger is already configured
    if logger.handlers:
        return logger
        
    # Get log level from config, default to INFO
    log_level_str = settings.log_level.upper()
    level = getattr(logging, log_level_str, logging.INFO)
    logger.setLevel(level)

    # Create formatters
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(filename)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler (Stdout)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    ch.setLevel(level)
    logger.addHandler(ch)

    # File Handler
    try:
        fh = logging.FileHandler("jarvis.log", encoding="utf-8")
        fh.setFormatter(formatter)
        fh.setLevel(level)
        logger.addHandler(fh)
    except Exception as e:
        # Fallback if log file cannot be written
        logger.warning(f"Could not initialize file log handler: {e}")

    # Prevent logs from propagating to the root logger
    logger.propagate = False

    return logger

# Single application-wide logger instance
logger = setup_logger()
