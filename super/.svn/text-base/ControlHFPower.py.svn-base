import time
import xmlrpclib

import hw_mgr_config
import super_config
import utils
from datetime import datetime

        
class ControlHFPower:
    """Control the HF radio power
    """ 
    def __init__(self, log):
        self.master_power_enable = 0    # 0 = off, 1 = on    
        self._log = log
        self._hw_mgr_svr_proxy = None
        self._temp_valid = False
        self._over_temp = False
        self._under_temp = False
        self._power_state = None
        self._thermostat_switch_on = True
        self._temp = 0
        self._hf_sched_state = 1
        self._hf_stop_time = None
        self._hw_mgr_lock = utils.Lock(self._log)
        self._hw_mgr_svr_proxy = utils.set_power_state('hf', 'off', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)
        # True if master_power_enable has sole control of power. Used only for testing.
        self._manual_power_override = False
         
    def run(self):
        self._control_power()
        
    def stop(self):
        utils.set_power_state('hf', 'off', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)       
        
    def _control_power(self):
        """Turn HF power on or off depending on:
            - Availability of current HF power state
            - Availability of router board temp
            - Router board temp
            - HF power schedule
            - self._master_power_enable
        """
        power_state_is_known = self._get_power_state()
        temp_is_known = self._get_temp()
        thermostat_votes_yes = self._run_thermostat()
        scheduler_votes_yes = self._run_scheduler()
                     
        hf_should_be_on = power_state_is_known \
                          and temp_is_known \
                          and thermostat_votes_yes \
                          and scheduler_votes_yes
        
        # used only for software testing               
        if self._manual_power_override:
            hf_should_be_on = True
            
        if hf_should_be_on:
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
                    utils.get_hw_status('hf_pwr', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)
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
            HF should be powered up.              
        """
        temp_valid = self._temp is not None      
        if temp_valid != self._temp_valid:
            if temp_valid:
                self._log.info('HF (router board) temp is valid')
            else:
                self._log.error('HF  (router board) temp is NOT valid')
            self._temp_valid = temp_valid
            
        if temp_valid:
            over_temp = self._temp > super_config.hf_power_off_temp
            under_temp = self._temp < super_config.hf_power_on_temp
            if over_temp != self._over_temp:
                if over_temp:
                    self._log.info('HF (router board) temp rose above the high setpoint')
                    self._thermostat_switch_on = False
            if under_temp != self._under_temp:
                if under_temp:
                    self._log.info('HF (router board) temp dropped below the low setpoint')
                    self._thermostat_switch_on = True
            self._over_temp = over_temp
            self._under_temp = under_temp
        return self._temp_valid and self._thermostat_switch_on
        
    def _run_scheduler(self):
        """ Based on the HF run schedule,
            determine if HF should be powered up at this time.
            Return True if HF should be powered up.
        """               
        if (self._hf_sched_state == 1):
            item = self._get_sched_start_item(datetime.now())
            if item == None:
                return False
            self._hf_stop_time = item.stop_time
            self._hf_sched_state = 2
            return True     
        elif (self._hf_sched_state == 2):
            now = datetime.now()
            if (now.hour == self._hf_stop_time.hour) and (now.minute == self._hf_stop_time.minute):
               self._hf_sched_state = 1
               return False
            return True
                      
    def _turn_power_on_or_off(self, desired_power_state):
        """ Turn HF on or off if it is not in the desired_power_state.
            desired_power_state:
                0 = off
                1 = on
        """
        if self._power_state != desired_power_state:
            if desired_power_state == 1:
                self._hw_mgr_svr_proxy = utils.set_power_state('hf', 'on', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)
                self._log.info('Turned HF power on')
            else:
                self._hw_mgr_svr_proxy = utils.set_power_state('hf', 'off', self._hw_mgr_svr_proxy, self._hw_mgr_lock, self._log)
                self._log.info('Turned HF power off')

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
        
        self._log.info(    '  master_pwr_enable   = %s' % str(self.master_power_enable))
        self._log.info(    '  manual_pwr_override = %s' % str(self._manual_power_override))
        self._log.info(    '  hf_sched_state      = %d' % self._hf_sched_state)
        if self._hf_sched_state == 2:
            self._log.info('  hf_stop_time        = %s' % str(self._hf_stop_time))
         
    def _get_sched_start_item(self, the_time):
        """ Return an item from one of the super_config HF schedules
            if the item.start's hour and minute match the_time's
            hour and minute.
            Return None otherwise.
        """
        for item in super_config.hf_schedule:
            if (item.start_time.hour == the_time.hour) and (item.start_time.minute == the_time.minute):
                return item
        return None
         
                
