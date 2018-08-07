import time
import xmlrpclib

import hw_mgr_config
import super_config
import utils

class ControlFGSCPower:
    """Control the fluxgate and searchcoil magnetometer power
    """ 
    def __init__(self, log):
        self._log = log
        self.fg_power_setting = 1
        self.sc_power_setting = 1
        self._hw_mgr_server = None
        self._hw_mgr_lock = utils.Lock(self._log)
        self._hw_mgr_server = utils.set_power_state('fg', 'on', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        self._hw_mgr_server = utils.set_power_state('sc', 'on', self._hw_mgr_server, self._hw_mgr_lock, self._log)
                                        
    def run(self):        
        self._control_fgsc_power()
            
    def stop(self):
        self._hw_mgr_server = utils.set_power_state('fg', 'off', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        self._hw_mgr_server = utils.set_power_state('sc', 'off', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        
    def _control_fgsc_power(self):
        """If not in commanded state, send command to hw_mgr"""
        #self._log.info('Entering ControlFGSCPower._control_fgsc_power')
        [fg_power_state, self._hw_mgr_server] = utils.get_hw_status('fg_pwr', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        if fg_power_state is not None:
            #self._log.info('  fg_power_state is %d' % fg_power_state)
            if fg_power_state != self.fg_power_setting:
                if self.fg_power_setting == 1:
                    self._hw_mgr_server = utils.set_power_state('fg', 'on', self._hw_mgr_server, self._hw_mgr_lock, self._log)
                else:
                    self._hw_mgr_server = utils.set_power_state('fg', 'off', self._hw_mgr_server, self._hw_mgr_lock, self._log)                   
        [sc_power_state, self._hw_mgr_server] = utils.get_hw_status('sc_pwr', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        if sc_power_state is not None:
            #self._log.info('  sc_power_state is %d' % sc_power_state)
            if sc_power_state != self.sc_power_setting:
                if self.sc_power_setting == 1:
                    self._hw_mgr_server = utils.set_power_state('sc', 'on', self._hw_mgr_server, self._hw_mgr_lock, self._log)
                else:
                    self._hw_mgr_server = utils.set_power_state('sc', 'off', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        #self._log.info('Leaving ControlFGSCPower._control_fgsc_power')
