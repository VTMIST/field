#!/usr/bin/env python

# Simple RPC Library

import sys
import threading
import Queue
import marshal
import logging

import sock_utils
import utils
import sock_utils
import logs
import global_config

"""
    RPC clients create an RPCServerProxy and use it
    to execute remote commands.
    RPC servers create an RPC server that is subclassed
    from BaseRPCServer.  See the module test code for
    a usage example.
"""


class RPCError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
    
    
class RPCServerProxy:
    def __init__(self, host, port, log, timeout=8.0):
        self._log = log
        self._timeout = timeout
        self._rpc_sock_h = sock_utils.connect_to_server(log, host, port)
        if self._rpc_sock_h is None:
            raise RPCError('Could not connect to RPC server')
            return
        utils.wait(1.0) # wait for server startup
        self._write_q = self._rpc_sock_h.get_write_q()
        self._read_q = self._rpc_sock_h.get_read_q()
        
    def call(self, *args):
        self._log.info('RPCServerProxy.call: args = %s' % repr(args))
        self._send_rpc_request(args)     
        resp = self._get_rpc_response()
        self._log.info('RPCServerProxy.call: resp = %s' % repr(resp))
        return(resp)
        
    def _send_rpc_request(self, args):
        # Send size and marshalled args to server
        ser_args = marshal.dumps(args)
        size = len(ser_args)
        size_msb = chr((size & 0xFF00) >> 8)
        size_lsb = chr(size & 0x00FF)
        self._write_q.put(''.join([size_msb, size_lsb, ser_args]))     
        
    def _get_rpc_response(self):
        # Get size and marshalled response from server
        resp = utils.q_get(self._read_q, get_timeout=self._timeout)
        if resp is None:
            self._log.error('RPCServerProxy._get_rpc_response: timed out waiting for start of response')
            return None
        if len(resp) < 2:
            self._log.error('RPCServerProxy._get_rpc_response: Did not get both size bytes')
            return None
        size = ord(resp[0]) * 256 + ord(resp[1])
        resp = resp[2:]
        while len(resp) < size:
            chunk = utils.q_get(self._read_q, get_timeout=self._timeout)
            if chunk is None:
               self._log.error('RPCServerProxy._get_rpc_response: timed out waiting for end of response')
               return None
            resp += chunk           
        return marshal.loads(resp)
        
    def close(self):
        if self._rpc_sock_h and self._rpc_sock_h.is_running():
            self._rpc_sock_h.stop()        
             

class RPCConnectionThread(threading.Thread):
    """Handle an RPC connection with a single client"""
    def __init__(self, sock_h, base_rpc_server, log, exit_callback):
        threading.Thread.__init__(self)
        self._sock_h = sock_h
        self._base_rpc_server = base_rpc_server
        self._log = log
        self._exit_callback = exit_callback
        self._read_q = sock_h.get_read_q()
        self._write_q = sock_h.get_write_q()
        self._stop_event = threading.Event()
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
         
    def run(self):
        """The actual thread code"""
        #self._log.info('Starting %s ' % self.name)
        self._running = True
        self._started = True
        
        while not self._stop_event.isSet():
            if not self._sock_h.is_running():
                self._stop_event.set()
                continue
            cmd = self._get_rpc_request(timeout=0.5)
            if cmd:
                self._log.info('RPCConnectionThread.run: Executing %s' % cmd)
                resp = eval(cmd)
                self._log.info('RPCConnectionThread.run: %s returned %s' % (cmd, resp))
                self._send_rpc_response(resp)
                
        self._running = False
        if self._sock_h.is_running():
            self._sock_h.stop()
        self._exit_callback(self)
        #self._log.info('Exiting %s ' % self.name)
        
    def _get_rpc_request(self, timeout=None):
        # Get size and marshalled request from server
        req = utils.q_get(self._read_q, get_timeout=timeout)
        if req is None:
            return None
        if len(req) < 2:
            self._log.error('RPCConnectionThread._get_rpc_request: Did not get both size bytes')
            return None
        size = ord(req[0]) * 256 + ord(req[1])
        req = req[2:]
        while len(req) < size:
            chunk = utils.q_get(self._read_q, get_timeout=self._timeout)
            if chunk is None:
                self._log.error('RPCConnectionThread._get_rpc_request: timed out waiting for end of request')
                return None
            req += chunk
        args = marshal.loads(req)        
        self._log.info('RPCConnectionThread._get_rpc_request: args = %s' % repr(args))
        cmd_parts = []
        for i, arg in enumerate(args):
            if i == 0:
                cmd_parts.append(''.join(['self._base_rpc_server.', arg, '(']))
            else:
                if i != 1:
                    cmd_parts.append(', ')
                cmd_parts.append(arg)
        cmd_parts.append(')')
        cmd = ''.join(cmd_parts)
        self._log.info('RPCConnectionThread._get_rpc_request: returning command: %s' % cmd)
        return cmd   
    
    def _send_rpc_response(self, response):
        # Send size and marshalled response to server
        ser_resp = marshal.dumps(response)
        size = len(ser_resp)
        size_msb = chr((size & 0xFF00) >> 8)
        size_lsb = chr(size & 0x00FF)
        self._write_q.put(''.join([size_msb, size_lsb, ser_resp]))      

    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread"""
        if self._running:
            self._stop_event.set()
            self.join()
        

class BaseRPCServer(threading.Thread):
    """ Connect to one RPC client at at time and handle RPC requests """
    def __init__(self, host, port, log, exit_callback=None):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._log = log
        self._exit_callback = exit_callback
        self._host = host
        self._port = port
        self._children = []
        self._stop_event = threading.Event()
        self.name = 'BaseRPCServer thread'
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
                                        
    def run(self):
        """The actual thread code"""
        #self._log.info('Starting %s ' % self.name)
        self._running = True
        self._started = True
        
        while not self._stop_event.isSet():
            # Wait for client to connect
            #self._log.info('BaseRPCServer.run: waiting for client to connect')
            sock, addr, connected_flag = \
                        sock_utils.connect_to_client(self._log,
                                                    self._host,
                                                    self._port,
                                                    self._stop_event)
            #self._log.info('BaseRPCServer.run: returned from sock_utils.connect_to_client')
            if self._stop_event.isSet():
                continue
            if len(self._children) > 10:
                self._log.error('BaseRPCServer: more than 10 clients, connection refused')
                sock.close()
                continue
            if connected_flag:
                #self._log.info('BaseRPCServer: connected_flag is true')
                self._rpc_sock_h = sock_utils.SockHandler(sock,
                                     self._log,
                                     log_all_data=False,
                                     read_data_q=Queue.Queue(),
                                     write_data_q=Queue.Queue(),
                                     hand_exit_callback=self._my_exit_callback,
                                     type='stream')
                #self._log.info('BaseRPCServer.run: returned from sock_utils.SockHandler ')
                self._log.info('BaseRPCServer: connected to client')
                self._log.info('  client port is %s' % str(self._rpc_sock_h.get_peer_port()))
                self._log.info('  local port is %s' % str(self._rpc_sock_h.get_sock_port()))
                # Create a RPCConnectionThread to handle this client
                self._children.append(RPCConnectionThread(self._rpc_sock_h,
                                        self, self._log, self._my_exit_callback))              
            
        self._running = False
        #self._log.info('Stopping %s ' % self.name)
        self._stop_children()
        if self._exit_callback:
            self._exit_callback(self)
        #self._log.info('Exiting %s ' % self.name)
        
    def _stop_children(self):
        for child in self._children:
            if child.is_running():
                child.stop()            
            
    def _my_exit_callback(self, child):
        """Child threads call this when they die"""
        utils.safe_remove(self._children, child)
        
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread and its child threads"""
        if self._running:
            self._stop_event.set()
            # force connect_to_client to return
            sock_utils.dummy_connection(self._host, self._port)
            self.join()
            
            
class TestRPCServer(BaseRPCServer):
    def __init__(self, host, port, log):
        BaseRPCServer.__init__(self, host, port, log)
        
    def test(self):
        return 'Passed the test'            
   

def _test_this_module(log):
    rpc_svr_port = 44432    # just a random number
    # Start the RPC server
    rpc_svr_thread = TestRPCServer('localhost', rpc_svr_port, log)
    
    # Create a RPC server proxy
    try:
        svr_proxy = RPCServerProxy('localhost', rpc_svr_port, log)
    except RPCError, e:
        print e
        rpc_svr_thread.stop()
        return
        
    # Send RPC command
    print 'Sending test RPC command'
    resp = svr_proxy.call('test')
    if resp:
        print 'Response from test RPC call: %s' % resp
    else:
        print 'No response from test RPC call'
    svr_proxy.close()
    rpc_svr_thread.stop()
    
    
if __name__ == '__main__':
    print 'Testing RPC Library'
    log = logs.open('rpc_lib_test',
                    global_config.field_log_dir,
                    logging.DEBUG,
                    file_max_bytes = 50000,
                    num_backup_files = 1)
    _test_this_module(log)
    utils.wait_for_child_threads()
    


#====================  move to utils.py  ==================================
def sock_rpc_set_power_state(device, state, server_proxy, hw_mgr_lock, log=None):
    """Turn a device on or off using hw_mgr.
    state = 'on' | 'off'
    Return the server proxy if successful,
      None if not successful.
    """ 
    hw_mgr_lock.acquire()
    attempt = 1
    while (attempt <= 2):
        if server_proxy is None:
            if log:
                log.info('utils.sock_rpc_set_power_state: server_proxy is None, creating new one')
            server_proxy = sock_rpc_get_server_proxy(hw_mgr_config.sock_rpc_svr_port, log)
            if server_proxy is None:
                if log:
                    log.info('utils.sock_rpc_set_power_state: server_proxy creation failed')
                break
        try:
            resp = server_proxy.call('set_power', ''.join(["'", device, "'"]), ''.join(["'", state, "'"]))
        except Exception, e:
            if log:
                log.error('utils.sock_rpc_set_power_state exception: %s' % e)
            server_proxy.close()
            server_proxy = None
            attempt += 1
            continue    # retry in case bad server_proxy was passed in
        if resp != 'OK':
            break
        hw_mgr_lock.release()
        return server_proxy
    hw_mgr_lock.release()
    return None
    

#====================  move to utils.py  ==================================
def sock_rpc_get_hw_status(value_name, server_proxy, hw_mgr_lock, log=None):
    """Get a status value from hw_mgr
    Return [status_value, hw_mgr_server]
    Return [None, None] if unsucessful.
    """
    hw_mgr_lock.acquire()
    attempt = 1
    while (attempt <= 2):
        if server_proxy is None:
            if log:
                log.info('utils.sock_rpc_get_hw_status: server_proxy is None, creating new one')
            server_proxy = sock_rpc_get_server_proxy(hw_mgr_config.sock_rpc_svr_port, log)
            if server_proxy is None:
                if log:
                    log.info('utils.sock_rpc_get_hw_status: server_proxy creation failed')
                break
        try:
            status_value = server_proxy.call('get_status', ''.join(["'", value_name, "'"]))
        except Exception, e:
            if log:
                log.error('utils.sock_rpc_get_hw_status exception:  %s' % e)
            server_proxy.close()
            server_proxy = None
            attempt += 1
            continue    # retry in case bad hw_mgr_server was passed in
        if status_value == 'failed':
            break
        hw_mgr_lock.release()
        return [status_value, server_proxy]
    hw_mgr_lock.release()
    return [None, None]


#====================  move to utils.py  ==================================
def sock_rpc_get_full_hw_status(server_proxy, hw_mgr_lock, log):
    """Get the entire status dictionary from hw_mgr
    Return [status_dict, hw_mgr_server]
    Return [None, None] if unsucessful.
    """
    hw_mgr_lock.acquire()
    attempt = 1
    while (attempt <= 2):
        if server_proxy is None:
            server_proxy = sock_rpc_get_server_proxy(hw_mgr_config.sock_rpc_svr_port, log)
            if server_proxy is None:
                hw_mgr_lock.release()
                return [None, None]
        try:
            status_dict = server_proxy.call('get_full_status')
        except Exception, e:
            log.error('utils.sock_rpc_get_full_hw_status exception:  %s' % e)
            server_proxy.close()
            server_proxy = None
            attempt += 1
            continue    # retry in case bad hw_mgr_server was passed in
        hw_mgr_lock.release()
        return [status_dict, server_proxy]
    hw_mgr_lock.release()
    return [None, None]


#====================  move to utils.py  ==================================
def sock_rpc_get_server_proxy(svr_port, log=None):
    """Create a socket server proxy for a remote server.
        Return the server proxy or None.
    """
    try:
        server_proxy = sock_rpc.RPCServerProxy('localhost', svr_port, log)
    except Exception, e:
        if log:
            log.error('utils.get_sock_rpc_server_proxy exception: %s' % e)
        return None
    return server_proxy

    

