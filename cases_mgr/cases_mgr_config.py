# Search Coil Magnetometer Instrument Manager Configuration

import logging
import global_config

# Process name
proc_mnemonic =                 'cases'
proc_name =                     'cases_mgr'
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
base_port = global_config.cases_mgr_base_port
#if global_config.use_alt_ports:
#    base_port = base_port + global_config.alt_port_offset

console_port =                  base_port + 0
XMLRPC_port =                   base_port + 40
XMLRPC_URL =                    ''.join(('http://localhost:', str(XMLRPC_port)))

# Miscellaneous
accept_sigint =                 True
daemonize =                     False

# Temp file storage dir
temp_dir =                      ''.join((global_config.temp_dir, proc_name, '/'))

# Instrument serial port
serial_device =                 '/dev/ttyS2'
baud_rate =                     115200

# Max data file storage period, seconds
data_file_storage_period =      60 * 10
# Max data file storage size, bytes
data_file_max_size =            1024 * 75

# Maximum time gap allowed between bytes in a packet, seconds
max_interbyte_gap =             0.5


