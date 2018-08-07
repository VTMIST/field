
# Proxy utilities

import threading
from datetime       import datetime,timedelta
import time
import logging
import socket
import Queue

import sock_utils
import utils
import logs
from ProxyPkt import ProxyPkt, PassthroughPkt, ConnectPkt, DisconnectPkt


class Packetize(threading.Thread):
    """Packetize stream data from a socket. Write pkts to a queue.
    
    Exit if the socket connection is dropped
        
    """ 
    def __init__(self,
                sock_h,
                pkt_write_q,
                pkt_src_port,
                pkt_dest_port,
                log,
                exit_callback=None):
        """Instantiate the Packetize thread
        
        sock_h = socket handler (source of stream data)
        pkt_write_q = proxy packets are written to this queue
        pkt_src_port = source address stored in the proxy pkts
        pkt_dest_port = destination address stored in the proxy pkts
        log = log object
        exit_callback = called when this thread exits
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._sock_h = sock_h
        self._pkt_write_q = pkt_write_q
        self._pkt_src_port = pkt_src_port
        self._pkt_dest_port = pkt_dest_port
        self._log = log
        self._exit_callback = exit_callback
        self._stream_read_q = sock_h.get_read_q()
        self._stop_event = threading.Event()
        self.name = 'Packetize thread, pkt source port %s, pkt dest port %s' % \
                        (str(pkt_src_port), str(pkt_dest_port))
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
                                        
    def run(self):
        """The actual thread code"""
        self._log.debug('Starting %s ' % self.name)
        self._running = True
        self._started = True
        
        while not self._stop_event.isSet():
            if not self._sock_h.is_running():
                self._stop_event.set()
                continue
            data = utils.q_get(self._stream_read_q, get_timeout=0.5)
            if data is not None:
                #self._log.debug('Packetize: received %s bytes' % str(len(data)))
                self._send_passthrough_pkts(data)
            
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        if self._exit_callback:
            self._exit_callback(self)
        self._log.debug('Exiting %s ' % self.name)
        
    def _send_passthrough_pkts(self, data):
        """Send a series of passthrough proxy packets containing data"""
        src = self._pkt_src_port
        dest = self._pkt_dest_port
        max_len = ProxyPkt.MAX_PASSTHROUGH_DATA_LEN
        while data:
            self._pkt_write_q.put(PassthroughPkt(src, dest, data[:max_len]))
            data = data[max_len:]
        
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread and its child threads"""
        #self._log.debug('Packetize: entering stop()')
        if self._running:
            self._stop_event.set()
            self.join()

            
class Depacketize(threading.Thread):
    """Depacketize proxy packets. Send stream to a socket.
    
    Exit if the client connection is dropped
        
    """ 
    def __init__(self,
                sock_h,
                log,
                exit_callback=None):
        """
        sock_h = socket handler (destination of stream data)
        pkt_read_q = source of proxy packets
        log = log object
        exit_callback = called when this thread exits
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._sock_h = sock_h
        self._pkt_read_q = Queue.Queue()
        self._log = log
        self._exit_callback = exit_callback
        self._stream_write_q = sock_h.get_write_q()
        self._stop_event = threading.Event()
        self._got_disconnect_pkt = False
        self.name = 'Depacketize thread, stream dest port is %s' % \
                        str(self._sock_h.get_peer_port())
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
                                        
    def run(self):
        """The actual thread code"""
        self._log.debug('Starting %s ' % self.name)
        self._running = True
        self._started = True
        
        while not self._stop_event.isSet():
            if not self._sock_h.is_running():
                self._log.debug('Depacketize: exiting because sock_h is not running')
                self._stop_event.set()
                continue
            #self._log.debug('Depacketize: polling queue %s' % repr(self._pkt_read_q))
            pkt_buf = utils.q_get(self._pkt_read_q, get_timeout=0.5)
            if pkt_buf is None:
                continue
            #self._log.debug('Depacketize: got a pkt')
            pkt = ProxyPkt(pkt_buf)
            pkt_type = pkt.get_type()
            if pkt_type == ProxyPkt.PASSTHROUGH:
                #self._log.debug('Depacketize: a PASSTHROUGH pkt')
                self._send_stream_data(pkt)
                continue
            if pkt_type == ProxyPkt.CONNECT:
                # Got a CONNECT pkt from the other proxy.
                #  Ignore since we are already connected.
                continue
            if pkt_type == ProxyPkt.DISCONNECT:
                # Got a DISCONNECT pkt from the other proxy
                self._log.debug('Depacketize: Got DISCONNECT')
                self._got_disconnect_pkt = True
                self._stop_event.set()
                self._log.debug('Depacketize: exiting because got a DISCONNECT')
                continue
            
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        if self._exit_callback:
            self._exit_callback(self)
        self._log.debug('Exiting %s ' % self.name)
            
    def _send_stream_data(self, pkt):
        """Send pkt's passthrough data to the client"""
        #self._log.debug('Depacketize: entering _send_stream')
        stream_data_len = pkt.get_passthrough_data_len()
        if stream_data_len > 0:
            start_i = ProxyPkt.PASSTHROUGH_DATA
            end_i = start_i + stream_data_len
            self._stream_write_q.put(pkt.get_pkt_buf()[start_i:end_i])
            
    def send(self, pkt):
        """Depacketize and send the stream data to the client"""
        self._pkt_read_q.put(pkt.get_pkt_buf())
        
    def is_running(self):
        return self._running
        
    def got_disconnect_pkt(self):
        return self._got_disconnect_pkt
        
    def stop(self):
        """Stop the socket server thread and its child threads"""
        #self._log.debug('Depacketize: entering stop()')
        if self._running:
            self._stop_event.set()
            self.join()

