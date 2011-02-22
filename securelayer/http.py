# -*- coding: utf-8 -*-
# (c) 2009-2011 Ruslan Popov <ruslan.popov@gmail.com>

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils import simplejson
import httplib, urllib, sys

class Http:

    host = None
    port = 80
    protocol = httplib.HTTPConnection
    session_id = None
    headers = {
        'Content-type': 'application/x-www-form-urlencoded',
        'Accept': 'text/plain'
        }

    def __init__(self, host, port=80, protocol='http'):
        self.host = host
        self.port = port
        self.connect()
        if protocol == 'https':
            self.protocol =  httplib.HTTPSConnection
        if settings.DEBUG:
            print 'SecureLayer URL: %s://%s:%s' % (protocol, host, port)

    def __del__(self):
        self.disconnect()

    def connect(self, host=None, port=None):
        if host:
            self.host = host
        if port:
            self.port = port
        self.conn = self.protocol('%s:%s' % (self.host, self.port))

    def disconnect(self):
        self.conn.close()

    def reconnect(self):
        self.disconnect()
        self.connect()

    def is_session_open(self):
        return self.session_id is not None

    def request(self, url, method='POST', params={}): # public
        if self.session_id and self.session_id not in self.headers:
            self.headers.update( { 'Cookie': 'securelayer_sessionid=%s' % self.session_id } )

        params = urllib.urlencode(params)
        while True:
            try:
                self.conn.request(method, url, params, self.headers)
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
                try:
                    key, value = item.split('=', 1)
                except ValueError:
                    pass
                cookie.update( { key: value } )
            self.session_id = cookie.get('sessionid', None)
        return True

    def parse(self, is_json=True): # public
        if not self.response: # request failed
            return { 'status': 599, 'desc': _('No response.') }
        if self.response.status == 200: # http status
            response = self.response.read()
            if is_json:
                response = simplejson.loads(response)
            return response
        elif self.response.status == 302: # authentication
            return { 'status': 302, 'desc': _('Authenticate Yourself.') }
        elif self.response.status == 500: # error
            open('./dump.html', 'w').write(self.response.read())
            return { 'status': 500, 'desc': _('Internal Error.') }
        else:
            return { 'status': self.response.status, 'desc': self.response.reason }

def check(boolean):
    if boolean:
        print 'passed'
    else:
        print 'failed'

if __name__=="__main__":
    print 'GET to http://ya.ru/',
    h = Http('ya.ru', 80, 'http')
    h.connect()
    h.request('/', 'GET')
    resp = h.parse(False)
    check( '<!DOCTYPE HTML PUBLIC' == resp[:21] )

    print 'POST to http://ya.ru/',
    h = Http('ya.ru', 80, 'http')
    h.connect()
    h.request('/', 'POST')
    resp = h.parse(False)
    check( '<!DOCTYPE HTML PUBLIC' == resp[:21] )

    print 'GET to https://yandex.ru/',
    h = Http('yandex.ru', 443, 'https')
    h.connect()
    h.request('/', 'GET')
    resp = h.parse(False)
    check( type(resp) is dict and resp['status'] != 500 )

    print 'POST to https://yandex.ru/',
    h = Http('yandex.ru', 443, 'https')
    h.connect()
    h.request('/', 'POST')
    resp = h.parse(False)
    check( type(resp) is dict and resp['status'] != 500 )

    sys.exit(0)
