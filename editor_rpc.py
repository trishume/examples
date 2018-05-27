import enum
import json
import os
import queue
import select
import socket
import struct
import threading
import traceback
import xmlrpc.client as xmlrpclib
from xml.sax.saxutils import escape

from talon import rctx

class opaque(object):
    def __init__(self, s):
        self.desc = s

    def __repr__(self):
        return self.desc

    @staticmethod
    def load(marshall, s):
        marshall.append(opaque(s))
        marshall.type = 'opaque'
        marshall._value = 0

    @staticmethod
    def dump(marshall, value, append):
        append('<value><opaque>%s</opaque></value>' % escape(value.desc))

xmlrpclib.Unmarshaller.dispatch['opaque'] = opaque.load
xmlrpclib.Marshaller.dispatch[opaque] = opaque.dump

def xml_loads(data):
    p, u = xmlrpclib.getparser()
    p.feed(data)
    p.close()
    return u.close()

class NotConnected(Exception): pass

class ClientTransport(xmlrpclib.Transport):
    def __init__(self, s):
        self.buf = b''
        self.s = s
        self.q = queue.Queue()
        self.need = -1
        self.msg_type = -1
        self.lock = threading.Lock()
        xmlrpclib.Transport.__init__(self)

    def recv_size(self, n):
        while len(self.buf) < n:
            data = self.s.recv(1024)
            if not data:
                raise socket.error
            self.buf += data
        out = self.buf[:n]
        self.buf = self.buf[n:]
        return out

    def recv_data(self):
        data = self.s.recv(4096)
        if not data:
            raise socket.error('end of file')
        self.buf += data

    def _enough(self):
        return (self.need == -1 and len(self.buf) >= 5
                or self.need >= 0 and len(self.buf) >= self.need)

    def on_data(self):
        self.recv_data()
        out = []
        while self._enough():
            if self.need == -1:
                self.msg_type, self.need, = struct.unpack('>BI', self.buf[:5])
                self.buf = self.buf[5:]
            else:
                data = self.buf[:self.need]
                self.buf = self.buf[self.need:]
                if self.msg_type == 0:
                    self.q.put(data)
                elif self.msg_type == 1:
                    out.append(json.loads(data.decode('utf8')))
                self.need = -1
        return out

    def recv(self):
        return self.q.get()

    def send(self, body):
        self.s.send(struct.pack('>I', len(body)))
        self.s.send(body)

    def close(self):
        try: self.s.shutdown(socket.SHUT_RDWR)
        except: pass
        try: self.s.close()
        except: pass
        self.q.put(None)

    def single_request(self, host, handler, body, verbose=0):
        with self.lock:
            try:
                self.send(body)
                data = self.recv()
            except socket.error as e:
                self.close()
                raise
            return xml_loads(data)

class Client(xmlrpclib.ServerProxy):
    def __init__(self, s):
        self._active = False
        self._transport = ClientTransport(s)
        xmlrpclib.ServerProxy.__init__(self, 'http://.', transport=self._transport, allow_none=True)

    def _close(self):
        self._transport.close()

    def __bool__(self):
        return self._active

    def __repr__(self):
        return '<Client {:#x}>'.format(id(self))
    __str__ = __repr__

class Server(object):
    def __init__(self):
        self.callbacks = set()
        self.clients = {}
        self.cb = queue.Queue()

    def client(self):
        if len(self.clients) > 1:
            raise RuntimeError("Multiple connected editors, this shouldn't happen")
        for k,v in self.clients.items():
            return v
        return None

    def detach(self, client):
        print('detached {}'.format(client))
        client._close()
        if client == self.client:
            self.client = None
        del self.clients[client._transport.s]

    def register(self, cb):
        self.callbacks.add(cb)
        rctx.register(lambda: self.callbacks.remove(cb))

    def emit(self, client, msg):
        cmd = msg.pop('cmd', None)
        print('emit', client, cmd, msg)
        # if cmd == 'active':
        #     if msg.get('active'):
        #         if self.client:
        #             self.client._active = False
        #         self.client = client
        #         client._active = True
        #     elif self.client == client:
        #         client._active = False

        for cb in self.callbacks:
            self.cb.put((cb, (client, cmd, msg)))

    def cb_thread(self):
        while True:
            cb, args = self.cb.get()
            try:
                cb(*args)
            except Exception:
                traceback.print_exc()

    def serve(self, path):
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if os.path.exists(path):
            os.unlink(path)
        server.bind(path)
        server.listen(1)
        while True:
            sockets = list(self.clients.keys()) + [server]
            ready, _, errors = select.select(sockets, [], sockets, 0.5)
            for s in ready:
                client = None
                if s == server:
                    sock, addr = server.accept()
                    client = Client(sock)
                    print('accepted new connection: {}'.format(client))
                    try:
                        self.clients[sock] = client
                    except Exception:
                        traceback.print_exc()
                else:
                    try:
                        client = self.clients[s]
                        result = client._transport.on_data()
                        try:
                            for msg in result:
                                self.emit(client, msg)
                        except Exception:
                            traceback.print_exc()
                    except socket.error:
                        self.detach(client)
                    except Exception:
                        traceback.print_exc()
                        self.detach(client)

    def spawn(self, path):
        t = threading.Thread(target=self.serve, args=(path, ))
        t.daemon = True
        t.start()
        t = threading.Thread(target=self.cb_thread)
        t.daemon = True
        t.start()

server = Server()
server.spawn('/tmp/talon_editor_socket')
register = server.register

def active(): return server.client()
# def clients(): return list(server.clients.values())
