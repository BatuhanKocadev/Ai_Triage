import logging
import sys

def setup_logger():
    logger = logging.getLogger("ai_triage")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
logger = setup_logger()