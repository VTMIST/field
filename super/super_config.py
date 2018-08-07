# AAL-PIP Supervisor Configuration

import logging
import global_config
from datetime import time

# Process name
proc_mnemonic =                 'super'
proc_name =                     'super'
exe_file_name =                 ''.join((proc_name, '.py'))

# Log name
log_name =                      proc_name

# Logging
log_dir =                       global_config.field_log_dir
log_file_max_bytes =            50000
log_files_backup_files =        2

# Logging levels
#DEBUG | INFO | WARNING | ERROR | CRITICAL
log_level =                     logging.INFO

# Socket port numbers
base_port = global_config.super_base_port

console_port =                  base_port + 0
XMLRPC_port =                   base_port + 40
XMLRPC_URL =                    ''.join(('http://localhost:', str(XMLRPC_port)))

# Miscellaneous
accept_sigint =                 True
daemonize =                     False

# Temp file storage dir
temp_dir =                      ''.join((global_config.temp_dir, proc_name, '/'))

# XMLRPC connection timeout
xmlrpc_conn_timeout =           10

# GPS control
gps_max_sync_age =              3600

# Heater control
temp_default_setpoint =         -25.0
temp_hysteresis =               0.25

# Overtemp Protection
# CASES is powered down if overtemp.
# Temp is measured at router board.
cases_power_off_temp =          50.0
cases_power_on_temp =           45.0

# HF is powered down if overtemp.
# Temp is measured at router board.
hf_power_off_temp =             50.0
hf_power_on_temp =              45.0

# CASES Power Schedules
class cases_sched_item:
    def __init__(self, start_time_, stop_time_, data_limit_):
        self.start_time = start_time_
        self.stop_time = stop_time_
        self.data_limit = data_limit_
               
cases_storm_schedule = [cases_sched_item(time(1, 0, 0),  time(2, 0, 0),  100000000),
                        cases_sched_item(time(3, 0, 0),  time(4, 0, 0),  100000000),
                        cases_sched_item(time(5, 0, 0),  time(6, 0, 0),  100000000),
                        cases_sched_item(time(7, 0, 0),  time(8, 0, 0),  100000000),
                        cases_sched_item(time(9, 0, 0),  time(10, 0, 0),  100000000),
                        cases_sched_item(time(11, 0, 0),  time(12, 0, 0),  100000000),
                        cases_sched_item(time(13, 0, 0),  time(14, 0, 0),  100000000),
                        cases_sched_item(time(15, 0, 0),  time(16, 0, 0),  100000000),
                        cases_sched_item(time(17, 0, 0),  time(18, 0, 0),  100000000),
                        cases_sched_item(time(19, 0, 0),  time(20, 0, 0),  100000000),
                        cases_sched_item(time(21, 0, 0),  time(22, 0, 0),  100000000),
                        cases_sched_item(time(23, 0, 0),  time(0, 0, 0),  100000000)]

cases_normal_schedule =[cases_sched_item(time(1, 0, 0),  time(2, 0, 0),  4000000),
                        cases_sched_item(time(7, 0, 0),  time(8, 0, 0),  4000000),
                        cases_sched_item(time(13, 0, 0),  time(14, 0, 0),  4000000),
                        cases_sched_item(time(19, 0, 0),  time(20, 0, 0),  4000000)]

# Months that CASES should run
cases_window = [12, 1, 2, 3, 4]
                        
# HF Transceiver Power Schedule
class hf_sched_item:
    def __init__(self, start_time_, stop_time_):
        self.start_time = start_time_
        self.stop_time = stop_time_
        
power_on_minutes = 10
hf_schedule = [ hf_sched_item(time(0, 30, 0),  time(0, 30 + power_on_minutes, 0)),
                hf_sched_item(time(2, 30, 0),  time(2, 30 + power_on_minutes, 0)),
                hf_sched_item(time(4, 30, 0),  time(4, 30 + power_on_minutes, 0)),
                hf_sched_item(time(6, 30, 0),  time(6, 30 + power_on_minutes, 0)),
                hf_sched_item(time(8, 30, 0),  time(8, 30 + power_on_minutes, 0)),
                hf_sched_item(time(10, 30, 0),  time(10, 30 + power_on_minutes, 0)),
                hf_sched_item(time(12, 30, 0),  time(12, 30 + power_on_minutes, 0)),
                hf_sched_item(time(14, 30, 0),  time(14, 30 + power_on_minutes, 0)),
                hf_sched_item(time(16, 30, 0),  time(16, 30 + power_on_minutes, 0)),
                hf_sched_item(time(18, 30, 0),  time(18, 30 + power_on_minutes, 0)),
                hf_sched_item(time(20, 30, 0),  time(20, 30 + power_on_minutes, 0)),
                hf_sched_item(time(22, 30, 0),  time(22, 30 + power_on_minutes, 0))]

# RUDICS communication
comm_max_init_time =            60 * 180    # 1.5 hours
comm_max_down_time =            3600 * 2
comm_max_up_time =              3600 * 12
comm_low_power =                False

# Housekeeping storage parameters
hskp_temp_dir =                 ''.join([global_config.temp_dir, 'hskp/'])

# HW manager
hw_mgr_restart_timeout =        15

# HF Radio
hf_max_on_time =                60 * 30

# Iridium modem power control
data_xfer_timeout =             60 * 5

