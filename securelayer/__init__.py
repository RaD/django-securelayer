# -*- coding: utf-8 -*-
# (c) 2010-2011 Ruslan Popov <ruslan.popov@gmail.com>

from django import forms
from django.utils import simplejson
from django.utils.translation import ugettext_lazy as _

from datetime import datetime

class SecuredForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(SecuredForm, self).__init__(*args, **kwargs)

    def get_attr_list(self, field, attrs):
        context = {}
        for i in attrs:
            value = getattr(field, i, None)
            if value is not None:
                context.update( {i: value} )
        return context

    def field_meta(self, name, field):
        fname = name
        ftype = field.__class__.__name__
        if ftype not in ('BooleanField', 'CharField', 'ChoiceField', 'DateField',
                         'DateTimeField', 'EmailField', 'FloatField',
                         'IntegerField', 'IPAddressField', 'MultipleChoiceField',
                         'SlugField', 'TimeField', 'URLField',):
            msg = _(u'Field %s is not supported!')
            raise RuntimeError(msg % ftype)

        attrs = {
            'label': field.label,
            'help_text': field.help_text,
            'required': field.required,
            }
        if ftype in ('CharField',):
            if isinstance(field.widget, forms.widgets.PasswordInput):
                ftype = 'PasswordField'
        if ftype in ('CharField', 'EmailField', 'URLField',):
            attrs.update( self.get_attr_list(field, ('min_length', 'max_length',)) )
        if ftype in ('ChoiceField', 'MultipleChoiceField',):
            attrs.update( self.get_attr_list(field, ('choices',)) )
        if ftype == 'URLField':
            for v in field.validators:
                verify_exists = getattr(v, 'verify_exists', False)
                if verify_exists:
                    attrs.update( {'verify_exists': verify_exists} )

        return (fname, ftype, attrs)

    def as_json(self, caption=None, desc=None):
        field_list = []
        for name, field in self.fields.items():
            fname, ftype, attrs = self.field_meta(name, field)
            record = {'fname': fname, 'ftype': ftype, 'attrs': attrs}
            field_list.append( record )
        return simplejson.dumps( { 'form': field_list, 'caption': caption, 'desc': desc } )

    def import_json(self, jsonified):
        self.data = simplejson.loads(jsonified)
        self.source = 'JSON'
        self.cleaned_data = {}
        for name, field in self.fields.items():
            fname, ftype, attrs = self.field_meta(name, field)
            value = self.data.get(fname, None)
            if value:
                if ftype == 'IntegerField':
                    value = int(value)
                if ftype == 'DateField':
                    value = datetime.strptime(value, '%Y-%m-%d').date()
                if ftype == 'TimeField':
                    value = datetime.strptime(value, '%H:%M:%S').time()
                if ftype == 'DateTimeField':
                    value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            self.cleaned_data[fname] = value
        self.is_bound = True
