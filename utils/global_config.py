# AAL-PIP Field Software Global Config

import os

# Software Version Number
sw_version_number = '8.12'

# If True modem is used for RUDICS connection.
# If False ethernet is used instead.
use_modem = True

# Remote system server port numbers.
# These are the localhost port numbers of
#  services on the remote system that are
#  accessible through the RUDICS connection.
SSH_server_port =           22
file_server_port =          37559

# Process base port numbers.
# Each process uses this port number to
#   calculate its console and XMLRPC server
#   port numbers
modem_svr_base_port =       26003
svr_proxy_base_port =       27003
fg_mgr_base_port =          28003
usb_mgr_base_port =         29003
sc_mgr_base_port =          30003
cases_mgr_base_port =       31003
hw_mgr_base_port =          32003
super_base_port =           33003

# Our LAN IP address.
# This address is used when the ethernet port
# is connected to a LAN
our_lan_ip_addr = '192.168.1.10'

# RUDICS server host address and port
#  This is the IP addr of the direct ethernet connection
#  to the the RUDICS server.
#  This address is used only for development.
rudics_host =               '192.168.1.50'  
rudics_port =               25000

# Default temporary file storage directory
temp_dir =                  '/tmp/'
flag_dir =                  '/var/log'

# Default log file directory
field_log_dir =             '/var/log'

# Field executables directory
field_bin_dir =             '/aal-pip/field/bin'

# Global value for sys.setcheckinterval()
check_interval =            25


