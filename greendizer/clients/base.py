# -*- coding: utf-8 -*-
import re
from math import modf
from datetime import datetime, timedelta


## {{{ http://code.activestate.com/recipes/65215/ (r5)
EMAIL_PATTERN = re.compile('^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]' \
                           '+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$')


def to_unicode(text):
    '''
    Converts an input text to a unicode object.
    @param text:object Input text
    @returns:unicode
    '''
    return text.decode("UTF-8") if type(text) == str else unicode(text)


def to_byte_string(text):
    '''
    Converts an input text to a unicode object.
    @param text:object Input text
    @returns:unicode
    '''
    return text.encode("UTF-8") if type(text) == unicode else str(text)


def is_valid_email(s):
    '''
    Returns a value indicating whether the submitted string is a valid
    email address.
    @param s:str Email
    @return: bool
    '''
    return (s and len(s) > 7 and EMAIL_PATTERN.match(s))


def timestamp_to_datetime(s):
    '''
    Parses a timestamp to a datetime instance.
    @param: s:str Timestamp string.
    @return: datetime
    '''
    f, i = modf(long(s) / float(1000))
    return datetime.fromtimestamp(i) + timedelta(milliseconds=f * 1000)


def datetime_to_timestamp(d):
    '''
    Converts a datetime instance into a timestamp string.
    @param d:datetime Date instance
    @return:long
    '''
    return long(d.strftime("%s") + "%03d" % (d.time().microsecond / 1000))


def extract_id_from_uri(s):
    '''
    Returns the ID section of an URI.
    @param s:str URI
    @return: str
    '''
    return [ item for item in s.split("/") if item ][-1]


def size_in_bytes(data):
    '''
    Gets the size in bytes of a str.
    @return: long
    '''
    try:
        from os import sys
        return sys.getsizeof(data)
    except AttributeError:
        import base64 #2.5 and older...
        return len(base64.encodestring(data)) #1 ASCII char = 1 byte
