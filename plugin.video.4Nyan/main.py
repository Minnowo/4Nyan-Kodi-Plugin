# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html


import os.path
import sys
import logging
import json 
from urllib.parse import urlencode, parse_qsl

import requests
from requests.exceptions import Timeout

import xbmcgui
import xbmcplugin

# Get the plugin url in plugin:// notation.
_URL = sys.argv[0]
# Get the plugin handle as an integer number.
_HANDLE = int(sys.argv[1])

TIMEOUT = 5
VERIFY = True 

data = None 

with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as reader:

    data = json.load(reader)

    if "server_ip" not in data:
        raise Exception("server id is required")

    if "port" not in data:
        raise Exception("port is required")

BNYAN_HOST = "http://{}:{}/".format(data["server_ip"], data['port'])
BNYAN_API = {
    "get_categories" : BNYAN_HOST + "search/get_categories",
    "get_file_tags"  : BNYAN_HOST + "search/get_file_tags",
    "get_files"      : BNYAN_HOST + "search/get_files"
}


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

LOGGER = get_logger("Kodi Plugin Test", os.path.join(os.path.dirname(__file__), "sample-kodi.log"))


def fetch(url, method ="get"):

    try:

        response = requests.request(method, url, stream=True, timeout=TIMEOUT, verify=VERIFY)
    
    except (ConnectionError, Timeout) as exc:

        LOGGER.error(exc.__repr__())
        return []
    
    except Exception as exc:

        print("Fatal error occured: " + exc.__repr__())
        LOGGER.fatal("in get_categories -> requests.requests('GET'...): " + exc.__repr__())
        return []

    
    status = response.status_code

    if status == 404:
        LOGGER.info("Request to '{}' 404'd".format(url))
        return []  

    if status != 200:  # OK
        LOGGER.info("Request to '{1}' returned unknown status: '{2}'".format(url, status))
        return []

    return response.json()



def get_url(**kwargs):
    """
    Create a URL for calling the plugin recursively from the given set of keyword arguments.

    :param kwargs: "argument=value" pairs
    :return: plugin call URL
    :rtype: str
    """
    return '{}?{}'.format(_URL, urlencode(kwargs))


def get_categories():

    return fetch(BNYAN_API['get_categories'])


def get_videos(category):
    
    return ""


def list_categories():
    """
    Create the list of video categories in the Kodi interface.
    """
    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_HANDLE, 'My Video Collection')
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_HANDLE, 'videos')
    # Get video categories
    categories = get_categories()
    # Iterate through categories
    for category in categories:

        LOGGER.info(category)


        # Create a list item with a text label and a thumbnail image.
        list_item = xbmcgui.ListItem(label=category.get("tag", "NULL"))

        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use the same image for all items for simplicity's sake.
        # In a real-life plugin you need to set each image accordingly.
        # list_item.setArt({'thumb': VIDEOS[category][0]['thumb'],
        #                   'icon': VIDEOS[category][0]['thumb'],
        #                   'fanart': VIDEOS[category][0]['thumb']})


        # Set additional info for the list item.
        # Here we use a category name for both properties for for simplicity's sake.
        # setInfo allows to set various information for an item.
        # For available properties see the following link:
        # https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
        # 'mediatype' is needed for a skin to display info for this ListItem correctly.
        list_item.setInfo('video', {'title': category.get("tag", "NULL"),
                                    'genre': category.get("tag", "NULL"),
                                    'mediatype': 'video'})


        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=listing&category=Animals
        url = get_url(action='listing', category=category.get("tag", "NULL"), tag_id=str(category.get("tag_id")))

        # is_folder = True means that this item opens a sub-list of lower level items.
        is_folder = True

        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)


    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_HANDLE)


def list_videos(category):
    """
    Create the list of playable videos in the Kodi interface.

    :param category: Category name
    :type category: str
    """

    # Set plugin category. It is displayed in some skins as the name
    # of the current section.
    xbmcplugin.setPluginCategory(_HANDLE, category["category"])
    
    # Set plugin content. It allows Kodi to select appropriate views
    # for this type of content.
    xbmcplugin.setContent(_HANDLE, 'videos')


    

    LOGGER.info("list videos: " + str(category))
    
    tag_id = category.get("tag_id")
    
    url = BNYAN_API['get_files'] + "?tid={}".format(tag_id)

    LOGGER.info(url)

    json = fetch(url)

    for v in json['content']:

        file_id  = v["hash_id"]
        filename = v["hash"]

        LOGGER.info("File id: " + str(file_id))
        LOGGER.info("Calling: " + BNYAN_API['get_file_tags'] + "?fid={}".format(file_id))

        tags = fetch(BNYAN_API['get_file_tags'] + "?fid={}".format(file_id))

        # LOGGER.info("Response: " + str(tags))

        if tags:
            tags = tags[str(file_id)]

        for tag in tags:

            if tag["namespace"] == "filename":
                
                filename = tag["tag"]


        v_url   = v["static_url"][0]
        v_thumb = v["static_url"][1]

        if len(v['static_url']) > 2:
            v_url = v['static_url'][2]

        list_item = xbmcgui.ListItem(label=v['hash'])

        list_item.setInfo('video', {'title': filename,
                                    'genre': category["category"],
                                    'mediatype': 'video'})

        # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
        # Here we use the same image for all items for simplicity's sake.
        # In a real-life plugin you need to set each image accordingly.
        # list_item.setArt({'thumb': video['thumb'], 'icon': video['thumb'], 'fanart': video['thumb']})

        # Set 'IsPlayable' property to 'true'.
        # This is mandatory for playable items!
        list_item.setProperty('IsPlayable', 'true')
        # Create a URL for a plugin recursive call.
        # Example: plugin://plugin.video.example/?action=play&video=http://www.vidsplay.com/wp-content/uploads/2017/04/crab.mp4
        url = get_url(action='play', video=v_url)
        # Add the list item to a virtual Kodi folder.
        # is_folder = False means that this item won't open any sub-list.
        is_folder = False
        # Add our item to the Kodi virtual folder listing.
        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, is_folder)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_HANDLE)


def play_video(path):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    # Create a playable item with a path to play.
    play_item = xbmcgui.ListItem(path=path)
    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)


def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """

    # Parse a URL-encoded paramstring to the dictionary of
    # {<parameter>: <value>} elements
    params = dict(parse_qsl(paramstring))


    LOGGER.info(paramstring)
    LOGGER.info(params)


    # Check the parameters passed to the plugin
    if params:
        if params['action'] == 'listing':
            # Display the list of videos in a provided category.
            list_videos(params)
        elif params['action'] == 'play':
            # Play a video from a provided URL.
            play_video(params['video'])
        else:
            # If the provided paramstring does not contain a supported action
            # we raise an exception. This helps to catch coding errors,
            # e.g. typos in action names.
            raise ValueError('Invalid paramstring: {}!'.format(paramstring))
    else:
        # If the plugin is called from Kodi UI without any parameters,
        # display the list of video categories
        list_categories()


if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    router(sys.argv[2][1:])
