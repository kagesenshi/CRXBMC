import urllib
import urllib2
import urllib2_ssl
import httplib
import sys
import json
import socket
import xbmc
import os

def makeSessionRequest(args, method, options):
    from crunchy_json import log
    from crunchy_json import pretty

    if method != 'start_session':
        raise KeyError(method)

    if args.user_data['premium_type'] in 'anime|drama|manga|UNKNOWN':
        log("CR: makeSessionRequest: get JSON")

        path = args._addon.getAddonInfo('path')
        path = os.path.join(path, 'cacert.pem')
        # TODO: Update cert master file on EVERY UPDATE!
        
        values = {'version': args.user_data['API_VERSION'],
                  'locale':  args.user_data['API_LOCALE']}

        values.update(options)
        options = urllib.urlencode(values)
        
        if sys.version_info >= (2, 7, 9):
            handler = urllib2.HTTPSHandler()
        else:
            handler = urllib2_ssl.HTTPSHandler(ca_certs=path)

        opener = urllib2.build_opener(handler)
        opener.addheaders = args.user_data['API_HEADERS']
        urllib2.install_opener(opener)

        opts = {
            "version": "1.1",
            "user_id": args.user_data['username']
        }
        auth_token = args.user_data.get('auth_token', None)
        if auth_token:
            opts["auth"] = auth_token

        qs = urllib.urlencode(opts)

        url = 'https://api2.cr-unblocker.com/start_session?%s' % qs

        log("CR: makeSessionRequest: url = %s" % url)
        log("CR: makeSessionRequest: options = %s" % options)


        try:
            en = ev = None

            req = opener.open(url)
            json_data = req.read()

            if req.headers.get('content-encoding', None) == 'gzip':
                json_data = gzip.GzipFile(fileobj=StringIO.StringIO(json_data))
                json_data = json_data.read().decode('utf-8', 'ignore')

            req.close()

            request = json.loads(json_data)

        except (httplib.BadStatusLine,
                socket.error,
                urllib2.HTTPError,
                urllib2.URLError) as e:
            log("CR: makeSessionRequest: Connection failed: %r" % e,
                xbmc.LOGERROR)

            en, ev = sys.exc_info()[:2]
        finally:
            # Return dummy response if connection failed
            if en is not None:
                request = {'code':    'error',
                           'message': "Connection failed: %r, %r" % (en, ev),
                           'error':   True}

        #log("CR: makeSessionRequest: request = %s" % str(request), xbmc.LOGDEBUG)
        log("CR: makeSessionRequest: reply =", xbmc.LOGDEBUG)
        pretty(request)

    else:
        pt = args.user_data['premium_type']
        s  = "Premium type check failed, premium_type:"

        request = {'code':    'error',
                   'message': "%s %s" % (s, pt),
                   'error':   True}

        log("CR: makeSessionRequest: %s %s" % (s, pt), xbmc.LOGERROR)

    return request


