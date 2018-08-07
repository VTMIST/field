# Server Proxy Configuration

import logging
import global_config

# Process name
proc_mnemonic =                 'svr_proxy'
proc_name =                     'svr_proxy'
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

# Socket port numbers
base_port = global_config.svr_proxy_base_port
XMLRPC_port =                   base_port + 40
XMLRPC_URL =                    ''.join(('http://localhost:', str(XMLRPC_port)))

# Miscellaneous
accept_sigint =                 True
daemonize =                     False

# Times of last RUDICS connection and disconnection
# These files are "touched" whenever a RUDICS
#  connection is made or broken.
connect_time_file =             ''.join([global_config.flag_dir, '/connect_time'])
disconnect_time_file =          ''.join([global_config.flag_dir, '/disconnect_time'])

