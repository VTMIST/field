# Socket I/O Utilities
# 
# There is one exposed class:
#     SockHandler
#
# and three exposed functions:
#     connect_to_server
#     connect_to_client
#     dummy_connection
#     
# connect_to_server is called to connect to a server and create
# a SockHandler.  The SockHandler is the used for
# all interaction with the socket.
#
# connect_to_client waits until a client connect to a server. 
#
# SockHandler creates and manages socket read and write threads.
# Queues are created and used to transmit
# socket data and receive socket stream data or packets.

import sys
import time
import logging
import socket
import Queue
import threading
from datetime import datetime,timedelta
from errno import EINTR

import utils
import logs
from ProxyPkt import ProxyPkt

def connect_to_server(log, host, port, exit_callback=None, data_type='stream'):
    """Connect to a socket server at host, port
    
    exit_callback is called when the socket handler thread exits
    If data_type = 'stream' data read from the socket is enqueued
        without any interpretation.
    if data_type = 'packet', data read from the socket is assembled
        into proxy packets.  Only complete, valid packets are enqueued.    
    Return a SocketHandler if connection is successful
    Return None if not connected       
    """
    #log.debug('in sock_utils.connect_to_server:')
    #log.debug('  host is %s' % host)
    #log.debug('  port is %s' % str(port))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            sock.settimeout(0.5)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except OSError, e:
            if e.errno == EINTR:
                continue
        except socket.error, (value,message):
            #print "Socket error: " + message
            return None
        break
    while True:
        try:
            sock.connect((host, port))
        except OSError, e:
            if e.errno == EINTR:
                continue
        except socket.error:
            #print 'Socket error'
            return None
        break
    return SockHandler(sock, log,
                            log_all_data=False,
                            read_data_q=Queue.Queue(100),
                            write_data_q=Queue.Queue(100),
                            hand_exit_callback=exit_callback,
                            type=data_type
                            )
 
def connect_to_client(log, host, port, stop_event):
    """Open up a server port and wait for a client to connect
    
    Return (sock, addr, connected_flag)
    Shuts down the socket server before returning.
    
    accept() blocks until a client tries to connect.  
    This causes a problem when the caller wants shut down the server.
    To shut down the server and force a return from connect_to_client,
    the caller should:
      stop_event.set()
      dummy_connection(host, port)
    """
    #log.debug('connect_to_client: waiting on port %s' % str(port))
    ret_val = (0, 0, False)
    serve = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # The SO_REUSEADDR option must be set before binding
    serve.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)        
    serve.bind((host, port))
    serve.listen(1)
    while not stop_event.isSet():
        try:        
            sock, addr = serve.accept()
        except OSError, e:
            if e.errno == EINTR:
                continue
        except Exception:
            continue
        if not stop_event.isSet():
            ret_val = (sock, addr, True)
            break
    serve.shutdown(socket.SHUT_RDWR)
    serve.close()
    return ret_val                    
                            
                            
def dummy_connection(host, port):
    """Make a socket connection to host, port and then shut it down
    
    dummy_connection() is only used to force socket server
    threads to return from accept().  All errors and
    exceptions are ignored.
    """
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.shutdown(socket.SHUT_RDWR)
            s.close()
        except OSError, e:
            if e.errno == EINTR:
                continue
        except Exception:
            pass
        break


class PacketReadThread(threading.Thread):
    """
        Read stream data from a socket,  assemble proxy packets
        and enqueue them.
        Only strings containing well-formed, whole packets are
        written to the queue.
        The socket is closed and the thread exits
        if the peer disconnects.
    """
    def __init__(self, sock, log, log_data_flag=False, data_q=None,
                    exit_callback=None):
        """
            sock =          socket to read from
            pkt_q =        packet queue
            log =           log object
            log_data_flag = True to log all socket data
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._stop_event = threading.Event()
        self._log = log
        self._sock = sock
        self._log_all_data = log_data_flag
        self._data_q = data_q
        self._new_data_q_avail = False
        self._new_data_q = None
        self._new_data_q_lock = threading.Lock()
        self._client = utils.get_peer_addr_str(sock)
        self._host = utils.get_sock_addr_str(sock)
        self._data_path = '%s->%s' % (self._host, self._client)
        self.name = 'PacketReadThread (%s)' % self._data_path
        self._exit_callback = exit_callback
        self._rx_byte_buf = ''
        self._pkt_state = 0
        self._pkt_read_index = 0
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
        
    def _print_buffer(self, data):
        """Print contents of a data buffer"""
        if self._log_all_data:
            self._log.info('Rx from %s:%s' % (self._client, repr(data)))
            
    def run(self):
        """The actual thread code"""
        #self._log.debug('Starting %s' % self.name)
        try:
            self._sock.settimeout(0.1)
        except socket.error:
            # client disconnected
            self._stop_event.set()
        self._running = True
        self._started = True
        while not self._stop_event.isSet():
            self._check_for_new_data_q()
            try:
                data = self._sock.recv(ProxyPkt.MAX_PKT_LEN)
            except socket.timeout, msg:
                continue
            except socket.error:
                # client disconnected
                self._stop_event.set()
                continue
            except OSError, e:
                if e.errno == EINTR:
                    continue
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                utils.log_exc_traceback(exc_type, exc_value, exc_traceback, self._log)
                sys.exit(1)
            if not data:
                self._stop_event.set()
                break
            if self._data_q is not None:
                #self._log.debug('Received %s bytes from %s' % (str(len(data)), self._client))
                self._handle_rx_data(data)
        self._running = False
        #self._log.debug('Stopping %s' % self.name)
        utils.close_sock(self._sock)
        if self._exit_callback:
            self._exit_callback(self)
        #self._log.debug('Exiting %s' % self.name)
            
    def _handle_rx_data(self, data):
        """Buffer and packetize the input data"""
        self._rx_byte_buf += data
        self._packetize()
        
    def _packetize(self):
        """Assemble and enqueue proxy packet buffers"""
#         self._log.debug('in _packetize: rx_byte_buf is %s' % \
#                             utils.bytes_to_hex(self._rx_byte_buf))
#         self._log.debug('in _packetize: self._rx_byte_buf length is %s' % \
#                             str(len(self._rx_byte_buf)))
#         self._log.debug('in _packetize: self._pkt_read_index is %s' % \
#                             str(self._pkt_read_index))
        while True:
            if self._pkt_read_index == len(self._rx_byte_buf):
                return
            if self._pkt_state == 0:
                self._trim_rx_byte_buf()
                if self._rx_byte_buf[self._pkt_read_index:self._pkt_read_index+1] == \
                                        ProxyPkt.SYNC_BYTE_0_VALUE:
                    self._pkt_state += 1
                    #self._log.debug('  got sync byte 0')
                else:
                    self._pkt_state = 0
                self._pkt_read_index += 1
                continue
            elif self._pkt_state == 1:
                if self._rx_byte_buf[self._pkt_read_index:self._pkt_read_index+1] == \
                                        ProxyPkt.SYNC_BYTE_1_VALUE:
                    self._pkt_state += 1
                    #self._log.debug('  got sync byte 1')
                else:
                    self._pkt_state = 0
                self._pkt_read_index += 1
                continue
            elif self._pkt_state == 2:
                if self._rx_byte_buf[self._pkt_read_index:self._pkt_read_index+1] == \
                                        ProxyPkt.SYNC_BYTE_2_VALUE:
                    self._pkt_state += 1
                    #self._log.debug('  got sync byte 2')
                else:
                    self._pkt_state = 0
                self._pkt_read_index += 1
                continue
            elif self._pkt_state == 3:
                if self._rx_byte_buf[self._pkt_read_index:self._pkt_read_index+1] == \
                                        ProxyPkt.SYNC_BYTE_3_VALUE:
                    self._pkt_state += 1
                    #self._log.debug('  got sync byte 3')
                else:
                    self._pkt_state = 0
                self._pkt_read_index += 1
                continue
            elif self._pkt_state == 4:
                # Get pkt length LSB
                self._len_lsb = self._rx_byte_buf[self._pkt_read_index:self._pkt_read_index+1]
                self._pkt_read_index += 1
                self._pkt_state += 1
                continue
            elif self._pkt_state == 5:
                # Get pkt length MSB
                self._len_msb = self._rx_byte_buf[self._pkt_read_index:self._pkt_read_index+1]
                self._pkt_read_index += 1
                self._pkt_len = (ord(self._len_msb) * 256) + ord(self._len_lsb)
                if self._pkt_len > ProxyPkt.MAX_PKT_LEN:
                    self._log.error('Got invalid proxy packet length, too long')
                    self._pkt_state = 0
                    continue
                if self._pkt_len < ProxyPkt.MIN_PKT_LEN:
                    self._log.error('Got invalid proxy packet length, too short')
                    self._pkt_state = 0
                    continue
                self._pkt_state += 1
                #self._log.debug('  got good pkt length')
                continue
            elif self._pkt_state == 6:
                # Get pkt type
                self._pkt_type = self._rx_byte_buf[self._pkt_read_index:self._pkt_read_index+1]
                self._pkt_read_index += 1
                if self._pkt_type > chr(ProxyPkt.MAX_PKT_TYPE):
                    self._log.error('Got invalid proxy packet type (%s)' % \
                                    str(self._pkt_type))
                    self._pkt_state = 0
                    continue
                self._pkt_state += 1
                #self._log.debug('  got good pkt type')
                continue
            elif self._pkt_state == 7:
                # Wait for pkt data and checksum to arrive
                bytes_avail = len(self._rx_byte_buf) - self._pkt_read_index
                bytes_needed = self._pkt_len - ProxyPkt.HDR_LEN
                if bytes_avail < bytes_needed:
                    return
                else:
                    start_i = self._pkt_read_index - ProxyPkt.HDR_LEN
                    end_i = self._pkt_read_index + bytes_needed
                    pkt = ProxyPkt(self._rx_byte_buf[start_i:end_i])
                    self._rx_byte_buf = self._rx_byte_buf[end_i:]
                if pkt.cksum_is_valid():
                    self._data_q.put(pkt.get_pkt_buf())
                    #self._log.debug('PacketReadThread: Received packet:')
                    #self._log.debug(pkt.str())
                else:
                    self._log.error('Got invalid proxy packet checksum')
                self._pkt_read_index = 0
                self._pkt_state = 0
                continue
            else:
                self._log.error('Invalid state value in sock_utils.PacketReadThread()')
           
    def _trim_rx_byte_buf(self):
        """Prevent gibberish from overflowing the rx byte buf"""
        pass
#         if self._pkt_read_index >= 100:
#             self._rx_byte_buf = self._rx_byte_buf[self._pkt_read_index:]
#             self._pkt_read_index = 0

    def _check_for_new_data_q(self):
        """
            If a new data queue is available, start
             using it now.
        """
        self._new_data_q_lock.acquire()
        if self._new_data_q_avail:
            self._data_q = self._new_data_q
            self._new_data_q_avail = False       
        self._new_data_q_lock.release()
    
    def set_data_q(self, q):
        """
            Start using a new data queue the next time
            the thread code runs
        """
        self._new_data_q_lock.acquire()
        self._new_data_q = q
        self._new_data_q_avail = True       
        self._new_data_q_lock.release()
        
    def is_running(self):
        return self._running                     
                
    def stop(self):
        """Stop this thread and wait for it to end"""
        if self._running:
            self._stop_event.set()
            self.join()


class SockWriteThread(threading.Thread):
    """Read data from a queue, write it to a socket.
        The socket is closed and the thread exits
        if the peer disconnects.
    """
    def __init__(self, sock, log, log_data_flag=False, data_q=None,
                timeout=10, exit_callback=None):
        """
            sock =          socket to write data to
            data_q =        queue to read data from
            log =           log object
            log_data_flag = True to log all socket data
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._stop_event = threading.Event()
        self._log = log
        self._sock = sock
        self._log_all_data = log_data_flag
        self._timeout = timedelta(seconds=timeout)
        self._data_q = data_q
        self._new_data_q_avail = False
        self._new_data_q = None
        self._new_data_q_lock = threading.Lock()
        self._client = utils.get_peer_addr_str(sock)
        self._host = utils.get_sock_addr_str(sock)
        self._data_path = '%s->%s' % (self._host, self._client)
        self.name = 'SockWriteThread (%s)' % self._data_path
        self._exit_callback = exit_callback
        self._started = False
        self._running = False
        self.start()
        while not self._started:
            utils.wait(0.05)
        
    def _print_buffer(self, data):
        """Print contents of a data buffer"""
        if self._log_all_data:
            self._log.info('Tx to %s:  %s' % (self._client, repr(data)))
            
    def run(self):
        """The actual thread code"""
        #self._log.debug('Starting %s' % self.name)
        try:
            self._sock.settimeout(0.5)
        except socket.error:
            # client disconnected
            self._stop_event.set()
        self._started = True
        self._running = True
        while not self._stop_event.isSet():
            self._check_for_new_data_q()
            if self._data_q is None:
                # no data queue exists yet
                utils.wait(0.5)
                continue
            data = utils.q_get(self._data_q, get_timeout=1)
            if data is None:
                continue
            #self._log.debug('SockWriteThread: dequeued a %s' % repr(data))
            startTime = datetime.now()
            # keep sending until all data is sent or timeout
            while data and (not self._stop_event.isSet()):
                while True:
                    try:
                        sent = self._sock.send(data[:ProxyPkt.MAX_PKT_LEN])
                    except OSError, e:
                        if e.errno == EINTR:
                            continue
                    except socket.error:
                        # client disconnected
                        self._stop_event.set()
                        break  # out of while True
                    break # out of while True
                if self._stop_event.isSet():
                    break
                #self._log.debug('SockWriteThread: Sent %s bytes to %s' % (str(sent), self._client))
                data = data[sent:]
                elapsedTime = datetime.now() - startTime
                if elapsedTime > self._timeout:
                    self._log.error('Timed out writing to %s' % self._peer_addr_port)
                    self._stop_event.set()
                    break
        self._running = False
        #self._log.debug('Stopping %s' % self.name)
        utils.close_sock(self._sock)
        if self._exit_callback:
            self._exit_callback(self)
        #self._log.debug('Exiting %s' % self.name)
        
    def _check_for_new_data_q(self):
        """
            If a new data queue is available, start
             using it now.
        """
        self._new_data_q_lock.acquire()
        if self._new_data_q_avail:
            self._data_q = self._new_data_q
            self._new_data_q_avail = False       
        self._new_data_q_lock.release()
    
    def set_data_q(self, q):
        """
            Start using a new data queue the next time
            the thread code runs.
        """
        self._new_data_q_lock.acquire()
        self._new_data_q = q       
        self._new_data_q_avail = True
        self._new_data_q_lock.release()
        
    def is_running(self):
        return self._running              
                
    def stop(self):
        """Stop this thread and wait for it to end"""
        if self._running:
            self._stop_event.set()
            self.join()
            

class StreamReadThread(threading.Thread):
    """
        Read stream data from a socket, write it to a queue.
        The socket is closed and the thread exits
         if the client disconnects.
    """
    def __init__(self, sock, log, log_data_flag=False, data_q=None,
                    exit_callback=None):
        """
            sock =          socket to read from
            data_q =        queue to write to
            log =           log object
            log_data_flag = True to log all socket data
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._stop_event = threading.Event()
        self._log = log
        self._sock = sock
        self._log_all_data = log_data_flag
        self._data_q = data_q
        self._new_data_q_avail = False
        self._new_data_q = None
        self._new_data_q_lock = threading.Lock()
        self._client = utils.get_peer_addr_str(sock)
        self._host = utils.get_sock_addr_str(sock)
        self._data_path = '%s->%s' % (self._host, self._client)
        self.name = 'StreamReadThread (%s)' % self._data_path
        self._exit_callback = exit_callback
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
        
    def _print_buffer(self, data):
        """Print contents of a data buffer"""
        if self._log_all_data:
            self._log.info('Rx from %s:%s' % (self._client, repr(data)))
            
    def run(self):
        """The actual thread code"""
        #self._log.debug('Starting %s' % self.name)
        try:
            self._sock.settimeout(0.1)
        except socket.error:
            # client disconnected
            self._stop_event.set()
        self._running = True
        self._started = True
        while not self._stop_event.isSet():
            self._check_for_new_data_q()
            try:
                data = self._sock.recv(ProxyPkt.MAX_PKT_LEN)
            except socket.timeout, msg:
                continue
            except socket.error:
                # client disconnected
                self._stop_event.set()
                continue
            except OSError, e:
                if e.errno == EINTR:
                    continue
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                utils.log_exc_traceback(exc_type, exc_value, exc_traceback, self._log)
                sys.exit(1)
            if not data:
                self._stop_event.set()
                break
            if data is not None:
                #self._log.debug('Received %s bytes from %s' % (str(len(data)), self._client))
                self._data_q.put(data)
                self._print_buffer(data)
        self._running = False
        #self._log.debug('Stopping %s' % self.name)
        utils.close_sock(self._sock)
        if self._exit_callback:
            self._exit_callback(self)
        #self._log.debug('Exiting %s' % self.name)

    def _check_for_new_data_q(self):
        """
            If a new data queue is available, start
             using it now.
        """
        self._new_data_q_lock.acquire()
        if self._new_data_q_avail:
            self._data_q = self._new_data_q
            self._new_data_q_avail = False       
        self._new_data_q_lock.release()
    
    def set_data_q(self, q):
        """
            Start using a new data queue the next time
            the thread code runs
        """
        self._new_data_q_lock.acquire()
        self._new_data_q = q
        self._new_data_q_avail = True       
        self._new_data_q_lock.release()
        
    def is_running(self):
        return self._running                     
                
    def stop(self):
        """Stop this thread and wait for it to end"""
        if self._running:
            self._stop_event.set()
            self.join()
            
            
class SockHandler(threading.Thread):
    """
        A class that creates a read and a write
         socket thread and contains state information
         to coordinate them.
    """
    def __init__(self,
                 sock,
                 log,
                 log_all_data=False,
                 read_data_q=None,
                 write_data_q=None,
                 hand_exit_callback=None,
                 type='stream'):
        """
            sock = socket object
            log = log object
            read_data_q = contains data read from the socket
            write_data_q = contains data to be written to the socket
            If type = 'stream' data read from the socket is enqueued
                without any interpretation.
            if type = 'packet', data read from the socket is assembled
                into proxy packets.  Only complete, valid packets are enqueued.    
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._stop_event = threading.Event()
        self._log = log
        self.sock = sock
        self._read_thread = None
        self._write_thread = None
        self._read_data_q = read_data_q
        self._write_data_q = write_data_q
        self._log_all_data = log_all_data
        self.client_addr = utils.get_peer_addr_str(sock)
        self.host_addr = utils.get_sock_addr_str(sock)  
        self.name = 'socket handler thread (host %s, client %s)' % (self.host_addr, self.client_addr)
        self._exit_callback = hand_exit_callback
        self._running = False
        self._started = False
        self._type = type
        self.start()
        while not self._started:
            utils.wait(0.05)
        
    def run(self):
        """The actual thread code"""
        self._log.debug('Starting %s' % self.name)
        
        if self._type == 'stream':
            self._read_thread = StreamReadThread(self.sock, self._log,
                                    log_data_flag=self._log_all_data,
                                    data_q=self._read_data_q,
                                    exit_callback=self._my_exit_callback)
        else:
            # must be packet type
            self._read_thread = PacketReadThread(self.sock, self._log,
                                    log_data_flag=self._log_all_data,
                                    data_q=self._read_data_q,
                                    exit_callback=self._my_exit_callback)
        
        self._write_thread = SockWriteThread(self.sock, self._log,
                                log_data_flag=self._log_all_data,
                                data_q=self._write_data_q,
                                exit_callback=self._my_exit_callback)
        self._running = True
        self._started = True
        
        self._stop_event.wait()
             
        self._running = False
        #self._log.debug('Stopping %s' % self.name)
        self._read_thread.stop()
        self._write_thread.stop()
        if self._exit_callback:
            self._exit_callback(self)
        #self._log.debug('Exiting %s' % self.name)
        
    def _my_exit_callback(self, child):
        """Child threads call this when they die"""
        self._stop_event.set()
        
    def set_read_q(self, q):
        """Set the read thread data queue"""
        self._read_thread_q = q
        self._read_thread.set_data_q(q)

    def set_write_q(self, q):
        """Set the write thread data queue"""
        self._write_thread_q = q
        self._write_thread.set_data_q(q)
        
    def get_read_q(self):
        """Return the handler socket read queue"""
        return self._read_data_q
        
    def get_write_q(self):
        """Return the handler socket write queue"""
        return self._write_data_q
        
    def get_peer_port(self):
        """Return the socket's peer port number"""
        return utils.get_peer_port(self.sock)
        
    def get_sock_port(self):
        """Return the socket's port number"""
        return utils.get_sock_port(self.sock)
    
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread and all its child threads"""
        if self._running:
            self._stop_event.set()
            self.join()
            
            

            
