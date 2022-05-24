# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import os.path
import sys
import logging
from urllib.parse import urlencode, parse_qsl

import xbmcgui
import xbmcplugin

_URL = sys.argv[0]
_HANDLE = int(sys.argv[1])

TIMEOUT = 5
VERIFY = True 

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

LOGGER = get_logger("4Nyan Image Plugin", os.path.join(os.path.dirname(__file__), "4NyanImage.log"))


def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :return: plugin call URL
    :rtype: str
    """
    return '{}?{}'.format(_URL, urlencode(kwargs))


def show_image(**kwargs):
    pass 


def router(paramstring):

    params = dict(parse_qsl(paramstring))

    if not params:
        return 

    LOGGER.info(str(params))

    map_ = {
        'show_image' : show_image
    }

    if 'action' in params:

        map_['action'](**params)


if __name__ == '__main__':
    LOGGER.info(str(sys.argv))
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
