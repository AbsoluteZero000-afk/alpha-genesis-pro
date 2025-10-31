from loguru import logger
from typing import Optional
import sys

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

_configured = False

def configure_logging(level: str = "INFO", logfile: Optional[str] = None) -> None:
    global _configured
    if _configured:
        return
    logger.remove()
    logger.add(sys.stdout, level=level, format=LOG_FORMAT, enqueue=True, backtrace=False, diagnose=False)
    if logfile:
        logger.add(logfile, rotation="10 MB", retention="10 days", level=level, format=LOG_FORMAT, enqueue=True)
    _configured = True
