import time
import xmlrpclib
import threading
from datetime import datetime,timedelta
import time

import super_config
import hw_mgr_config
import usb_mgr_config
import utils


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
            result = xmlrpc_svr.store_file('hskp',
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
        

class StoreHskp:
    """Store housekeeping info in a data file"""
    def __init__(self, log, exit_callback=None):
        self._log = log
        self._server_proxy = None
        self._data_file = None
        self._data_file_path = None
        self._data_file_state = 1
        self._data_file_hdr_row = 'Year,Month,Day,Hour,Minute,Second,Modem_on,FG_on,SC_on,CASES_on,HF_On,Htr_On,Garmin_GPS_on,Overcurrent_status_on,T_batt_1,T_batt_2,T_batt_3,T_FG_electronics,T_FG_sensor,T_router,V_batt_1,V_batt_2,V_batt_3,I_input,P_input,lat,long,sys_time_error_secs,UTC_sync_age_secs,Uptime_secs,CPU_load_1_min,CPU_load_5_min,CPU_load_15_min\n'
        utils.make_dirs(super_config.hskp_temp_dir, self._log)
                                        
    def run(self, time_stamp):       
        self._store_hskp_record(time_stamp)
        
    def stop(self):
        self._close_data_file()
        if self._data_file_path is not None:
            self._close_data_file()
            save_file_thread = SaveFileThread(self._data_file_path, True, self._log)
            save_file_thread.join()
        
    def _store_hskp_record(self, time_stamp):
        data_row = self._get_data_row(time_stamp)
        if data_row is None:
            return
        if self._data_file_state == 1:
            # Open new data file and write the header row to it
            self._data_file_path = "".join((super_config.hskp_temp_dir,
                                'hskp_',
                                utils.time_stamp_str(time_stamp),
                                '.dat.csv'))
            if not self._open_data_file():
                return
            self._write_to_data_file(self._data_file_hdr_row)
            self._write_to_data_file(data_row)
            self._data_file_state = 2
            return
        if self._data_file_state is 2:
            self._write_to_data_file(data_row)
            end_of_hour = (time_stamp.minute == 59) and (time_stamp.second == 45)
                
            if end_of_hour:
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
        self._log.error('StoreHskp._store_hskp: unknown state value')
        
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
            
    def _write_to_data_file(self, s):
        """Write a string to self._data_file"""
        if self._data_file:
            try:
                self._data_file.write(s)
            except IOError:
                self._log.error('Could not write to file %s', self._data_file)       
        
    def _get_data_row(self, time_stamp):
        """Return a CSV string containing all the hskp values
            Return None if status data was not available
        """
        dummy_lock = utils.Lock(self._log)
        [hw_status, self._server_proxy] = utils.get_full_hw_status(self._server_proxy,
                                            dummy_lock, self._log)
        if hw_status is None:
            self._log.error('StoreHskp._get_data_row: Could not get full status from hw_mgr')
            return None
        parts = []
        # Build up a row of CSV data
        try:
            parts.append(','.join([ \
                '%d' % time_stamp.year,
                '%d' % time_stamp.month,
                '%d' % time_stamp.day,
                '%d' % time_stamp.hour,
                '%d' % time_stamp.minute,
                '%d' % time_stamp.second,
                str(hw_status['irid_pwr']),
                str(hw_status['fg_pwr']),
                str(hw_status['sc_pwr']),
                str(hw_status['cases_pwr']),
                str(hw_status['hf_pwr']),
                str(hw_status['htr_pwr']),
                str(hw_status['gps_pwr']),
                str(hw_status['ovr_cur_status']),
                '%.2f' % hw_status['batt_1_temp'],
                '%.2f' % hw_status['batt_2_temp'],
                '%.2f' % hw_status['batt_3_temp'],
                '%.2f' % hw_status['fg_elec_temp'],
                '%.2f' % hw_status['fg_sens_temp'],
                '%.2f' % hw_status['router_temp'],        
                '%.2f' % hw_status['batt_1_volt'],
                '%.2f' % hw_status['batt_2_volt'],
                '%.2f' % hw_status['batt_3_volt'],
                '%.3f' % hw_status['in_current'],            
                '%.3f' % hw_status['in_power'],            
                '%.6f' % hw_status['lat'],
                '%.6f' % hw_status['long'],
                '%.6f' % hw_status['sys_time_error'],
                '%d,'  % hw_status['sync_age']]))
        except Exception, e:
            self._log.error('StoreHskp._get_data_row exception: %s' % e)
            return None       
        # get uptime_secs and idle_secs
        [ut, std_error] = utils.call_subprocess('cat /proc/uptime')    
        fields = ut.split()
        parts.append('%d,' % int(float(fields[0])))
        ut = hw_status['uptime'].replace(',', '')
        fields = ut.split()
        last = len(fields)- 1
        parts.append(','.join([ \
            '%.2f' % float(fields[last-2]),
            '%.2f' % float(fields[last-1]),
            '%.2f\n' % float(fields[last])]))
        data_row = ''.join(parts)
        #self._log.info(data_row)
        return data_row           
