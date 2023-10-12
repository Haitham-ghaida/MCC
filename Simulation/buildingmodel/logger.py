import functools
import logging
import time
from datetime import timedelta
from shape_optim.buildingmodel import log_dir


def create_logger():
    """
    Creates a logging object and returns it
    """
    logger = logging.getLogger("logger")
    logger.setLevel(logging.INFO)
    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_dir / "test.log")
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


logger = create_logger()


def duration_logging(function):
    """
    A decorator that wraps the passed in function and logs the execution time
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            start = time.time()
            result = function(*args, **kwargs)
            duration = time.time() - start
            logger.info(f'duration of {function.__name__} : {timedelta(seconds=duration)}')
            return result
        except:
            # log the exception
            err = "There was an exception in  "
            err += function.__name__
            logger.exception(err)
            # re-raise the exception
            raise
    return wrapper