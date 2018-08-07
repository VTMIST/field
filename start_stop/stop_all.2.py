#! /usr/bin/python

import utils

if __name__ == '__main__':
    """ Stop all the aal-pip processes"""
    
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
                 
    for process in processes:
        if not utils.process_is_running(process):
            print '%s is not running' % process
            continue
        print 'Stopping %s' % process
        utils.stop_process_by_name(process)
    #utils.wait(5)
    #utils.call_subprocess('sync')
    #utils.wait(5)
    
