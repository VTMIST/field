import time
import xmlrpclib
from datetime import datetime
import super_config
import svr_proxy_config
import utils

class ControlModemPower:
    def __init__(self, log):
        self._log = log
        self._hw_mgr_lock = utils.Lock(self._log)
        self._kill_power = False
        self._power_cntl_cmd_pending = False
        self._timer = time.time()
        self._hw_mgr_server = None
        self._svr_proxy_server = None
        self._power_up_modem()
        self._data_xfer_timer = time.time()
        self._comm_state = 'powered_up'
                                        
    def run(self):
        self._control_modem_power()
        if self._power_cntl_cmd_pending:
            self._handle_power_control_cmd()
            
    def stop(self):
        self._power_down_modem()
        
    def _control_modem_power(self):
        if self._comm_state is 'powered_up':
            #self._log.debug('ControlModemPower: comm_state is powered up')
            if self._data_xfer_timed_out():
                #self._log.info('ControlModemPower: timed out waiting for data')
                self._power_down_modem()
                self._comm_state = 'powered_down'
                return
        elif self._comm_state is 'powered_down':
            #self._log.debug('ControlModemPower: comm_state is powered_down')
            now = datetime.now()
            if (now.minute == 0) or (now.minute == 30):
                self._power_up_modem()
                self._data_xfer_timer = time.time()
                self._comm_state = 'powered_up'
                return
        else:
            self._log.error('ControlModemPower: Unknown state value')           
                
    def power_off(self):
        """Turn modem power off and keep it off"""
        self._kill_power = True
        self._power_cntl_cmd_pending = True
        
    def power_on(self):
        """Turn modem on and then allow automatic power control"""
        self._kill_power = False
        self._power_cntl_cmd_pending = True
        
    def _handle_power_control_cmd(self):
        self._power_cntl_cmd_pending = False
        if self._kill_power:
            self._power_down_modem()
        else:
            self._power_up_modem()          
        
    def _power_up_modem(self):
        if not self._kill_power:
            self._hw_mgr_server = utils.set_power_state('irid', 'on', self._hw_mgr_server, self._hw_mgr_lock, self._log)
            self._log.info('ControlModemPower: Iridium modem power turned on')
               
    def _power_down_modem(self):
        self._hw_mgr_server = utils.set_power_state('irid', 'off', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        self._log.info('ControlModemPower: Iridium modem power turned off')
        
    def _data_xfer_timed_out(self):
        """ Return True if we timed out waiting
            for modem data transfer.  Pings are
            not considered data transfer.
        """
        now = time.time()
        timer_et = now - self._data_xfer_timer
        if timer_et < super_config.data_xfer_timeout:
            #self._log.info('ControlModemPower: In initial 5 minute grace period')
            return False  # In initial grace period
       
        self._svr_proxy_server = utils.get_XMLRPC_server_proxy(svr_proxy_config.XMLRPC_URL, self._log)
        if self._svr_proxy_server is None:
            self._log.error('ControlModemPower: Could not create svr_proxy XMLRPC server proxy.')
            return False
        try:
            time_of_last_data_xfer = self._svr_proxy_server.time_of_last_data_xfer()
        except Exception, e:
            self._log.error('ControlModemPower: svr_proxy XMLRPC cmd failed.  %s' % e)
            return False
        et_since_last_data_xfer = now - time_of_last_data_xfer
        #self._log.info('ET since last data transfer: %s sec' % str(int(et_since_last_data_xfer)))
        return et_since_last_data_xfer > super_config.data_xfer_timeout
        
        
            
