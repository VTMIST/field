#! /usr/bin/python

# HF Radio Manager

import sys
import threading
import serial
from datetime       import datetime,timedelta
import time
import xmlrpclib

import utils
import logs
import usb_mgr_config
import hf_mgr_config
import global_config

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
        #self._log.debug('Starting %s ' % self.name)
        self._running = True
        self._started = True
        
        try:
            xmlrpc_svr = xmlrpclib.Server(usb_mgr_config.XMLRPC_URL)
        except Exception:
            self._log.error('Could not connect to usb_mgr XML-RPC server')
            return
        try:
            result = xmlrpc_svr.store_file(hf_mgr_config.proc_mnemonic,
                                            self._data_file_path,
                                            self._compress)
        except Exception, e:
            self._log.error('Could not write file %s to USB flash drive: %s' % \
                             (self._data_file_path, e))
            return
        #self._log.info('Stored %s on USB flash drive' % self._data_file_path)
        utils.delete_file(self._data_file_path, self._log)
            
        self._running = False
        #self._log.debug('Stopping %s ' % self.name)
        #self._log.debug('Exiting %s ' % self.name)
        
        
class HFMgrThread(threading.Thread):
    def __init__(self, log, exit_callback=None):
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self.name = 'HFMgrThread'
        self._log = log
        self._exit_callback = exit_callback
        self._stop_event = threading.Event()
        self._state = ''
        self._change_state('waiting_for_power_on')
        self._serial_port_open = False
        self._newline = str('\x0D')
        self._cntl_c = str('\x03')
        self._data_file = None
        self._data_file_path = None
        self._sys_index = None
        self._sys_call_sign = None
        self._sys_name = None
        self._sys_num = None 
        self._test_msg = None
        self._rx_buf_list = []
        self._time_stamp = None
        self._hw_mgr_svr_proxy = None
        self._hw_mgr_lock = utils.Lock(self._log)
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
        
        self._open_serial_port()
        if self._serial_port_open:           
            self._log.info('Waiting for UTC synchronization')
            self._wait_for_UTC_sync()
            if not self._stop_event.isSet():
                self._log.info('Synchronized with UTC')
                self._get_system_info()          
                self._manage()

        self._running = False
        if self._serial_port_open:
            self._port.close()
        #self._log.debug('Stopping %s ' % self.name)
        if self._exit_callback:
            self._exit_callback(self)
        #self._log.debug('Exiting %s ' % self.name)
        
    def _manage(self):
        while not self._stop_event.isSet():
            if self._state == 'waiting_for_power_on':
                self._wait_for_power_on()
            elif self._state == 'receiving':
                self._receive()
            elif self._state == 'transmitting':
                self._transmit()
            else:
                self._log.error('Unknown state in _manage')
                self._stop_event.set()
    
    def _wait_for_power_on(self):
        while not self._stop_event.isSet():
            if self._autoset_baud_rate():
                self._time_stamp = datetime.now()
                self._rx_buf_list = []
                if self._init_modem():
                    self._change_state('receiving')
                    return
                    
    def _receive(self):
        while not self._stop_event.isSet():
            if not self._hf_power_is_on():
                self._store_rx_buf()
                self._change_state('waiting_for_power_on')
                return
            if self._in_transmit_window():
                utils.wait(hf_mgr_config.tx_dead_time)
                self._enter_transmit_mode()
                self._change_state('transmitting')
                return
            bytes_avail = self._port.inWaiting()
            if bytes_avail > 0:
                rx_str = self._port.read(bytes_avail)
                self._rx_buf_list.append(rx_str)
            utils.wait(2)
            
    def _transmit(self):
        while not self._stop_event.isSet():
            if not self._hf_power_is_on():
                self._enter_receive_mode()
                self._store_rx_buf()
                self._change_state('waiting_for_power_on')
                return
            if not self._in_transmit_window():
                #self._log_port_rx_buf()
                self._port.flushInput() # Toss test msg echos
                self._enter_receive_mode()
                self._change_state('receiving')
                return
            self._send_test_msg()
            utils.wait(1)
        self._enter_receive_mode()                                                          
                    
    def _init_modem(self):
        """ Initialize the modem and leave it in receive mode.
            Return True if successful.
        """
        self._log.debug('Initializing modem...')                             
        if not self._cmd_and_response(self._sys_call_sign + self._newline, ':'):
            return False
        if not self._cmd_and_response('xflow off' + self._newline, ':'):
            return False
        if not self._cmd_and_response('port 1' + self._newline, ':'):
            return False
        if not self._cmd_and_response('reset' + self._newline, ':'):
            return False
        if not self._cmd_and_response('ba off' + self._newline, ':'):
            return False
        if not self._cmd_and_response('hbaud 300/300' + self._newline, ':'):
            return False
        if not self._cmd_and_response('shift modem' + self._newline, ':'):      
            return False
        mark_freq = self._calc_mark_freq()
        if not self._cmd_and_response('mark ' + str(mark_freq) + self._newline, ':'):
            return False
        self._rx_buf_list.append("Mark = %s, " % str(mark_freq))
        if not self._cmd_and_response('space ' + str(mark_freq + self._tone_shift)  + self._newline, ':'):
            return False
        self._rx_buf_list.append("Space = %s" % str(mark_freq + self._tone_shift) + self._newline)
        if not self._cmd_and_response('xmitlvl 59/59' + self._newline, ':'):
            return False
        if not self._cmd_and_response('MYSELCAL ' + self._sys_call_sign + self._newline, ':'):
            return False
        if not self._cmd_and_response('tor' + self._newline, 'STANDBY>'):
            return False
        self._go_to_cmd_mode()
        self._cmd_and_response('fec' + self._newline)
        utils.wait(1)
        self._port.flushInput() # Toss fec echo
        self._enter_receive_mode()
        self._log.debug('Completed modem initialization')
        return True
            
    def _enter_transmit_mode(self):
        self._cmd_and_response(self._cntl_c)
        utils.wait(1)
        self._cmd_and_response('t')
        self._log.debug('Commanded modem into transmit mode')
        
    def _enter_receive_mode(self):
        self._cmd_and_response(self._cntl_c)
        utils.wait(1)
        self._cmd_and_response('r')
        self._log.debug('Commanded modem into receive mode')
        
    def _go_to_cmd_mode(self):
        self._cmd_and_response(self._cntl_c)
        utils.wait(1)
        if not self._cmd_and_response('x', ':'):
            self._log.error('Failed to go to cmd mode after <cntl-c>x')
            
    def _in_transmit_window(self):
        """ Return True if this system is in its
            transmit time window.
        """
        in_window = int((self._get_test_time() / hf_mgr_config.tx_period)) == self._sys_index
        #self._log.debug('test_time = %d, sys_index = %d, in_window = %s' % \
        #                (test_time, self._sys_index, str(in_window)))
        return in_window
        
    def _get_test_time(self): 
        # test_time ranges from 0 to hf_config.test_period - 1
        return int(time.time() % hf_mgr_config.test_period)        
        
    def _send_test_msg(self):
        """ Send the test message.
            Return when it has been fully transmitted.
        """
        #self._log.debug('Sent test msg "%s"' % self._make_printable(self._test_msg))
        self._port.write(self._test_msg)
        tx_time = (len(self._test_msg) * 10) / hf_mgr_config.hf_tx_bit_rate
        utils.wait(tx_time)
                 
    def _calc_mark_freq(self):
        """ Calculate and return the mark frequency.
            It depends heavily on temperature.
        """               
        T = self._get_fg_electronics_temp()
        self._rx_buf_list.append("Temp = %s, " % str(T))
        return int(round( self._tone_coeff_2 * T * T \
                        + self._tone_coeff_1 * T \
                        + self._tone_coeff_0 ))
                  
    def _get_system_info(self):
        """ Set self._sys_index,
                self._sys_name,
                self._sys_num
                self._sys_call_sign,
                self._tone_coeff_2
                self._tone_coeff_1
                self._tone_coeff_0
                self._tone_shift
                self._test_msg
            based on the CPU serial number.
        """
        cpu_sn = self._get_cpu_serial_num()
        for i, item in enumerate(hf_mgr_config.sys_info):
            if item.cpu_sn == cpu_sn:
                self._sys_index = i
                self._sys_call_sign = item.call_sign
                self._sys_name = item.sys_name
                self._sys_num = item.sys_num
                self._tone_coeff_2 = item.tone_coeff_2
                self._tone_coeff_1 = item.tone_coeff_1
                self._tone_coeff_0 = item.tone_coeff_0
                self._tone_shift = item.tone_shift
                self._test_msg = ''.join(['VVV VVV VVV TESTING USAP AALPIP SYS ', str(self._sys_num), self._newline])
                return
        self._log.error('This CPU serial number is not in hf_mgr_config.py')         
                
    def _autoset_baud_rate(self):            
        """ Wait for "BAUD RATE"
            Send an asterisk.
            Wait for 'CALLSIGN=>'
            Return True if 'CALLSIGN=>' received before hf_mgr_config.autobaud_timeout
        """
        rx_bytes = ''
        target = 'BAUD RATE'
        while not self._stop_event.isSet():
            bytes_avail = self._port.inWaiting()
            if bytes_avail > 0:
                rx_bytes += self._port.read(bytes_avail)
                if (rx_bytes.find(target) > -1):
                    self._log.debug('Received "%s"' % target)
                    if self._cmd_and_response('*', '=>', hf_mgr_config.autobaud_timeout):
                        utils.wait(2)
                        return True
                if len(rx_bytes) > 200:
                    rx_bytes = ''
            utils.wait(1)
        return False
                 
    def _cmd_and_response(self, cmd, expected=None, timeout_secs=None):
        """ Send cmd and wait for expected.
            If expected is None, don't wait.
            Return True if expected received before timeout_secs.
        """
        #self._port.flushInput()
        self._port.write(cmd)       
        printable_cmd = self._make_printable(cmd)      
        #self._log.debug('Sent "%s" command' % printable_cmd)
        if expected == None:
            return True
        if timeout_secs == None:
            resp_timeout = hf_mgr_config.default_cmd_timeout
        else:
            resp_timeout = timeout_secs
        rx_bytes = ''
        start_time = time.time()
        while (time.time() - start_time) < resp_timeout:
            bytes_avail = self._port.inWaiting()
            if bytes_avail > 0:
                rx_bytes += self._port.read(bytes_avail)
                if (rx_bytes.find(expected) > -1):
                    #self._log.debug('  Received "%s"' % self._make_printable(rx_bytes))
                    utils.wait(1)
                    return True
            utils.wait(0.1)
        self._log.error('Timed out waiting for "%s" response to "%s" command' % (expected, printable_cmd))
        self._log.error('  Received "%s" before timing out' % self._make_printable(rx_bytes))
        return False
        
    def _wait_for_UTC_sync(self):
        hw_mgr_server = None
        dummy_lock = utils.Lock(self._log)
        while not self._stop_event.isSet():
            [utc_sync_age, hw_mgr_server] = utils.get_hw_status('sync_age', hw_mgr_server, dummy_lock, self._log)
            if (utc_sync_age is not None) and (utc_sync_age < 10000):
                break
            utils.wait(0.5)
        
    def _store_rx_buf(self):
        if len(self._rx_buf_list) == 0:
            self._log.debug('No received data to store')
            return
        self._data_file_path = "".join((hf_mgr_config.temp_dir,
                    hf_mgr_config.proc_mnemonic,
                    '_',
                    utils.time_stamp_str(self._time_stamp),
                    '.txt'))
        if not self._open_data_file():
            return
        rx_str = ''.join(self._rx_buf_list)
        #self._log.debug(''.join(['Received from another system:', self._newline, rx_str]))
        self._write_to_data_file(rx_str)
        self._data_file.close()          
        # Spin off a thread to execute the XMLRPC command.
        compress = True
        save_file_thread = SaveFileThread(self._data_file_path, compress, self._log)
        # save_file_thread deletes data file after storage
        self._data_file_path = None

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
                self._data_file.write(pkt)
            except IOError:
                self._log.error('Could not write to file %s', self._data_file)
        
    def _open_serial_port(self):       
        """Open the instrument serial port"""
        self._serial_port_open = False
        try:
            self._port = serial.Serial(port=hf_mgr_config.serial_device,
                                        baudrate=hf_mgr_config.baud_rate,
                                        rtscts = 0,
                                        timeout = 0,
                                        stopbits = serial.STOPBITS_ONE)
        except serial.SerialException:
            pass
        if self._port.isOpen():
            self._log.info('Serial port %s opened' % self._port.portstr)
            self._serial_port_open = True
        else:
            self._log.error('Serial port %s failed to open' % self._port.portstr)
        self._log.debug(self._port)
    
    def _get_cpu_serial_num(self):
        cpu_sn = '?'
        [s, stderr] = utils.call_subprocess('cat /proc/cpuinfo')
        #self._log.debug('s = %s' % s)
        lines = s.split('\n')
        for line in lines:
            #self._log.debug('line = %s' % line)
            if line.find('Serial') != -1:
                fields = line.split()
                #self._log.debug('fields = %s' % repr(fields))
                cpu_sn = fields[2]
                break
        return cpu_sn

    def _get_fg_electronics_temp(self):
        """ Return the FG electronics temp.
            Return 30.0 if the temp is unknown.
        """
        [temp, self._hw_mgr_svr_proxy] = \
                    utils.get_hw_status('fg_elec_temp', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)
        if temp == None:
            self._log.error('Could not get the fluxgate electronics temp')
            return 30.0     # A reasonable default
        return temp
        
    def _hf_power_is_on(self):
        """ Return True if HF power is on.
        """
        [power_state, self._hw_mgr_svr_proxy] = \
                    utils.get_hw_status('hf_pwr', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)
        if power_state == None:
            self._log.error('Could not get the HF power state')
            return False
        return power_state == 1
        
    def _make_printable(self, s):
        """ Convert the non-printable chars in s to
            their printable hex equivalents.
        """
        p_list = []
        for ch in s:
            ord_ch = ord(ch)
            if (ord_ch < 0x20) or (ord_ch > 0x7E):
                if ord_ch == 0x03:
                    p_list.append('<cntl-c>')
                elif ord_ch == 0x0A:
                    p_list.append('<LF>')
                elif ord_ch == 0x0D:
                    p_list.append('<CR>')
                else:               
                    p_list.append('<' + utils.bytes_to_hex(ch) + '>')
            else:
                p_list.append(ch)
        return ''.join(p_list)
        
    def _change_state(self, state):
        self._state = state
        self._log.debug('Entering %s state. Test time is %d.' % (self._state, self._get_test_time()))
        
    def _log_port_rx_buf(self):
        bytes_avail = self._port.inWaiting()
        if bytes_avail > 0:
            rx_bytes = self._port.read(bytes_avail)
        self._log.debug(''.join(['Received while transmitting:', self._newline, self._make_printable(rx_bytes)]))               
                      
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread and its child threads"""
        if self._running:
            self._stop_event.set()
            self.join()
    
                
def _run_mgr(log):
    """
        Run the HF manager until terminated
    """
    log.info('')
    log.info('****** Starting HF manager ******')
        
    try:
        hf_mgr_thread = HFMgrThread(log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
                      
    while True:
        try:
            utils.wait(1)
            if not hf_mgr_thread.is_running():
                log.error('Data thread died unexpectedly')
                break
        except KeyboardInterrupt:
            if hf_mgr_config.accept_sigint:
                log.info('Got SIGINT, shutting down')
                break
            else:
                log.info('Got SIGINT, ignored')
        except:
            # handle all unexpected application exceptions
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
            sys.exit(1)
                   
    hf_mgr_thread.stop()
    utils.wait_for_child_threads()
    log.info('****** Exiting HF manager ******')
    
    
if __name__ == '__main__':
    sys.setcheckinterval(global_config.check_interval)
    if hf_mgr_config.daemonize:
        utils.daemonize()
    log = logs.open(hf_mgr_config.log_name,
                    hf_mgr_config.log_dir,
                    hf_mgr_config.log_level,
                    file_max_bytes = hf_mgr_config.log_file_max_bytes,
                    num_backup_files = hf_mgr_config.log_files_backup_files)
    utils.make_dirs(hf_mgr_config.temp_dir, log)
    _run_mgr(log)

