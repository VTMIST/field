import time
import xmlrpclib

import hw_mgr_config
import super_config
import utils

class ControlGPSPower:
    """Control the Garmin GPS receiver power
    based on the current sync age  
    """ 
    def __init__(self, log):
        self._log = log
        self._max_sync_age = super_config.gps_max_sync_age
        self._hw_mgr_server = None
        self._hw_mgr_lock = utils.Lock(self._log)
                                        
    def run(self):
        self._control_gps_power()
        
    def stop(self):
        utils.set_power_state('gps', 'off', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        
    def _control_gps_power(self):
        [sync_age, self._hw_mgr_server] = utils.get_hw_status('sync_age', self._hw_mgr_server, self._hw_mgr_lock, self._log)
        if sync_age is None:
            self._log.error('Could not get sync_age from hw_mgr')
            return
        if sync_age < self._max_sync_age:
            # gps power should be off
            [status, self._hw_mgr_server] = utils.get_hw_status('gps_pwr', self._hw_mgr_server, self._hw_mgr_lock, self._log)
            if (status is not None) and (status == 1):
                self._hw_mgr_server = utils.set_power_state('gps', 'off', self._hw_mgr_server, self._hw_mgr_lock, self._log)        
        if sync_age > self._max_sync_age:
            # gps power should be on
            [status, self._hw_mgr_server] = utils.get_hw_status('gps_pwr', self._hw_mgr_server, self._hw_mgr_lock, self._log)
            if (status is not None) and (status == 0):
                self._hw_mgr_server = utils.set_power_state('gps', 'on', self._hw_mgr_server, self._hw_mgr_lock, self._log)
    
