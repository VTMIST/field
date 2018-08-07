#! /usr/bin/python

# Server Proxy Process

# If necessary, starts the modem server.
# Connects to the modem server.

import sys
import os
import threading
from datetime       import datetime,timedelta
import time
import logging
import socket
import Queue
import xmlrpclib

import sock_utils
import utils
import logs
import global_config
import modem_svr_config
import svr_proxy_config
from ProxyPkt import ProxyPkt, DisconnectPkt
import proxy_utils
from BasicXMLRPCThread import BasicXMLRPCThread

class ModemSvrConnection(threading.Thread):
    """There is only one ModemSvrConnection.
    Handles CONNECT proxy protocol packets by creating
    ServerConnections.
    Directs packets from the modem server to
    the correct ServerConnection.
    Exits when the modem_svr connection is lost or
    when stopped by parent.
    """
    def __init__(self, modem_svr_sock_h, xfer_rec, log):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._modem_svr_sock_h = modem_svr_sock_h
        self._xfer_rec = xfer_rec
        self._log = log
        self._stop_event = threading.Event()
        self.name = 'ModemSvrConnection thread'
        self._modem_svr_proxy = None
        self._children = []
        self._children_lock = threading.Lock()
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)

    def run(self):
        """The actual thread code"""
        self._log.debug('Starting %s' % self.name)
        self._running = True
        self._started = True
        read_pkt_q = self._modem_svr_sock_h.get_read_q()
        write_pkt_q = self._modem_svr_sock_h.get_write_q()
        self._update_connected_flag()
        
        #self._log.debug('ModemSvrConnection: modem_svr_sock_h read q is %s' % repr(read_pkt_q))
        #self._log.debug('ModemSvrConnection: modem_svr_sock_h write q is %s' % repr(write_pkt_q))
        while not self._stop_event.isSet():
            # If modem server connection is lost, exit thread
            if not self._modem_svr_sock_h.is_running():
                self._stop_event.set()
                continue
            pkt_buf = utils.q_get(read_pkt_q, get_timeout=0.5)
            if pkt_buf:
                pkt = ProxyPkt(pkt_buf)
                #self._log.debug('ModemSvrConnection: received pkt')                
                #self._log.debug(pkt.str())                
                pkt_type = pkt.get_type()
                if pkt_type == ProxyPkt.PING:
                    #self._log.debug('Got a PING packet.')
                    self._send_ping(write_pkt_q)
                    continue
                if pkt_type == ProxyPkt.ICCID_REQ:
                    self._xfer_rec.set_time(time.time())
                    self._send_iccid(write_pkt_q)
                    continue
                if (pkt_type == ProxyPkt.PASSTHROUGH) or \
                    (pkt_type == ProxyPkt.DISCONNECT):
                    self._xfer_rec.set_time(time.time())                    
                    self._children_lock.acquire()
                    for ch in self._children:                       
                        if (ch.get_server_port() == pkt.get_dest_port()) and \
                                (ch.get_client_port() == pkt.get_src_port()):
                            ch.send(pkt)
                            break
                    self._children_lock.release()
                    continue                    
                    
                if pkt_type == ProxyPkt.CONNECT:
                    self._xfer_rec.set_time(time.time())
                    self._log.debug('ModemSvrConnection: got CONNECT')
                    sc = ServerConnection(write_pkt_q,
                                        pkt.get_dest_port(),
                                        pkt.get_src_port(),
                                        self._log,
                                        exit_callback=self._my_exit_callback)
                    if sc.is_connected():
                        self._children_lock.acquire()
                        self._children.append(sc)
                        self._children_lock.release()
            
        self._running = False
        self._log.debug('Stopping %s' % self.name)
        self._update_disconnected_flag()
        for ch in self._children:
            ch.stop()
        self._log.debug('Exiting %s' % self.name)
                                  
    def _my_exit_callback(self, child):
        """Child threads call this when they die"""
        if self._running:
            self._children_lock.acquire()
            # if child failed to init, it won't be in self._children
            utils.safe_remove(self._children, child)
            self._children_lock.release()
                        
    def _send_iccid(self, write_q):
        """Transmit a pkt containing the modem SIM ICCID"""
        self._modem_svr_proxy = utils.get_XMLRPC_server_proxy(modem_svr_config.XMLRPC_URL, self._log)
        if self._modem_svr_proxy is None:
            self._log.error('_send_iccid: Could not create modem_svr XMLRPC server proxy.')
            return
        try:
            iccid = self._modem_svr_proxy.get_iccid()
        except Exception, e:
            self._log.error('_send_iccid: svr_proxy XMLRPC cmd failed.  %s' % e)
            return
        self._modem_svr_proxy = None    # allow garbage collection                
        self._log.debug('Got ICCID from modem server (%s)' % iccid)
        pkt = ProxyPkt()
        pkt.build(ProxyPkt.ICCID, iccid)
        write_q.put(pkt.get_pkt_buf())
        self._log.debug('Sent ICCID packet')
        
    def _send_ping(self, write_q):
        """Transmit a PING packet"""    
        pkt = ProxyPkt()
        pkt.build(ProxyPkt.PING)
        write_q.put(pkt.get_pkt_buf())
        #self._log.debug('Sent PING packet')       
        
    def _update_connected_flag(self):
        """Touch the "connected" file"""
        self._touch(global_config.flag_dir, svr_proxy_config.connect_time_file)
                      
    def _update_disconnected_flag(self):
        """Touch the "disconnected" file"""
        self._touch(global_config.flag_dir, svr_proxy_config.disconnect_time_file)
            
    def _touch(self, directory, path):
        if os.path.exists(path):
            os.utime(path, None)    
        else:          
            utils.make_dirs(directory)
            f = open(path, 'w')
            f.close()
        
    def is_running(self):
        return self._running
            
    def stop(self):
        """Stop this thread and its child threads"""
        if self._running:
            self._stop_event.set()
            self.join()


class ServerConnection(threading.Thread):
    """Handles a single client-server connection
    Creates packetize and depacketize threads.
    Exits if either the packetize or depacketize thread dies.
    Exits if stopped by parent.
    """

    def __init__(self,
                pkt_write_q,
                svr_port,
                client_port,
                log,
                exit_callback=None):
        """
        pkt_write_q = outgoing pkts to the modem server
        svr_port = Port number of server on local machine
        client_port = port number of client on the other machine
        log = log object
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._host = 'localhost'
        self._port = client_port
        self._pkt_write_q = pkt_write_q
        self._svr_port = svr_port
        self._client_port = client_port
        self._sock_h = None
        self._pack_thread = None
        self._depack_thread = None
        self._log = log
        self._exit_callback = exit_callback        
        self._connected = False
        self._stop_event = threading.Event()
        self.name = 'ServerConnection thread, server port %s' % str(svr_port)
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
                                        
    def run(self):
        """The actual thread code"""
        self._log.debug('Starting %s ' % self.name)
        #self._log.debug('ServerConnection: Trying to connect to server at port %s' % \
        #                        str(self._svr_port))
                         
        self._sock_h = sock_utils.connect_to_server(self._log,
                                    self._host,
                                    self._svr_port,
                                    exit_callback=self._my_exit_callback,
                                    data_type='stream')
        if self._sock_h is None:
            self._log.debug('ServerConnection: could not connect to server')
        else:
            self._log.debug('ServerConnection: Connected to server')
            self._connected = True
              
        self._started = True
        self._running = True
        if self._sock_h is not None:
            #self._log.debug('ServerConnection: connected to server')
            #self._log.debug('  server proxy port is %s' % str(self._sock_h.get_peer_port()))
            #self._log.debug('  local port is %s' % str(self._sock_h.get_sock_port()))
            self._pack_thread = proxy_utils.Packetize(self._sock_h,                                        
                                        self._pkt_write_q,
                                        self._svr_port,
                                        self._client_port,
                                        log,
                                        exit_callback=self._my_exit_callback)                  
            self._depack_thread = proxy_utils.Depacketize(self._sock_h,
                                        log,
                                        exit_callback=self._my_exit_callback)
            self._stop_event.wait()
            
        if not self._connected:
            # failed to connect to server
            self._pkt_write_q.put(DisconnectPkt(self._svr_port, self._client_port))
            self._log.debug('ServerConnection: sent DISCONNECT')                
            
        self._running = False
        self._log.debug('Stopping %s ' % self.name)
        self._stop_all_children()
        if self._exit_callback:
            self._exit_callback(self)
        self._log.debug('Exiting %s ' % self.name)
        
    def _stop_all_children(self):
        if self._depack_thread is not None:
            # if we didn't get a DISCONNECT from the other proxy, send one       
            if not self._depack_thread.got_disconnect_pkt():
                self._pkt_write_q.put(DisconnectPkt(self._svr_port, self._client_port))
                self._log.debug('ServerConnection: sent DISCONNECT')                
            self._depack_thread.stop()
            self._depack_thread = None
        if self._pack_thread is not None:
            self._pack_thread.stop()
            self._pack_thread = None
        if self._sock_h is not None:
            self._sock_h.stop()
            self._sock_h = None
        
    def _my_exit_callback(self, child):
        self._stop_event.set()
        
    def get_server_port(self):
        return self._svr_port
        
    def get_client_port(self):
        return self._client_port
        
    def send(self, pkt):
        """Send a packet to the server"""
        if self._depack_thread:
            self._depack_thread.send(pkt)

    def is_connected(self):
        """Return True if connected to the server"""
        return self._connected
        
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop the socket server thread and its child threads"""
        if self._running:
            self._stop_event.set()
            self.join()



class ModemSvrConnector(threading.Thread):
    """There is only one ModemSvrConnector.
    Keeps attempting to connect to the modem_svr when
    not connected.
    Connects to modem_svr when modem_svr opens a port.
    Creates single ModemSvrConnection after connecting to modem_svr.
    Resumes modem_svr connection attempts if ModemSvrConnections dies.
    Exits when stopped by parent.
    """
    def __init__(self, xfer_rec, log):
        """
            log = log object
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._stop_event = threading.Event()
        self._xfer_rec = xfer_rec
        self._log = log
        self.name = 'ModemSvrConnector thread'
        self._host = 'localhost'
        self._port = modem_svr_config.client_port
        self._modem_svr_sock_h = None
        self._modem_svr_conn = None
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)

    def run(self):
        """The actual thread code"""
        self._log.debug('Starting %s' % self.name)
        self._running = True
        self._started = True
        # Connect to the modem server
        #self._log.debug('Trying to connect to the modem server')
        while not self._stop_event.isSet():
            if self._modem_svr_conn is None:
                # try to connect to the modem server          
                self._modem_svr_sock_h = sock_utils.connect_to_server(self._log,
                                        self._host,
                                        self._port,
                                        exit_callback=self._my_exit_callback,
                                        data_type='packet')
                if self._modem_svr_sock_h is not None:
                    self._log.debug('Connected to the modem server')
                    self._modem_svr_conn = ModemSvrConnection(self._modem_svr_sock_h,
                                            self._xfer_rec, self._log)
            else:
                # is modem server connection still alive?
                if not self._modem_svr_conn.is_running():
                    self._log.debug('Disconnected from the modem server')
                    self._modem_svr_conn = None
            self._stop_event.wait(0.5)                                                     
            
        self._running = False
        #self._log.debug('Stopping %s' % self.name)
        if self._modem_svr_conn:
            self._modem_svr_conn.stop()
        self._log.debug('Exiting %s' % self.name)
        
    def _my_exit_callback(self, child):
        """Child threads call this when they die"""
        if self._modem_svr_conn:
            self._modem_svr_conn.stop()
            self._modem_svr_conn = None
        if self._modem_svr_sock_h:
            self._modem_svr_sock_h = None
        
    def is_running(self):
        return self._running
            
    def stop(self):
        """Stop this thread and its child threads"""
        if self._running:
            self._stop_event.set()
            self.join()
            
            
class XMLRPCThread(BasicXMLRPCThread):
    def __init__(self, host, port, xfer_rec, log):
        BasicXMLRPCThread.__init__(self, host, port, log)
        self._log = log
        self._xfer_rec = xfer_rec
        self._server.register_function(self.time_of_last_data_xfer)
           
    def time_of_last_data_xfer(self):
        """Return the time of the most recent non-ping
            data transfer
        """
        return self._xfer_rec.get_time()

        
class XferRec:
    """ Keeps track of the last time non-ping
        data was transferred
    """
    def __init__(self, log):
        self._lock = utils.Lock(log)
        self._time = time.time()
        
    def set_time(self, the_time):
        self._lock.acquire()
        self._time = the_time
        self._lock.release()
        
    def get_time(self):
        self._lock.acquire()
        the_time = self._time
        self._lock.release()
        return the_time
        
       
def _run_proxy(log):
    """
        Run the server proxy until terminated
        via KeyboardInterrupt or XMLRPC command
    """
    log.info('')
    log.info('****** Starting server proxy ******')
    
    xfer_rec = XferRec(log)
    
    try:
        modem_svr_connector = ModemSvrConnector(xfer_rec, log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
        
    try:
        xmlrpc_thread = XMLRPCThread('localhost',
                            svr_proxy_config.XMLRPC_port, xfer_rec, log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
        
    while True:
        try:
            utils.wait(0.5)
            if not modem_svr_connector.is_running():
                break
            if not xmlrpc_thread.is_running():
                log.error('XMLRPC server thread died unexpectedly')
                break
        except KeyboardInterrupt:
            if svr_proxy_config.accept_sigint:
                log.info('Got SIGINT (shutting down)')
                break
            else:
                log.info('Got SIGINT ignored)')
        except:
            # handle all unexpected application exceptions
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
            sys.exit(1)
                   
    modem_svr_connector.stop()
    xmlrpc_thread.stop()
    utils.wait_for_child_threads()
    log.info('****** Exiting server proxy ******')
    

if __name__ == '__main__':
    sys.setcheckinterval(global_config.check_interval)
    if svr_proxy_config.daemonize:
        utils.daemonize()
    log = logs.open(svr_proxy_config.log_name,
                    svr_proxy_config.log_dir,
                    svr_proxy_config.log_level,
                    file_max_bytes = svr_proxy_config.log_file_max_bytes,
                    num_backup_files = svr_proxy_config.log_files_backup_files)
    _run_proxy(log)

