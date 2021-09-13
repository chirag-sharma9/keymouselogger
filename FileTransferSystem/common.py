class HTTPRequest(object):
    "Represents a complete HTTP client request"
    def __init__(self, serveraddr, rmtaddr, req, body):
        self.rmtaddr = rmtaddr
        self._serveraddr = serveraddr
        self.environ = self._parse_req(req)
        self.body = body
    def _parse_req(self, req):
        reqlines = req.split(b'\r\n' if b'\r\n' in req else b'\n')
        reqwords = reqlines[0].split(b' ')
        urlparts = reqwords[1].split(b'?')
        headers = map(lambda v: ((v if v[0] in [b'CONTENT_TYPE',
                                                b'CONTENT_LENGTH'] else b'HTTP_'+ v[0]), v[1]),
                      map(lambda w: ((w[0].strip().replace(b'-',b'_').upper()), w[2].strip()),
                          map(lambda l: l.partition(b':'),
                              reqlines[1:])))
        return dict([ ('SERVER_NAME', self._serveraddr[0] or 'localhost'),
                      ('SERVER_PORT', self._serveraddr[1]),
                      ('REQUEST_METHOD', reqwords[0]),
                      ('SERVER_PROTOCOL', reqwords[2]),
                      ('PATH_INFO', urlparts[0]),
                      ('QUERY_STRING', 'none' if len(urlparts) < 2 else urlparts[1]),
                      ('wsgi.version', (1, 0)),
                      ('wsgi.url_scheme', 'http'),
                      ('wsgi.input', ''),
                      ('wsgi.errors', []),
                      ('wsgi.multithread', False),
                      ('wsgi.multiprocess', True),
                      ('wsgi.run_once', False),
        ] + list(headers))


class HTTPRequestBuf(object):
    """A buffer that accumulates data and can indicate when a complete
       HTTP request is present in the data."""
    def __init__(self, initial=None):
        self.incbuf = initial or b''
        self._rmtClosed = False
    def addMore(self, more):
        if hasattr(self, 'body'):
            self.body += more
        else:
            self.incbuf += more
    def __len__(self): return len(self.incbuf)
    def rmtClosed(self):
        self._rmtClosed = True
    def remaining(self):
        return getattr(self, 'clen', 65535) - len(getattr(self, 'body', self.incbuf))
    def isComplete(self):
        # If calculation has already been cached
        if hasattr(self, 'clen') and hasattr(self, 'body'):
            return len(self.body) >= self.clen
        # Check for complete request, caching elements for later use
        if b'\r\n\r\n' not in self.incbuf and b'\n\n' not in self.incbuf:
            return False
        if b'\r\n\r\n'  in self.incbuf:
            self.headers, self.body = self.incbuf.split(b'\r\n\r\n')
            hlines = self.headers.split(b'\r\n')
        else:
            self.headers, self.body = self.incbuf.split(b'\n\n')
            hlines = self.headers.split(b'\n')
        for hline in hlines:
            hwords = hline.split(b':')
            if hwords[0].lower() != b'content-length':
                continue
            self.clen = int(hwords[1])
            return len(self.body) >= self.clen
        # No Content-Length, so assume finished only when the other
        # side closes (shutdown WR).
        return self._rmtClosed
    def extract(self, reqbuilder):
        if self.isComplete():
            return (reqbuilder(self.headers, self.body[:self.clen]),
                    HTTPRequestBuf(self.body[self.clen:]))
        return None


class IncomingSocket(object):
    "Object for managing client sockets"
    def __init__(self, acceptInfo):
        self.socket, self.rmtaddr = acceptInfo
        self.incbuf = HTTPRequestBuf()
        self.socket.setblocking(0)
        self.responded = False
    def close(self):
        import socket
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()


class HTTPResponse(object):
    def __init__(self, request, response_data, status=200, data_type='text/html'):
        self.request = request
        self.status = status
        self.data = response_data
        self.data_type = data_type
    @property
    def ststxt(self):
        return {200: '200 OK',
                }.get(self.status, '500 ERR')
    def serialize(self):
        return '\r\n'.join(['HTTP/1.1 ' + self.ststxt,
                            'Content-Type: ' + self.data_type,
                            'Content-Length: ' + str(len(self.data)),
                            '',
self.data]).encode('utf-8')