import sys
from thespian.actors import *
import logging
import select
import socket
import errno
from datetime import timedelta
from functools import partial
from common import *


class Handler(ActorTypeDispatcher):
    def receiveMsg_HTTPRequest(self, reqmsg, sender):
        self.send(sender, HTTPResponse(reqmsg,'<h1>Hello, World!</h1>'))
        
        
class StartServer(object):
    # Message sent to ServerActor to start HTTP server on a given port,
    # passing requests to the handler actor
    def __init__(self, port, handler):
        self.port = port
        self.handler = handler
        
    
class ServerActor(ActorTypeDispatcher):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._response_only = []
        
    def check_socket(self, incsock):
        # Reads incoming data from a client-connected socket. When a full HTTP request has been received, sends it to the handler
        try:
            newdata = incsock.socket.recv(incsock.incbuf.remaining())