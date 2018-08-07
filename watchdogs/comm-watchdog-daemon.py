#! /usr/bin/python

import time
import threading
import sys

import utils
import svr_proxy_config

"""
    This is a stand-alone program that reboots
    with the golden code if:
    - A RUDICS connection not established within
        two hours of a reboot
    - No RUDICS connection occurs during a
        contiguous 24 hour period
    - No RUDICS disconnection occurs during a
        contiguous 24 hour period
"""
polling_period = 20
max_init_interval = 2 * 60 * 60
max_up_time_interval = 24 * 60 * 60
max_down_time_interval = 24 * 60 * 60
comm_state = 'init'
timer = 0

def _run_watchdog():
    global polling_period
    global comm_state
    comm_state = 'init'
    print 'comm-watchdog: state is init'
    while True:
        _check_comm()
        utils.wait(polling_period)
        
def _check_comm():
    """Reboot if comm is messed up"""
    global max_init_interval
    global max_up_time_interval
    global max_down_time_interval
    global comm_state
    global timer

    if comm_state is 'init':
        timer = time.time()
        print 'comm-watchdog: state is starting_up'
        comm_state = 'starting_up'
        return
    elif comm_state is 'starting_up':
        if _connected():
            timer = time.time()
            print 'comm-watchdog: state is connected'
            comm_state = 'connected'
            return
        if utils.get_et_secs(timer) > max_init_interval:
            print 'comm-watchdog: rebooting, no initial connection'
            utils.reboot_golden_code()
            comm_state = 'waiting_to_die'
            return
    elif comm_state is 'connected':
        if not _connected():
            timer = time.time()
            print 'comm-watchdog: state is disconnected'
            comm_state = 'disconnected'
            return              
        if utils.get_et_secs(timer) > max_up_time_interval:
            print 'comm-watchdog: rebooting, exceeded max connect time'
            utils.reboot_golden_code()
            comm_state = 'waiting_to_die'
            return
    elif comm_state is 'disconnected':
        if _connected():
            timer = time.time()
            print 'comm-watchdog: state is connected'
            comm_state = 'connected'
            return
        if utils.get_et_secs(timer) > max_down_time_interval:
            print 'comm-watchdog: rebooting, exceeded max disconnect time'
            utils.reboot_golden_code()
            comm_state = 'waiting_to_die'
            return
    elif comm_state is 'waiting_to_die':
        return
    else:
        print 'comm-watchdog: Unknown state value.  Rebooting with golden code.'
        utils.reboot_golden_code()
        comm_state = 'waiting_to_die'
                   
        
def _connected():
    """Return True if currently connected to the RUDICS server"""
    if not utils.path_exists(svr_proxy_config.connect_time_file):
        # Haven't connected yet
        print '_connected: connect_time_file does not exist'
        return False
    if not utils.path_exists(svr_proxy_config.disconnect_time_file):
        # Haven't disconnected yet
        print '_connected: disconnect_time_file does not exist'
        return True   
    last_connect_time = utils.get_file_mod_time(svr_proxy_config.connect_time_file)
    last_disconnect_time = utils.get_file_mod_time(svr_proxy_config.disconnect_time_file)
    connected = last_connect_time > last_disconnect_time
    print '_connected: returning %s' % str(connected)
    return connected
        
                        
if __name__ == '__main__':
    utils.daemonize()
    _run_watchdog()
            
    
