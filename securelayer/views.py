# -*- coding: utf-8 -*-
# (c) 2010-2011 Ruslan Popov <ruslan.popov@gmail.com>

from django.conf import settings
from django import forms
from django.http import Http404
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _

from securelayer.http import Http

import gnupg

class NextStep(forms.Form):
    """ This form is used to redirect a client to SecureLayer site."""
    data = forms.CharField(widget=forms.HiddenInput)

def sign_this(data):
    """ Converts the data into GPG signed JSON. """
    jsonified = simplejson.dumps(data)
    gpg = gnupg.GPG(gnupghome=settings.GPG_HOMEDIR)
    signed = gpg.sign(jsonified, passphrase=settings.GPG_PASSPHRASE)
    return signed.data.decode('utf-8')

def secured_request(url, params={}, session_key=None):
    """ Relizes data transfer through SSL. Sends params to URL. Uses Cookies."""
    http = Http(settings.SECURELAYER_HOST, settings.SECURELAYER_PORT)
    if session_key:
        http.session_id = session_key
    if http.request(url, {'data': sign_this(params)}):
        response = http.parse()
        if response.get('status', None) == 200:
            return (True, response, http.session_id)
    else:
        response = { 'status': 598, 'desc': _('Request error.') }
    return (False, response, None)

def use_secured_form(request, form, context, caption, desc):
    """ Processes client's data through SecureLayer site."""
    if request.method == 'GET':
        session_key = request.GET.get('ss', None)
        if session_key:
            ready, response, cookie = secured_request('/api/data/',
                                                      {'service': 'data'},
                                                      session_key)
            form.import_json(response.get('data', None))
            return form
        else:
            context.update( {
                'action': 'http://%s:%s/show/' % (
                    settings.SECURELAYER_HOST,
                    settings.SECURELAYER_PORT),
                'button_list': [{'title': _(u'Redirect'),
                                 'name': 'redirect', 'type': 'submit'},],
                'body': _(u'You will be redirected on SecureLayer '
                          'for secure data entering.')} )
            params = {
                'return_to': request.build_absolute_uri(),
                'form': form.as_json(caption=caption, desc=desc)
                }
            return NextStep(initial={'data': sign_this(params)})
    else:
        # пост придти в эту форму не может
        raise Http404

def form(local_form, caption=None, desc=None):
    """ SecureLayer's Decorator. """
    def renderer(view):
        def wrapper(request, *args, **kwargs):
            context = {
                'action': '.',
                'body': _(u'The data would be transferred by open channel.'),
                }
            check = ready, status, session_key = \
                    secured_request('/api/check/', {'service': 'check'})
            if not ready:
                form = local_form(request.POST or None, *args, **kwargs)
            else:
                form = use_secured_form(request, local_form(), context, caption, desc)
            form.request = request
            return view(request, form, context, check, *args, **kwargs)
        return wrapper
    return renderer
