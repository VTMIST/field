#! /usr/bin/python

# CPU Load Watchdog

import sys
import threading
import Queue
from datetime       import datetime,timedelta
import time

import utils
import logs
import cpu_load_wd_config
import global_config

        
class WDThread(threading.Thread):
    """ CPU load watchdog thread """
    def __init__(self, log, exit_callback=None):
        """
        """
        threading.Thread.__init__(self)
        self.setDaemon(False)
        self.name = 'cpu_load_wd'
        self._log = log
        self._stop_event = threading.Event()
        self._loop_period = 1.0
        self._poll_period = 20.0
        self._poll_loops = self._poll_period / self._loop_period
        self._poll_loop_cntr = 0
        self._cpu_load_max = 5.0
        self._running = False
        self._started = False
        self.start()
        while not self._started:
            utils.wait(0.05)
                                        
    def run(self):
        """The actual thread code"""
        self._log.info('Starting %s ' % self.name)
        self._running = True
        self._started = True

        while not self._stop_event.isSet():
            self._poll_loop_cntr += 1
            if self._poll_loop_cntr >= self._poll_loops:
                 self._poll_loop_cntr = 0;
                 self._check_cpu_load()
            #self._log.info('run(): _poll_loop_cntr is %d' % self._poll_loop_cntr)
            #self._log.info('run(): _poll_loops is %d' % self._poll_loops)
            utils.wait(self._loop_period)

        self._running = False
        #self._log.info('Stopping %s ' % self.name)
        self._log.info('Exiting %s ' % self.name)
        
    # Reboot the system if the five minute load average
    # is greater than self._cpu_load_max. 
    def _check_cpu_load(self):
        #self._log.info('Entering _check_cpu_load()')
        load = self._get_5_min_cpu_load()
        if load > self._cpu_load_max:
            self._log.info('CPU 5 minute load average is %f ' % load)
            self._log.info('CPU load is excessive, rebooting the system')
            utils.reboot()
            self._stop_event.set()
        #self._log.info('Leaving _check_cpu_load()')   

    # Get the 5 minute cpu load average using
    # using the uptime shell command
    def _get_5_min_cpu_load(self):
        #self._log.info('Entering _get_5_min_cpu_load()')
        (output, error) = utils.call_subprocess('uptime')
        #self._log.info('  uptime cmd output is %s ' % output)
        fields = output.split()
        num_fields = len(fields)
        load_index = num_fields - 2
        if load_index < 0:
            self._log.error('uptime parsing error, not enough fields')
            #self._log.error('Leaving _get_5_min_cpu_load()')
            return 0.0
        load_str = fields[load_index]
        #self._log.info('  load_str is %s ' % load_str)
        load_str = load_str.replace(",", "")
        #self._log.info('  returning %f ' % float(load_str))
        #self._log.info('Leaving _get_5_min_cpu_load()')
        return float(load_str)
              
    def is_running(self):
        return self._running
        
    def stop(self):
        """Stop this thread """
        if self._running:
            self._stop_event.set()
            self.join()
    
                
def _run_wd(log):
    """
        Run the watchdog until terminated
    """
    global gv
    log.info('')
    log.info('****** Starting CPU load watchdog ******')
    
    try:
        wd_thread = WDThread(log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)              
    while True:
        try:
            utils.wait(0.5)
            if not wd_thread.is_running():
                log.error('Watchdog thread died unexpectedly')
                break
        except KeyboardInterrupt:
            if cpu_load_wd_config.accept_sigint:
                log.info('Got SIGINT (shutting down)')
                break
            else:
                log.info('Got SIGINT (ignored)')
        except:
            sys.exit(1)
                   
    wd_thread.stop()
    utils.wait_for_child_threads()
    log.info('****** Exiting CPU load watchdog ******')
    
    
class GlobalVars:
    """ Global variables """
    def __init__(self):
        self.console = None
        
    
if __name__ == '__main__':
    sys.setcheckinterval(global_config.check_interval)
    if cpu_load_wd_config.daemonize:
        utils.daemonize()
    gv = GlobalVars
    log = logs.open(cpu_load_wd_config.log_name,
                    cpu_load_wd_config.log_dir,
                    cpu_load_wd_config.log_level,
                    file_max_bytes = cpu_load_wd_config.log_file_max_bytes,
                    num_backup_files = cpu_load_wd_config.log_files_backup_files)
    _run_wd(log)

