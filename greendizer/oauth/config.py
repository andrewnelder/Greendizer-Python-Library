# -*- coding: utf-8 -*-


__all__ = ('DEBUG', 'VERSION')


DEBUG = False
def switch_to_local(endpoint='http://services.local.greendizer.com/oauth/'):
    from greendizer import oauth
    global DEBUG
    DEBUG = True
    oauth.OAUTH_URI = endpoint


VERSION = "1.0"