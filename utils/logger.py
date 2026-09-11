import logging
import sys
from config import settings

def setup_logger() -> logging.Logger:
    """Configure and return the root logger with structured formatting."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    logger = logging.getLogger("JoinVerifyBot")
    logger.setLevel(log_level)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        
        try:
            import colorlog
            formatter = colorlog.ColoredFormatter(
                "%(log_color)s[%(asctime)s] [%(levelname)-8s]%(reset)s %(blue)s[%(name)s]%(reset)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
                log_colors={
                    "DEBUG": "cyan",
                    "INFO": "green",
                    "WARNING": "yellow",
                    "ERROR": "red",
                    "CRITICAL": "bold_red",
                }
            )
        except ImportError:
            formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
            
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

logger = setup_logger()
