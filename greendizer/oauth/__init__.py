# -*- coding: utf-8 -*-
import urllib2
from urllib import urlencode
try:
    import simplejson as json
except ImportError:
    import json


__all__ = ('AccessTokenError', 'OAuthClient')


DEBUG = False
OAUTH_URI = 'https://services.greendizer.com/oauth/'


def switch_to_local(endpoint='http://services.local.greendizer.com/oauth/'):
    global OAUTH_URI
    OAUTH_URI = endpoint


class AttributeDict(dict): 
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class AccessTokenError(Exception):
    pass


class OAuthClient(object):
    def __init__(self, client_type, client_id, client_secret, scope,
                 redirect_uri=None):
        
        self.client_type = client_type
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        
        self.__authorize_uri = OAUTH_URI + client_type + '/authorize/'
        self.__access_uri = OAUTH_URI + client_type + '/access/'
        
        credentials = (':'.join((client_id, client_secret)).encode('base64'))
        self.__headers = {'Authorization': 'BASIC ' + credentials.strip('\n'), 
                          'Accept':'application/json',
                          'Content-Type': 'application/x-www-form-urlencoded'}
        
    def __do_request(self, grant_type, code_type, code, scope=None,
                     redirect_uri=None):
        payload = {'grant_type': grant_type, code_type: code,
                   'scope': scope or self.scope,
                   'redirect_uri': redirect_uri or self.redirect_uri}
        
        request = urllib2.Request(url=self.__access_uri,
                                  headers=self.__headers,
                                  data=urlencode(payload))
        try:
            response = urllib2.urlopen(request)
            return AttributeDict(json.loads(response.read()))
        except(urllib2.URLError), error:
            if error.code < 500:
                raise AccessTokenError(json.loads(error.read())['error'])
            raise RuntimeError(error.read())
        
    def get_authorize_url(self, redirect_uri=None, scope=None):
        return (self.__authorize_uri + '?' +
                urlencode({'client_id': self.client_id,
                           'response_type': 'code',
                           'redirect_uri': redirect_uri or self.redirect_uri,
                           'scope': scope or self.scope}))
        
    def refresh_token(self, token, redirect_uri=None, scope=None):
        return self.__do_request('refresh_token', 'refresh_token', token,
                                 scope=scope, redirect_uri=redirect_uri)
    
    def obtain_token(self, code, redirect_uri=None, scope=None):
        return self.__do_request('authorization_code', 'code', code, 
                                 scope=scope, redirect_uri=redirect_uri)