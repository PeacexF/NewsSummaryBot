# Taken from another project


import logging
from logging.handlers import TimedRotatingFileHandler
import os
import sys

def setup_logger():
    # config (non-existent btw)
    log_level_str = "INFO"
    log_file = "log/log.log"    # logloglogloglog XDD
    retention_days = 7
    
    # log dir
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    level = getattr(logging, log_level_str, logging.INFO)
    log_format = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler for the console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)

    # Auto cleanup
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",                # Rotate log file each midnight
        interval=1,                     # once a day
        backupCount=retention_days,     # how many old ones to store
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    file_handler.suffix = "%Y-%m-%d"    # date as a suffix to each log file

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return logging.getLogger("NewsSummary")

logger = setup_logger()