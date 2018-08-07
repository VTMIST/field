#! /usr/bin/python

# CASES Dual Frequency GPS Receiver Manager

import sys
import threading
import Queue
import serial
from datetime       import datetime,timedelta
import time
import xmlrpclib
import os

import utils
import sock_utils
import logs
import usb_mgr_config
import cases_mgr_config
import global_config
from BasicXMLRPCThread import BasicXMLRPCThread
from SockConsole import SockConsole
import CASESPkt

class SaveFileThread(threading.Thread):
    """Copy a data file to USB flash drive. Delete original data file after copying. """
    def __init__(self, data_file_path, compress, log, exit_callback=None):
        """
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._data_file_path = data_file_path
        self._compress = compress
        self._log = log
        self.name = 'SaveFileThread'
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
        
        try:
            xmlrpc_svr = xmlrpclib.Server(usb_mgr_config.XMLRPC_URL)
        except Exception:
            self._log.error('Could not connect to usb_mgr XML-RPC server')
            return
        try:
            result = xmlrpc_svr.store_file(cases_mgr_config.proc_mnemonic,
                                            self._data_file_path,
                                            self._compress)
        except Exception, e:
            self._log.error('Could not write file %s to USB flash drive: %s' % \
                             (self._data_file_path, e))
            return
        self._log.info('Stored %s on USB flash drive' % self._data_file_path)
        utils.delete_file(self._data_file_path, self._log)
            
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        self._log.debug('Exiting %s ' % self.name)
        
    
class RxDataThread(threading.Thread):
    """ Receive and store instrument data """
    def __init__(self, log, serial_port, exit_callback=None):
        """
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self.rx_data_enabled = True
        self._log = log
        self._port = serial_port
        self._exit_callback = exit_callback
        self._stop_event = threading.Event()
        self.name = 'RxDataThread'
        self._serial_port_open = False
        self._pkt_state = 1
        self._data_file_state = 1
        self._data_file = None
        self._data_file_path = None
        self._time_epoch = datetime(1970, 1, 1, 0, 0, 0)
        self._data_tx_delay = timedelta(seconds=1)
        self._rx_time_gap = 0
        self._last_rx_time = time.time()
        self._data_bytes_to_receive = 0
        self._lost_sync = False
        self.data_production_lock = threading.Lock()
        self.data_production = 0
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
            bytes_avail = self._port.inWaiting()
            if bytes_avail > 0:
                if self.rx_data_enabled:
                    rx_time = time.time()
                    self._rx_time_gap = rx_time - self._last_rx_time
                    self._last_rx_time = rx_time
                    #self._log.info('RxDataThread.run: received %s bytes' % str(bytes_avail))
                    self._process_rx_bytes(self._port.read(bytes_avail))
                else:
                    # Ignore CASE data.  This is done when uploading
                    #  files to the CASES SBC to reduce system load.
                    self._port.read(bytes_avail)
            utils.wait(0.01)

        self._running = False
        self._close_data_file()
        if self._data_file_path is not None:
            self._close_data_file()
            save_file_thread = SaveFileThread(self._data_file_path, True, self._log)
            save_file_thread.join()
        #self._log.debug('Stopping %s ' % self.name)
        if self._exit_callback:
            self._exit_callback(self)
        self._log.debug('Exiting %s ' % self.name)
        
    def _process_rx_bytes(self, rx_buf):
        """Process a string of rx bytes"""
        # If there is a significant time gap between
        #   bytes, go back to byte-by-byte processing
        #   to recover packet sync.
        if self._rx_time_gap > cases_mgr_config.max_interbyte_gap:
            self._data_bytes_to_receive = 0

        buf_len = len(rx_buf)
        if buf_len > 4094:
            self._log.debug('Got %s byte chunk' % str(buf_len))
        if self._lost_sync:
            self._log.error('Lost packet sync')
            self._lost_sync = False
                        
        # Report Batch messages can be very large and
        #  data rates can be high.
        # Store large chunks of packet data here to avoid
        #  inefficiently processing individual bytes
        #  in _process_rx_byte.
        while len(rx_buf) > 0:
            if self._data_bytes_to_receive > 1:
                max_chunk_size = self._data_bytes_to_receive - 1
                data_chunk = rx_buf[:max_chunk_size]
                self._pkt_data_chunks.append(data_chunk)
                data_chunk_len = len(data_chunk)
                rx_buf = rx_buf[data_chunk_len:]
                self._data_bytes_to_receive -= data_chunk_len
            # Process individual bytes until receiving pkt data again
            i = 0
            for rx_byte in rx_buf:
                self._process_rx_byte(rx_byte)
                i += 1
                if self._data_bytes_to_receive > 1:
                    break
            rx_buf = rx_buf[i:]          
            
    def _process_rx_byte(self, rx_byte):
        """Process a byte received from the instrument"""
        # If there is a long time gap between bytes,
        # either we are between packets or something is wrong.
        # Either way we can safely change the state to recover packet sync.
        
        if self._rx_time_gap > cases_mgr_config.max_interbyte_gap:
            #self._log.debug('rx_time_gap: %s' % str(self._rx_time_gap))
            self._rx_time_gap = 0
            self._pkt_state = 1

        # Get the packet sync code
        if self._pkt_state == 1:
            if rx_byte == CASESPkt.CASESPkt.SYNC_BYTE_0_VALUE:
                self._data_bytes_to_receive = 0
                self._pkt_time_stamp = datetime.now()
                self._pkt_state += 1
            else:
                self._lost_sync = True
        elif self._pkt_state == 2:
            if rx_byte == CASESPkt.CASESPkt.SYNC_BYTE_1_VALUE:
                self._pkt_state += 1
            else:
                self._lost_sync = True
                self._pkt_state = 1
        elif self._pkt_state == 3:
            if rx_byte == CASESPkt.CASESPkt.SYNC_BYTE_2_VALUE:
                self._pkt_state += 1
            else:
                self._lost_sync = True
                self._pkt_state = 1
        elif self._pkt_state == 4:
            if rx_byte == CASESPkt.CASESPkt.SYNC_BYTE_3_VALUE:
                #self._log.debug('Got sync code')
                self._pkt_state += 1
            else:
                self._lost_sync = True
                self._pkt_state = 1
        # Get the packet length
        elif self._pkt_state == 5:
            self._pkt_len = ord(rx_byte) << 24
            self._pkt_state += 1
        elif self._pkt_state == 6:
            self._pkt_len += ord(rx_byte) << 16
            self._pkt_state += 1
        elif self._pkt_state == 7:
            self._pkt_len += ord(rx_byte) << 8
            self._pkt_state += 1
        elif self._pkt_state == 8:
            self._pkt_len += ord(rx_byte)
            #self._log.debug('Got pkt length')
            self._pkt_state += 1
        # Get the packet type
        elif self._pkt_state == 9:
            self._pkt_type = ord(rx_byte)
            #self._log.debug('Got pkt type')
            # Verify pkt length and type
            if not CASESPkt.type_and_length_are_valid(self._pkt_type, self._pkt_len):
                self._log.error('Got bad pkt type or length. Pkt type: %d, Pkt len: %d' % \
                                (self._pkt_type, self._pkt_len))
                self._pkt_state = 1
                return
            self._data_bytes_to_receive = self._pkt_len - 1
            self._pkt_data_chunks = []
            if self._data_bytes_to_receive > 0:
                self._pkt_state = 10
            else:
                self._pkt_state = 11
        # Receive the the packet data bytes blindly.
        # Note that big chunks of data are stored in _process_rx_bytes
        # The first few bytes and last few bytes of packet data are
        #  processed here.
        elif self._pkt_state == 10:
            self._pkt_data_chunks.append(rx_byte)
            self._data_bytes_to_receive -= 1
            if self._data_bytes_to_receive == 0:
                self._pkt_state += 1
        # Build the pkt, receive and check the packet checksum
        elif self._pkt_state == 11:
            pkt_data = ''.join(self._pkt_data_chunks)
            self._pkt = CASESPkt.CASESPkt()
            self._pkt.build(self._pkt_type, pkt_data)
            self._cksum_msb = rx_byte
            self._pkt_state += 1
        elif self._pkt_state == 12:
            received_cksum = (ord(self._cksum_msb) << 8) + ord(rx_byte)
            if self._pkt.get_cksum() != received_cksum:
                self._log.error('Packet checksum error')
            else:
                self._log.info('Got %s (%s bytes)' % \
                        (self._pkt.type_str(), self._pkt.get_pkt_len()))
                #self._log.debug(''.join(['\n', self._pkt.str()]))
                self._process_rx_pkt(self._pkt, self._pkt_time_stamp)                       
            self._pkt_state = 1
        else:
            self._log.error('RxDataThread._process_rx_byte: unknown state value')
            self._pkt_state = 1

    def _process_rx_pkt(self, rx_pkt, pkt_time_stamp):
        """Process a pkt from the instrument"""
        if self._data_file_state == 1:
            # Open new data file and write a pkt to it
            self._data_file_path = ''.join((cases_mgr_config.temp_dir,
                                cases_mgr_config.proc_mnemonic,
                                '_',
                                utils.time_stamp_str(pkt_time_stamp),
                                '.dat'))
            if not self._open_data_file():
                return
            self._file_time_stamp = pkt_time_stamp
            self._write_to_data_file(rx_pkt)
            self._data_file_state = 2
        elif self._data_file_state == 2:
            self._write_to_data_file(rx_pkt)
            
            # If tmp file is max size or too old
            #  save it in USB flash
            file_age = pkt_time_stamp - self._file_time_stamp
            #self._log.debug('file_age is %s' % str(file_age.seconds))
            file_size = utils.get_file_size(self._data_file_path)
            save_due_to_size = file_size >= cases_mgr_config.data_file_max_size
            save_due_to_age = file_age.seconds >= cases_mgr_config.data_file_storage_period
            
            # Compress low rate data only.  Low rate data is saved due to age, not size.
            compress = save_due_to_age
            
            if save_due_to_size or save_due_to_age:            
                self._data_file.close()
                self.data_production_lock.acquire();
                self.data_production += os.path.getsize(self._data_file_path)
                self.data_production_lock.release();        
                # Spin off a thread to execute the XMLRPC command.
                # If it's a big file, it will take a while for the USB mgr
                #  to copy the file to temp storage.  The serial buffer
                #  could overflow while waiting.
                save_file_thread = SaveFileThread(self._data_file_path, compress, self._log)
                # save_file_thread deletes data file after storage
                self._data_file_path = None
                self._data_file_state = 1
        else:
            self._log.error('RxDataThread._process_rx_pkt: unknown state value')
            self._data_file_state = 1          

    def _open_data_file(self):
        """Open self._data_file. Return True if successful"""
        try:
            self._data_file = open(self._data_file_path, 'wb')
        except IOError:
            self._log.error('Could not open %s' % self._data_file_path)
            self._data_file = None
            return False
        return True      
         
    def _close_data_file(self):
        """Close self._data_file"""
        if self._data_file:
            try:
                self._data_file.close()
            except IOError:
                self._log.error('Could not close %s' % self._data_file_path)
            self._data_file = None
      
    def _write_to_data_file(self, pkt):
        """Write a pkt to self._data_file"""
        if self._data_file:
            try:
                self._data_file.write(pkt.get_pkt_buf())
            except IOError:
                self._log.error('Could not write to file %s', self._data_file)
        
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread and its child threads"""
        if self._running:
            self._stop_event.set()
            self.join()
    

class TxDataThread(threading.Thread):
    """ Transmit packets from a packet queue """
    def __init__(self, log, serial_port, exit_callback=None):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self._log = log
        self._port = serial_port
        self._exit_callback = exit_callback
        self._pkt_q = Queue.Queue()
        self._stop_event = threading.Event()
        self.name = 'TxDataThread'
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
            pkt = utils.q_get(self._pkt_q, get_timeout=0.5)
            if pkt is not None:
                self._transmit_pkt(pkt)
            
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        if self._exit_callback:
            self._exit_callback(self)
        self._log.debug('Exiting %s ' % self.name)
        
    def _transmit_pkt(self, pkt):
        """ Transmit a packet in chunks so other threads
        have a chance to run while transmitting a big packet
        """
        self._log.info('Started transmitting %s', pkt.type_str())
        self._log.info(''.join(['\n', pkt.str()]))                       
        pkt_buf = pkt.get_pkt_buf()
        block_size = 1152
        while (len(pkt_buf) > 0) and (not self._stop_event.isSet()):
            self._port.write(pkt_buf[0:block_size])
            pkt_buf = pkt_buf[block_size:]
            utils.wait(0.1)            
        if not self._stop_event.isSet():
            self._log.info('Finished transmitting %s', pkt.type_str())

     
    def enqueue_pkt(self, pkt):
        """Enqueue a packet for transmission"""
        self._pkt_q.put(pkt)   
        #self._log.debug('TxDataThread.enqueue_pkt: enqueued a pkt')
        
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop the thread and its child threads"""
        if self._running:
            self._stop_event.set()
            self.join()

           
class XMLRPCThread(BasicXMLRPCThread):
    """An extended BasicXMLRPCThread"""
    def __init__(self, host, port, tx_data_thread, rx_data_thread, console, log):
        BasicXMLRPCThread.__init__(self, host, port, log)
        self._log = log
        self._tx_data_thread = tx_data_thread
        self._rx_data_thread = rx_data_thread
        self._console = console
        self._server.register_function(self.help)
        self._server.register_function(self.soft_reset)
        self._server.register_function(self.hard_reset)
        self._server.register_function(self.halt)
        self._server.register_function(self.upload_dsp_image)
        self._server.register_function(self.upload_dsp_config)
        self._server.register_function(self.upload_sbc_config)
        self._server.register_function(self.set_power_state)
        self._server.register_function(self.query_status) 
        self._server.register_function(self.retrieve_file) 
        self._server.register_function(self.transfer_file) 
        self._server.register_function(self.execute_sys_cmd) 
        self._server.register_function(self.get_data_production) 
        self._server.register_function(self.clear_data_production)
        self._server.register_function(self.stop_rx_data) 
        self._server.register_function(self.start_rx_data) 
           
    def help(self):
        """ Show the available XMLRPC commands """
        if self._console.is_connected():
            msg = ''.join([ \
                '\nCASES manager XMLRPC commands\n',
                '  help\n',
                '  soft_reset\n',
                '  hard_reset\n',
                '  halt\n',
                '  upload_dsp_image <image_file_path>\n',
                '  upload_dsp_config <config file path>\n',
                '  upload_sbc_config <config file path>\n',
                '  set_power_state <one-byte power state>\n',
                '  query_status\n',
                '  retrieve_file <filepath>\n',
                '    Request SBC file\n',
                '  transfer_file <source filepath> <destination filepath>\n',
                '    Send file to SBC\n',
                '  execute_sys_cmd <command to be executed>\n',
                '    Execute a shell command on the SBC\n',
                '  get_data_production\n',
                '    Returns the number of bytes received from CASES since the data\n',
                '    production counter was last cleared\n',
                '  clear_data_production\n',
                '    Sets the data production counter to zero\n',
                '  stop_rx_data\n',
                '    Ignore data received from CASES\n',
                '  start_rx_data\n',
                '    Process data received from CASES\n',
                '  dis\n',
                '    Disconnect from console\n'
           ])
            self._console.write(msg)
        return 'OK'
        
    def soft_reset(self):
        pkt = CASESPkt.CASESPkt()
        pkt.build(CASESPkt.CASESPkt.SOFT_RESET_CMD)
        return self._send_pkt(pkt)
        
    def hard_reset(self):
        pkt = CASESPkt.CASESPkt()
        pkt.build(CASESPkt.CASESPkt.HARD_RESET_CMD)
        return self._send_pkt(pkt)
        
    def halt(self):
        pkt = CASESPkt.CASESPkt()
        pkt.build(CASESPkt.CASESPkt.EXECUTE_SYS_CMD, 'halt')
        #self._log.info('Got halt command')
        return self._send_pkt(pkt)          
        
    def upload_dsp_image(self, image_file_path):
        return self._send_pkt_with_file(CASESPkt.CASESPkt.UPLOAD_DSP_IMAGE_CMD, image_file_path)
        
    def upload_dsp_config(self, config_file_path):
        return self._send_pkt_with_file(CASESPkt.CASESPkt.UPLOAD_DSP_CONFIG_CMD, config_file_path)
        
    def upload_sbc_config(self, config_file_path):
        return self._send_pkt_with_file(CASESPkt.CASESPkt.UPLOAD_SBC_CONFIG_CMD, config_file_path)
        
    def set_power_state(self, power_state):
        """Set the CASES power state.
        power_state is a one byte string containing '1', '2' etc.
        """
        try:
            power_state_int = int(power_state)
        except ValueError:
            self._log.error('XMLRPC command error: power_state is not a positive integer')
            return "failed"
        if (power_state_int > 255) or (power_state_int < 0):
            self._log.error('XMLRPC command error: power_state < 0 or > 255')
            return "failed"        
        pkt = CASESPkt.CASESPkt()
        pkt.build(CASESPkt.CASESPkt.SET_POWER_STATE_CMD, chr(power_state_int))
        return self._send_pkt(pkt)
        
    def execute_sys_cmd(self, cmd_str):
        pkt = CASESPkt.CASESPkt()
        pkt.build(CASESPkt.CASESPkt.EXECUTE_SYS_CMD, cmd_str)
        return self._send_pkt(pkt)          
        
    def query_status(self):
        pkt = CASESPkt.CASESPkt()
        pkt.build(CASESPkt.CASESPkt.QUERY_STATUS_CMD)
        return self._send_pkt(pkt)
        
    def retrieve_file(self, file_path):
        pkt = CASESPkt.CASESPkt()
        pkt.build(CASESPkt.CASESPkt.RETRIEVE_FILE_CMD, file_path)
        return self._send_pkt(pkt)
    
    def transfer_file(self, src_file_path, dest_file_path):
        file_contents = copy_file_to_string(src_file_path, self._log)
        if file_contents is None:
            return ''.join(['Failed: Could not open ', src_file_path])
        pkt = CASESPkt.CASESPkt()
        pkt.build(CASESPkt.CASESPkt.TRANSFER_FILE_MSG, ''.join([dest_file_path, '\x0A', file_contents]))
        return self._send_pkt(pkt)
        
    def get_data_production(self):
        self._rx_data_thread.data_production_lock.acquire()
        dp = self._rx_data_thread.data_production
        self._rx_data_thread.data_production_lock.release()
        return dp
        
    def clear_data_production(self):
        self._rx_data_thread.data_production_lock.acquire()
        self._rx_data_thread.data_production = 0
        self._rx_data_thread.data_production_lock.release()
        return('OK')
        
    def stop_rx_data(self):
        self._rx_data_thread.rx_data_enabled = False
        return 'OK'       
        
    def start_rx_data(self):
        self._rx_data_thread.rx_data_enabled = True
        return 'OK'     

    def _send_pkt_with_file(self, pkt_type, file_path):
        file_contents = copy_file_to_string(file_path, self._log)
        if file_contents is None:
            self._console.write('Could not open %s' % file_path)
            return 'failed'           
        pkt = CASESPkt.CASESPkt()
        pkt.build(pkt_type, file_contents)
        return self._send_pkt(pkt)       
        
    def _send_pkt(self, pkt):
        self._tx_data_thread.enqueue_pkt(pkt)
        if self._console.is_connected():
            self._console.write('Sent %s' % pkt.type_str())
        return('OK')
       
        
def copy_file_to_string(file_path, log):
    """Return a string containing the contents of a file
    Return None if file does not exist
    """
    log.debug('trying to open %s' % file_path)
    try:
        f = open(file_path, 'rb')
    except Exception:
        log.error('Could not open %s' % file_path)
        return None
    file_size = utils.get_file_size(file_path)
    file_str = f.read(file_size)
    f.close()
    return file_str
                          

def _run_mgr(log, test=False):
    """
        Run the instrument manager until terminated
    """
    log.info('')
    log.info('****** Starting CASES manager ******')
    
    """Open the instrument serial port"""
    try:
        serial_port = serial.Serial(port=cases_mgr_config.serial_device,
                                    baudrate=cases_mgr_config.baud_rate,
                                    rtscts = 0,
                                    timeout = 0,
                                    writeTimeout = 0,
                                    stopbits = serial.STOPBITS_ONE)
    except serial.SerialException:
        pass
    if serial_port.isOpen():
        log.info('Serial port %s opened' % serial_port.portstr)
    else:
        log.error('Serial port %s failed to open' % serial_port.portstr)
        sys.exit(1)
    log.debug(serial_port)    
    
    try:
        console = SockConsole('localhost',
                            cases_mgr_config.console_port,
                            log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)

    try:
        tx_data_thread = TxDataThread(log, serial_port)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
        
    try:
        rx_data_thread = RxDataThread(log, serial_port)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
                
    try:
        xmlrpc_thread = XMLRPCThread('localhost',
                                    cases_mgr_config.XMLRPC_port,
                                    tx_data_thread,
                                    rx_data_thread,
                                    console,
                                    log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
        
        
    i = 1
    while True:
        try:
            """
            i += 1
            if (i % 8) == 0:
                data_buf = '0123456789ABCDEF' * 128  # 2K data buffer          
                pkt = CASESPkt.CASESPkt()
                pkt.build(CASESPkt.CASESPkt.UPLOAD_DSP_IMAGE_CMD, data_buf[:2037])       
                tx_data_thread.enqueue_pkt(pkt)
            """   
            utils.wait(0.5)
            if not console.is_running():
                log.error('Console thread died unexpectedly')
                break
            if not xmlrpc_thread.is_running():
                log.error('XMLRPC server thread died unexpectedly')
                break
            if not tx_data_thread.is_running():
                log.error('Tx data thread died unexpectedly')
                break
            if not rx_data_thread.is_running():
                log.error('Rx data thread died unexpectedly')
                break
        except KeyboardInterrupt:
            if cases_mgr_config.accept_sigint:
                log.info('Got SIGINT (shutting down)')
                break
            else:
                log.info('Got SIGINT (ignored)')
        except:
            # handle all unexpected application exceptions
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
            sys.exit(1)
            break
                   
    tx_data_thread.stop()
    rx_data_thread.stop()
    console.stop()
    serial_port.close()
    xmlrpc_thread.stop()
    utils.wait_for_child_threads()
    log.info('****** Exiting CASES manager ******')
    

   
    
if __name__ == '__main__':
    sys.setcheckinterval(global_config.check_interval)
    if cases_mgr_config.daemonize:
        utils.daemonize()
    log = logs.open(cases_mgr_config.log_name,
                    cases_mgr_config.log_dir,
                    cases_mgr_config.log_level,
                    file_max_bytes = cases_mgr_config.log_file_max_bytes,
                    num_backup_files = cases_mgr_config.log_files_backup_files)
    utils.make_dirs(cases_mgr_config.temp_dir, log)
    _run_mgr(log, test=True)

