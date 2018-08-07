import time
import xmlrpclib

import hw_mgr_config
import super_config
import utils

class ControlTemp:
    """Control the electronics temp using the heater""" 
    def __init__(self, log):
        """
        """
        self._log = log
        self.setpoint = super_config.temp_default_setpoint
        self._hysteresis = super_config.temp_hysteresis
        self._htr_desired_state = 0
        self._hw_mgr_server = None
        self._hw_mgr_lock = utils.Lock(self._log)
                                        
    def run(self):
        self._control_temp()
            
    def stop(self):
        self._hw_mgr_server = utils.set_power_state('htr', 'off', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        
    def _control_temp(self):
        [temp, self._hw_mgr_server] = utils.get_hw_status('router_temp', self._hw_mgr_server, self._hw_mgr_lock, self._log)       
        if temp is None:
            self._log.error('Could not get router board temp from hw_mgr')
            return        
        if temp > (self.setpoint + self._hysteresis):
            self._htr_desired_state = 0
        if temp < (self.setpoint - self._hysteresis):
            self._htr_desired_state = 1       
        [htr_state, self._hw_mgr_server] = utils.get_hw_status('htr_pwr', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        if htr_state is None:
            self._log.error('Could not get heater power status from hw_mgr')
            return       
        if htr_state != self._htr_desired_state:
            if self._htr_desired_state == 1:
                self._hw_mgr_server = utils.set_power_state('htr', 'on', self._hw_mgr_server, self._hw_mgr_lock, self._log)
            else:
                self._hw_mgr_server = utils.set_power_state('htr', 'off', self._hw_mgr_server, self._hw_mgr_lock, self._log)                
    
