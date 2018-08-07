
# Iridium RUDICS modem server configuration file

from datetime       import timedelta
import logging

import global_config

# Process name
proc_mnemonic =                 'modem_svr'
proc_name =                     'modem_svr'
exe_file_name =                 ''.join((proc_name, '.py'))

# Log name
log_name =                      proc_name
sim_log_name =                  ''.join((proc_name, '_sim'))

# Logging
log_dir =                       global_config.field_log_dir
log_file_max_bytes =            50000
log_files_backup_files =        1
log_all_data =                  False

# Logging levels
# DEBUG | INFO | WARNING | ERROR | CRITICAL
log_level =                     logging.INFO

# Modem server
connect_timeout =               timedelta(seconds=60)

# Kill connection if no data received withing rx_data_timeout seconds
rx_data_timeout =               90

# Port numbers
base_port =                     global_config.modem_svr_base_port

client_port =                   base_port + 0
XMLRPC_port =                   base_port + 1
XMLRPC_URL =                    ''.join(('http://localhost:', str(XMLRPC_port)))

# Miscellaneous
accept_sigint =                 True
daemonize =                     False
