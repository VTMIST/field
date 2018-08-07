#! /usr/bin/python

# AAL-PIP Hardware Manager
import sys
import threading
import Queue
import xmlrpclib
import math
import time
import copy

import utils
import logs
import global_config
import fg_mgr_config
import hw_mgr_config
from BasicXMLRPCThread import BasicXMLRPCThread
from SockConsole import SockConsole


# Global Status Dictionary
status = {}
            
# Some global values used to speed up
#  temperature calculations
a = 1.40408e-3
b = 2.36858e-4
c = 7.10570e-8
d = 9.56178e-8

# The default ADC offset and gain
adc_offset = 0.0
adc_gain = 1.0

# Global subprocess mutex
subprocess_lock = None

def garmin_to_degs(garm):
    """Convert a Garmin format lat or long into
    a floating pt number of degrees
    """
    sign = 1.0
    if garm < 0.0:
        garm = -garm
        sign = -1.0
    degs = garm // 100.0
    minutes = garm - (degs * 100.0)
    frac_deg = minutes * (1.0/60.0)
    return (degs + frac_deg) * sign
            
            
def refresh_status(console, log):
    """Update the global status dict with current status"""
    #log.debug('Calling refresh_sbcctl_status()')
    refresh_sbcctl_status(log)
    #log.debug('Calling refresh_fg_status()')
    refresh_fg_status(log)
    #log.debug('Calling refresh_sys_time_status()')
    refresh_sys_time_status(log)
    #log.debug('Calling refresh_uptime_status()')   
    refresh_uptime_status(log)
      

def refresh_uptime_status(log):
    """Update uptime, mem usage and CPU load status"""
    global status
    global subprocess_lock
    
    subprocess_lock.acquire()
    [uptime, stderr] = utils.call_subprocess('uptime')
    subprocess_lock.release()
    status['uptime'] = uptime    


def refresh_sys_time_status(log):
    """Update the system time status"""
    global status
    global subprocess_lock
    
    subprocess_lock.acquire()
    [time_stat, stderr] = utils.call_subprocess('cat /proc/gps_pps')
    subprocess_lock.release()
    # time_stat looks like:
    #     Sync Age,Sys Time Error,Lat,Long
    #     1284036102,0.0,0.0,0.0
    # or:
    #     Sync Age,Sys Time Error,Lat,Long
    #     60,-0.996319,4217.6544,-08342.6943
    status['sync_age'] = 0
    status['sys_time_error'] = 0.0
    status['lat'] = 0.0
    status['long'] = 0.0
    lines = time_stat.split('\n')
    if len(lines) < 2:
        # gps_pps driver not running
        return
    if lines[0].split(',')[0] != 'Sync Age':
        return
    fields = lines[1].split(',')
    status['sync_age'] = int(fields[0])
    status['sys_time_error'] = float(fields[1])
    status['lat'] = garmin_to_degs(float(fields[2]))
    status['long'] = garmin_to_degs(float(fields[3]))
    # Iridium Time Fix JAN2018
    if status['sync_age'] > 10000:
        status['sync_age'] = utils.get_iridium_time()


def refresh_fg_status(log):
    """Update the fluxgate temp status"""
    global status
    status['fg_elec_temp'] = 0.0
    status['fg_sens_temp'] = 0.0
    try:
        fg_mgr = xmlrpclib.Server(fg_mgr_config.XMLRPC_URL)
    except Exception, e:
        log.error('Could not connect to fluxgate manager XML-RPC server.  %s' % e)
        return
    try:
        elec_temp = fg_mgr.get_elec_temp()
        sensor_temp = fg_mgr.get_sensor_temp()
    except Exception, e:
        log.error('XMLRPC call to fg_mgr failed.  %s' % e)
        return
    status['fg_elec_temp'] = float(elec_temp)
    status['fg_sens_temp'] = float(sensor_temp)
    
    
def refresh_sbcctl_status(log):
    """Parse the status info returned by sbcctl and
    store it in global status dict
    """
    global status
    
    executable = ''.join([global_config.field_bin_dir, '/sbcctl'])
    subprocess_lock.acquire()
    #log.debug('refresh_sbcctl_status(): Calling utils.call_subprocess')
    (con_out, con_err) = utils.call_subprocess([executable, 'status'])
    #log.debug('refresh_sbcctl_status(): Returned from utils.call_subprocess')
    subprocess_lock.release()
    if (con_out is None) and (con_err is None):
        log.error('utils.subprocess failed')
        return
    if con_err:
        log.error('Error from sbcctl status command: %s' % con_err)
        
    #log.debug('refresh_sbcctl_status(): starting sbcctl output parsing')
    lines = con_out.split('\n')
    status['sys_date'] = get_str(lines[2], 1)
    status['sys_time'] = get_str(lines[2], 2)
    status['irid_pwr'] = get_int(lines[6], 2)
    status['fg_pwr'] = get_int(lines[7], 2)         
    status['sc_pwr'] = get_int(lines[8], 2)         
    status['cases_pwr'] = get_int(lines[9], 2)          
    status['hf_pwr'] = get_int(lines[10], 2)          
    status['htr_pwr'] = get_int(lines[11], 2)          
    status['gps_pwr'] = get_int(lines[12], 2)          
    status['ethernet_pwr'] = get_int(lines[48], 1)          
    status['usb_pwr'] = get_int(lines[49], 1)          
    status['pc104_pwr'] = get_int(lines[50], 1)          
    status['rs232_pwr'] = get_int(lines[51], 1)
    status['cpu_temp'] = get_float(lines[31], 1)
    status['router_temp'] = get_router_temp(lines[45], log)
    status['batt_1_temp'] = get_batt_temp(lines[39], log)
    status['batt_1_temp_raw_v'] = get_float(lines[39], 1)
    status['batt_2_temp'] = get_batt_temp(lines[40], log)
    status['batt_3_temp'] = get_batt_temp(lines[41], log)
    status['batt_1_volt'] = get_batt_v(lines[42])
    status['batt_2_volt'] = get_batt_v(lines[43])
    status['batt_3_volt'] = get_batt_v(lines[44])
    status['in_current'] = get_input_current(lines[46])
    status['in_current_adc'] = get_float(lines[46], 1)
    status['ovr_cur_status'] = get_int(lines[20], 2)
    status['ovr_cur_reset'] = get_int(lines[19], 2)
    status['jumper_2'] = get_int(lines[25], 1)
    status['jumper_3'] = get_int(lines[26], 1)
    status['jumper_4'] = get_int(lines[27], 1)
    status['jumper_5'] = get_int(lines[28], 1)
    status['jumper_6'] = get_int(lines[29], 1)
    #log.debug('refresh_sbcctl_status(): finished sbcctl output parsing')

    # Calculate input power
    #log.debug('refresh_sbcctl_status(): starting power calculation')

    V1 = status['batt_1_volt']
    V2 = status['batt_2_volt']
    V3 = status['batt_3_volt']
    I = status['in_current']
    V = V1
    if V2 > V:
        V = V2
    if V3 > V:
        V = V3    
    status['in_power'] = I * V
    #log.debug('refresh_sbcctl_status(): finished power calculation')



def status_to_console(console):
    """If the console is connected, write a formatted
    form of the current status to the console
    """
    if console.is_connected():
        console.write('\n'.join(format_status()) + '\n')


def format_status():
    """Format the current status.
    Return a tuple with one line per element.
    """
    global status
    parts = []
    parts.append('Power Switches:')
    parts.append(' Iridium:     %d' % status['irid_pwr'])
    parts.append(' Fluxgate:    %s' % status['fg_pwr']) 
    parts.append(' Search coil: %s' % status['sc_pwr']) 
    parts.append(' CASES:       %s' % status['cases_pwr']) 
    parts.append(' HF radio:    %s' % status['hf_pwr']) 
    parts.append(' Heater:      %s' % status['htr_pwr']) 
    parts.append(' Garmin GPS:  %s' % status['gps_pwr'])
    parts.append(' Ethernet:    %s' % status['ethernet_pwr'])
    parts.append(' USB:         %s' % status['usb_pwr'])
    parts.append(' PC104:       %s' % status['pc104_pwr'])
    parts.append(' RS-232:      %s' % status['rs232_pwr']) 
    parts.append('Temps:')
    parts.append(' CPU board:   %.2f C' % status['cpu_temp']) 
    parts.append(' Router brd:  %.2f C' % status['router_temp']) 
    parts.append(' Batt 1:      %.2f C' % status['batt_1_temp']) 
    parts.append('   raw volts: %.3f V' % status['batt_1_temp_raw_v']) 
    parts.append(' Batt 2:      %.2f C' % status['batt_2_temp']) 
    parts.append(' Batt 3:      %.2f C' % status['batt_3_temp'])
    parts.append(' FG sensor:   %.2f C' % status['fg_sens_temp'])
    parts.append(' FG elec:     %.2f C' % status['fg_elec_temp'])
    parts.append('Voltages:')
    parts.append(' Batt 1:      %.2f V' % status['batt_1_volt']) 
    parts.append(' Batt 2:      %.2f V' % status['batt_2_volt']) 
    parts.append(' Batt 3:      %.2f V' % status['batt_3_volt'])
    parts.append('Current:')
    parts.append(' Input:       %.3f A' % status['in_current'])
    #parts.append(' Raw V:       %.3f V' % status['in_current_adc'])
    #parts.append(' Corrected V: %.3f V' % corrected_adc_v(status['in_current_adc']))
    parts.append('Power:')
    parts.append(' Input:       %.3f W' % status['in_power'])
    parts.append('Overcurrent:')
    parts.append(' Status:      %d' % status['ovr_cur_status']) 
    parts.append(' Reset:       %d' % status['ovr_cur_reset'])
    parts.append('Jumpers:')
    parts.append(' J2:          %d' % status['jumper_2']) 
    parts.append(' J3:          %d' % status['jumper_3']) 
    parts.append(' J4:          %d' % status['jumper_4']) 
    parts.append(' J5:          %d' % status['jumper_5']) 
    parts.append(' J6:          %d' % status['jumper_6'])
    parts.append('Time and Position:')   
    parts.append(' Sys time:       %s' % ' '.join((status['sys_date'], status['sys_time'])))
    parts.append(' Sys time error: %.6f s' % status['sys_time_error'])
    parts.append(' UTC sync age:   %d s' % status['sync_age'])
    parts.append(' Latitude:       %.6f deg' % status['lat'])
    parts.append(' Longitude:      %.6f deg' % status['long'])
    parts.append('OS:')   
    parts.append(' Uptime:        %s' % status['uptime'])
    return parts    
        
    
def get_str(s, field):
    """Return a string field from a string"""
    return s.split()[field]
    
    
def get_int(s, field):
    """Return an integer from a string"""
    return int(s.split()[field])
    
    
def get_float(s, field):
    """Return a float from a string"""
    return float(s.split()[field])
    
        
def get_input_current(line):
    """Return an input current float"""
    adc_v = corrected_adc_v(float(line.split()[1]))
    return adc_v * 1.6997
    
    
def get_router_temp(line, log):
    """Return the router board thermistor temp float"""
    """
    Rt is thermistor temp in Ohms
    Vt is voltage measured by the ADC in Volts
    T is thermistor temperature in deg C
    a is 1.40408e-3
    b is 2.36858e-4
    c is 7.10570e-8
    d is 9.56178e-8
    
    Rt = (53200 * Vt) / (5.0 - Vt)
    T = 1/(a + b*ln(Rt) + c*(ln(Rt)^2) + d*(ln(Rt)^3)) - 273.15   
    """
    raw_v = float(line.split()[1])
    #log.debug('raw router Vt = %.3f' % raw_v)
    Vt = corrected_adc_v(raw_v)
    #log.debug('corrected router Vt = %.3f' % Vt)
    if Vt < 0.001:
        Vt = 0.001
    Rt = (53200.0 * Vt) / (5.0 - Vt)
    #log.debug('router Rt = %.3f' % Rt)
    lnRt = math.log(Rt)
    lnRt2 = lnRt * lnRt
    lnRt3 = lnRt * lnRt2
    return 1.0/(a + b*lnRt + c*lnRt2 + d*lnRt3) - 273.15


def get_batt_temp(line, log):
    """Return a battery thermistor temp float"""
    """
    Rt is thermistor temp in Ohms
    Vt is voltage measured by the ADC in Volts
    T is thermistor temperature in deg C
    a is 1.40408e-3
    b is 2.36858e-4
    c is 7.10570e-8
    d is 9.56178e-8
    
    Rt = (549000 * Vt) / (5.0 - Vt)
    T = 1/(a + b*ln(Rt) + c*(ln(Rt)^2) + d*(ln(Rt)^3)) - 273.15   
    """
    raw_v = float(line.split()[1])
    #log.debug('raw batt Vt = %.3f' % raw_v)
    Vt = corrected_adc_v(raw_v)
    #log.debug('corrected batt Vt = %.3f' % Vt)
    if Vt < 0.001:
        Vt = 0.001
    Rt = (549000.0 * Vt) / (5.0 - Vt)
    #log.debug('batt Rt = %.3f' % Rt)
    lnRt = math.log(Rt)
    lnRt2 = lnRt * lnRt
    lnRt3 = lnRt * lnRt2
    return 1.0/(a + b*lnRt + c*lnRt2 + d*lnRt3) - 273.15
    
        
def get_batt_v(line):
    """Return a battery voltage float"""
    adc_v = corrected_adc_v(float(line.split()[1]))
    return adc_v * 4.3887
    

def corrected_adc_v(adc_v):
    """ Return an ADC voltage corrected for offset and gain """
    corr_v = adc_v - adc_offset
    if (corr_v < 0.0):
        corr_v = 0.0
    return corr_v / adc_gain
      

def sbcctl_cmd(args, log):
    """Execute any sbcctl command.
    Does not return sbcctl console output
    args is a string of command arguments"""
    
    #log.debug('Entering sbcctl_cmd.  args = %s' % args)
    executable = ''.join([global_config.field_bin_dir, '/sbcctl'])
    exe_and_args = ' '.join([executable, args])
    #log.debug('  exe_and_args = %s' % exe_and_args)
    subprocess_lock.acquire()
    (con_out, con_err) = utils.call_subprocess(exe_and_args)
    subprocess_lock.release()
    if (con_out is None) and (con_err is None):
        log.error('utils.call_subprocess failed trying to execute: %s' % exe_and_args)
        #log.debug('Exiting sbcctl_cmd')
        return
    if con_err:
        log.error('Error from %s command: %s' % (exe_and_args, con_err))
    #log.debug('Exiting sbcctl_cmd')
                         

def _init_adc_params(log):
    """Get the ADC offset and gain for this
    TS-7260 board
    """
    global adc_offset
    global adc_gain
    global subprocess_lock
    
    cpu_sn = '?'
    subprocess_lock.acquire()
    [s, stderr] = utils.call_subprocess('cat /proc/cpuinfo')
    subprocess_lock.release()
    #log.debug('s = %s' % s)
    lines = s.split('\n')
    for line in lines:
        #log.debug('line = %s' % line)
        if line.find('Serial') != -1:
            fields = line.split()
            #log.debug('fields = %s' % repr(fields))
            cpu_sn = fields[2]
            break
    if cpu_sn in hw_mgr_config.adc_params:
        adc_offset = hw_mgr_config.adc_params[cpu_sn][0]
        adc_gain = hw_mgr_config.adc_params[cpu_sn][1]
    else:
        log.error('This CPU serial number is not in hw_mgr_config.py')         
        adc_offset = 0.0
        adc_gain = 1.0    
    log.info('cpu_sn = %s' % repr(cpu_sn))         
    log.info('adc_offset = %s' % str(adc_offset))
    log.info('adc_gain = %s' % str(adc_gain))
    

def _init_digital_IO(log):
    # DIO1 bit directions are set in the dio1 driver.
    # Set DIO2 bit directions.
    sbcctl_cmd('setdir DIO2 0 out', log)
    sbcctl_cmd('setdir DIO2 1 out', log)
    sbcctl_cmd('setdir DIO2 2 out', log)
    sbcctl_cmd('setdir DIO2 3 out', log)
    sbcctl_cmd('setdir DIO2 4 in', log)
    sbcctl_cmd('setdir DIO2 7 out', log)
    
    # Enable latched overcurrent detection
    sbcctl_cmd('setpin DIO2 7 off', log)
    
    # Clear possible overcurrent condition
    sbcctl_cmd('setpin DIO2 3 on', log)
    utils.wait(hw_mgr_config.over_cur_reset_dwell)
    sbcctl_cmd('setpin DIO2 3 off', log)

   
def _stop_dig_io():
    # Disables latched overcurrent detection
    sbcctl_cmd('setpin DIO2 7 on', log)    
    

class XMLRPCThread(BasicXMLRPCThread):
    """An extended BasicXMLRPCThread"""
    def __init__(self, host, port, console, log):
        BasicXMLRPCThread.__init__(self, host, port, log)
        self._log = log
        self._console = console
        self._exec_lock = utils.Lock(log)
        self._server.register_function(self.help)
        self._server.register_function(self.set_power)
        self._server.register_function(self.reset_overcurrent)
        self._server.register_function(self.status)
        self._server.register_function(self.get_status)
        self._server.register_function(self.get_full_status)
        self._server.register_function(self.refresh)
           
    def help(self):
        """ Show the available XMLRPC commands """
        self._exec_lock.acquire()
        if self._console.is_connected():
            msg = ''.join([ \
                '\nHardware manager XMLRPC commands\n',
                '> help\n',
                '> set_power <device> <state>\n',
                '       device:\n',
                '           irid | fg | sc | cases | hf | htr | gps |\n',
                '           usb | ethernet | pc104 | rs232| \n',
                '       state:\n',
                '           on | off\n',
                '> refresh\n',
                '       Refresh the full hardware status\n',
                '> status\n',
                '       Refresh and return full hardware status in readable form\n',
                '> get_status <name_of_status_value>\n',
                '       Return a single status value\n',
                '> get_full_status\n',
                '       Return entire status dictionary\n',
                '> reset_overcurrent\n',
                '       Reset a router board overcurrent condition\n',
                '> dis\n',
                '    Disconnect from console\n'
           ])
            self._console.write(msg)
            self._exec_lock.release()
        return 'OK'
        
    def set_power(self, device, state):
        """ Turn a single device on or off"""
        #self._log.debug('Entering set_power')
        ret_val = 'OK'
        self._exec_lock.acquire()
        device = device.lower()
        state = state.lower()
        
        if device == 'usb' or \
           device == 'ethernet' or \
           device == 'pc104' or \
           device == 'rs232':
            sbcctl_cmd(''.join([device, ' %s' % state]), self._log)        
        elif device == 'irid':
            sbcctl_cmd('setpin DIO1 0 %s' % state, self._log)
            self._control_PC104_power()
        elif device == 'fg':
            sbcctl_cmd('setpin DIO1 1 %s' % state, self._log)
        elif device == 'sc':
            sbcctl_cmd('setpin DIO1 2 %s' % state, self._log)
        elif device == 'cases':
            sbcctl_cmd('setpin DIO1 3 %s' % state, self._log)
            self._control_PC104_power()
        elif device == 'hf':
            sbcctl_cmd('setpin DIO1 4 %s' % state, self._log)
            self._control_PC104_power()
        elif device == 'htr':
            sbcctl_cmd('setpin DIO1 5 %s' % state, self._log)
        elif device == 'gps':
            sbcctl_cmd('setpin DIO1 6 %s' % state, self._log)
            self._control_PC104_power()
        else:
            self._log.error('Got invalid set_power XMLRPC cmd: device: %s, state: %s' % (device, state))
            #self._log.debug('Exiting set_power')
            ret_val = 'failed'
        self._exec_lock.release()
        #self._log.debug('Exiting set_power')
        return ret_val
        
    def reset_overcurrent(self):
        """Clear a router board overcurrent condition"""
        #self._log.debug('Entering reset_overcurrent')
        self._exec_lock.acquire()
        sbcctl_cmd('setpin DIO2 3 on', self._log)
        utils.wait(hw_mgr_config.over_cur_reset_dwell)
        sbcctl_cmd('setpin DIO2 3 off', self._log)
        self._exec_lock.release()
        #self._log.debug('Exiting reset_overcurrent')
        return 'OK'
        
    def refresh(self):
        #self._log.debug('Entering refresh')
        self._exec_lock.acquire()
        #self._log.debug('calling refresh_status()')
        refresh_status(self._console, self._log)
        self._exec_lock.release()
        #self._log.debug('Exiting refresh')
        return 'OK'
        
    def status(self):
        """Write the current status it to the console"""
        #self._log.debug('Entering status')
        ret_val = 'OK'
        self._exec_lock.acquire()
        try:
            status_to_console(self._console)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
            #self._log.debug('Exiting status')
            ret_val = 'failed'
        self._exec_lock.release()
        #self._log.debug('Exiting status')
        return ret_val
            
    def get_status(self, name_of_value):
        """Return a single status value"""
        global status
        #self._log.debug('Entering get_status. name_of_value = %s' % name_of_value)
        value = ''
        self._exec_lock.acquire()
        try:
            value = status[name_of_value]
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
            value = 'failed'
        self._exec_lock.release()
        #self._log.debug('Exiting _get_status')
        return value
        
    def get_full_status(self):
        """Return the entire status dictionary"""
        global status
        #self._log.debug('Entering get_full_status')
        self._exec_lock.acquire()
        all_values = copy.deepcopy(status)
        self._exec_lock.release()
        #self._log.debug('Exiting _get_full_status')
        return all_values
        
     
    def _control_PC104_power(self):
        """Turn the PC-104 bus power on and off as needed"""
        # Leave PC-104 power on because we need it
        #  for USB
        global status
        if status['pc104_pwr'] == 0:
            sbcctl_cmd('pc104 on', self._log)


def _init_status():
    global status
    status = {  'sys_time' : '00:00:00',
                'sys_date' : '0000-00-00',
                'irid_pwr' : 0,
                'fg_pwr' : 0,          
                'sc_pwr' : 0,          
                'cases_pwr': 0,          
                'hf_pwr' : 0,          
                'htr_pwr' : 0,          
                'gps_pwr' : 0,          
                'ethernet_pwr' : 0,          
                'usb_pwr' : 0,          
                'pc104_pwr' : 0,          
                'rs232_pwr' : 0,
                'cpu_temp' : 0.0,
                'router_temp' : 0.0,
                'batt_1_temp' : 0.0,
                'batt_2_temp' : 0.0,
                'batt_3_temp' : 0.0,
                'batt_1_temp_raw_v' : 0.0,
                'fg_elec_temp' : 0.0,
                'fg_sens_temp' : 0.0,
                'batt_1_volt' : 0.0,
                'batt_2_volt' : 0.0,
                'batt_3_volt' : 0.0,
                'in_current' : 0.0,
                'in_current_adc' : 0.0,
                'in_power' : 0.0,
                'ovr_cur_status' : 0.0,
                'ovr_cur_reset' : 0.0,
                'jumper_2' : 0.0,
                'jumper_3' : 0.0,
                'jumper_4' : 0.0,
                'jumper_5' : 0.0,
                'jumper_6' : 0.0,
                'sync_age' : 8888888,
                'sys_time_error' : 0.0,
                'lat' : 0.0,
                'long' : 0.0,
                'uptime' : ''}
        
           
def _run_mgr(log):
    """
        Run the hardware manager until terminated
    """
    global subprocess_lock
    
    log.info('')
    log.info('****** Starting hardware manager ******')
    subprocess_lock = utils.Lock(log)
    _init_status()   
    _init_digital_IO(log)
    _init_adc_params(log)
    
    try:
        console = SockConsole('localhost',
                            hw_mgr_config.console_port,
                            log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
    try:
        xmlrpc_thread = XMLRPCThread('localhost',
                            hw_mgr_config.XMLRPC_port, console, log)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
        sys.exit(1)
        
    while True:
        try:
            utils.wait(0.5)
            if not console.is_running():
                log.error('Console thread died unexpectedly')
                break
            if not xmlrpc_thread.is_running():
                log.error('XMLRPC server thread died unexpectedly')
                break
        except KeyboardInterrupt:
            if hw_mgr_config.accept_sigint:
                log.info('Got SIGINT (shutting down)')
                break
            else:
                log.info('Got SIGINT (ignored)')
        except Exception, e:
            # handle all unexpected application exceptions
            print '*** Unexpected exception in hw_mgr: %s' % e
            exc_type, exc_value, exc_traceback = sys.exc_info()
            utils.log_exc_traceback(exc_type, exc_value, exc_traceback, log)
            sys.exit(1)
            break
                   
    _stop_dig_io()                   
    console.stop()
    xmlrpc_thread.stop()
    utils.wait_for_child_threads()
    log.info('****** Exiting hardware manager ******')
    
    
if __name__ == '__main__':
    sys.setcheckinterval(global_config.check_interval)
    if hw_mgr_config.daemonize:
        utils.daemonize()
    log = logs.open(hw_mgr_config.log_name,
                    hw_mgr_config.log_dir,
                    hw_mgr_config.log_level,
                    file_max_bytes = hw_mgr_config.log_file_max_bytes,
                    num_backup_files = hw_mgr_config.log_files_backup_files)
    _run_mgr(log)

