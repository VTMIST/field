import time

import super_config
import svr_proxy_config
import utils

class MonitorRUDICSComm:
    """Reboot if RUDICS comm is lost for a long period"""  
    def __init__(self, log):
        self._log = log
        self._comm_state = 'init'
        self._timer = time.time()
        self._rebooting = False
                                        
    def run(self):
        if not self._rebooting:
            self._check_comm()
            
    def stop(self):
        pass
                
    def _check_comm(self):
        """Reboot if there hasn't been a RUDICS connection for an
        extended period or if we have been connected for
        an unbelievably long time.
        """
        if self._comm_state is 'init':
            #self._log.debug('comm_state is init')
            self._timer = time.time()
            self._comm_state = 'starting_up'
            return
        elif self._comm_state is 'starting_up':
            #self._log.debug('comm_state is starting_up')
            if self._connected():
                #self._log.info('Connected to RUDICS server')
                self._timer = time.time()
                self._comm_state = 'connected'
                return
            if utils.get_et_secs(self._timer) > super_config.comm_max_init_time:
                self._log.error('Rebooting - no initial RUDICS connection')
                utils.reboot()
                return
        elif self._comm_state is 'connected':
            #self._log.debug('comm_state is connected')
            if not self._connected():
                #self._log.info('Disconnected from RUDICS server')
                self._timer = time.time()
                self._comm_state = 'disconnected'
                return              
            if utils.get_et_secs(self._timer) > super_config.comm_max_up_time:
                self._log.error('Rebooting - exceeded max RUDICS connect time')
                self._rebooting = True
                utils.reboot()
                return
        elif self._comm_state is 'disconnected':
            #self._log.debug('comm_state is disconnected')
            if self._connected():
                #self._log.info('Connected to RUDICS server')
                self._timer = time.time()
                self._comm_state = 'connected'
                return
            if utils.get_et_secs(self._timer) > super_config.comm_max_down_time:
                self._log.error('Rebooting - exceeded max RUDICS disconnect time')
                self._rebooting = True
                utils.reboot()
                return
        else:
            self._log.error('Unknown state value in CommWatchdog._check_comm()')           
        
    def _connected(self):
        """Return True if currently connected to the RUDICS server"""
        if not utils.path_exists(svr_proxy_config.connect_time_file):
            # Haven't connected yet
            #self._log.debug('Not connected to RUDICS server')
            return False
        if not utils.path_exists(svr_proxy_config.disconnect_time_file):
            # Haven't disconnected yet
            #self._log.debug('Connected to RUDICS server')
            return True   
        last_connect_time = utils.get_file_mod_time(svr_proxy_config.connect_time_file)
        last_disconnect_time = utils.get_file_mod_time(svr_proxy_config.disconnect_time_file)
        connected = last_connect_time > last_disconnect_time
        #if not connected:
        #    self._log.debug('Not connected to RUDICS server')
        #else:
        #    self._log.debug('Connected to RUDICS server')
        return connected
            
