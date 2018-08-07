# Hardware Manager Configuration

import logging
import global_config

# Process name
proc_mnemonic =                 'hw'
proc_name =                     'hw_mgr'
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
base_port = global_config.hw_mgr_base_port
console_port =                  base_port + 0
XMLRPC_port =                   base_port + 40
XMLRPC_URL =                    ''.join(('http://localhost:', str(XMLRPC_port)))

# Miscellaneous
accept_sigint =                 True
daemonize =                     False

# Temp file storage dir
temp_dir =                      ''.join((global_config.temp_dir, proc_name, '/'))

# Max data file storage period, seconds
data_file_storage_period =      60 * 10
# Max data file storage size, bytes
data_file_max_size =            1024 * 150

# Overcurrent reset dwell period
over_cur_reset_dwell =           0.30

# The TS-7260 ADC has significant offset
# and gain errors that must be corrected
# in software.
# The offset and gain for every board is
# different, so each board is calibrated
# individually.  The measured gain and offset
# for each board is stored in the following
# dictionary.
# The dictionary key is the TS-7260 CPU serial
# number.
adc_params = { '000000009254ca35': [0.022, 0.9811],
               '000000009255788c': [0.021, 0.9843],
               '000000009227d6e1': [0.022, 0.9796],
			   '0000000092282748': [0.024, 0.9914],
			   '00000000922e522e': [0.023, 0.9923],
			   '00000000922e5190': [0.023, 0.9843],
			   '00000000923d5c57': [0.025, 0.9884]}
			   
			   


