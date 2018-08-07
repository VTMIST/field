# Search Coil Magnetometer Instrument Manager Configuration

import logging
import global_config

# Process name
proc_mnemonic =                 'sc'
proc_name =                     'sc_mgr'
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
base_port = global_config.sc_mgr_base_port

console_port =                  base_port + 0
XMLRPC_port =                   base_port + 40
XMLRPC_URL =                    ''.join(('http://localhost:', str(XMLRPC_port)))

# Miscellaneous
accept_sigint =                 True
daemonize =                     False

# Temp file storage dir
temp_dir =                      ''.join((global_config.temp_dir, proc_name, '/'))

# Instrument serial port
serial_device =                 '/dev/ttyAM0'
baud_rate =                     19200

# Data file storage
data_file_storage_period =      60 * 15

# Minimum inter-packet time gap
min_interpacket_gap =           0.15
packet_len =                    30

# Maximum allowable gap between instrument data packets
max_data_pkt_gap =              1.3

# Maximum packet arrival time jitter around the UTC start of second,
#   in microseconds
max_pkt_jitter =            300000


