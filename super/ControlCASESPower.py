import time
import xmlrpclib

import hw_mgr_config
import super_config
import cases_mgr_config
import utils
from datetime import datetime
 

class ControlCASESPower:
    """Control the CASES receiver power
    """ 
    def __init__(self, log):
        self.master_power_enable = 1    # 0 = off, 1 = on    
        self.mode = "normal"            # "normal", "storm" or "update"
        self._log = log
        self._hw_mgr_svr_proxy = None
        self._temp_valid = False
        self._over_temp = False
        self._under_temp = False
        self._power_state = None
        self._thermostat_switch_on = True
        self._temp = 0
        self._hit_data_limit = False
        self._cases_sched_state = 1
        self._cases_stop_time = None
        self._cases_data_limit = None
        self._hw_mgr_lock = utils.Lock(self._log)
        self._hw_mgr_svr_proxy = utils.set_power_state('cases', 'off', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)
        self._power_down_pending = False
                                        
    def run(self):
        if self._power_down_pending:
            self._power_down_pending = False
            self._hw_mgr_svr_proxy = utils.set_power_state('cases', 'off', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)                           
            self._log.info('Turned CASES power off')
            return
        self._control_power()
        
    def stop(self):
        self._send_halt_cmd()
        utils.wait(10)
        utils.set_power_state('cases', 'off', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)       
                
    def _send_halt_cmd(self):
        """ Send an XMLRPC halt command to CASES """
        cases_mgr_svr_proxy = utils.get_XMLRPC_server_proxy(cases_mgr_config.XMLRPC_URL, self._log)
        if cases_mgr_svr_proxy is None:
            self._log.error('ControlCASES._send_halt_cmd: Could not create cases_mgr XMLRPC server proxy.')
            return
        try:
            status_value = cases_mgr_svr_proxy.halt()
        except Exception, e:
            self._log.error('ControlCASES._send_halt_cmd: cases_mgr XMLRPC halt cmd failed.  %s' % e)
            return
        self._log.info('Sent Halt command to CASES')
       
    def _control_power(self):
        """Turn CASES power on or off depending on:
            - Availability of current CASES power state
            - Availability of router board temp
            - Router board temp
            - CASES schedule
            - CASES data production limits
            - self._master_power_enable
        """
        power_state_is_known = self._get_power_state()
        temp_is_known = self._get_temp()
        thermostat_votes_yes = self._run_thermostat()
        scheduler_votes_yes = self._run_scheduler()
        
        if self.mode == "update":
            # ignore the scheduler if in update mode
            cases_should_be_on =    power_state_is_known \
                                and temp_is_known \
                                and thermostat_votes_yes
        else:                   
            cases_should_be_on =    power_state_is_known \
                                and temp_is_known \
                                and thermostat_votes_yes \
                                and scheduler_votes_yes
        if cases_should_be_on:
            desired_power_state = self.master_power_enable
        else:
            desired_power_state = 0        
        self._turn_power_on_or_off(desired_power_state)
        #self._log_power_cntl_info()
        
    def _get_power_state(self):
        """ Set self._power_state.
            Return True if the power state is known.
        """
        [self._power_state, self._hw_mgr_svr_proxy] = \
                    utils.get_hw_status('cases_pwr', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)
        return self._power_state != None
        
    def _get_temp(self):
        """ Set self._temp.
            Return True if the temp is known.
        """
        [self._temp, self._hw_mgr_svr_proxy] = \
                    utils.get_hw_status('router_temp', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)
        return self._temp != None       
                        
    def _run_thermostat(self):
        """ Set
                self._under_temp
                self._over_temp
                self._thermostat_switch_on
            Returns True if the thermostat decides that 
            CASES should be powered up.              
        """
        temp_valid = self._temp is not None      
        if temp_valid != self._temp_valid:
            if temp_valid:
                self._log.info('CASES (router board) temp is valid')
            else:
                self._log.error('CASES (router board) temp is NOT valid')
            self._temp_valid = temp_valid
            
        if temp_valid:
            over_temp = self._temp > super_config.cases_power_off_temp
            under_temp = self._temp < super_config.cases_power_on_temp
            if over_temp != self._over_temp:
                if over_temp:
                    self._log.info('CASES (router board) temp rose above the high setpoint')
                    self._thermostat_switch_on = False
            if under_temp != self._under_temp:
                if under_temp:
                    self._log.info('CASES (router board) temp dropped below the low setpoint')
                    self._thermostat_switch_on = True
            self._over_temp = over_temp
            self._under_temp = under_temp
        return self._temp_valid and self._thermostat_switch_on               
    
    def _run_scheduler(self):
        """ Based on the CASES run schedule and data production,
            determine if CASES should be powered up at this time.
            Return True if CASES should be powered up.
        """               
        if (self._cases_sched_state == 1):
            item = self._get_sched_start_item(datetime.now())
            if item == None:
                return False
            self._clear_data_production()
            self._cases_stop_time = item.stop_time
            self._cases_data_limit = item.data_limit
            self._cases_sched_state = 2
            return True     
        elif (self._cases_sched_state == 2):
            now = datetime.now()
            if ((now.hour == self._cases_stop_time.hour) and (now.minute == self._cases_stop_time.minute)) \
                   or self._data_limit_exceeded():
               self._cases_sched_state = 1
               return False
            return True
                       
    def _turn_power_on_or_off(self, desired_power_state):
        """ Turn CASES on or off if it is not in the desired_power_state.
            desired_power_state:
                0 = off
                1 = on
        """
        if self._power_state != desired_power_state:
            if desired_power_state == 1:
                self._hw_mgr_svr_proxy = utils.set_power_state('cases', 'on', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)
                self._log.info('Turned CASES power on')
            else:
                self._send_halt_cmd()
                # Allow halt cmd to take effect.
                # Power down the next time run() is called.
                self._power_down_pending = True
                
    def _clear_data_production(self):
        """ Clear the CASES data production
        """ 
        try:
            xmlrpc_svr = xmlrpclib.Server(cases_mgr_config.XMLRPC_URL)
            xmlrpc_svr.clear_data_production()
        except Exception, e:
            self._log.error('Exception in _clear_data_production: %s' % e)
            self._log.error('Could not clear CASES data production')
        
    def _data_limit_exceeded(self):
        """ Set self._hit_data_limit.
            Return True if data limit has been exceeded.
        """
        data_production = None
        try:
            xmlrpc_svr = xmlrpclib.Server(cases_mgr_config.XMLRPC_URL)
            data_production = xmlrpc_svr.get_data_production()
        except Exception, e:
            self._log.error('Exception in _data_limit_exceeded: %s' % e)
            self._log.error('Could not get data production from cases_mgr')
            return False
        hit_data_limit = data_production > self._cases_data_limit       
        if hit_data_limit != self._hit_data_limit:
            if hit_data_limit:
                self._log.info('Hit the CASES data production limit')
        self._hit_data_limit = hit_data_limit
        return hit_data_limit
                
    def _log_power_cntl_info(self):
        self._log.info('---------------------')
        
        if self._temp_valid:
            self._log.info('  temp                = %0.1f' % self._temp)
            self._log.info('  under_temp          = %s' % str(self._under_temp))
            self._log.info('  over_temp           = %s' % str(self._over_temp))
            self._log.info('  thermo_switch_on    = %s' % str(self._thermostat_switch_on))
        else:
            self._log.info('  temp                = not valid')
            self._log.info('  under_temp          = not valid')
            self._log.info('  over_temp           = not valid')
            self._log.info('  thermo_switch_on    = not valid')
            
        if self._power_state == None:
            self._log.info('  power_state         = not valid')
        else:
            self._log.info('  power_state         = %d' % self._power_state)
        
        self._log.info(    '  hit_data_limit      = %s' % str(self._hit_data_limit))
        self._log.info(    '  master_power_enable = %s' % str(self.master_power_enable))
        self._log.info(    '  cases_sched_state   = %d' % self._cases_sched_state)
        if self._cases_sched_state == 2:
            self._log.info( '  cases_stop_time     = %s' % str(self._cases_stop_time))
            self._log.info( '  cases_data_limit    = %d' % self._cases_data_limit)
            
    def _get_sched_start_item(self, the_time):
        """ Return an item from one of the super_config CASES schedules
            if the item.start's hour and minute match the_time's
            hour and minute.
            Return None otherwise.
        """
        if self.mode == 'normal' or self.mode == 'update':
            schedule = super_config.cases_normal_schedule
        elif self.mode == 'storm':
            schedule = super_config.cases_storm_schedule
        else:
            self._log.error('Unknown CASES operating mode')
            return None
        for item in schedule:
            if (item.start_time.hour == the_time.hour) and (item.start_time.minute == the_time.minute):
                return item
        return None
                 
            
            
            
            
            
            
            
            
            
            
            
            
