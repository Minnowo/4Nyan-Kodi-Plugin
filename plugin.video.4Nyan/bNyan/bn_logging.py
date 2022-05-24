
import sys 
import logging 
import os.path 


def get_logger(name: str, log_file: str = "", log_level=logging.DEBUG):
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)-8s] %(message)s", "%Y-%m-%d %H:%M:%S")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    logger = logging.getLogger(name)

    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    logger.addHandler(stdout_handler)
    logger.setLevel(log_level)

    return logger
