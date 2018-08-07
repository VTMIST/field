import time
import xmlrpclib

import hw_mgr_config
import utils

class RefreshStatus:
    """Refresh hardware status periodically"""
    def __init__(self, log):
        self._log = log
        self._hw_mgr_svr_proxy = None
                                        
    def run(self):
        self._refresh_status()
        
    def stop(self):
        pass

    def _refresh_status(self):
        self._execute_refresh_cmd()
                
    def _execute_refresh_cmd(self):
        """Execute the hw_mgr XMLRPC refresh command.
            Return True if successful.
        """
        succeeded = True
        if self._hw_mgr_svr_proxy is None:
            self._hw_mgr_svr_proxy = utils.get_XMLRPC_server_proxy(hw_mgr_config.XMLRPC_URL, self._log)
            if self._hw_mgr_svr_proxy is None:
                self._log.error('RefreshStatus._execute_refresh_cmd: Could not create hw_mgr XMLRPC server proxy.')
                succeeded = False
        if succeeded:
            try:
                status_value = self._hw_mgr_svr_proxy.refresh()
            except Exception, e:
                self._log.error('RefreshStatus._execute_refresh_cmd: XMLRPC call to hw_mgr refresh failed.  %s' % e)
                self._hw_mgr_svr_proxy = None
                succeeded = False
        return succeeded
