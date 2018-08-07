# Fluxgate Mag Instrument Manager Configuration

import logging
import global_config

# Process name
proc_mnemonic =                 'fg'
proc_name =                     'fg_mgr'
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
base_port = global_config.fg_mgr_base_port

console_port =                  base_port + 0
XMLRPC_port =                   base_port + 40
XMLRPC_URL =                    ''.join(('http://localhost:', str(XMLRPC_port)))

# Miscellaneous
accept_sigint =                 True
daemonize =                     False

# Temp file storage dir
temp_dir =                      ''.join((global_config.temp_dir, proc_name, '/'))

# Instrument serial port
serial_device =             '/dev/ttyTS0'
baud_rate =                 9600

# Maximum allowable gap between instrument data packets
max_data_pkt_gap =          1.1

# Maximum packet arrival time jitter around the UTC start of second,
#   in microseconds
max_pkt_jitter =            300000



