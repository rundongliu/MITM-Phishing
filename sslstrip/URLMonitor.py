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

import re
from change import local_host, target_host

class URLMonitor:    

    '''
    The URL monitor maintains a set of (client, url) tuples that correspond to requests which the
    server is expecting over SSL.  It also keeps track of secure favicon urls.
    '''

    # Start the arms race, and end up here...
    _instance          = None

    def __init__(self):
        self.linkDomain = dict()
        self.linkPort = dict()
        self.secureLink = set()
    
    def getDomain(self, url):
        if url in self.linkDomain:
            return self.linkDomain[url]
        else:
            return target_host
    def isSecureLink(self, url):

        return url in self.secureLink

    def getPort(self, url):
        if url in self.linkPort:
            return self.linkPort[url]
        else:
            return 443

    def addLink(self, url):
        methodIndex = url.find("//") + 2
        method      = url[0:methodIndex]

        pathIndex   = url.find("/", methodIndex)
        host        = url[methodIndex:pathIndex]
        path        = url[pathIndex:]

        portIndex   = host.find(":")
        
        port = 80
        if method=="http://":
            if (portIndex != -1):
                host = host[0:portIndex]
                port = int(host[portIndex+1:])
                if len(port) == 0:
                    port = 80
            else:
                port = 80

        elif method=="https://":
            port = 443
            if (portIndex != -1):
                host = host[0:portIndex]
                port = int(host[portIndex+1:])
                if len(port) == 0:
                    port = 443

        url = "http://" + local_host + path
        
        if method=="https://":
            self.secureLink.add(url)
        if url in self.linkDomain and len(host)>len(self.linkDomain[url]):
            pass
        else:
            self.linkDomain[url] = host
        self.linkPort[url] = port
        
        return url

    def getInstance():
        if URLMonitor._instance == None:
            URLMonitor._instance = URLMonitor()

        return URLMonitor._instance

    getInstance = staticmethod(getInstance)
