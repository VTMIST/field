# USB Manager Configuration

import logging
import global_config

# Process name
proc_mnemonic =                 'usb'
proc_name =                     'usb_mgr'
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
base_port = global_config.usb_mgr_base_port
console_port =                  base_port + 0
XMLRPC_port =                   base_port + 40
XMLRPC_URL =                    ''.join(('http://localhost:', str(XMLRPC_port)))

# Miscellaneous
accept_sigint =                 True
daemonize =                     False

# Temp file storage dir
temp_dir =                      ''.join((global_config.temp_dir, proc_name, '/'))

# USB Flash Drive
usb_flash_device_a =            '/dev/sda1'
usb_flash_device_b =            '/dev/sdb1'
usb_flash_device_c =            '/dev/sdc1'
usb_flash_dir =                 '/mnt/usbflash'
data_file_dir =                 'data'
usb_flash_data_dir =            ''.join((usb_flash_dir, '/', data_file_dir))
usb_power_up_timeout =          20

# gzip file compression level 1 to 10, ten is most compression (see gzip docs)
compression_level =             10
