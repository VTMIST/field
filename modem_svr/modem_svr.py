#! /usr/bin/python

# Modem Server
# 
# Provides a socket interface to the Iridium RUDICS modem

import sys
import threading
from datetime       import datetime,timedelta
import time
import logging
import socket
import Queue

import utils
import logs
import global_config
import modem_svr_config
import sock_utils
from RudicsModem    import RudicsModem
from RudicsModemSim import RudicsModemSim
from BasicXMLRPCThread import BasicXMLRPCThread
from ProxyPkt import ProxyPkt


class ModemReadThread(threading.Thread):
    """Read data from the modem, write it to a queue.
    Exit if timed out waiting for data.
    """
    def __init__(self,
                modem,
                data_q,
                log):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._log = log
        self._stop_event = threading.Event()
        self.name = 'ModemReadThread'
        self._modem = modem
        self._data_q = data_q
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
        rx_timer = time.time()
        
        while not self._stop_event.isSet():
            if time.time() > (rx_timer + modem_svr_config.rx_data_timeout):
                self._stop_event.set()
                self._log.info('ModemReadThread: Timed out, exiting')
                continue
            data = self._modem.read()
            while data:
                rx_timer = time.time()
                #self._log.debug('ModemReadThread received %s bytes:' % str(len(data)))
                #self._log.debug('ModemReadThread data to %s' % repr(self._data_q))
                self._data_q.put(data[:])
                data = self._modem.read()
            self._stop_event.wait(0.1)
            
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        self._log.debug('Exiting %s ' % self.name)
        
    def is_running(self):
        return self._running

    def stop(self):
        if self._running:
            self._stop_event.set()
            self.join()

   
class ModemWriteThread(threading.Thread):
    """Read data from a queue, write it to the modem.
        Exit only when stopped by parent
    """
    def __init__(self,
                modem,
                write_q,
                log):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._log = log
        self._stop_event = threading.Event()
        self.name = 'ModemWriteThread'
        self._modem = modem
        self._data_q = write_q
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
            data = utils.q_get(self._data_q, get_timeout=0.5)
            if data:
                #self._log.debug('ModemWriteThread sent a pkt')
                self._modem.write(data)
        
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        self._log.debug('Exiting %s ' % self.name)
        
    def is_running(self):
        return self._running

    def stop(self):
        if self._running:
            self._stop_event.set()
            # force thread code to run
            self._data_q.put('This wakes up the modem write thread')
            self.join()


class RUDICSSvrProxyConnection(threading.Thread):
    """Handle a single svr_proxy-modem connection.
    Creates ModemReadThread and ModemWriteThread.
    Exits if svr_proxy connection dies or the
    ModemReadThread dies.
    """
    def __init__(self, client_sock, modem, log):
        """
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._modem = modem
        self._client_sock = client_sock
        self._log = log
        self._stop_event = threading.Event()
        self.name = 'RUDICSSvrProxyConnection thread'
        self._read_thread = None
        self._write_thread = None
        self._client_sock_h = None        
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

        self._inbound_data_q = Queue.Queue()  # inbound from modem
        self._outbound_data_q = Queue.Queue() # outbound to modem       
        self._client_sock_h = sock_utils.SockHandler(self._client_sock,
                                    self._log,
                                    read_data_q=self._outbound_data_q,
                                    write_data_q=self._inbound_data_q,
                                    hand_exit_callback=self._my_exit_callback,
                                    type='packet')
        self._modem.flushBoth()           
        self._read_thread = ModemReadThread(self._modem, self._inbound_data_q, self._log)
        self._write_thread = ModemWriteThread(self._modem, self._outbound_data_q, self._log)
        #self._log.debug('RUDICSSvrProxyConnection: sock read q is %s' % repr(client_sock_h.get_read_q()))        
        #self._log.debug('RUDICSSvrProxyConnection: sock write q is %s' % repr(client_sock_h.get_write_q()))        
        
        while not self._stop_event.isSet():
            if not self._read_thread.is_running():
                break
            self._stop_event.wait(0.5)
            
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        if self._read_thread:
            self._read_thread.stop()
        if self._write_thread:
            self._write_thread.stop()
        if self._client_sock_h:
            self._client_sock_h.stop()
        self._log.debug('Exiting %s ' % self.name)
        
    def _my_exit_callback(self, child):
        self._stop_event.set()
        
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop the this thread and its child threads"""
        if self._running:
            self._stop_event.set()
            self.join()
    

class SvrProxyConnector(threading.Thread):
    """ Open a server port so the svr_proxy can make
    a socket connection.
    Makes one connection and then waits to be stopped.
    """
    def __init__(self,
                log,
                exit_callback=None):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._log = log
        self._host = 'localhost'
        self._port = modem_svr_config.client_port
        self._exit_callback = exit_callback
        self.sock = None
        self._stop_event = threading.Event()
        self.name = 'SvrProxyConnector thread'
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
        connected = False
        
        while not self._stop_event.isSet():
            if connected:
                break
            # The following blocks until a client connects
            self.sock, addr, connected_flag = sock_utils.connect_to_client(self._log,
                                self._host,
                                self._port,
                                self._stop_event)
        
        while not self._stop_event.isSet():
            self._stop_event.wait(0.5)
                                                                    
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        if self._exit_callback:
            self._exit_callback(self)
        self._log.debug('Exiting %s ' % self.name)
            
    def _my_exit_callback(self, child):
        """Called by child threads when they exit"""
        self.stop()
        
    def is_running(self):
        return self._running

    def stop(self):
        if self._running:
            self._stop_event.set()
            # force connect_to_client to return
            sock_utils.dummy_connection(self._host, self._port)
            self.join()


class RUDICSSvrProxyConnector(threading.Thread):
    """Keeps trying to connect the svr_proxy
        to the RUDICS server
	"""
    def __init__(self,
                log,
                xmlrpc_thread,
                exit_callback=None):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._log = log
        xmlrpc_thread.set_rudics_conn_thread(self)
        self._modem = None
        self._svr_proxy_connector = None
        self._rudics_svr_proxy_connection = None
        self._stop_event = threading.Event()
        self.name = 'RUDICSSvrProxyConnector thread'
        self._exit_callback = exit_callback
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
        state = 'start'
        
        while True:
            self._stop_event.wait(0.5)
            if self._stop_event.isSet():
                break
            modem_connected_to_rudics = self._modem and self._modem.isConnected()
            fully_connected = self._rudics_svr_proxy_connection \
                                        and self._rudics_svr_proxy_connection.is_running() \
                                        and modem_connected_to_rudics
        
            if state == 'start':
                if modem_connected_to_rudics:
                    state = 'connect_to_svr_proxy'
                    continue
                if not self._make_rudics_connection():
                    self._stop_event.wait(5.0)
                continue
                
            if state == 'connect_to_svr_proxy':
                if not modem_connected_to_rudics:
                    self._kill_connections()
                    state = 'start'
                    continue
                if not self._svr_proxy_connector:
                    self._svr_proxy_connector = SvrProxyConnector(log)
                if self._svr_proxy_connector.sock:
                    sock = self._svr_proxy_connector.sock
                    self._rudics_svr_proxy_connection = \
                                RUDICSSvrProxyConnection(sock, self._modem, self._log)
                    state = 'connection_established'
                continue
                
            if state == 'connection_established':
                if not fully_connected:
                    self._kill_connections()
                    state = 'start'
           
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        self._kill_connections()
        self._log.debug('Exiting %s ' % self.name)
        
    def _make_rudics_connection(self):
        """ Return True if successful """
        self._modem = RudicsModem(self._log)
        connected = self._modem.dialup()
        if not connected:
            self._modem.hangup()
            self._modem = None
        return connected
        
    def _kill_connections(self):
        if self._svr_proxy_connector:
            self._svr_proxy_connector.stop()
            self._svr_proxy_connector = None            
        if self._rudics_svr_proxy_connection:
            self._rudics_svr_proxy_connection.stop()
            self._rudics_svr_proxy_connection = None
        if self._modem:
            self._modem.hangup()
            self._modem = None
                  
            
    def get_iccid(self):
        """Return the modem SIM ICCID"""
        if self._modem is None:
            return ''
        else:
            return self._modem.iccid()
        
    def _my_exit_callback(self, child):
        pass
        
    def is_running(self):
        return self._running

    def stop(self):
        if self._running:
            self._stop_event.set()
            self.join()

            
                        
class XMLRPCThread(BasicXMLRPCThread):
    """An extended BasicXMLRPCThread"""
    def __init__(self, host, port, log):
        BasicXMLRPCThread.__init__(self, host, port, log)
        self._server.register_function(self.get_iccid)

    def get_iccid(self):
        """Return the SIM ICCID from the modem"""
        self._log.debug('XMLRPC: got get_iccid command')
        # "try" in case rudics_conn_thread doesn't exist yet
        try:
            return self._rudics_conn_thread.get_iccid()
        except Exception:
            return ''       
        
    def set_rudics_conn_thread(self, rudics_conn_thread):
        """Set rudics_conn_thread so we can get the modem SIM ICCID"""
        self._rudics_conn_thread = rudics_conn_thread
            
    
def run_server(log, use_modem):
    """
        Run the modem server until terminated
        via KeyboardInterrupt or XMLRPC command
    """
    log.info('')
    log.info('****** Starting modem server ******')
    
    try:
        xmlrpc_thread = XMLRPCThread('localhost',
                        modem_svr_config.XMLRPC_port,
                        log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
        
    try:
        rudics_conn = RUDICSSvrProxyConnector(log, xmlrpc_thread)   
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
        
    while True:
        try:
            utils.wait(0.5)
            if not rudics_conn.is_running():
                break
            if not xmlrpc_thread.is_running():
                log.error('XMLRPC thread died unexpectedly')
                break
        except KeyboardInterrupt:
            if modem_svr_config.accept_sigint:
                log.info('Got SIGINT (shutting down)')
                break
            else:
                log.info('Got SIGINT (ignored)')
        except:
            # handle all unexpected application exceptions
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
                   
    rudics_conn.stop()
    xmlrpc_thread.stop()
    utils.wait_for_child_threads()
    log.info('****** Exiting modem server ******')


if __name__ == '__main__':
    sys.setcheckinterval(global_config.check_interval)
    if modem_svr_config.daemonize:
        utils.daemonize()
    log = logs.open(modem_svr_config.log_name,
                    modem_svr_config.log_dir,
                    modem_svr_config.log_level,
                    file_max_bytes = modem_svr_config.log_file_max_bytes,
                    num_backup_files = modem_svr_config.log_files_backup_files)
    run_server(log, global_config.use_modem)
        
        
        
        
        
        
        
        
        
        
        
