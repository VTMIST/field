#! /usr/bin/python

# Fluxgate Magnetometer Manager

import sys
import threading
import Queue
import serial
from datetime       import datetime,timedelta
import time
import xmlrpclib

import utils
import sock_utils
import logs
import usb_mgr_config
import fg_mgr_config
import global_config
from BasicXMLRPCThread import BasicXMLRPCThread
from SockConsole import SockConsole

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
            result = xmlrpc_svr.store_file(fg_mgr_config.proc_mnemonic,
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
        self._log.debug('Exiting %s ' % self.name)
        
        
class DataThread(threading.Thread):
    """ Receive and store instrument data """
    def __init__(self, console, log, exit_callback=None):
        """
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self.name = 'DataThread'
        self.elec_temp = '0.0'
        self.sensor_temp = '0.0'
        self._console = console
        self._log = log
        self._exit_callback = exit_callback
        self._stop_event = threading.Event()
        self._serial_port_open = False
        self._pkt_state = 1
        self._pkt_delim = str(chr(0x0A))
        self._pkt_newline = str('\x0D\x0A')
        self._data_file_state = 1
        self._data_file = None
        self._data_file_path = None
        self._data_file_hdr_row = 'Bx,By,Bz,Calibrating\n'
        self._time_epoch = datetime(1970, 1, 1, 0, 0, 0)
        self._prev_pkt_time_stamp = None
        self._data_tx_delay = timedelta(days=0, seconds=1)
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
        self._open_serial_port()
        if not self._serial_port_open:
            self._stop_event.set()
            
        self._log.info('Waiting for UTC synchronization')
        hw_mgr_server = None
        dummy_lock = utils.Lock(self._log)
        while not self._stop_event.isSet():
            [utc_sync_age, hw_mgr_server] = utils.get_hw_status('sync_age', hw_mgr_server, dummy_lock, self._log)
            if (utc_sync_age is not None) and (utc_sync_age < 10000):
                break
            utils.wait(0.5)
        if not self._stop_event.isSet(): 
            self._log.info('Synchronized with UTC')
            self._port.flushInput()          

        while not self._stop_event.isSet():
            bytes_avail = self._port.inWaiting()
            if bytes_avail > 0:
                self._process_rx_bytes(self._port.read(bytes_avail))
            utils.wait(0.05)

        self._running = False
        self._close_data_file()
        if self._data_file_path is not None:
            self._close_data_file()
            save_file_thread = SaveFileThread(self._data_file_path, True, self._log)
            save_file_thread.join()
        if self._serial_port_open:
            self._port.close()
        #self._log.debug('Stopping %s ' % self.name)
        if self._exit_callback:
            self._exit_callback(self)
        self._log.debug('Exiting %s ' % self.name)
        
    def _process_rx_bytes(self, rx_bytes):
        """Process a string of rx bytes"""
        for rx_byte in rx_bytes:
            self._process_rx_byte(rx_byte)
        
    def _process_rx_byte(self, rx_byte):
        """Process a byte from the instrument"""
        if self._pkt_state == 1:
            # wait for end of pkt and then start a new packet
            if rx_byte == self._pkt_delim:
                self._pkt_buf = ''
                self._pkt_state = 2
            return
        if self._pkt_state == 2:
            # store first byte and time of first byte
            self._pkt_time_stamp = datetime.now() - self._data_tx_delay
            self._pkt_buf = rx_byte
            self._pkt_state = 3
            return
        if self._pkt_state == 3:
            # Build up packet until end of pkt
            self._pkt_buf += rx_byte
            if rx_byte == self._pkt_delim:
                #self._log.info(self._pkt_buf)
                # Round the time stamp to the nearest second because
                #  it jitters around the UTC second +- ~50 msec.
                [rnd_pkt_time_stamp, adj_usec] = utils.round_datetime_to_sec(self._pkt_time_stamp)
                #sec = self._pkt_time_stamp.second
                #usec = self._pkt_time_stamp.microsecond
                #rnd_sec = rnd_pkt_time_stamp.second
                #rnd_usec = rnd_pkt_time_stamp.microsecond
                #self._log.info('%02d.%06d,  %02d.%06d, adj = 0.%06d' % (sec, usec, rnd_sec, rnd_usec, adj_usec))
                if (adj_usec > fg_mgr_config.max_pkt_jitter) or \
                    (adj_usec < -(fg_mgr_config.max_pkt_jitter)):
                    self._log.error('Significant packet arrival jitter')          
                self._process_rx_pkt(self._pkt_buf, rnd_pkt_time_stamp)
                self._pkt_buf = ''
                self._pkt_state = 2
            return
        self._log.error('DataThread._process_rx_byte: unknown state value')

    def _process_rx_pkt(self, rx_pkt, pkt_time_stamp):
        """Process a pkt from the instrument"""
        if self._data_file_state == 1:
            # Open new data file and write a pkt to it
            self._data_file_path = "".join((fg_mgr_config.temp_dir,
                                fg_mgr_config.proc_mnemonic,
                                '_',
                                utils.time_stamp_str(pkt_time_stamp),
                                '.dat.csv'))
            if not self._open_data_file():
                return
            self._write_to_data_file(self._data_file_hdr_row)
            self._format_and_write_pkt(rx_pkt, pkt_time_stamp)
            self._file_pkt_cnt = 1
            self._data_file_state = 2
            self._prev_pkt_time_stamp = pkt_time_stamp
            return
        if self._data_file_state is 2:
            
            # If there is a significant gap between instrument
            #  data pkts, don't store the current packet and
            #  start a new data file
            time_between_pkts = utils.total_seconds(pkt_time_stamp - self._prev_pkt_time_stamp)
            self._prev_pkt_time_stamp = pkt_time_stamp            
            #self._log.debug('time between pkts: %.3f' % time_between_pkts)
            data_gap = False
            if time_between_pkts > fg_mgr_config.max_data_pkt_gap:
                self._log.error('Excessive time gap between fluxgate data packets')
                data_gap = True
            if not data_gap:
                self._format_and_write_pkt(rx_pkt, pkt_time_stamp)          
                self._file_pkt_cnt += 1
            end_of_hour = (pkt_time_stamp.minute == 59) and (pkt_time_stamp.second == 59)
                
            if data_gap or end_of_hour:
                self._data_file.close()          
                # Spin off a thread to execute the XMLRPC command.
                # If it's a big file, it will take a while for the USB mgr
                #  to copy the file to temp storage.
                compress = True
                save_file_thread = SaveFileThread(self._data_file_path, compress, self._log)
                # save_file_thread deletes data file after storage
                self._data_file_path = None
                self._data_file_state = 1
            return
        self._log.error('DataThread._process_rx_pkt: unknown state value')

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
      
    def _delete_data_file(self):
        """Delete self._data_file_path"""
        if self._data_file_path:
            utils.delete_file(self._data_file_path, self._log)
            self._data_file_path = None
      
    def _write_to_data_file(self, pkt):
        """Write a pkt to self._data_file"""
        if self._data_file:
            try:
                self._data_file.write(pkt)
            except IOError:
                self._log.error('Could not write to file %s', self._data_file)
        
    def _format_pkt(self, pkt, time_stamp):
        """Convert pkt to CSV format, prepend time stamp"""
        clean_pkt = pkt.strip()
        calibrating = '0'
        if clean_pkt.find('C') != -1:
            calibrating = '1'
        clean_pkt = clean_pkt.replace('   ', ',')
        clean_pkt = clean_pkt.replace('  ', ',')
        clean_pkt = clean_pkt.replace(' ', ',')      
        clean_pkt = clean_pkt.replace('+', '')
        list1 = clean_pkt.split(',')
        self.elec_temp = list1[3]
        self.sensor_temp = list1[4]        
        list2 = list1[:3]   # strip temps, add cal flag
        list2.append(calibrating)
        clean_pkt = ','.join(list2)         
        return ''.join([clean_pkt, '\n'])
        
    def _format_and_write_pkt(self, rx_pkt, pkt_time_stamp):
        formatted_pkt = self._format_pkt(rx_pkt, pkt_time_stamp)
        self._write_to_data_file(formatted_pkt)
        if self._console.is_connected():
            formatted_pkt = formatted_pkt.replace('\n', '')                             
            lst = formatted_pkt.split(',')
            readings = ''.join(['X: ', lst[0], '  Y: ', lst[1], '  Z: ', lst[2]])
            msg = ''.join([readings,
                    '  Telec: ', self.elec_temp,
                    '  Tsens: ', self.sensor_temp])
            if lst[3].find('1') != -1:
                # sensor is currently calibrating
                msg = ''.join([msg, ' *Calibrating*'])
            self._console.write(''.join([msg, '\n']))                        
        
    def _open_serial_port(self):       
        """Open the instrument serial port"""
        self._serial_port_open = False
        try:
            self._port = serial.Serial(port=fg_mgr_config.serial_device,
                                        baudrate=fg_mgr_config.baud_rate,
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
        
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread and its child threads"""
        if self._running:
            self._stop_event.set()
            self.join()
    
                
class XMLRPCThread(BasicXMLRPCThread):
    """An extended BasicXMLRPCThread"""
    def __init__(self, host, port, data_thread, log):
        BasicXMLRPCThread.__init__(self, host, port, log)
        self._data_thread = data_thread
        self._log = log
        self._server.register_function(self.get_elec_temp)
        self._server.register_function(self.get_sensor_temp)
        
    def get_elec_temp(self):
        return self._data_thread.elec_temp
        
    def get_sensor_temp(self):
        return self._data_thread.sensor_temp
            

def _run_mgr(log):
    """
        Run the instrument manager until terminated
    """
    global gv
    log.info('')
    log.info('****** Starting fluxgate instrument manager ******')
    
    try:
        gv.console = SockConsole('localhost',
                            fg_mgr_config.console_port,
                            log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
        
    try:
        data_thread = DataThread(gv.console, log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)              
        
    try:
        xmlrpc_thread = XMLRPCThread('localhost',
                            fg_mgr_config.XMLRPC_port, data_thread, log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
       
    while True:
        try:
            utils.wait(0.5)
            if not gv.console.is_running():
                log.error('Console thread died unexpectedly')
                break
            if not xmlrpc_thread.is_running():
                log.error('XMLRPC server thread died unexpectedly')
                break
            if not data_thread.is_running():
                log.error('Data thread died unexpectedly')
                break
        except KeyboardInterrupt:
            if fg_mgr_config.accept_sigint:
                log.info('Got SIGINT (shutting down)')
                break
            else:
                log.info('Got SIGINT (ignored)')
        except:
            # handle all unexpected application exceptions
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
            sys.exit(1)
                   
    data_thread.stop()
    gv.console.stop()
    xmlrpc_thread.stop()
    utils.wait_for_child_threads()
    log.info('****** Exiting fluxgate instrument manager ******')
    
    
class GlobalVars:
    """ Global variables """
    def __init__(self):
        self.console = None
        
    
if __name__ == '__main__':
    sys.setcheckinterval(global_config.check_interval)
    if fg_mgr_config.daemonize:
        utils.daemonize()
    gv = GlobalVars
    log = logs.open(fg_mgr_config.log_name,
                    fg_mgr_config.log_dir,
                    fg_mgr_config.log_level,
                    file_max_bytes = fg_mgr_config.log_file_max_bytes,
                    num_backup_files = fg_mgr_config.log_files_backup_files)
    utils.make_dirs(fg_mgr_config.temp_dir, log)
    _run_mgr(log)

