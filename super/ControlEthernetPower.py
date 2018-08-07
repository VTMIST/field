import time

import utils

class ControlEthernetPower:
    """Control the ethernet interface power.
    Check to see if the eth0 link status is 'UP'.
    If not, turn ethernet power off.
    """ 
    def __init__(self, log):
        self._log = log
        self._hw_mgr_server = None
        self._hw_mgr_lock = utils.Lock(self._log)
                                        
    def run(self):
        self._control_ethernet_power()
        
    def stop(self):
        pass
        
    def _control_ethernet_power(self):
        """Turn ethernet power off if the link is not up"""
        (output, error) = utils.call_subprocess('ifconfig eth0')
        if output.find('RUNNING') > -1:
            self._log.info('Ethernet cable is connected.  Leaving ethernet power on')
        else:
            self._log.info('Ethernet cable is not connected..  Turning ethernet power off')
            self._hw_mgr_server = utils.set_power_state('ethernet', 'off', self._hw_mgr_server, self._hw_mgr_lock, self._log)
    
