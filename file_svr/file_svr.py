#! /usr/bin/python

# File Server

import sys
import threading
import zlib
import Queue

import utils
import logs
import sock_utils
import file_svr_config
import global_config


class ClientConnection(threading.Thread):
    """Handle a single file server client"""
    def __init__(self, sock_h, log, exit_callback=None):
        threading.Thread.__init__(self)
        self._sock_h = sock_h
        self._log = log
        self._exit_callback = exit_callback
        self.setDaemon(False)
        self._stop_event = threading.Event()
        self.name = 'ClientConnection thread'
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
        
        self._manage_file_xfer(self._sock_h)
            
        self._running = False       
        if self._sock_h != None:
            self._sock_h.stop()       
        if self._exit_callback:
            self._exit_callback(self)
        #self._log.debug('Exiting %s' % self.name)
        
    def _manage_file_xfer(self, sock):
        while not self._shut_down_is_pending():
            cmd_line = self._readline(sock)
            if cmd_line != None:
                self._execute_cmd(sock, cmd_line)
        
    def _execute_cmd(self, sock, cmd_line):
        """ Execute the command in cmd_line """
        fields = cmd_line.split(',')
        if len(fields) < 1:
            self._handle_cmd_error(sock, cmd_line)
            return
        if fields[0] == 'SEND_FILE_CHUNK':
            self._execute_send_file_chunk_cmd(sock, cmd_line)
        else:
            self._handle_cmd_error(sock, cmd_line)
                        
    def _execute_send_file_chunk_cmd(self, sock, cmd_line):
        """ The send file chunk command looks like this:
            "SEND_FILE_CHUNK,path,offset,length,crc,\n"
                All fields are printable text
            The server responds with:
            data_length,crc,<data>
                data_length and crc are printable text
                data is binary            
        """
        fields = cmd_line.split(',')
        if len(fields) < 5:
            self._handle_cmd_error(sock, cmd_line)
            return
        cmd = fields[0]
        path = fields[1]
        offset_str = fields[2]
        length_str = fields[3]
        crc = fields[4]
        if not self._crc_is_ok(cmd, path, offset_str, length_str, crc):
            self._log.error('CRC error in client command, command ignored')
            return
        try:
            offset = int(offset_str)
            length = int(length_str)
        except ValueError:
            self._handle_cmd_error(sock, cmd_line)
            return
        try:
            f = open(path, 'rb')
        except IOError:
            self._handle_error(sock, 'Cannot open %s' % path)
            return
            
        f.seek(offset)   
        data = f.read(length)
        data_len = len(data)
        crc = zlib.adler32(data)
        self._send_hdr(sock, data_len, crc)
        if (data_len > 0):
            self._sock_h.get_write_q().put(data)      
        
    def _readline(self, sock):
        """ Read a line ending with \n from sock.
            Return received line.
            Return None if shutdown is pending.
        """   
        timeout_secs = 2
        max_rx_buf_len = 200
        rx_buf = ''
        while not self._shut_down_is_pending():
            rx_bytes = utils.q_get(self._sock_h.get_read_q(), timeout_secs)
            if rx_bytes is None:
                continue    # timed out
            rx_buf += rx_bytes
            if rx_buf.endswith('\n'):
                return rx_buf
            if len(rx_buf) > max_rx_buf_len:
                self._log.error('Flushing _readline.rx_buf. Received "%s"' % rx_buf)
                rx_buf = ''
        return None
        
    def _crc_is_ok(self, cmd, path, offset, length, crc):
        req = ','.join([cmd, path, offset, length])
        return str(zlib.adler32(req)) == crc
        
    def _handle_cmd_error(self, sock, cmd_line):
        err_msg = 'Invalid command: "%s"' % cmd_line
        self._handle_error(sock, err_msg)
        
    def _handle_error(self, sock, err_msg):    
        self._log.error(err_msg)
        self._send_hdr(sock, -len(err_msg), zlib.adler32(err_msg))
        self._sock_h.get_write_q().put(err_msg)
    
    def _send_hdr(self, sock, length, crc):
        hdr = ''.join([str(length), ',', str(crc), ',' ]) 
        self._sock_h.get_write_q().put(hdr)
        
    def _shut_down_is_pending(self):
        if self._stop_event.isSet():
            return True
        if not self._sock_h.is_running():
            self._log.debug('Client connection broken')
            self._stop_event.set()
            return True
                           
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread """
        if self._running:
            self._stop_event.set()
            self.join()
        
        
class ClientConnector(threading.Thread):
    """Handle client connection requests"""
    def __init__(self, host, log, exit_callback=None):
        threading.Thread.__init__(self)
        self._log = log
        self._exit_callback = exit_callback
        self.setDaemon(False)
        self._host = host
        self._port = global_config.file_server_port
        self._children = []
        self._children_lock = threading.Lock()
        self._stop_event = threading.Event()
        self.name = '%s ClientConnector thread'
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
            sock, addr, connected_flag = \
                    sock_utils.connect_to_client(self._log,
                                                self._host,
                                                self._port,
                                                self._stop_event)                    
            if self._stop_event.isSet():
                continue
            sock_handler = sock_utils.SockHandler(sock,
                                     self._log,
                                     log_all_data=False,
                                     read_data_q=Queue.Queue(),
                                     write_data_q=Queue.Queue(),
                                     hand_exit_callback=None,
                                     type='stream')
            self._children_lock.acquire()
            self._children.append(ClientConnection(sock_handler, self._log,
                                                exit_callback=self._my_exit_callback))
            self._children_lock.release()               
                                                                
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        for ch in self._children:
            ch.stop()
        if self._exit_callback:
            self._exit_callback(self)
        #self._log.debug('Exiting %s' % self.name)
        
    def _my_exit_callback(self, child):
        """Child threads call this when they die"""
        if self._running:
            self._children_lock.acquire()       
            self._children.remove(child)
            self._children_lock.release()       
        
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread and its child threads"""
        #self._log.debug('ClientConnector: entering stop()')
        if self._running:
            self._stop_event.set()
            # Issue dummy connection request so connect_to_client() returns
            sock_utils.dummy_connection(self._host, self._port)
            self.join()
            
                
def _run_svr(log):
    """
        Run the file server until terminated
    """
    log.info('')
    log.info('****** Starting File Server ******')
        
    try:
        lan_client_connector = ClientConnector(global_config.our_lan_ip_addr, log)
        rudics_client_connector = ClientConnector('localhost', log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
                      
    while True:
        try:
            utils.wait(1)
            if not lan_client_connector.is_running():
                log.error('lan_client_connector died unexpectedly')
                break
            if not rudics_client_connector.is_running():
                log.error('rudics_client_connector died unexpectedly')
                break
            
        except KeyboardInterrupt:
            if file_svr_config.accept_sigint:
                log.info('Got SIGINT, shutting down')
                break
            else:
                log.info('Got SIGINT, ignored')
        except:
            # handle all unexpected application exceptions
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
            sys.exit(1)
                   
    lan_client_connector.stop()
    rudics_client_connector.stop()
    utils.wait_for_child_threads()
    log.info('****** Exiting File Server ******')
    
    
if __name__ == '__main__':
    sys.setcheckinterval(global_config.check_interval)
    if file_svr_config.daemonize:
        utils.daemonize()
    log = logs.open(file_svr_config.log_name,
                    file_svr_config.log_dir,
                    file_svr_config.log_level,
                    file_max_bytes = file_svr_config.log_file_max_bytes,
                    num_backup_files = file_svr_config.log_files_backup_files)
    utils.make_dirs(file_svr_config.temp_dir, log)
    _run_svr(log)

