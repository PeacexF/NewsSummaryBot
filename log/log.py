# Taken from another project
# Probably temporary

import logging
from logging.handlers import TimedRotatingFileHandler
import os
import sys

def setup_logger():
    # конфиг
    log_level_str = "INFO"
    log_file = "log/log.log"    # logloglogloglog
    retention_days = 7
    
    # директория для логов
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    level = getattr(logging, log_level_str, logging.INFO)
    log_format = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)

    # автоочистка
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",                # ротация файлов каждую полночь
        interval=1,                     # раз в 1 день
        backupCount=retention_days,     # сколько старых файлов хранить
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    file_handler.suffix = "%Y-%m-%d"    # дата к каждомму уник лог файлу

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return logging.getLogger("NewsSummary")

logger = setup_logger()