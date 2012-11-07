# -*- coding: utf-8 -*-
import urllib
import urllib2
import re
import zlib
import urlparse
import logging
from datetime import datetime, date
from gzip import GzipFile
from StringIO import StringIO
from greendizer.clients.config import DEBUG, VERSION
from greendizer.clients.base import (timestamp_to_datetime, to_byte_string,
                                     datetime_to_timestamp,)


try:
    import simplejson as json
except ImportError:
    import json


COMPRESSION_DEFLATE = "deflate"
COMPRESSION_GZIP = "gzip"
API_ROOT = "https://api.greendizer.com/"
USER_AGENT = "Greendizer Python Library/" + VERSION
USE_GZIP = True
HTTP_METHODS_WITH_DATA = ['post', 'put', 'patch']
HTTP_METHODS = ["head", "get", "delete", "options"] + HTTP_METHODS_WITH_DATA
CONTENT_TYPES = ["application/xml",
                 "application/x-www-form-urlencoded"]
HTTP_POST_ONLY = False


def gzip_str(data):
    '''
    Gzips a string to the highest compression level.
    @param data:str
    @return data:str
    '''
    bf = StringIO('')
    f = GzipFile(fileobj=bf, mode='wb', compresslevel=9)
    f.write(data)
    f.close()
    return bf.getvalue()


class ApiError(Exception):
    '''
    Represents an API-related exception
    '''
    def __init__(self, response):
        '''
        Initializes a new instance of the ApiError class.
        @param response:Response
        '''
        self.__response = response

    @property
    def code(self):
        '''
        Gets the error code
        @return: int
        '''
        return self.__response.status_code

    def __str__(self):
        '''
        Returns a string representation of the exception
        @return: str
        '''
        return ((self.__response.data or {})
                .get('desc', "Unexpected error (code: %s)" % self.code))
        

class Request(object):
    '''
    Represents an HTTP request to the Greendizer API
    '''
    class HttpRequest(urllib2.Request):
        '''
        Represents an HTTP request
        This class inherits from the urllib2 Request class to extend the
        HTTP methods available beyond the GET and POST already built-in.
        '''
        def __init__(self, uri, method="GET", **kwargs):
            '''
            Initializes a new instance of the Request class.
            @param uri:str The URI to which will be bound.
            @param method:str The HTTP method to use with the request.
            '''
            self.__method = method
            urllib2.Request.__init__(self, uri, **kwargs)

        def get_method(self):
            '''
            Gets the HTTP method in use.
            @return: str
            '''
            return self.__method.upper()

    def __init__(self, client=None, method="GET", uri=None, data=None,
                 content_type="application/x-www-form-urlencoded"):
        '''
        Initializes a new instance of the Request class.
        @param method:str HTTP method
        @param content_type:str MIME type of the data to carry to the server.
        '''
        if not uri:
            raise ValueError("Invalid URI.")

        if method.lower() not in HTTP_METHODS:
            raise ValueError("Invalid HTTP method.")

        if content_type not in CONTENT_TYPES:
            raise ValueError("Invalid content type value.")

        self.__content_type = content_type
        self.data = data
        self.uri = urlparse.urlsplit(API_ROOT + uri)
        self.method = method.lower()
        self.headers = {}
        if client:
            client.sign_request(self)

    def __getitem__(self, header):
        '''
        Gets the value of a header
        @param header:str
        @return object
        '''
        return self.headers.get(header, None)

    def __setitem__(self, header, value):
        '''
        Sets a header
        @param header:str Header name
        @param value:object Header value
        '''
        self.headers[header] = value

    def __delitem__(self, header):
        '''
        Removes a header
        @param header:str
        '''
        if header in self.headers:
            del self.headers[header]

    def __serialize_headers(self):
        '''
        Serializes the values of the headers to strings
        @return: dict
        '''
        serialized = {}
        for header, value in self.headers.items():
            if type(value) in [datetime, date]:
                serialized[header] = value.isoformat()
            elif getattr(value, '__iter__', False):  # is iterable
                serialized[header] = ';'.join([self.__serialize_headers(i)
                                               for i in value])
            else:
                serialized[header] = str(value)

        return serialized

    def get_response(self, use_gzip=True):
        '''
        Sends the request and returns an HTTP response object.
        @return: Response
        '''
        if self.method in HTTP_METHODS_WITH_DATA and not self.data:
            raise Exception("%s requests must carry data." %
                            self.method.upper())

        headers = self.__serialize_headers()
        headers.update({
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip, deflate",
            "Cache-Control": "no-cache"
        })

        #X-HTTP-Method-Override support
        method = self.method.lower()
        if ((HTTP_POST_ONLY and self.method in HTTP_METHODS_WITH_DATA) or
            self.method == "patch"):
            headers["X-HTTP-Method-Override"] = self.method.upper()
            method = "post"

        #Data encoding and compression for POST, PUT and PATCH requests
        data = self.data
        if method in HTTP_METHODS_WITH_DATA:
            headers["Content-Type"] = self.__content_type + "; charset=utf-8"

            #URL encoding
            if self.__content_type == "application/x-www-form-urlencoded":
                data = to_byte_string(urllib.urlencode(data))

            #GZip compression
            if not DEBUG and USE_GZIP and use_gzip:
                headers["Content-Encoding"] = COMPRESSION_GZIP
                data = gzip_str(to_byte_string(data))

        request = Request.HttpRequest(self.uri.geturl(),
                                      data=data,
                                      method=method, headers=headers)

        try:
            response = urllib2.urlopen(request)
            return Response(self,
                            200,
                            response.read(),
                            response.info())

        except(urllib2.HTTPError), e:
            instance = Response(self, e.code, e.read(), e.info())
            if e.code not in [201, 202, 204, 206, 304, 409, 416]:
                raise ApiError(instance)

            return instance

        except urllib2.URLError:
            raise Exception("Unable to reach the server")
        

class Response(object):
    '''
    Represents an HTTP response to a Greendizer API Request
    '''
    def __init__(self, request, status_code, data, info):
        '''
        Initializes a new instance of the Response class.
        @param request:Request Request at the origin of this response
        @param status_code:int Status code
        @param data:str Data carried in the body of the response
        @param info:object Encapsulates methods to access the headers.
        '''
        self.__request = request
        self.__status_code = status_code

        content_encoding = info.getheader("Content-Encoding")
        if content_encoding == COMPRESSION_DEFLATE:
            data = zlib.decompress(data)
        elif content_encoding == COMPRESSION_GZIP:
            data = GzipFile(fileobj=StringIO(data)).read()

        self.__data = data
        self.__info = info

    def __getitem__(self, header):
        '''
        Gets the value of a header
        @param header:str Header name
        @return: object
        '''
        return self.get_header(header)

    def get_header(self, name):
        '''
        Gets the value of a header
        @param name:str Header name
        @return: object
        '''
        header, value = name.lower(), self.__info.getheader(name, None)
        if not value:
            return
        
        if header in ["date", "last-modified"]:
            if "GMT" in value:
                #RFC1122
                return datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT")
            
            #ISO8601
            '''
            WARNING:
            The HTTP protocol requires dates to be UTC.
            The parsing of ISO8601 is made assuming there's no
            time zone info in the string.
            '''
            return datetime(*map(int, re.split('[^\d]', value)[:-1]))

        if header == "etag":
            return Etag.parse(value)

        if header == "content-range":
            return ContentRange.parse(value)

        return value

    @property
    def status_code(self):
        '''
        Gets the status code of the response
        @return: int
        '''
        return self.__status_code

    @property
    def request(self):
        '''
        Gets the request at the origin of this response
        @return: Request
        '''
        return self.__request

    @property
    def data(self):
        '''
        Gets the data found in the body of the response
        @return: dict
        '''
        try:
            return json.loads(self.__data)
        except:
            raise ValueError('Unable to parse the response received:\n' +
                             (self.__data or ''))


class Etag(object):
    '''
    Represents a Greendizer ETag
    '''
    def __init__(self, last_modified, identifier):
        '''
        Initializes a new instance of the Etag class.
        @param last_modified:datetime Last modification date
        @pram identifier:str ID of the resource or collection
        '''
        self.__last_modified = last_modified
        self.__id = identifier

    @property
    def last_modified(self):
        '''
        Gets the date on which the resource was last modified.
        @return: datetime
        '''
        return self.__last_modified

    @property
    def timestamp(self):
        '''
        Gets the timestamp of the last modification date.
        @return: long
        '''
        return datetime_to_timestamp(self.__last_modified)

    @property
    def id(self):
        '''
        Gets the ID of the resource.
        @return: str
        '''
        return self.__id

    def __str__(self):
        '''
        Returns a string representation of the Etag
        @return: str
        '''
        return "%s-%s" % (self.timestamp, self.__id)

    @classmethod
    def parse(cls, raw):
        '''
        Parses a string and returns a new instance of the Etag class.
        @param raw:str String to parse
        @return: Etag
        '''
        if not raw or len(raw) == 0:
            raise ValueError('Invalid ETag value \'%s\'.' % raw)

        timestamp, identifier = raw.split('-', 1)
        return cls(timestamp_to_datetime(timestamp), identifier)


class Range(object):
    '''
    Represents an HTTP Range
    '''
    def __init__(self, unit="resources", offset=0, limit=200):
        '''
        Initializes a new instance of the Range class.
        @param unit:str Range unit
        @param offset:int Range offset
        @param limit:int Number of elements to include.
        '''
        self.unit = unit
        self.offset = int(offset)
        self.limit = int(limit)

    def __str__(self):
        '''
        Returns a string representation of the object
        @return: str
        '''
        return "%s=%d-%d" % (self.unit, self.offset, self.limit)


class ContentRange(object):
    '''
    Represents an HTTP Content-Range
    '''
    REG_EXP = r'^(?P<unit>\w+)(?:[ ]|=)(?P<offset>\d+)-(?P<last>\d+)' \
                '\/(?P<total>\d+)$'

    def __init__(self, unit, offset, limit, total):
        '''
        Initializes a new instance of the ContentRange class.
        @param unit:str Range unit
        @param offset:int Range offset
        @param last:int Range last item zero-based index
        @param total:total Total number of items available
        '''
        self.__unit = unit
        self.__offset = int(offset)
        self.__limit = int(limit)
        self.__total = int(total)

    @property
    def unit(self):
        '''
        Gets the content range unit
        @return: str
        '''
        return self.__unit

    @property
    def offset(self):
        '''
        Gets the offset
        @return: int
        '''
        return self.__offset

    @property
    def limit(self):
        '''
        Gets the zero-based index of the last element in the range
        @return: int
        '''
        return self.__limit

    @property
    def total(self):
        '''
        Gets the total number of resources available
        @return: int
        '''
        return self.__total

    @classmethod
    def parse(cls, raw):
        '''
        Parses a string into a new instance of the ContentRange class.
        @param raw:str String to parse
        @return: ContentRange
        '''
        if not raw:
            raise ValueError('Invalid Content-Range value \'%s\'' % raw)

        match = re.match(cls.REG_EXP, raw)
        if not match or len(match.groupdict()) < 4:
            return

        return cls(*match.groups())
