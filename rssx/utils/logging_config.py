import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(config):
    """
    Configure application logging.
    
    Args:
        config: Configuration object with logging settings
    """
    log_level_name = config.get("LOG_LEVEL", "INFO")
    log_file = config.get("LOG_FILE", "rssx.log")
    
    # Map log level name to actual log level
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)
    
    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create a file handler for logging to a file
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # Add the file handler to the root logger
    logging.getLogger('').addHandler(file_handler)
    
    # Set log levels for specific loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Create a logger for this module
    logger = logging.getLogger(__name__)
    logger.info("Logging configured successfully")
    
    return logger