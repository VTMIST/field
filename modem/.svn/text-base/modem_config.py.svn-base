# Iridium Modem Configuration

from datetime       import timedelta

import logging
import global_config

# Logging
log_dir =                   global_config.field_log_dir
log_file_max_bytes =        50000
log_files_backup_files =    1

# Log names
log_name_modem =            'modem'

# Logging levels
#DEBUG | INFO | WARNING | ERROR | CRITICAL
log_level =                 logging.INFO

# Iridium modem
rudics_phone_number =       '0088160000500'
lock_file_path =            '/var/lock/LCK..ttyS1'
connect_timeout =           timedelta(seconds=60)
read_timeout =              timedelta(seconds=15)
write_timeout =             timedelta(seconds=15)
serial_device =             '/dev/ttyS1'
baud_rate =                 19200
connect_tries =             2
