# Console Program Configuration

import logging
import global_config
import fg_mgr_config
import sc_mgr_config
import cases_mgr_config
import svr_proxy_config
import modem_svr_config
import usb_mgr_config
import hw_mgr_config
import super_config

# Process name
proc_mnemonic =                 'cons'
proc_name =                     'console'
exe_file_name =                 ''.join((proc_name, '.py'))

# Log name
log_name =                      proc_name

# Logging
log_dir =                       global_config.field_log_dir
log_file_max_bytes =            50000
log_files_backup_files =        1

# Logging levels
#DEBUG | INFO | WARNING | ERROR | CRITICAL
log_level =                     logging.INFO

# Miscellaneous
accept_keyboard_interrupt =     True

# Parameters associated with process mnemonics 
proc_mne_params = {fg_mgr_config.proc_mnemonic: [fg_mgr_config.console_port,
                        fg_mgr_config.exe_file_name,
                        fg_mgr_config.XMLRPC_URL],
                    sc_mgr_config.proc_mnemonic: [sc_mgr_config.console_port,
                        sc_mgr_config.exe_file_name,
                        sc_mgr_config.XMLRPC_URL],
                    hw_mgr_config.proc_mnemonic: [hw_mgr_config.console_port,
                        hw_mgr_config.exe_file_name,
                        hw_mgr_config.XMLRPC_URL],
                    cases_mgr_config.proc_mnemonic: [cases_mgr_config.console_port,
                        cases_mgr_config.exe_file_name,
                        cases_mgr_config.XMLRPC_URL],
                    usb_mgr_config.proc_mnemonic: [usb_mgr_config.console_port,
                        usb_mgr_config.exe_file_name,
                        usb_mgr_config.XMLRPC_URL],
                    super_config.proc_mnemonic: [super_config.console_port,
                        super_config.exe_file_name,
                        super_config.XMLRPC_URL],
                    svr_proxy_config.proc_mnemonic: [None,
                        svr_proxy_config.exe_file_name,
                        svr_proxy_config.XMLRPC_URL],                     
                    'gps': [None,
                        'gps_mgr',
                        None],                        
                    modem_svr_config.proc_mnemonic: [None,
                        modem_svr_config.exe_file_name,
                        modem_svr_config.XMLRPC_URL]}
