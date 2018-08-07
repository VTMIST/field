#! /usr/bin/python

# AAL-PIP Supervisor
#   Controls overall AAL-PIP operation

import sys
import threading
from datetime       import datetime,timedelta
import time
import xmlrpclib

import utils
import logs
import super_config
import hw_mgr_config
import global_config
from BasicXMLRPCThread import BasicXMLRPCThread
from SockConsole import SockConsole
from ControlGPSPower import ControlGPSPower
from ControlTemp import ControlTemp
from RefreshStatus import RefreshStatus
from ControlEthernetPower import ControlEthernetPower
from ControlModemPower import ControlModemPower
from ControlFGSCPower import ControlFGSCPower
from ControlHFPower import ControlHFPower
from ControlCASESPower import ControlCASESPower
from MonitorRUDICSComm import MonitorRUDICSComm
from StoreHskp import StoreHskp


class Controllers:
    def __init__(self, log):
        self.control_cases_power = ControlCASESPower(log)
        self.control_ethernet_power = ControlEthernetPower(log)
        self.control_gps_power = ControlGPSPower(log)
        self.control_temp = ControlTemp(log)
        self.refresh_status = RefreshStatus(log)
        self.store_hskp = StoreHskp(log)
        self.control_fgsc_power = ControlFGSCPower(log)
        self.control_hf_power = ControlHFPower(log)
        self.control_modem_power = ControlModemPower(log)
        self.monitor_rudics_comm = MonitorRUDICSComm(log)

def _init_super(log):
    """ Initialize the supervisor.
        Return a Controllers object if sucessful,
        None if not.
    """
    if not _wait_for_hw_mgr(log):
        return None
    return Controllers(log)
    

def run_super_loop(controllers, log):
    """Call the controllers periodically"""
    c = controllers
    utils.wait(15)
    c.control_ethernet_power.run()  # run one time only
    while True:
        # wait for the next 15 second period
        start = datetime.now()
        if (start.second % 15) == 0:
            c.refresh_status.run()
            c.store_hskp.run(start)
            c.control_cases_power.run()
            c.control_gps_power.run()
            c.control_temp.run()
            c.control_fgsc_power.run()
            c.control_hf_power.run()
            c.control_modem_power.run()
            c.monitor_rudics_comm.run()
            #et = utils.total_seconds(datetime.now() - start)
            #log.info('supervisor loop took: %0.1f s' % et)
        else:
            utils.wait(0.5)

    
def _wait_for_hw_mgr(log):
    """hw_mgr takes a while before it is ready to
       accept XMLRPC commands.  Wait here until
       it accepts a command.
       Return True if successful.
    """
    start_time = time.time()
    hw_mgr_server = None
    dummy_lock = utils.Lock(log)
    while True:
        if (time.time() - start_time) > super_config.xmlrpc_conn_timeout:
            log.error('Timed out connecting to hw_mgr XMLRPC server.')
            return False
        [status, hw_mgr_server] = utils.get_hw_status('fg_pwr', hw_mgr_server, dummy_lock, log)
        if status is None:
            utils.wait(1)
        else:
            break
    return True
    
                     

def _shutdown_super(controllers, log):
    # For debugging only.  Save selected logs to flash.
    utils.call_subprocess('mkdir -p /aal-pip/field/reboot_logs')
    #utils.call_subprocess('cp /var/log/cases_mgr.log /aal-pip/field/reboot_logs', log)
    #utils.call_subprocess('cp /var/log/fg_mgr.log /aal-pip/field/reboot_logs', log)
    #utils.call_subprocess('cp /var/log/gps_mgr.log /aal-pip/field/reboot_logs', log)
    utils.call_subprocess('cp /var/log/hw_mgr.log /aal-pip/field/reboot_logs', log)
    #utils.call_subprocess('cp /var/log/modem_svr.log /aal-pip/field/reboot_logs', log)
    #utils.call_subprocess('cp /var/log/sc_mgr.log /aal-pip/field/reboot_logs', log)
    utils.call_subprocess('cp /var/log/super.log /aal-pip/field/reboot_logs', log)
    #utils.call_subprocess('cp /var/log/svr_proxy.log /aal-pip/field/reboot_logs', log)
    #utils.call_subprocess('cp /var/log/usb_mgr.log /aal-pip/field/reboot_logs', log)
    utils.call_subprocess('cp /var/log/cpu_load_wd.log /aal-pip/field/reboot_logs', log)
    c = controllers
    c.store_hskp.stop()
    c.control_ethernet_power.stop()
    c.refresh_status.stop()
    c.control_cases_power.stop()
    c.control_gps_power.stop()
    c.control_temp.stop()
    c.control_fgsc_power.stop()
    c.control_hf_power.stop()
    c.control_modem_power.stop()
    c.monitor_rudics_comm.stop()

             
class XMLRPCThread(BasicXMLRPCThread):
    """An extended BasicXMLRPCThread"""
    def __init__(self,
                host,
                port,
                console,
                controllers,
                log):
        BasicXMLRPCThread.__init__(self, host, port, log)
        self._log = log
        self._console = console
        self._control_temp = controllers.control_temp
        self._control_fgsc_power = controllers.control_fgsc_power
        self._control_hf_power = controllers.control_hf_power
        self._control_modem_power = controllers.control_modem_power
        self._control_cases_power = controllers.control_cases_power               
        self._server.register_function(self.help)
        self._server.register_function(self.set_temp)
        self._server.register_function(self.fg)
        self._server.register_function(self.sc)
        self._server.register_function(self.hf)
        self._server.register_function(self.cases)
        self._server.register_function(self.irid)
           
    def help(self):
        """ Show the available XMLRPC commands """
        if self._console.is_connected():
            msg = ''.join([ \
                '\nAAL-PIP supervisor XMLRPC commands\n',
                '> help\n',
                '> set_temp <temp>\n',
                '      temp: desired electronics temp in deg C\n',
                '> fg on|off\n',
                '> sc on|off\n',
                '> irid on|off\n',
                '> hf on|off\n',
                '> cases on|off\n',
                '> cases normal_mode|storm_mode|update_mode\n',
                '> test\n',
                '> dis\n',
                '    Disconnect from console\n'
           ])
            self._console.write(msg)
        return 'OK'
        
    def set_temp(self, temp):
        """Set the electronics temp setpoint.
        temp is a floating point string, deg C.
        """
        self._log.info('Temp setpoint set to %s' % temp)
        try:
            self._control_temp.setpoint = float(temp)
        except Exception, e:
            log.error(''.join(['Could not set temp to ', temp, '. Exception: ', e]))
            return 'failed'
        return 'OK'
        
    def fg(self, desired_state):
        """Turn fluxgate power on or off"""
        if desired_state == 'on':
            self._log.info('Got XMLRPC cmd: fg on')
            self._control_fgsc_power.fg_power_setting = 1
        if desired_state == 'off':
            self._log.info('Got XMLRPC cmd: fg off')
            self._control_fgsc_power.fg_power_setting = 0
        return 'OK'

    def sc(self, desired_state):
        """Turn search coil power on or off"""
        if desired_state == 'on':
            self._control_fgsc_power.sc_power_setting = 1
        if desired_state == 'off':
            self._control_fgsc_power.sc_power_setting = 0
        return 'OK'
        
    def hf(self, desired_state):
        """Turn HF radio power on or off"""
        if desired_state == 'on':
            self._control_hf_power.master_power_enable = 1
        if desired_state == 'off':
            self._control_hf_power.master_power_enable = 0
        return 'OK'
        
    def cases(self, command):
        """Enable the CASES controller to turn CASES power on.
           Set the CASES operating mode.
        """
        if command == 'on':
            self._control_cases_power.master_power_enable = 1
        if command == 'off':
            self._control_cases_power.master_power_enable = 0
        if command == 'normal_mode':
            self._control_cases_power.mode = "normal"
        if command == 'storm_mode':
            self._control_cases_power.mode = "storm"
        if command == 'update_mode':
            self._control_cases_power.mode = "update"
        return 'OK'
 
    def irid(self, desired_state):
        """Turn Iridium modem power on or off"""
        if desired_state == 'on':
            self._control_modem_power.power_on()
        if desired_state == 'off':
            self._control_modem_power.power_off()
        return 'OK'

        
def _run_super(log):
    log.info('')
    log.info('****** Starting AAL-PIP Supervisor ******')
    
    try:
        controllers = _init_super(log)
    except Exception, e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        print 'Exception in super._run_super: %s' % e
        sys.exit(1)
    if not controllers:
        sys.exit(1)
    try:
        console = SockConsole('localhost',
                            super_config.console_port,
                            log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
    try:
        xmlrpc_thread = XMLRPCThread('localhost',
                            super_config.XMLRPC_port,
                            console,
                            controllers,
                            log)
    except Exception, e:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        print 'Exception in super._run_super: %s' % e
        sys.exit(1)     
    
    while True:
        try:
            run_super_loop(controllers, log)
        except KeyboardInterrupt:
            log.info('Got SIGINT (shutting down)')
            break
        except:
            # handle all unexpected application exceptions
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
            sys.exit(1)
            break
    _shutdown_super(controllers, log)
    console.stop()
    xmlrpc_thread.stop()            
    utils.wait_for_child_threads()
    log.info('****** Exiting AAL-PIP Supervisor ******')
    
    
if __name__ == '__main__':
    sys.setcheckinterval(global_config.check_interval)
    if super_config.daemonize:
        utils.daemonize()
    log = logs.open(super_config.log_name,
                    super_config.log_dir,
                    super_config.log_level,
                    file_max_bytes = super_config.log_file_max_bytes,
                    num_backup_files = super_config.log_files_backup_files)
    _run_super(log)

