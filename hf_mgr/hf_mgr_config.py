# HF Manager Configuration

import logging
import global_config

# Process name
proc_mnemonic =                 'hf'
proc_name =                     'hf_mgr'
exe_file_name =                 ''.join((proc_name, '.py'))

# Log name
log_name =                      proc_name

# Logging
log_dir =                       global_config.field_log_dir
log_file_max_bytes =            50000
log_files_backup_files =        1

# Logging levels
#DEBUG | INFO | WARNING | ERROR | CRITICAL
log_level =                     logging.DEBUG

# Miscellaneous
accept_sigint =                 True
daemonize =                     False

# Temp file storage dir
temp_dir =                      ''.join((global_config.temp_dir, proc_name, '/'))

# Serial port
serial_device =                 '/dev/ttyS3'
baud_rate =                     9600

# Command timeouts
autobaud_timeout =              5
default_cmd_timeout =           5

# Test parameters
num_systems =                   5
test_period =                   10 * 60
tx_period =                     test_period / num_systems
tx_dead_time =                  10
hf_tx_bit_rate =                50
			  
# System-dependent information
class sys_info_item:
    def __init__(self,
                    cpu_sn_,
                    call_sign_,
                    sys_name_,
                    sys_num_,
                    tone_coeff_2_,
                    tone_coeff_1_,
                    tone_coeff_0_,
                    tone_shift_):
        self.cpu_sn = cpu_sn_
        self.call_sign = call_sign_
        self.sys_name = sys_name_
        self.sys_num = sys_num_
        self.tone_coeff_2 = tone_coeff_2_
        self.tone_coeff_1 = tone_coeff_1_
        self.tone_coeff_0 = tone_coeff_0_
        self.tone_shift = tone_shift_
sys_info =   [ sys_info_item('00000000922e522e', "KC4PGA", "sys_3", 3, 0.0867, -0.8079, 1318.4, 170),
			   sys_info_item('0000000092282748', "KC4PGB", "sys_4", 4, 0.0660, -2.0019, 1214.7, 170),
			   sys_info_item('00000000922e5190', "KC4PGC", "sys_5", 5, 0.0304, -3.5121, 1428.8, 170),
			   sys_info_item('00000000923d5c57', "KC4PGD", "sys_6", 6, 0.0316, -3.5269, 1422.7, 170),			   
			   sys_info_item('000000009254f5e0', "KC4PGE", "sys_7", 7, 0.0660, -2.0019, 1314.7, 170) ]

			   

