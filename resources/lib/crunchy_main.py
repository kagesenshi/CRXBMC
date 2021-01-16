# -*- coding: utf-8 -*-
"""
    Crunchyroll
    Copyright (C) 2012 - 2014 Matthew Beacher
    This program is free software; you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by the
    Free Software Foundation; either version 2 of the License.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License along with
this program; if not, write to the Free Software Foundation,
Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
"""
import os
import re
import sys
import urllib
import urllib.parse
try:
    import cPickle as pickle
except:
    import pickle

import xbmc
import xbmcgui
import xbmcplugin

from . import crunchy_json as crj

from .crunchy_json import log


class Args(object):
    """Arguments class.

    Hold all arguments passed to the script and also persistent user data and
    reference to the addon. It is intended to hold all data necessary for the
    script.
    """
    def __init__(self, *args, **kwargs):
        """Initialize arguments object.

        Hold also references to the addon which can't be kept at module level.
        """
        self._addon = sys.modules['__main__'].__settings__
        self._lang  = sys.modules['__main__'].__language__
        self._id    = self._addon.getAddonInfo('id')

        for key, value in kwargs.items():
            if value == 'None':
                kwargs[key] = None
            else:
                kwargs[key] = urllib.parse.unquote_plus(kwargs[key])
        self.__dict__.update(kwargs)


def encode(f):
    """Decorator for encoding strings.

    """
    def lang_encoded(*args):
        return f(*args).encode('utf8')
    return lang_encoded


def endofdirectory(sortMethod='none'):
    """Mark end of directory listing.
    """
    # Sort methods are required in library mode
    # Set for Queue only, not for anything else
    # Also check if sorting should be allowed
    if (sortMethod == 'user') and (boolSetting("sort_queue")):
       #Sort on "ordering" - ie, the order the items appeared
       xbmcplugin.addSortMethod(int(sys.argv[1]),
                                xbmcplugin.SORT_METHOD_VIDEO_SORT_TITLE)
       #Title sort - as expected
       xbmcplugin.addSortMethod(int(sys.argv[1]),
                             xbmcplugin.SORT_METHOD_TITLE)
       #Sort on percent played, ie - we are lying
       xbmcplugin.addSortMethod(int(sys.argv[1]),
                                xbmcplugin.SORT_METHOD_LASTPLAYED)
    else:
        xbmcplugin.addSortMethod(int(sys.argv[1]),
                                 xbmcplugin.SORT_METHOD_NONE)

    # Let xbmc know the script is done adding items to the list
    dontAddToHierarchy = False
    xbmcplugin.endOfDirectory(handle        = int(sys.argv[1]),
                              updateListing = dontAddToHierarchy)


def set_info_defaults (args,info):
    # Defaults in dict. Use 'None' instead of None so it is compatible for
    # quote_plus in parseArgs.
    info.setdefault('url',          'None')
    info.setdefault('thumb',        "DefaultFolder.png")
    info.setdefault('fanart_image',
                    xbmc.translatePath(args._addon.getAddonInfo('fanart')))
    info.setdefault('count',        '0')
    info.setdefault('filterx',      'None')
    info.setdefault('id',           'None')
    info.setdefault('series_id',    'None')
    info.setdefault('offset',       '0')
    info.setdefault('season',       '1')
    info.setdefault('series_id',    '0')
    info.setdefault('page_url',     'None')
    info.setdefault('complete',     'True')
    info.setdefault('media_type',   'None')
    info.setdefault('title',        'None')
    info.setdefault('year',         '0')
    info.setdefault('playhead',     '0')
    info.setdefault('duration',     '0')
    info.setdefault('episode',      '0')
    info.setdefault('plot',         'None')
    info.setdefault('percent',      0)
    info.setdefault('ordering',     '0')
    #And set all None to 'None'
    for key, value in info.items():
        if isinstance(value, bytes):
            info[key] = value.decode('utf-8')
        if key in ['percent']:
            info[key] = int(value)
        if value == None:
            info[key] = 'None'
    return info


def build_url (info):
    # Create params for xbmcplugin module
    s = sys.argv[0]    +\
        '?url='        + urllib.parse.quote_plus(info['url'])          +\
        '&mode='       + urllib.parse.quote_plus(info['mode'])         +\
        '&name='       + urllib.parse.quote_plus(info['title'])        +\
        '&id='         + urllib.parse.quote_plus(info['id'])           +\
        '&count='      + urllib.parse.quote_plus(info['count'])        +\
        '&series_id='  + urllib.parse.quote_plus(info['series_id'])    +\
        '&filterx='    + urllib.parse.quote_plus(info['filterx'])      +\
        '&offset='     + urllib.parse.quote_plus(info['offset'])       +\
        '&icon='       + urllib.parse.quote_plus(info['thumb'])        +\
        '&complete='   + urllib.parse.quote_plus(info['complete'])     +\
        '&fanart='     + urllib.parse.quote_plus(info['fanart_image']) +\
        '&season='     + urllib.parse.quote_plus(info['season'])       +\
        '&media_type=' + urllib.parse.quote_plus(info['media_type'])   +\
        '&year='       + urllib.parse.quote_plus(info['year'])         +\
        '&playhead='   + urllib.parse.quote_plus(info['playhead'])     +\
        '&duration='   + urllib.parse.quote_plus(info['duration'])     +\
        '&episode='    + urllib.parse.quote_plus(info['episode'])      +\
        '&plot='       + urllib.parse.quote_plus(info['plot']          +'%20')
    return s


def boolSetting(id):
    """Will return true if the setting (id) is "true"

    """
#    return args._addon.getSetting(id) == "true"
    return xbmcplugin.getSetting(int(sys.argv[1]), id) == "true"


def intSetting(id):
    """Will return the setting (id) as an integer

    """
#    return int(args._addon.getSetting(id))
    return int(xbmcplugin.getSetting(int(sys.argv[1]), id))


def add_item(args,
             info,
             isFolder=True,
             total_items=0,
             queued=False,
             rex=re.compile(r'(?<=mode=)[^&]*')):
    """Add item to directory listing.

    """
    info = set_info_defaults(args,info)
    u = build_url(info)

    #To skip having to check if args.mode is None all the time
    mode = "None" if (args.mode is None) else args.mode

    # Create list item
    li = xbmcgui.ListItem(label          = info['title'])
    li.setArt({'thumb': info['thumb']})

    percentPlayed = " "
    if ((int(info['percent']) > 0) and (boolSetting("show_percent"))):
        percentPlayed = " [COLOR FFbc3bfd] " + args._lang(30401) + " [/COLOR] [COLOR FF6fe335]" + str(info['percent']) + "%[/COLOR]"

    li.setInfo(type       = "Video",
               infoLabels = {"Title":   info['title'] + percentPlayed,
                             "Plot":    info['plot'],
                             "Year":    info['year'],
                             "episode": info['episode'],
                             "lastplayed": '2000-01-01 '+str(int(info['percent']) / 60).zfill(2)+':'+str(int(info['percent']) % 60).zfill(2)+':00',
                             "sorttitle":  info['ordering'],
                             "playcount": int(info['percent'] >= 90 and not isFolder)
                            }
              )

    li.setProperty("Fanart_Image", info['fanart_image'])

    # Add context menu
    s1  = re.sub(rex, 'add_to_queue',      u)
    s2  = re.sub(rex, 'remove_from_queue', u)
    s3  = re.sub(rex, 'list_coll', u)
    sP  = re.sub(rex, 'set_progress', u)
    sPlay  = re.sub(rex, 'videoplay', u)

    #Context menu list, initialize as empty list
    cm = []

    if (mode not in 'None|channels|list_categories') and (boolSetting("CM_queueV")):
        cm.append((args._lang(30504), 'XBMC.Action(Queue)')) #Queue Video

    if not isFolder:
        li.addStreamInfo('video', {"duration": info['duration']})
        # Let XBMC know this can be played, unlike a folder
        li.setProperty('IsPlayable', 'true')

        if boolSetting("CM_unwatched"):
            cm.append((args._lang(30514), 'XBMC.RunPlugin(%s)' % (sP + "&time=0"))) #Set to Unwatched
        if boolSetting("CM_watched"):
            cm.append((args._lang(30513), 'XBMC.RunPlugin(%s)' % (sP + "&time=" + str(info['duration'])))) #Set to Watched
        if (mode in 'history|queue') and (boolSetting("CM_gotoS")):
            cm.append((args._lang(30503), 'XBMC.ActivateWindow(Videos,%s)' % s3)) #Goto Series

        if boolSetting("CM_playFrom"):
            of = int(info['playhead']) #we are going to reference this a lot
            if of > 0: #No point in showing if it is the same as play
                if (of > int(int(info['duration']) * 0.9)) or (intSetting("autoresume")==1): #If watched (>90%) or autoresume==yes, ask to begin from the start
                    of = 0
                hrs = '' if of<3600 else str(of // 3600).zfill(2)+":"
                cm.append(("%s %s%s:%s" % (args._lang(30521),hrs,str((of % 3600) // 60).zfill(2), str(int(of % 60)).zfill(2)),'XBMC.PlayMedia(%s)' % (sPlay + "&resumetime="+str(of))))

        if intSetting("CM_playAt") > 0:
            cm.append((args._lang(30520) + " " + args._lang([30004,30005,30006,30008,30012][intSetting("CM_playAt")-1]), 'XBMC.PlayMedia(%s)' % (u + "&quality=" + str(intSetting("CM_playAt")-1)))) #Play at different quality

    if (not isFolder) or ((mode in 'list_coll|list_series|queue') and (isFolder)):
        if queued:
            if boolSetting("CM_dequeueS"):
                cm.append((args._lang(30501), 'XBMC.RunPlugin(%s)' % s2)) #Dequeue Series
        elif boolSetting("CM_enqueueS"):
                cm.append((args._lang(30502), 'XBMC.RunPlugin(%s)' % s1)) #Enqueue series

    if boolSetting("CM_settings"):
        cm.append((args._lang(30505), 'XBMC.Addon.OpenSettings(%s)' % args._id)) #Add-on settings

    if boolSetting("CM_toggledebug"):
        cm.append((args._lang(30512), 'XBMC.ToggleDebug')) #Toggle Debug

    if (mode in 'bad_login'):
        u = "%s?mode=%s" % (sys.argv[0],mode)

    li.addContextMenuItems(cm, replaceItems=(not boolSetting("CM_kodi"))) #Whether to use kodi menu items or not 

    # Add item to list
    xbmcplugin.addDirectoryItem(handle     = int(sys.argv[1]),
                                url        = u,
                                listitem   = li,
                                isFolder   = isFolder,
                                totalItems = total_items)


def bad_login(args):
    """Prompt addon settings

    """
    args._addon.openSettings(args._id) #Add-on settings


def show_main(args):
    """Show main menu.

    """
    anime   = args._lang(30100)
    drama   = args._lang(30104)
    queue   = args._lang(30105)
    history = args._lang(30111)

    add_item(args,
             {'title':      queue,
              'mode':       'queue'})
    add_item(args,
             {'title':      history,
              'mode':       'history'})
    add_item(args,
             {'title':      anime,
              'mode':       'channels',
              'media_type': 'anime'})
    add_item(args,
             {'title':      drama,
              'mode':       'channels',
              'media_type': 'drama'})
    endofdirectory()


def channels(args):
    """Show Crunchyroll channels.

    """
    popular         = args._lang(30103)
    simulcasts      = args._lang(30106)
    recently_added  = args._lang(30102)
    alpha           = args._lang(30112)
    browse_by_genre = args._lang(30107)
    seasons         = args._lang(30110)

    add_item(args,
             {'title':      popular,
              'mode':       'list_series',
              'media_type': args.media_type,
              'filterx':    'popular',
              'offset':     '0'})
    add_item(args,
             {'title':      simulcasts,
              'mode':       'list_series',
              'media_type': args.media_type,
              'filterx':    'simulcast',
              'offset':     '0'})
    add_item(args,
             {'title':      recently_added,
              'mode':       'list_series',
              'media_type': args.media_type,
              'filterx':    'updated',
              'offset':     '0'})
    add_item(args,
             {'title':      alpha,
              'mode':       'list_series',
              'media_type': args.media_type,
              'filterx':    'alpha',
              'offset':     '0'})
    add_item(args,
             {'title':      browse_by_genre,
              'mode':       'list_categories',
              'media_type': args.media_type,
              'filterx':    'genre',
              'offset':     '0'})
    add_item(args,
             {'title':      seasons,
              'mode':       'list_categories',
              'media_type': args.media_type,
              'filterx':    'season',
              'offset':     '0'})
    add_item(args,
             {'title':      'Random',
              'mode':       'get_random',
              'media_type': args.media_type,
              'filterx':    'random',
              'offset':     '0'})
    endofdirectory()


def fail(args):
    """Unrecognized mode found.

    """
    badstuff = args._lang(30207)

    add_item(args,
             {'title': badstuff,
              'mode':  'fail'})

    log("CR: Main: check_mode fall through", xbmc.LOGWARNING)

    endofdirectory()


def parse_args():
    """Decode arguments.

    """
    if (sys.argv[2]):
        log('CR %s' % sys.argv)
        params = [p.split('=') for p in sys.argv[2][1:].split('&')]
        for idx, item in enumerate(params):
            if len(item) == 1:
                item.append('None')
        return Args(**dict(params))

    else:
        # Args will turn the 'None' into None.
        # Don't simply define it as None because unquote_plus in updateArgs
        # will throw an exception.
        # This is a pretty ugly solution.
        return Args(mode = 'None',
                    url  = 'None',
                    name = 'None')


def check_mode(args):
    """Run mode-specific functions.

    """
    #For a very minimal request to play video
    try:
        mode = args.mode
    except:
        #Shorthand for play on id
        if hasattr(args,'id'):
           mode = 'videoplay'
        #Shorthand for play on url
        elif hasattr(args,'url'):
           mode = 'videoplay'
           args.id = re.sub(r'.*-', '', args.url)
           args.id = re.sub(r'\?.*', '', args.id)
        else:
           mode = None

    log("CR: Main: argv[0] = %s" % sys.argv[0],     xbmc.LOGDEBUG)
    log("CR: Main: argv[1] = %s" % sys.argv[1],     xbmc.LOGDEBUG)
    log("CR: Main: argv[2] = %s" % sys.argv[2],     xbmc.LOGDEBUG)
    log("CR: Main: args = %s" % str(args.__dict__), xbmc.LOGDEBUG)
    log("CR: Main: mode = %s" % mode,               xbmc.LOGDEBUG)

    if mode is None:
        show_main(args)
    elif mode == 'channels':
        channels(args)
    elif mode == 'list_series':
        crj.list_series(args)
    elif mode == 'list_categories':
        crj.list_categories(args)
    elif mode == 'list_coll':
        crj.list_collections(args)
    elif mode == 'list_media':
        crj.list_media(args)
    elif mode == 'history':
        crj.history(args)
    elif mode == 'queue':
        crj.queue(args)
    elif mode == 'add_to_queue':
        crj.add_to_queue(args)
    elif mode == 'remove_from_queue':
        crj.remove_from_queue(args)
    elif mode == 'videoplay':
        crj.start_playback(args)
    elif mode == 'get_random':
        crj.get_random(args)
    elif mode == 'set_progress':
        crj.set_progress(args,args.time)
    elif mode == 'bad_login':
        bad_login(args)
    else:
        fail(args)


def main():
    """Main function for the addon.

    """
    args = parse_args()

    if (hasattr(args,'mode')) and (args.mode == 'bad_login'):
        bad_login(args)
        args = parse_args()
        args.mode = None

    logged_in = True
    if crj.load_pickle(args) is False:
        base_path = xbmc.translatePath(args._addon.getAddonInfo('profile')).decode('utf-8')
        pickle_path = os.path.join(base_path, "cruchyPickle")
        if os.path.exists(pickle_path): #silently remove crunchyPickle and try again
            os.remove(pickle_path)
        if crj.load_pickle(args) is False: #Yes, we retry
            logged_in = False
            add_item(args,
                     {'title': args._lang(30206),
                      'mode':  'bad_login'})
            endofdirectory()

    if logged_in: 
        xbmcplugin.setContent(int(sys.argv[1]), 'tvshows')

        check_mode(args)

    try:
        base_path = xbmc.translatePath(args._addon.getAddonInfo('profile')).decode('utf-8')
        pickle_path = os.path.join(base_path, "cruchyPickle")
        user_data = pickle.dump(args.user_data, open(pickle_path, 'wb'))

    except:
        log("CR: Unable to dump pickle")
