#! /usr/bin/python

# Socket-connected console I/O for headless processes

import sys
import threading
import Queue

import utils
import sock_utils
import logs


class SockConsole(threading.Thread):
    """ Connect to console client and handle input and output """
    def __init__(self, host, port, log, exit_callback=None):
        """
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._log = log
        self._exit_callback = exit_callback
        self._host = host
        self._port = port
        self._console_sock_h = None
        self._console_read_q = None
        self._console_write_q = None
        self._stop_event = threading.Event()
        self.name = 'SockConsole thread'
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
                                        
    def run(self):
        """The actual thread code"""
        #self._log.debug('Starting %s ' % self.name)
        self._running = True
        self._started = True
        
        while not self._stop_event.isSet():
            if self._console_sock_h:
                self._stop_event.wait(0.5)
                continue
            #self._log.debug('SockConsole: waiting for client to connect')
            sock, addr, connected_flag = \
                        sock_utils.connect_to_client(self._log,
                                                    self._host,
                                                    self._port,
                                                    self._stop_event)
            #self._log.debug('SockConsole: returned from sock_utils.connect_to_client')
            if self._stop_event.isSet():
                continue
            if connected_flag:
                #self._log.debug('SockConsole: connected_flag is true')
                self._console_sock_h = sock_utils.SockHandler(sock,
                                     self._log,
                                     log_all_data=False,
                                     read_data_q=Queue.Queue(),
                                     write_data_q=Queue.Queue(),
                                     hand_exit_callback=self._my_exit_callback,
                                     type='stream')
                #self._log.debug('SockConsole: returned from sock_utils.SockHandler ')
                self._log.debug('SockConsole: connected to client')
                self._log.debug('  client port is %s' % str(self._console_sock_h.get_peer_port()))
                self._log.debug('  local port is %s' % str(self._console_sock_h.get_sock_port()))                
                self._console_read_q = self._console_sock_h.get_read_q()
                self._console_write_q = self._console_sock_h.get_write_q()
            
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        self._stop_children()
        if self._exit_callback:
            self._exit_callback(self)
        #self._log.debug('Exiting %s ' % self.name)
        
    def _stop_children(self):
        if self._console_sock_h is not None:
            self._console_sock_h.stop()
            self._console_sock_h = None
        self._console_read_q = None
        self._console_writ_q = None
            
    def write(self, s):
        """ Write s to the console """
        if self._console_write_q:
            self._console_write_q.put(s)
        
    def read(self, read_timeout=0):
        """ Read from the console
            Return the console input or None
        """
        if self._console_read_q is not None:
            return utils.q_get(self._console_read_q, get_timeout=read_timeout)
        else:
            utils.wait(read_timeout)
            return None

    def _my_exit_callback(self, child):
        """Child threads call this when they die"""
        self._console_sock_h = None
        self._console_read_q = None
        self._console_write_q = None
        
    def is_connected(self):
        """Return True if the console is connected"""
        return self._console_sock_h is not None
        
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread and its child threads"""
        if self._running:
            self._stop_event.set()
            # force connect_to_client to return
            sock_utils.dummy_connection(self._host, self._port)
            self.join()
