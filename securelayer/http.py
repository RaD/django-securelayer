# -*- coding: utf-8 -*-
# (c) 2009-2011 Ruslan Popov <ruslan.popov@gmail.com>

from django.utils.translation import ugettext_lazy as _
import httplib, urllib, json

class Http:

    host = None
    port = 80
    session_id = None
    headers = {
        'Content-type': 'application/x-www-form-urlencoded',
        'Accept': 'text/plain'
        }

    def __init__(self, host, port=80):
        self.host = host
        self.port = port
        self.connect()

    def __del__(self):
        self.disconnect()

    def connect(self, host=None, port=None):
        if host:
            self.host = host
        if port:
            self.port = port
        self.conn = httplib.HTTPConnection('%s:%s' % (self.host, self.port))

    def disconnect(self):
        self.conn.close()

    def reconnect(self):
        self.disconnect()
        self.connect()

    def is_session_open(self):
        return self.session_id is not None

    def request(self, url, params): # public
        if self.session_id and self.session_id not in self.headers:
            self.headers.update( { 'Cookie': 'sessionid=%s' % self.session_id } )

        params = urllib.urlencode(params)
        while True:
            try:
                self.conn.request('POST', url, params, self.headers)
                break
            except httplib.CannotSendRequest:
                self.reconnect()
            except Exception, e:
                self.error_msg = '[%s] %s' % (e.errno, e.strerror.decode('utf-8'))
                self.response = None
                return False

        self.response = self.conn.getresponse()

        cookie_string = self.response.getheader('set-cookie')
        if cookie_string:
            cookie = {}
            for item in cookie_string.split('; '):
                key, value = item.split('=')
                cookie.update( { key: value } )
            self.session_id = cookie.get('sessionid', None)
        return True

    def parse(self): # public
        if not self.response: # request failed
            return { 'status': 599, 'desc': _('No response.') }
        if self.response.status == 200: # http status
            data = self.response.read()
            if hasattr(json, 'read'):
                response = json.read(data) # 2.5
            else:
                response = json.loads(data) # 2.6
            return response
        elif self.response.status == 302: # authentication
            return { 'status': 302, 'desc': _('Authenticate Yourself.') }
        elif self.response.status == 500: # error
            open('./dump.html', 'w').write(self.response.read())
            return { 'status': 500, 'desc': _('Internal Error.') }
        else:
            return { 'status': self.response.status, 'desc': self.response.reason }
