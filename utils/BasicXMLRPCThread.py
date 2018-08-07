# XMLRPC Utilities


import sys
import xmlrpclib
import SimpleXMLRPCServer
import threading
import socket
import SocketServer

import utils

class XMLRPCServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer.SimpleXMLRPCServer):
        # Use the ThreadingMixIn to make XMLRPCServer multi-threaded.
        # Following line forces the TCPIP stack to reuse
        #  socket addresses (ports) instead of going though a
        #  long (~30 second) timeout when the socket is shut down.
        # Subclassing SimpleXMLRPCServer seems to be the only way
        #  to make this little trick work.
        allow_reuse_address = True


class BasicXMLRPCThread(threading.Thread):
    """
        XMLRPC server thread
        
        Accept and execute commands from
         XMLRPC clients
    """
    def __init__(self, host, port, log=None):
        threading.Thread.__init__(self)
        self._log = log
        self.setDaemon(False)
        self._stop_event = threading.Event()
        self._host = host
        self._port = port
        self.name = ''.join(('XMLRPC server thread (', self._host, ':', str(self._port), ')' ))
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
                
    def run(self):
        """ The actual thread code """
        #if self._log:
        #    self._log.debug('Starting %s ' % self.name)
        self._server = XMLRPCServer((self._host, self._port), logRequests=False)
        self._server.register_introspection_functions()        
        self._server.register_function(self.test)
        self._server.socket.settimeout(10)
        self._running = True
        self._started = True
        while not self._stop_event.isSet():
            self._server.handle_request()
        self._is_running = False
        #if self._log:
            #self._log.debug('Stopping %s ' % self.name)
            #self._log.debug('Exiting %s ' % self.name)

    def test(self):
        """XMLRPC server test command"""
        if self._log:
            self._log.debug('XMLRPC: test command received')
        return 'OK'
                
    def is_running(self):
        return self._running

    def stop(self):
        """Stop the XMLRPC server thread"""
        if self._running:
            self._server.socket.shutdown(socket.SHUT_RDWR)
            self._server.socket.close()        
            self._stop_event.set()
            self.join()
    
