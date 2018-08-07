#! /usr/bin/python

import utils
import global_config

if __name__ == '__main__':
    """ Start all the aal-pip processes"""
    
    processes = ["cpu_load_wd.py",
                 "file_svr.py",
                 "super.py",
                 "svr_proxy.py",
                 "modem_svr.py",
                 "hf_mgr.py",
                 "sc_mgr.py",
                 "fg_mgr.py",
                 "cases_mgr.py",
                 "usb_mgr.py",
                 "gps_mgr",
                 "hw_mgr.py"]
                 
    print ('AAL-PIP software version %s' % global_config.sw_version_number)
    for process in reversed(processes):
        if utils.process_is_running(process):
            print '%s is already running' % process
            continue
        print 'Starting %s' % process
        utils.start_process(process)
        utils.wait(2.0)
    for i in range(3):
        if utils.path_exists('/dev/sda1'):
            if not utils.path_exists('/mnt/usbflash'):
                utils.call_subprocess('mkdir -p /mnt/usbflash')
            utils.call_subprocess('mount /dev/sda1 /mnt/usbflash')
            if not utils.path_exists('/mnt/usbflash/data'):
                utils.call_subprocess('mkdir -p /mnt/usbflash/data')
            break
        utils.wait(2)
