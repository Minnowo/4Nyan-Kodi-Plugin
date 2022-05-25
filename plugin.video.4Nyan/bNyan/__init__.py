# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import os.path
import sys
from urllib.parse import urlencode, parse_qsl

import requests
from requests.exceptions import Timeout

from . import bn_logging

import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin

LOGGER = bn_logging.get_logger("Kodi Plugin Test", os.path.join(os.path.dirname(os.path.dirname(__file__)), "4Nyan.log"))

_URL = sys.argv[0]
_HANDLE = int(sys.argv[1])

ADDON = xbmcaddon.Addon()
ADDRESS = ADDON.getSetting('ipaddress')
PORT = ADDON.getSetting('port')

BNYAN_HOST = "http://{}:{}/".format(ADDRESS, PORT)
BNYAN_API = {
    "get_categories" : BNYAN_HOST + "search/get_categories",
    "get_file_tags"  : BNYAN_HOST + "search/get_file_tags",
    "get_files"      : BNYAN_HOST + "search/get_files",
    "heartbeat"      : BNYAN_HOST + "heartbeat"
}

TIMEOUT = 5
VERIFY = True 

BNYAN_IMAGE_MIME_RANGE = (100, 199) 
BNYAN_VIDEO_MIME_RANGE = (200, 299)
BNYAN_AUDIO_MIME_RANGE = (300, 399)

CONTENT_TYPE_UNKNOWN = -1
CONTENT_TYPE_IMAGE = 1
CONTENT_TYPE_VIDEO = 2
CONTENT_TYPE_AUDIO = 3


def fetch(url, method ="get"):

    try:

        response = requests.request(method, url, stream=True, timeout=TIMEOUT, verify=VERIFY)
    
    except (ConnectionError, Timeout) as exc:

        LOGGER.error(exc.__repr__(), exc_info=True)
        raise exc
    
    except Exception as exc:

        LOGGER.fatal("in get_categories -> requests.requests('GET'...): " + exc.__repr__(), exc_info=True)
        raise Exception("Fatal error making a request to {}. {}".format(url, exc))

    
    status = response.status_code

    if status == 404:
        LOGGER.info("Request to '{}' 404'd".format(url))
        return []  

    if status != 200:  # OK
        LOGGER.info("Request to '{1}' returned unknown status: '{2}'".format(url, status))
        return []

    try:
        return response.json()
    except Exception as e:

        LOGGER.error("Bad response, cannot decode json {}".format(e), exc_info=True)
        raise Exception("An error occured trying to decode the response from {} as json, likely the port or address are invalid. {}".format(url, e))



def get_url(url = _URL, **kwargs):

    return '{}?{}'.format(url, urlencode(kwargs))


def get_categories():

    return fetch(BNYAN_API['get_categories'])


def in_range(item, range):

    (min, max) = range 

    return item >= min and item <= max 


def list_categories():
    """
    Create the list of video categories in the Kodi interface.
    """

    xbmcplugin.setPluginCategory(_HANDLE, '4Nyan Categories')
    xbmcplugin.setContent(_HANDLE, 'videos')

    categories = get_categories()

    if not categories:
        LOGGER.error("Could not fetch categories")
        raise Exception("Could not fetch categories. Host {}".format(BNYAN_HOST))

    for category in categories:

        try:
            tag    = category['tag']
            tag_id = str(category['tag_id'])

        except KeyError as e:

            LOGGER.info("Key error from category response {}".format(e))
            LOGGER.info("Response content {}".format(category))
            continue 

        list_item = xbmcgui.ListItem(tag)

        list_item.setIsFolder(True)

        url = get_url(action='listing', category=tag, tag_id=tag_id)

        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item, True)

    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(_HANDLE)


def list_videos(category):
    """
    Create the list of playable videos in the Kodi interface.

    :param category: Category name
    :type category: str
    """

    xbmcplugin.setPluginCategory(_HANDLE, category["category"])
    xbmcplugin.setContent(_HANDLE, 'videos')

    
    tag_id = category.get("tag_id")
    
    url = BNYAN_API['get_files'] + "?" + urlencode({'tid' : tag_id })

    json = fetch(url)

    if 'content' not in json:

        LOGGER.error("Response from {} did not return any content {}".format(url, json))
        raise Exception("Response from {} did not return any content".format(url))

    for v in json['content']:

        try:
            file_id     = v["hash_id"]
            hash        = v["hash"]
            filename    = v["hash"]
            file_size   = v["size"]
            mime        = v["mime"]
            width       = v["width"]
            height      = v["height"]
            duration    = v["duration"]
            has_audio   = v["has_audio"]
            date_added  = v["date_added"]
            static_urls = v["static_url"]

        except KeyError as e:

            LOGGER.warning("Key error while parsing response json {}".format(e))
            LOGGER.warning("Response json: {}".format(v))

            continue

        tags = fetch(BNYAN_API['get_file_tags'] + "?fid={}".format(file_id))

        if tags:

            tags = tags.get(str(file_id), [])

        display_tags = []

        for tag in tags:

            try:

                namespace = tag["namespace"]
                tag       = tag["tag"]

            except KeyError as e:

                LOGGER.warning("Key error while getting tag information {}".format(e))
                LOGGER.warning("Response json {}".format(tag))

                continue 

            if namespace == "filename":

                filename = tag
            
            if namespace:
                display_tags.append(namespace + ":" + tag)

            else:
                display_tags.append(tag)

        content_urls = static_urls['content']
        thumb_urls   = static_urls['thumbs']

        # kodi only seems to recognize .srt subtitles 
        sub_urls     = list(filter(lambda x : x.endswith('.srt'), static_urls['subs']))
        
        content_type = CONTENT_TYPE_UNKNOWN

        if len(content_urls) < 1:

            LOGGER.warning("The response file has 0 content urls < mime: {}, hash_id: {}, hash: {} >".format(mime, file_id, hash))
            continue 

        if len(thumb_urls) < 1:
        
            LOGGER.warning("The response file has 0 thumb urls < mime: {}, hash_id: {}, hash: {} >".format(mime, file_id, hash))
            continue 

        if in_range(mime, BNYAN_IMAGE_MIME_RANGE):
            
            content_type = CONTENT_TYPE_IMAGE

            content_url = content_urls[0]
            thumb_url   = thumb_urls[0]

        elif in_range(mime, BNYAN_VIDEO_MIME_RANGE):

            content_type = CONTENT_TYPE_VIDEO

            content_url = content_urls[0]

            master = list(filter(lambda x : x.endswith('master.m3u8'), content_urls))

            if master:
                content_url = master[0]

            thumb_url   = thumb_urls[0]

        elif in_range(mime, BNYAN_AUDIO_MIME_RANGE):

            content_type = CONTENT_TYPE_AUDIO

            # 4Nyan doesn't do audio yet 
            LOGGER.error("Unsupported content type audio, ignoring.")
            continue 

        if content_type == CONTENT_TYPE_UNKNOWN:
            
            LOGGER.error("Invalid content type returned < mime: {}, hash_id: {}, hash: {} >".format(mime, file_id, hash))
            continue


        list_item = xbmcgui.ListItem(filename, hash)

        list_item.setUniqueIDs({ "hash" : hash, 'hash_id' : file_id })

        list_item.setProperty('IsPlayable', 'true')

        list_item.setIsFolder(False)

        list_item.setContentLookup(False)
        
        try:
            list_item.setDateTime(date_added)

        except AttributeError:
            LOGGER.warning("ListItem doesn't has setDateTime")

        if sub_urls:
            list_item.setSubtitles(sub_urls)


        if content_type == CONTENT_TYPE_IMAGE:

            list_item.setInfo('image', {
                'count'        : file_id,
                'date'         : date_added,
                'size'         : file_size,
                'picturepath'  : filename,
                })

        elif content_type == CONTENT_TYPE_VIDEO:

            list_item.setInfo('image', {
                'count'        : file_id,
                'date'         : date_added,
                'size'         : file_size,
                'tag'          : display_tags,
                'mediatype'    : 'video'
                })

        list_item.setArt({
            'thumb' : thumb_url, 
            'icon'  : thumb_url
            })

        
        url = get_url(
            action       = 'play',
            content_url  = content_url,
            sub_urls     = ' '.join(sub_urls),
            content_type = content_type
            )

        xbmcplugin.addDirectoryItem(_HANDLE, url, list_item)

    xbmcplugin.addSortMethod(_HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(_HANDLE)


def play_media(**kwargs):
    """
    Play a video by the provided path.

    :param path: Fully-qualified video URL
    :type path: str
    """
    try:
        path = kwargs['content_url']
        subs = kwargs.get('sub_urls', None)
        type = int(kwargs.get('content_type', -1))

    except ValueError:
        LOGGER.error("Value error reading play query {}".format(kwargs))
        raise Exception("Value error reading play query {}".format(kwargs))

    LOGGER.info(type)

    if type == CONTENT_TYPE_IMAGE:
        
        LOGGER.info("Showing image: {}".format(path))
        xbmc.executebuiltin('ShowPicture(%s)' % path)
        return 

    if type != CONTENT_TYPE_VIDEO:

        LOGGER.error("Content type {} is not image or video, nothing will be played".format(type))
        return 

    if subs :

        subs = subs.split(" ")

    LOGGER.info("Playing video: {}".format(path))

    play_item = xbmcgui.ListItem(path=path)

    if subs:

        play_item.setSubtitles(subs)

    # Pass the item to the Kodi player.
    xbmcplugin.setResolvedUrl(_HANDLE, True, listitem=play_item)


def router(paramstring):
    """
    Router function that calls other functions
    depending on the provided paramstring

    :param paramstring: URL encoded plugin paramstring
    :type paramstring: str
    """

    params = dict(parse_qsl(paramstring))

    if not params:
        list_categories()
        return 

    if params['action'] == 'listing':

        list_videos(params)
        return 

    if params['action'] == 'play':

        play_media(**params)
        return 

    LOGGER.error("No valid parms given {}".format(params))

    # If the provided paramstring does not contain a supported action
    # we raise an exception. This helps to catch coding errors,
    # e.g. typos in action names.
    raise ValueError('Invalid paramstring: {}!'.format(paramstring))
